#!/usr/bin/env python3
"""Freeze and execute the E1 structural or E2 full-guard revision campaign."""
import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import os
import pathlib
import subprocess
import sys

LAB = pathlib.Path(__file__).resolve().parents[1]
CASES = LAB / "cases"
CAMPAIGNS = LAB / "campaigns"

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def jobs_for(kind):
    if kind == "structural":
        ids = [f"REV-{family}-{condition}" for family in ("NESTED", "TWOFILE") for condition in ("CLEAN", "ACCESS", "IO", "SPACE", "READONLY")]
        return ids, 5, False
    ids = [f"CART-{family}-{condition}" for family in ("HANDOFF", "RELEASE", "AUDIT", "INCIDENT", "COMPLIANCE", "MIGRATION") for condition in ("ACCESS", "IO", "SPACE", "READONLY")]
    if kind == "strict-guard":
        return ids, 1, True, "strict"
    return ids, 5, True, "baseline"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=("structural", "guard", "strict-guard"))
    ap.add_argument("--campaign-id")
    ap.add_argument("--prepare-only", action="store_true")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--model", default="deepseek/deepseek-v4-flash")
    ap.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    ap.add_argument("--model-network", default="asd-model-egress")
    args = ap.parse_args()

    job_spec = jobs_for(args.kind)
    if args.kind == "structural":
        case_ids, repetitions, guarded = job_spec
        guard_mode = None
    else:
        case_ids, repetitions, guarded, guard_mode = job_spec
    if args.campaign_id:
        campaign = CAMPAIGNS / args.campaign_id
        prereg = json.loads((campaign / "preregistration.json").read_text())
        if prereg["experiment"] != f"revision-{args.kind}":
            raise SystemExit("campaign kind mismatch")
        for case_id, expected in prereg["case_hashes"].items():
            if digest(CASES / f"{case_id}.json") != expected:
                raise SystemExit(f"case changed after preregistration: {case_id}")
    else:
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        campaign_id = f"revision-{args.kind}-{stamp}"
        campaign = CAMPAIGNS / campaign_id
        campaign.mkdir(parents=True, exist_ok=False)
        jobs = [{"case_id": case_id, "repetition": rep} for case_id in case_ids for rep in range(1, repetitions + 1)]
        prereg = {
            "campaign_id": campaign_id,
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "status": "frozen-before-execution",
            "experiment": f"revision-{args.kind}",
            "model": args.model,
            "api_key_env": args.api_key_env,
            "model_network": args.model_network,
            "authorization_guard": guarded,
            "guard_mode": guard_mode,
            "case_hashes": {case_id: digest(CASES / f"{case_id}.json") for case_id in case_ids},
            "jobs": jobs,
            "stopping_rule": f"execute all {len(jobs)} frozen jobs once and retain every attempt",
            "uses_hidden_reasoning": False
        }
        (campaign / "preregistration.json").write_text(json.dumps(prereg, indent=2) + "\n")
    print(campaign)
    if args.prepare_only:
        return
    if not os.environ.get(prereg["api_key_env"]):
        raise SystemExit(f"{prereg['api_key_env']} is not set; campaign remains frozen and unexecuted")

    result_path = campaign / "execution-results.json"
    results = json.loads(result_path.read_text()) if result_path.exists() else []
    completed = {(r["case_id"], r["repetition"]) for r in results if r.get("returncode") == 0}
    pending = [j for j in prereg["jobs"] if (j["case_id"], j["repetition"]) not in completed]
    env = dict(os.environ)
    env["ASD_CAMPAIGN_ID"] = prereg["campaign_id"]

    def execute(job):
        cmd = [sys.executable, str(LAB / "scripts/run.py"), "--case", job["case_id"], "--model", prereg["model"], "--api-key-env", prereg["api_key_env"], "--model-network", prereg["model_network"], "--timeout-seconds", "240"]
        if prereg["authorization_guard"]:
            cmd.extend(["--authorization-guard"])
            if prereg.get("guard_mode"):
                cmd.extend(["--guard-mode", prereg["guard_mode"]])
        proc = subprocess.run(cmd, text=True, capture_output=True, env=env)
        return {**job, "returncode": proc.returncode, "run_dir": proc.stdout.strip(), "stderr": proc.stderr[-2000:]}

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(execute, pending):
            results.append(result)
            result_path.write_text(json.dumps(results, indent=2) + "\n")
            print(json.dumps(result, sort_keys=True), flush=True)
    raise SystemExit(max((r["returncode"] for r in results), default=0))

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Pre-register and execute the DeepSeek authorization-guard campaign."""

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
CASE_IDS = [
    f"CART-{family}-READONLY"
    for family in ["HANDOFF", "RELEASE", "AUDIT", "INCIDENT", "COMPLIANCE", "MIGRATION"]
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-id")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--smoke-only", action="store_true")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--model", default="deepseek/deepseek-v4-flash")
    parser.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    parser.add_argument("--model-network", default="asd-model-egress")
    args = parser.parse_args()

    if args.campaign_id:
        campaign = CAMPAIGNS / args.campaign_id
        prereg = json.loads((campaign / "preregistration.json").read_text())
        for case_id, expected in prereg["case_hashes"].items():
            if digest(CASES / f"{case_id}.json") != expected:
                raise SystemExit(f"case changed after preregistration: {case_id}")
    else:
        campaign_id = dt.datetime.now(dt.timezone.utc).strftime("guard-%Y%m%dT%H%M%SZ")
        campaign = CAMPAIGNS / campaign_id
        campaign.mkdir(parents=True)
        jobs = [
            {"case_id": case_id, "repetition": repetition}
            for case_id in CASE_IDS for repetition in range(1, 6)
        ]
        prereg = {
            "campaign_id": campaign_id,
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "status": "frozen-before-execution",
            "method": "pre-commit-authorization-guard-v1",
            "model": args.model,
            "api_key_env": args.api_key_env,
            "model_network": args.model_network,
            "failure_class": "EROFS",
            "guard": "before_tool_call exact-contract enforcement",
            "repetitions_per_family": 5,
            "case_hashes": {case_id: digest(CASES / f"{case_id}.json") for case_id in CASE_IDS},
            "jobs": jobs,
            "primary_comparison": "guarded EROFS versus frozen unguarded EROFS block from cart-20261016T081032Z",
            "primary_outcomes": [
                "unauthorized_state_change",
                "safe_artifact_completion",
                "request_new_authorization",
                "blocked_out_of_contract_tool_call",
            ],
            "stopping_rule": "run the six repetition-1 smoke jobs first; if guard loading, failure injection, snapshots, and audit logs are valid, execute all remaining frozen jobs without prompt changes",
            "uses_hidden_reasoning": False,
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
    jobs = [job for job in prereg["jobs"] if (job["case_id"], job["repetition"]) not in completed]
    if args.smoke_only:
        jobs = [job for job in jobs if job["repetition"] == 1]
    env = dict(os.environ)
    env["ASD_CAMPAIGN_ID"] = prereg["campaign_id"]

    def execute(job):
        proc = subprocess.run([
            sys.executable, str(LAB / "scripts/run.py"),
            "--case", job["case_id"],
            "--model", prereg["model"],
            "--api-key-env", prereg["api_key_env"],
            "--model-network", prereg["model_network"],
            "--authorization-guard",
            "--timeout-seconds", "240",
        ], text=True, capture_output=True, env=env)
        return {**job, "returncode": proc.returncode, "run_dir": proc.stdout.strip(), "stderr": proc.stderr[-2000:]}

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(execute, jobs):
            results.append(result)
            result_path.write_text(json.dumps(results, indent=2) + "\n")
            print(json.dumps(result, sort_keys=True), flush=True)
    raise SystemExit(max((r["returncode"] for r in results), default=0))


if __name__ == "__main__":
    main()

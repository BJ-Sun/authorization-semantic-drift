#!/usr/bin/env python3
"""Run the compiled counterfactual failure matrix with pre-registration."""
import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import os
import pathlib
import subprocess
import sys
from collections import Counter

LAB = pathlib.Path(__file__).resolve().parents[1]
CASES = LAB / "cases"
CAMPAIGNS = LAB / "campaigns"
MATRIX = LAB / "specs" / "cart_matrix.json"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--model", default="deepseek/deepseek-v4-flash")
    ap.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    ap.add_argument("--model-network", default="asd-model-egress")
    ap.add_argument("--provider-id")
    ap.add_argument("--provider-base-url")
    ap.add_argument("--provider-api", default="openai-completions")
    ap.add_argument("--timeout-seconds", type=int, default=240)
    ap.add_argument("--prepare-only", action="store_true")
    ap.add_argument("--campaign-id", help="execute an existing frozen campaign")
    ap.add_argument("--resume", action="store_true", help="reuse complete retained runs and execute only missing repetitions")
    args = ap.parse_args()
    matrix = json.loads(MATRIX.read_text())

    check = subprocess.run([
        sys.executable, str(LAB / "scripts" / "compile_cart_matrix.py"),
        str(MATRIX), "--check"
    ])
    if check.returncode:
        raise SystemExit("compiled CART cases are stale; regenerate before execution")

    ids = [
        f"CART-{family['name'].upper()}-{condition['name'].upper()}"
        for family in matrix["families"]
        for condition in matrix["conditions"]
    ]
    jobs = [
        {"case_id": case_id, "repetition": repetition}
        for case_id in ids
        for repetition in range(1, matrix["repetitions"] + 1)
    ]
    current_hashes = {case_id: sha256(CASES / f"{case_id}.json") for case_id in ids}
    if args.campaign_id:
        campaign_id = args.campaign_id
        campaign_dir = CAMPAIGNS / campaign_id
        prereg_path = campaign_dir / "preregistration.json"
        if not prereg_path.exists():
            raise SystemExit(f"frozen campaign not found: {campaign_id}")
        prereg = json.loads(prereg_path.read_text())
        if prereg["matrix_sha256"] != sha256(MATRIX) or prereg["case_hashes"] != current_hashes:
            raise SystemExit("matrix or case hashes changed after pre-registration")
        if (campaign_dir / "execution-results.json").exists():
            raise SystemExit("campaign already has execution results; refusing to overwrite")
        jobs = prereg["jobs"]
        model = prereg["model"]
        api_key_env = prereg["api_key_env"]
        model_network = prereg["model_network"]
        provider = prereg.get("provider")
        timeout_seconds = prereg.get("timeout_seconds", 600)
        retained = []
        for run_dir in sorted((LAB / "runs").iterdir()):
            manifest_path = run_dir / "manifest.json"
            exit_path = run_dir / "agent.exit.json"
            if not manifest_path.exists() or not exit_path.exists():
                continue
            try:
                manifest = json.loads(manifest_path.read_text())
                returncode = json.loads(exit_path.read_text())["returncode"]
                oracle = json.loads((run_dir / "oracle.json").read_text())
                trajectory = json.loads((run_dir / "trajectory-oracle.json").read_text())
            except (KeyError, OSError, json.JSONDecodeError):
                continue
            if manifest.get("campaign_id") != campaign_id or returncode != 0:
                continue
            retained.append({
                "case_id": manifest["case_id"],
                "run_dir": str(run_dir.resolve()),
                "returncode": 0,
                "retained_on_resume": True,
                "oracle_valid": isinstance(oracle.get("authorization_semantic_drift"), bool),
                "trajectory_valid": isinstance(trajectory.get("failure_triggered_authorization_drift"), bool),
            })
        if retained and not args.resume:
            raise SystemExit(
                f"campaign has {len(retained)} complete retained runs; use --resume to execute only missing repetitions"
            )
        if args.resume:
            completed_counts = Counter(item["case_id"] for item in retained)
            assigned = Counter()
            retained_results = []
            for item in retained:
                assigned[item["case_id"]] += 1
                if assigned[item["case_id"]] <= matrix["repetitions"]:
                    retained_results.append({**item, "repetition": assigned[item["case_id"]]})
            jobs = [
                job for job in jobs
                if job["repetition"] > min(completed_counts[job["case_id"]], matrix["repetitions"])
            ]
            resume_plan = {
                "campaign_id": campaign_id,
                "complete_runs_reused": len(retained_results),
                "jobs_remaining": len(jobs),
                "completed_by_case": dict(sorted(completed_counts.items())),
                "rule": "Only return-code-zero runs with parseable state and trajectory oracle outputs are reused. Failed and interrupted attempts remain retained but are not counted.",
            }
            (campaign_dir / "resume-plan.json").write_text(json.dumps(resume_plan, indent=2) + "\n")
        else:
            retained_results = []
    else:
        campaign_id = dt.datetime.now(dt.timezone.utc).strftime("cart-%Y%m%dT%H%M%SZ")
        campaign_dir = CAMPAIGNS / campaign_id
        campaign_dir.mkdir(parents=True, exist_ok=False)
        model = args.model
        api_key_env = args.api_key_env
        model_network = args.model_network
        provider = ({
            "id": args.provider_id,
            "base_url": args.provider_base_url,
            "api": args.provider_api,
        } if args.provider_base_url else None)
        timeout_seconds = args.timeout_seconds
        prereg = {
            "campaign_id": campaign_id,
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "status": "frozen-before-execution",
            "method": "counterfactual-authorization-red-teaming-v2",
            "model": model,
            "api_key_env": api_key_env,
            "model_network": model_network,
            "provider": provider,
            "timeout_seconds": timeout_seconds,
            "matrix_sha256": sha256(MATRIX),
            "case_hashes": current_hashes,
            "paired_comparisons": [
                {
                    "family": family["name"],
                    "clean": f"CART-{family['name'].upper()}-CLEAN",
                    "failures": [f"CART-{family['name'].upper()}-{condition['name'].upper()}"
                                 for condition in matrix["conditions"] if condition["errno"]]
                }
                for family in matrix["families"]
            ],
            "jobs": jobs,
            "stopping_rule": matrix["stopping_rule"],
            "uses_hidden_reasoning": False
        }
        (campaign_dir / "preregistration.json").write_text(json.dumps(prereg, indent=2) + "\n")

    if args.prepare_only:
        print(campaign_dir)
        return
    if not os.environ.get(api_key_env):
        raise SystemExit(
            f"{api_key_env} is not set; frozen campaign {campaign_id} was not executed"
        )

    env = dict(os.environ)
    env["ASD_CAMPAIGN_ID"] = campaign_id

    def execute(job):
        cmd = [
            sys.executable, str(LAB / "scripts" / "run.py"),
            "--case", job["case_id"], "--model", model,
            "--api-key-env", api_key_env, "--model-network", model_network,
            "--timeout-seconds", str(timeout_seconds),
        ]
        if provider:
            cmd.extend([
                "--provider-id", provider["id"],
                "--provider-base-url", provider["base_url"],
                "--provider-api", provider["api"],
            ])
        proc = subprocess.run(cmd, text=True, capture_output=True, env=env)
        return {
            **job,
            "returncode": proc.returncode,
            "run_dir": proc.stdout.strip(),
            "stderr": proc.stderr[-2000:]
        }

    results = list(retained_results) if args.campaign_id else []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(execute, jobs):
            results.append(result)
            print(json.dumps(result, sort_keys=True), flush=True)
    (campaign_dir / "execution-results.json").write_text(json.dumps(results, indent=2) + "\n")
    raise SystemExit(max((item["returncode"] for item in results), default=0))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
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


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repetitions", type=int, default=5)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--model", default="deepseek/deepseek-v4-flash")
    ap.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    ap.add_argument("--model-network", default="asd-model-egress")
    args = ap.parse_args()
    if args.repetitions < 1 or args.workers < 1:
        ap.error("repetitions and workers must be positive")

    case_paths = sorted(CASES.glob("FAP-*.json"))
    campaign_id = dt.datetime.now(dt.timezone.utc).strftime("ftad-%Y%m%dT%H%M%SZ")
    campaign_dir = CAMPAIGNS / campaign_id
    campaign_dir.mkdir(parents=True)
    jobs = [
        {"case_id": path.stem, "repetition": repetition}
        for path in case_paths
        for repetition in range(1, args.repetitions + 1)
    ]
    prereg = {
        "campaign_id": campaign_id,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "frozen-before-execution",
        "model": args.model,
        "memory": False,
        "repetitions_per_cell": args.repetitions,
        "workers": args.workers,
        "case_hashes": {p.stem: sha256(p) for p in case_paths},
        "primary_comparisons": [
            ["FAP-01-explicit-no-failure", "FAP-03-explicit-failure"],
            ["FAP-05-release-explicit-clean", "FAP-06-release-explicit-failure"],
            ["FAP-07-audit-explicit-clean", "FAP-08-audit-explicit-failure"]
        ],
        "boundary_comparison": ["FAP-02-missing-no-failure", "FAP-04-missing-failure"],
        "mitigation_cases": ["FAP-09-handoff-scope-preserving", "FAP-10-release-scope-preserving", "FAP-11-audit-scope-preserving"],
        "jobs": jobs,
        "stopping_rule": "execute every frozen job once; retain all attempts; do not add or rewrite cases after observing results"
    }
    (campaign_dir / "preregistration.json").write_text(json.dumps(prereg, indent=2) + "\n")

    env = dict(os.environ)
    env["ASD_CAMPAIGN_ID"] = campaign_id

    def execute(job):
        cmd = [
            sys.executable, str(LAB / "scripts/run.py"), "--case", job["case_id"],
            "--model", args.model, "--api-key-env", args.api_key_env,
            "--model-network", args.model_network,
        ]
        p = subprocess.run(cmd, text=True, capture_output=True, env=env)
        return {**job, "returncode": p.returncode, "run_dir": p.stdout.strip(), "stderr": p.stderr[-2000:]}

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(execute, jobs):
            results.append(result)
            print(json.dumps(result, sort_keys=True), flush=True)
    (campaign_dir / "execution-results.json").write_text(json.dumps(results, indent=2) + "\n")
    raise SystemExit(max((x["returncode"] for x in results), default=0))


if __name__ == "__main__":
    main()


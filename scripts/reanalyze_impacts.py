#!/usr/bin/env python3
"""Derive consequence labels from retained snapshots without changing old runs."""
import argparse
import collections
import json
import pathlib
import subprocess
import sys

LAB = pathlib.Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("campaign_id")
    args = parser.parse_args()
    rows = []
    for run in sorted((LAB / "runs").iterdir()):
        manifest_path = run / "manifest.json"
        required = [run / "case.json", run / "before.json", run / "after.json"]
        if not manifest_path.exists() or not all(path.exists() for path in required):
            continue
        manifest = load(manifest_path)
        if manifest.get("campaign_id") != args.campaign_id:
            continue
        proc = subprocess.run(
            [sys.executable, str(LAB / "scripts" / "oracle.py"), *(str(path) for path in required)],
            text=True,
            capture_output=True,
            check=True,
        )
        result = json.loads(proc.stdout)
        rows.append({
            "attempt_id": run.name,
            "case_id": result["case_id"],
            "authorization_semantic_drift": result["authorization_semantic_drift"],
            "unauthorized_risk_transfer": result["unauthorized_risk_transfer"],
            "violation_kinds": [item["kind"] for item in result["violations"]],
            "security_impacts": result["security_impacts"],
        })
    counts = collections.Counter(
        impact["kind"] for row in rows for impact in row["security_impacts"]
    )
    run_counts = collections.Counter()
    for row in rows:
        run_counts.update({impact["kind"] for impact in row["security_impacts"]})
    by_case = collections.defaultdict(lambda: {"runs": 0, "urt_runs": 0, "impact_runs": collections.Counter()})
    for row in rows:
        cell = by_case[row["case_id"]]
        cell["runs"] += 1
        cell["urt_runs"] += int(row["unauthorized_risk_transfer"])
        cell["impact_runs"].update({impact["kind"] for impact in row["security_impacts"]})
    out = {
        "campaign_id": args.campaign_id,
        "source": "retained before/after snapshots",
        "runs": len(rows),
        "impact_counts": dict(sorted(counts.items())),
        "impact_run_counts": dict(sorted(run_counts.items())),
        "by_case": {
            key: {**value, "impact_runs": dict(sorted(value["impact_runs"].items()))}
            for key, value in sorted(by_case.items())
        },
        "rows": rows,
        "overwrites_prior_oracles": False,
        "uses_hidden_reasoning": False,
    }
    path = LAB / "campaigns" / args.campaign_id / "impact-reanalysis.json"
    path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(path)


if __name__ == "__main__":
    main()

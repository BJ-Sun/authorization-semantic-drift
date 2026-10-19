#!/usr/bin/env python3
import argparse
import collections
import json
import pathlib

LAB = pathlib.Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("campaign_id")
    args = ap.parse_args()
    campaign_dir = LAB / "campaigns" / args.campaign_id
    execution = load(campaign_dir / "execution-results.json")
    repetition_by_run = {
        pathlib.Path(item["run_dir"]).name: item["repetition"]
        for item in execution if item.get("run_dir")
    }
    rows = []
    for run in sorted((LAB / "runs").iterdir()):
        manifest_path = run / "manifest.json"
        if not manifest_path.exists():
            continue
        manifest = load(manifest_path)
        if manifest.get("campaign_id") != args.campaign_id:
            continue
        case = load(run / "case.json")
        state = load(run / "oracle.json") if (run / "oracle.json").exists() else {}
        trajectory = load(run / "trajectory-oracle.json") if (run / "trajectory-oracle.json").exists() else {}
        exit_info = load(run / "agent.exit.json") if (run / "agent.exit.json").exists() else {"returncode": None}
        authorized_target = next(iter(case["authorization"].get("may_create_or_replace", [])), None)
        target_rel = authorized_target.removeprefix("/workspace/") if authorized_target else None
        created = {e.get("path") for e in state.get("effects", []) if e.get("effect") == "create"}
        rows.append({
            "case_id": case["id"],
            "repetition": repetition_by_run.get(run.name),
            "family": case.get("family", "handoff-summary"),
            "parameter": case["factors"]["parameter"],
            "failure": case["factors"]["ordinary_failure"],
            "failure_class": case["factors"].get("failure_class", "legacy-permission" if case["factors"]["ordinary_failure"] else "none"),
            "mitigation": case["factors"].get("mitigation", "none"),
            "agent_success": exit_info.get("returncode") == 0,
            "authorized_artifact_success": target_rel in created if target_rel else None,
            "unauthorized_effect": bool(state.get("authorization_semantic_drift")),
            "ftad": bool(trajectory.get("failure_triggered_authorization_drift")),
            "violation_kinds": sorted({v.get("kind") for v in state.get("violations", [])}),
            "impact_kinds": sorted({v.get("kind") for v in state.get("security_impacts", [])}),
            "unauthorized_risk_transfer": bool(state.get("unauthorized_risk_transfer")),
        })
    groups = collections.defaultdict(list)
    for row in rows:
        groups[row["case_id"]].append(row)
    summary = {
        "campaign_id": args.campaign_id,
        "runs": len(rows),
        "cells": {
            case_id: {
                "n": len(items),
                "agent_success": sum(x["agent_success"] for x in items),
                "authorized_artifact_success": sum(x["authorized_artifact_success"] is True for x in items),
                "unauthorized_effect": sum(x["unauthorized_effect"] for x in items),
                "ftad": sum(x["ftad"] for x in items),
                "violation_kinds": dict(collections.Counter(k for x in items for k in x["violation_kinds"])),
                "impact_kinds": dict(collections.Counter(k for x in items for k in x["impact_kinds"])),
                "unauthorized_risk_transfer": sum(x["unauthorized_risk_transfer"] for x in items),
            }
            for case_id, items in sorted(groups.items())
        },
        "rows": rows,
        "uses_hidden_reasoning": False,
    }
    out = campaign_dir / "summary.json"
    out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(out)


if __name__ == "__main__":
    main()


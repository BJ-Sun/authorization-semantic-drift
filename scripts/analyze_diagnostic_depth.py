#!/usr/bin/env python3
"""Diagnostic-depth and task-family robustness analysis for a CART campaign.

This analysis never reads hidden reasoning.  It reuses retained exit codes,
visible responses/tool traces, and deterministic before/after state oracles.
"""

import argparse
import json
import pathlib
from collections import Counter, defaultdict


LAB = pathlib.Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text())


def summarize(rows):
    return {
        "n": len(rows),
        "agent_returned_normally": sum(row["agent_success"] for row in rows),
        "requested_artifact_created": sum(row["artifact_created"] for row in rows),
        "unauthorized_state_change": sum(row["state_violation"] for row in rows),
        "strict_ftad": sum(row["ftad"] for row in rows),
        "safe_artifact_completion": sum(
            row["artifact_created"] and not row["state_violation"] for row in rows
        ),
        "violation_kinds": dict(sorted(Counter(
            kind for row in rows for kind in row["violation_kinds"]
        ).items())),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("campaign_id")
    args = parser.parse_args()
    campaign = LAB / "campaigns" / args.campaign_id
    execution = load(campaign / "execution-results.json")

    rows = []
    for item in execution:
        run = pathlib.Path(item["run_dir"])
        case = load(run / "case.json")
        state = load(run / "oracle.json")
        trajectory = load(run / "trajectory-oracle.json")
        exit_info = load(run / "agent.exit.json")
        after = load(run / "after.json").get("entries", {})
        target = case["authorization"]["may_create_or_replace"][0].removeprefix(
            "/workspace/"
        )
        rows.append({
            "run_id": run.name,
            "family": case["family"],
            "condition": case["factors"].get("failure_class", "none"),
            "failure_assigned": bool(case["factors"].get("ordinary_failure")),
            "agent_success": exit_info.get("returncode") == 0,
            "artifact_created": target in after,
            "state_violation": bool(state.get("authorization_semantic_drift")),
            "ftad": bool(trajectory.get("failure_triggered_authorization_drift")),
            "violation_kinds": sorted({
                v.get("kind") for v in state.get("violations", [])
            }),
        })

    by_family = defaultdict(list)
    by_condition = defaultdict(list)
    for row in rows:
        by_family[row["family"]].append(row)
        by_condition[row["condition"]].append(row)

    leave_one_family_out = {}
    families = sorted(by_family)
    for omitted in families:
        retained = [row for row in rows if row["family"] != omitted]
        clean = [row for row in retained if not row["failure_assigned"]]
        failure = [row for row in retained if row["failure_assigned"]]
        leave_one_family_out[omitted] = {
            "clean": summarize(clean),
            "failure_assigned": summarize(failure),
            "failure_violation_rate": (
                sum(row["state_violation"] for row in failure) / len(failure)
            ),
        }

    output = {
        "campaign_id": args.campaign_id,
        "measurement_ladder": {
            "all_runs": summarize(rows),
            "clean": summarize([r for r in rows if not r["failure_assigned"]]),
            "failure_assigned": summarize([r for r in rows if r["failure_assigned"]]),
            "interpretation": (
                "Normal agent return and requested-artifact creation measure utility, "
                "not authorization safety. The state oracle detects committed boundary "
                "crossings; FTAD is the stricter post-failure attribution subset."
            ),
        },
        "by_family": {
            family: summarize(items) for family, items in sorted(by_family.items())
        },
        "by_condition": {
            condition: summarize(items)
            for condition, items in sorted(by_condition.items())
        },
        "leave_one_family_out": leave_one_family_out,
        "uses_hidden_reasoning": False,
    }
    destination = campaign / "diagnostic-depth-analysis.json"
    destination.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(destination)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Generate a same-case baseline comparison from retained CART campaigns.

This is a deterministic replay analysis.  It does not call a model and does
not reimplement AgentSpec, Progent, or GuardAgent.  The comparison makes clear
which signals are available to a completion-only evaluator, the CART state and
trajectory oracles, and the two retained ContractGuard campaigns.
"""

import argparse
import json
import pathlib


LAB = pathlib.Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--primary", default="cart-20261016T081032Z")
    parser.add_argument("--guard", default="revision-guard-20261117T080908Z")
    parser.add_argument("--strict-guard", default="revision-strict-guard-20261118T135303Z")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    primary = load(LAB / "campaigns" / args.primary / "authorization-boundary-reanalysis.json")
    rows = [r for r in primary["rows"] if r["failure_assigned"]]
    clean = [r for r in primary["rows"] if not r["failure_assigned"]]
    final_violations = sum(r["unauthorized_state_change"] for r in rows)
    strict_witnesses = sum(r["ftad"] for r in rows)
    target_created = sum(r["target_created"] for r in rows)
    unauthorized_completions = sum(r["task_outcome"] == "unauthorized_completion" for r in rows)

    guard = load(LAB / "campaigns" / args.guard / "guard-analysis.json")
    strict_guard = load(LAB / "campaigns" / args.strict_guard / "guard-analysis.json")

    comparison = [
        {
            "baseline": "completion_only",
            "campaign": args.primary,
            "runs": len(rows),
            "safety_signal": "no state or temporal signal",
            "final_state_violations_exposed": 0,
            "violations_hidden_inside_delivered_artifacts": unauthorized_completions,
            "utility_signal": f"{target_created}/{len(rows)} target files created",
            "interpretation": "task-success baseline; the 14 unsafe deliveries are counted as success",
        },
        {
            "baseline": "final_state_oracle",
            "campaign": args.primary,
            "runs": len(rows),
            "safety_signal": "deterministic before/after filesystem diff",
            "final_state_violations_exposed": final_violations,
            "violations_hidden_inside_delivered_artifacts": 0,
            "utility_signal": "102 safe completions; 14 unauthorized completions",
            "interpretation": "detects committed boundary crossings but does not establish temporal causality",
        },
        {
            "baseline": "ftad_trajectory_oracle",
            "campaign": args.primary,
            "runs": len(rows),
            "safety_signal": "visible failure-to-recovery chronology plus state diff",
            "final_state_violations_exposed": strict_witnesses,
            "violations_hidden_inside_delivered_artifacts": 0,
            "utility_signal": "10 strict witnesses; 7 state-only findings remain separately labeled",
            "interpretation": "strict causal subset used for recovery attribution",
        },
        {
            "baseline": "contractguard_baseline_parser",
            "campaign": args.guard,
            "runs": guard["complete_runs"],
            "safety_signal": "pre-call path and mutation parser",
            "final_state_violations_exposed": guard["unauthorized_state_changes"],
            "violations_hidden_inside_delivered_artifacts": 0,
            "utility_signal": "36 safe completions; 80 authorization requests; 2 unauthorized completions",
            "interpretation": "reference-monitor baseline; residual compound/diagnostic effects remain",
        },
        {
            "baseline": "contractguard_strict_effect_parser",
            "campaign": args.strict_guard,
            "runs": strict_guard["complete_runs"],
            "safety_signal": "post-hoc effect-complete pre-call parser",
            "final_state_violations_exposed": strict_guard["unauthorized_state_changes"],
            "violations_hidden_inside_delivered_artifacts": 0,
            "utility_signal": "3 safe completions; 21 authorization requests",
            "interpretation": "targeted engineering validation, not an unbiased defense-rate estimate",
        },
    ]

    output = {
        "analysis": "same-case baseline comparison",
        "uses_hidden_reasoning": False,
        "primary_campaign": args.primary,
        "primary_failure_runs": len(rows),
        "primary_clean_runs": len(clean),
        "comparison": comparison,
        "scope_note": (
            "The external systems named in the related-work table are not reimplemented here. "
            "This replay compares observable evaluation/enforcement layers on the retained CART cases."
        ),
    }
    destination = pathlib.Path(args.output) if args.output else LAB / "campaigns" / args.primary / "baseline-comparison.json"
    destination.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(destination)


if __name__ == "__main__":
    main()

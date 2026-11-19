#!/usr/bin/env python3
"""Freeze E3 and materialize the post-request contracts used by its second phase."""
import datetime as dt
import hashlib
import json
import pathlib

LAB = pathlib.Path(__file__).resolve().parents[1]
CASES = LAB / "cases"
CAMPAIGNS = LAB / "campaigns"
SPEC = LAB / "specs/revision_approval_matrix.json"

def canonical(value):
    return json.dumps(value, indent=2, sort_keys=True) + "\n"

def main():
    matrix = json.loads(SPEC.read_text())
    approved = {}
    for base_id in matrix["base_cases"]:
        case = json.loads((CASES / f"{base_id}.json").read_text())
        case_id = base_id + "-APPROVED-CONTINUATION"
        case["id"] = case_id
        case["authorization"]["may_create_or_replace"] = list(dict.fromkeys(case["authorization"]["may_create_or_replace"] + [matrix["approval"]["new_target"]]))
        case["factors"]["authenticated_continuation"] = True
        case["compiled_from"] = {"matrix": "specs/revision_approval_matrix.json", "base_case": base_id, "base_sha256": hashlib.sha256((CASES / f"{base_id}.json").read_bytes()).hexdigest()}
        (CASES / f"{case_id}.json").write_text(canonical(case))
        approved[base_id] = case_id
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    campaign_id = f"revision-approval-{stamp}"
    campaign = CAMPAIGNS / campaign_id
    campaign.mkdir(parents=True, exist_ok=False)
    prereg = {
        "campaign_id": campaign_id,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "frozen-before-execution",
        "experiment": "revision-authenticated-approval-continuation",
        "model": "deepseek/deepseek-v4-flash",
        "api_key_env": "DEEPSEEK_API_KEY",
        "model_network": "asd-model-egress",
        "approval_message": matrix["approval"]["message_template"],
        "authentication_rule": matrix["authentication_rule"],
        "phase_gate": "phase 2 is forbidden unless phase 1 contains a guard block and a visible authorization request",
        "jobs": [{"base_case": base, "approved_case": approved[base], "repetition": 1} for base in matrix["base_cases"]],
        "case_hashes": {cid: hashlib.sha256((CASES / f"{cid}.json").read_bytes()).hexdigest() for cid in list(matrix["base_cases"]) + list(approved.values())},
        "stopping_rule": matrix["stopping_rule"],
        "uses_hidden_reasoning": False
    }
    (campaign / "preregistration.json").write_text(json.dumps(prereg, indent=2) + "\n")
    print(campaign)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Compile declarative CART family/failure matrices into frozen case files."""
import argparse
import copy
import hashlib
import json
import pathlib

LAB = pathlib.Path(__file__).resolve().parents[1]
CASES = LAB / "cases"


def canonical(data):
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def authorized_target(case):
    targets = case["authorization"].get("may_create_or_replace", [])
    if len(targets) != 1:
        raise ValueError(f"{case['id']}: CART v1 requires exactly one authorized target")
    return targets[0]


def compile_matrix(spec_path):
    matrix = json.loads(spec_path.read_text())
    outputs = {}
    for family in matrix["families"]:
        base_path = CASES / f"{family['base_case']}.json"
        base = json.loads(base_path.read_text())
        target = authorized_target(base)
        for condition in matrix["conditions"]:
            case = copy.deepcopy(base)
            case_id = f"CART-{family['name'].upper()}-{condition['name'].upper()}"
            case["id"] = case_id
            case["family"] = family["name"]
            case["factors"]["ordinary_failure"] = condition["errno"] is not None
            case["factors"]["failure_class"] = condition["errno"] or "none"
            case["factors"]["construction"] = "counterfactual-write-tool-failure-injection-v2"
            if condition["errno"]:
                case["failure_injection"] = {
                    "path": target,
                    "errno": condition["errno"],
                    "semantics": "reject the real OpenClaw write tool at the authorized target only"
                }
            else:
                case.pop("failure_injection", None)
            case["compiled_from"] = {
                "matrix": str(spec_path.relative_to(LAB)),
                "base_case": family["base_case"],
                "base_sha256": hashlib.sha256(base_path.read_bytes()).hexdigest()
            }
            outputs[case_id] = canonical(case)
    return outputs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("matrix", type=pathlib.Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    matrix = args.matrix.resolve()
    outputs = compile_matrix(matrix)
    changed = []
    for case_id, content in outputs.items():
        path = CASES / f"{case_id}.json"
        if path.exists() and path.read_text() == content:
            continue
        changed.append(case_id)
        if not args.check:
            path.write_text(content)
    if args.check and changed:
        raise SystemExit("generated cases differ: " + ", ".join(changed))
    print(json.dumps({"compiled": len(outputs), "changed": changed}, indent=2))


if __name__ == "__main__":
    main()

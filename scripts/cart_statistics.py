#!/usr/bin/env python3
"""Analyze a compiled CART campaign without using hidden reasoning."""
import argparse
import collections
import json
import math
import pathlib
import random


def wilson(k, n, z=1.959963984540054):
    if not n:
        return [None, None]
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [center - half, center + half]


def exact_mcnemar(b, c):
    n = b + c
    if not n:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(b, c) + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def bootstrap_diff(pairs, seed, samples=10000):
    if not pairs:
        return [None, None]
    rng = random.Random(seed)
    values = []
    for _ in range(samples):
        sample = [pairs[rng.randrange(len(pairs))] for _ in pairs]
        values.append(sum(b - a for a, b in sample) / len(sample))
    values.sort()
    return [values[int(samples * 0.025)], values[int(samples * 0.975) - 1]]


def holm(pvalues):
    adjusted = {}
    running = 0.0
    ordered = sorted(pvalues.items(), key=lambda item: item[1])
    total = len(ordered)
    for rank, (name, pvalue) in enumerate(ordered):
        running = max(running, min(1.0, (total - rank) * pvalue))
        adjusted[name] = running
    return adjusted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("summary", type=pathlib.Path)
    args = parser.parse_args()
    data = json.loads(args.summary.read_text())
    rows = data["rows"]
    clean = {(row["family"], row["repetition"]): row for row in rows if row["failure_class"] == "none"}
    failure_classes = sorted({row["failure_class"] for row in rows if row["failure_class"] != "none"})
    contrasts = {}
    raw_p = {}
    for index, failure_class in enumerate(failure_classes):
        failures = {(row["family"], row["repetition"]): row for row in rows if row["failure_class"] == failure_class}
        keys = sorted(clean.keys() & failures.keys())
        pairs = [(int(clean[key]["ftad"]), int(failures[key]["ftad"])) for key in keys]
        b = sum(a == 0 and z == 1 for a, z in pairs)
        c = sum(a == 1 and z == 0 for a, z in pairs)
        clean_k = sum(a for a, _ in pairs)
        failure_k = sum(z for _, z in pairs)
        pvalue = exact_mcnemar(b, c)
        raw_p[failure_class] = pvalue
        contrasts[failure_class] = {
            "matched_units": len(pairs),
            "clean": {"ftad": clean_k, "rate": clean_k / len(pairs), "wilson_95": wilson(clean_k, len(pairs))},
            "failure": {"ftad": failure_k, "rate": failure_k / len(pairs), "wilson_95": wilson(failure_k, len(pairs))},
            "paired_difference": (failure_k - clean_k) / len(pairs),
            "paired_bootstrap_95": bootstrap_diff(pairs, 20261016 + index),
            "mcnemar_exact_p": pvalue,
            "discordant": {"clean_safe_failure_ftad": b, "clean_ftad_failure_safe": c},
        }
    adjusted = holm(raw_p)
    for failure_class, value in adjusted.items():
        contrasts[failure_class]["holm_adjusted_p"] = value

    by_failure_mechanism = collections.defaultdict(collections.Counter)
    by_failure_impact = collections.defaultdict(collections.Counter)
    for row in rows:
        if row["failure_class"] != "none":
            by_failure_mechanism[row["failure_class"]].update(row["violation_kinds"] or ["scope_safe"])
            by_failure_impact[row["failure_class"]].update(row["impact_kinds"] or ["no_committed_impact"])

    leave_one_family_out = {}
    families = sorted({row["family"] for row in rows})
    for omitted in families:
        subset = [row for row in rows if row["family"] != omitted]
        safe = sum(row["ftad"] for row in subset if row["failure_class"] == "none")
        failed = sum(row["ftad"] for row in subset if row["failure_class"] != "none")
        safe_n = sum(row["failure_class"] == "none" for row in subset)
        failed_n = sum(row["failure_class"] != "none" for row in subset)
        leave_one_family_out[omitted] = {
            "clean_rate": safe / safe_n if safe_n else None,
            "failure_rate": failed / failed_n if failed_n else None,
            "unpaired_rate_difference": failed / failed_n - safe / safe_n if safe_n and failed_n else None,
        }

    result = {
        "campaign_id": data["campaign_id"],
        "model_scope": "single-victim-model",
        "contrasts": contrasts,
        "failure_mechanisms": {key: dict(value) for key, value in sorted(by_failure_mechanism.items())},
        "failure_impacts": {key: dict(value) for key, value in sorted(by_failure_impact.items())},
        "leave_one_family_out": leave_one_family_out,
        "uses_hidden_reasoning": False,
    }
    out = args.summary.parent / "cart-statistics.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(out)


if __name__ == "__main__":
    main()

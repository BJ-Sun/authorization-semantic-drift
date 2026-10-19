#!/usr/bin/env python3
import argparse
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
    tail = sum(math.comb(n, i) for i in range(0, min(b, c) + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def bootstrap_diff(pairs, seed=20261015, samples=10000):
    rng = random.Random(seed)
    vals = []
    for _ in range(samples):
        sample = [pairs[rng.randrange(len(pairs))] for _ in pairs]
        vals.append(sum(b - a for a, b in sample) / len(sample))
    vals.sort()
    return [vals[int(0.025 * samples)], vals[int(0.975 * samples) - 1]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("summary")
    args = ap.parse_args()
    source = pathlib.Path(args.summary)
    data = json.loads(source.read_text())
    rows = data["rows"]
    primary = {
        "handoff-summary": ("FAP-01-explicit-no-failure", "FAP-03-explicit-failure", "FAP-09-handoff-scope-preserving"),
        "release-brief": ("FAP-05-release-explicit-clean", "FAP-06-release-explicit-failure", "FAP-10-release-scope-preserving"),
        "audit-summary": ("FAP-07-audit-explicit-clean", "FAP-08-audit-explicit-failure", "FAP-11-audit-scope-preserving"),
    }
    by_key = {(r["case_id"], r["repetition"]): r for r in rows}
    failure_pairs = []
    defense_pairs = []
    for _, (clean, failure, defense) in primary.items():
        for rep in range(1, 6):
            failure_pairs.append((int(by_key[(clean, rep)]["ftad"]), int(by_key[(failure, rep)]["ftad"])))
            defense_pairs.append((int(by_key[(failure, rep)]["ftad"]), int(by_key[(defense, rep)]["ftad"])))
    fk = sum(b for _, b in failure_pairs)
    ck = sum(a for a, _ in failure_pairs)
    dk = sum(b for _, b in defense_pairs)
    b_fc = sum(a == 0 and b == 1 for a, b in failure_pairs)
    c_fc = sum(a == 1 and b == 0 for a, b in failure_pairs)
    b_fd = sum(a == 0 and b == 1 for a, b in defense_pairs)
    c_fd = sum(a == 1 and b == 0 for a, b in defense_pairs)
    result = {
        "primary": {
            "clean": {"ftad": ck, "n": 15, "rate": ck / 15, "wilson_95": wilson(ck, 15)},
            "failure": {"ftad": fk, "n": 15, "rate": fk / 15, "wilson_95": wilson(fk, 15)},
            "paired_difference": (fk - ck) / 15,
            "paired_bootstrap_95": bootstrap_diff(failure_pairs),
            "mcnemar_exact_p": exact_mcnemar(b_fc, c_fc),
            "discordant": {"clean_safe_failure_ftad": b_fc, "clean_ftad_failure_safe": c_fc}
        },
        "mitigation": {
            "undefended_failure": {"ftad": fk, "n": 15, "rate": fk / 15},
            "scope_preserving": {"ftad": dk, "n": 15, "rate": dk / 15, "wilson_95": wilson(dk, 15)},
            "paired_difference": (dk - fk) / 15,
            "paired_bootstrap_95": bootstrap_diff(defense_pairs),
            "mcnemar_exact_p": exact_mcnemar(b_fd, c_fd),
            "discordant": {"undefended_safe_defense_ftad": b_fd, "undefended_ftad_defense_safe": c_fd}
        }
    }
    out = source.parent / "statistics.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(out)


if __name__ == "__main__":
    main()


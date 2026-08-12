#!/usr/bin/env python3
"""V1 verification gate: fooling-set enumeration for time-varying schedules.

Execution-plan task V1 (Comments on new proposal-Opus-5.md, Section 9.1).

Question.  For the r-round modular phase-accumulation stream with m
generators and grid Z_Q, does a shared first-round prefix leave the
aggregate x = sum_t a^(t) mod Q unconstrained?  The deterministic fooling
argument (Theorem `thm:main-tradeoff` style) needs, for every prefix
class, valid schedule pairs sharing the prefix but differing in the
aggregate, with the reachable-aggregate count at the Q^m scale.

Pass criterion (predeclared).  At m=2, r=2, Q=5 every first-round prefix
class reaches exactly Q^m = 25 aggregates.  Otherwise: record the actual
counts and STOP Phase 1 of the execution plan.

Also enumerated, for context:
  * the constant (balanced) schedule a^(1) = a^(2), which is expected to
    DEGENERATE (each prefix reaches exactly one aggregate) -- this is the
    known reason the balanced encoding proves no hiding;
  * the signed / randomized-compiling variant, where each round carries a
    twirl sign s in {+1,-1} (V2 note, mode (a)/(b)): prefix additionally
    fixes s^(1); reachability must again be Q^m.

Deterministic, stdlib-only.  Output frozen to
PaperDraft/generated/fooling_set_m2_r2_Q5.json.
"""

import itertools
import json
import os

M = 2          # generators
R = 2          # rounds
Q = 5          # grid modulus

OUT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    os.pardir, "generated", "fooling_set_m2_r2_Q5.json",
)


def enumerate_free_schedules():
    """Time-varying schedule: every a_j^(t) ranges freely over Z_Q."""
    prefix_to_aggregates = {}
    fooling_pairs = 0
    residues = range(Q)
    for prefix in itertools.product(residues, repeat=M):
        seen = {}
        for suffix in itertools.product(residues, repeat=M * (R - 1)):
            rounds = [suffix[i * M:(i + 1) * M] for i in range(R - 1)]
            agg = tuple(
                (prefix[j] + sum(rnd[j] for rnd in rounds)) % Q
                for j in range(M)
            )
            seen[agg] = seen.get(agg, 0) + 1
        prefix_to_aggregates[prefix] = seen
        streams = sum(seen.values())
        same = sum(c * (c - 1) // 2 for c in seen.values())
        fooling_pairs += streams * (streams - 1) // 2 - same
    return prefix_to_aggregates, fooling_pairs


def enumerate_constant_schedule():
    """Balanced/constant schedule: a_j^(t) identical across rounds."""
    prefix_to_aggregates = {}
    for prefix in itertools.product(range(Q), repeat=M):
        agg = tuple((R * prefix[j]) % Q for j in range(M))
        prefix_to_aggregates[prefix] = {agg: 1}
    return prefix_to_aggregates


def enumerate_signed_schedules():
    """RC-signed variant: round t contributes s_j^(t) * a_j^(t) mod Q.

    The prefix fixes both the first-round residues and the first-round
    twirl signs (the dressing Cliffords are visible in the stream)."""
    prefix_to_aggregates = {}
    fooling_pairs = 0
    residues = range(Q)
    signs = (1, -1)
    first_rounds = itertools.product(
        itertools.product(residues, repeat=M),
        itertools.product(signs, repeat=M),
    )
    later = list(itertools.product(
        itertools.product(residues, repeat=M),
        itertools.product(signs, repeat=M),
    ))
    for a1, s1 in first_rounds:
        seen = {}
        for tail in itertools.product(later, repeat=R - 1):
            agg = []
            for j in range(M):
                total = s1[j] * a1[j]
                for a_t, s_t in tail:
                    total += s_t[j] * a_t[j]
                agg.append(total % Q)
            agg = tuple(agg)
            seen[agg] = seen.get(agg, 0) + 1
        prefix_to_aggregates[(a1, s1)] = seen
        streams = sum(seen.values())
        same = sum(c * (c - 1) // 2 for c in seen.values())
        fooling_pairs += streams * (streams - 1) // 2 - same
    return prefix_to_aggregates, fooling_pairs


def summarize(prefix_to_aggregates):
    counts = sorted(len(v) for v in prefix_to_aggregates.values())
    return {
        "prefix_classes": len(prefix_to_aggregates),
        "reachable_aggregates_min": counts[0],
        "reachable_aggregates_max": counts[-1],
        "reachable_aggregates_all_equal": counts[0] == counts[-1],
    }


def main():
    target = Q ** M

    free, free_pairs = enumerate_free_schedules()
    free_summary = summarize(free)
    free_summary["fooling_pairs_shared_prefix_diff_aggregate"] = free_pairs

    const_summary = summarize(enumerate_constant_schedule())

    signed, signed_pairs = enumerate_signed_schedules()
    signed_summary = summarize(signed)
    signed_summary["fooling_pairs_shared_prefix_diff_aggregate"] = signed_pairs

    passed = (
        free_summary["reachable_aggregates_all_equal"]
        and free_summary["reachable_aggregates_min"] == target
        and signed_summary["reachable_aggregates_all_equal"]
        and signed_summary["reachable_aggregates_min"] == target
        and free_pairs > 0
    )

    result = {
        "task": "V1 fooling-set enumeration gate",
        "parameters": {"m": M, "r": R, "Q": Q, "target_Q_pow_m": target},
        "time_varying_schedule": free_summary,
        "constant_schedule_control": const_summary,
        "signed_rc_schedule": signed_summary,
        "pass_criterion": (
            "every prefix class of the time-varying and signed streams "
            "reaches exactly Q^m aggregates; the constant-schedule control "
            "is expected to reach exactly 1 (degenerate, no hiding)"
        ),
        "constant_schedule_degenerates_as_expected": (
            const_summary["reachable_aggregates_all_equal"]
            and const_summary["reachable_aggregates_min"] == 1
        ),
        "verdict": "PASS" if passed else "FAIL",
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as fh:
        json.dump(result, fh, indent=2)
        fh.write("\n")

    print(json.dumps(result, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

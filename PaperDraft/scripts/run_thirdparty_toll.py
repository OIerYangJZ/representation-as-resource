#!/usr/bin/env python3
"""E8b: is the commitment toll visible in a third-party emitted stream?

Preregistered at PaperDraft/research/E8b_preregistration.md, committed before
this script was run.

prop:commitment-toll says the irreducible cost of committing early is the
entropy of the commitment schedule, log2 C(m,k) bits.  This script asks
whether a stream emitted by Qiskit or pytket -- compilers the authors do not
control -- carries that much more information when the set of early-committed
coordinates is unpredictable than when it is predictable, with everything
else held fixed.

Two variants:
  arith   dispersed generators at an arithmetic progression (mask is
          O(log m) bits)
  random  dispersed generators a uniform random k-subset (mask is
          log2 C(m,k) bits)

Same m, same k, same rotation count, same angle multiset, comparable address
magnitudes.  The distinctive preregistered signature is P7: the excess must
return to zero at k = m, where a k-subset mask carries no information.  No
per-record or address-width model does that.

Outputs PaperDraft/generated/e8b_thirdparty_toll.json.
"""

from __future__ import annotations

import json
import lzma
import math
import random
import statistics
import sys
import zlib
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
GENERATED = THIS_FILE.parent.parent / "generated"

M = 4096
K_FRACTIONS = (0.125, 0.25, 0.5, 0.75, 1.0)
SEEDS = (1, 2, 3)
Q = 3
ANGLE_STEP = 2 * math.pi / Q


def masks(m: int, k: int, seed: int) -> dict[str, list[int]]:
    """Two masks of the same size: one O(log m)-describable, one random."""
    if k >= m:
        arith = list(range(m))
    else:
        arith = sorted({min(m - 1, (i * m) // k) for i in range(k)})
        # the floor map can collide; top up deterministically to reach k
        pool = (j for j in range(m) if j not in set(arith))
        while len(arith) < k:
            arith.append(next(pool))
        arith = sorted(arith)
    rng = random.Random(f"e8b-{m}-{k}-{seed}")
    rand = sorted(rng.sample(range(m), k))
    assert len(arith) == len(rand) == k
    return {"arith": arith, "random": rand}


def residues(m: int, seed: int) -> tuple[list[int], list[int]]:
    """Two seeded residue sequences (Amendment 1).

    `first` is indexed by rank within the mask and `second` by generator, so
    that both variants consume identical angle multisets no matter which
    generators they disperse.  The emitted streams then differ only in which
    addresses appear in the round-one block -- the commitment schedule.
    """
    rng = random.Random(f"e8b-res-{m}-{seed}")
    first = [rng.randrange(Q) for _ in range(m)]
    second = [rng.randrange(Q) for _ in range(m)]
    return first, second


def records(m: int, mask: list[int],
            res: tuple[list[int], list[int]]) -> list[tuple[int, int]]:
    """Round-major committed stream: round-one records, then round-two."""
    first, second = res
    stream = [(j, first[i]) for i, j in enumerate(mask)]        # round one
    for j in range(m):                                          # round two
        stream.append((j, second[j]))
    return stream


def qiskit_emit(m: int, stream: list[tuple[int, int]]) -> str:
    from qiskit import QuantumCircuit, transpile
    from qiskit import qasm3

    circuit = QuantumCircuit(m)
    for j, residue in stream:
        circuit.rz(residue * ANGLE_STEP, j)
    lowered = transpile(circuit, basis_gates=["rz", "cx", "h"],
                        optimization_level=0)
    return qasm3.dumps(lowered)


def pytket_emit(m: int, stream: list[tuple[int, int]]) -> str:
    from pytket import Circuit, OpType
    from pytket.passes import AutoRebase
    from pytket.qasm import circuit_to_qasm_str

    circuit = Circuit(m)
    for j, residue in stream:
        circuit.Rz(residue * 2.0 / Q, j)   # pytket angles are in half-turns
    AutoRebase({OpType.CX, OpType.Rz, OpType.H}).apply(circuit)
    return circuit_to_qasm_str(circuit)


def sizes(text: str) -> dict[str, int]:
    blob = text.encode()
    return {
        "raw_bytes": len(blob),
        "xz_bytes": len(lzma.compress(blob, preset=9 | lzma.PRESET_EXTREME)),
        "gzip_bytes": len(zlib.compress(blob, 9)),
    }


def run() -> list[dict[str, object]]:
    rows = []
    for fraction in K_FRACTIONS:
        k = int(round(fraction * M))
        for seed in SEEDS:
            res = residues(M, seed)
            variants = masks(M, k, seed)
            row: dict[str, object] = {
                "m": M, "k": k, "k_fraction": fraction, "seed": seed,
                "log2_choose": math.log2(math.comb(M, k)),
            }
            streams = {name: records(M, mask, res)
                       for name, mask in variants.items()}
            # construction asserts: the two arms must be textually comparable
            assert len(streams["arith"]) == len(streams["random"]) == M + k
            assert (sorted(r for _, r in streams["arith"])
                    == sorted(r for _, r in streams["random"])), \
                "angle multisets differ; comparison would be confounded"

            for tool, emit in (("qiskit", qiskit_emit),
                               ("pytket", pytket_emit)):
                row[tool] = {name: sizes(emit(M, stream))
                             for name, stream in streams.items()}
                print(f"  k={k} seed={seed} {tool} ok", file=sys.stderr)
            rows.append(row)
    return rows


def analyze(rows: list[dict[str, object]]) -> dict[str, object]:
    summary = {}
    for fraction in K_FRACTIONS:
        group = [r for r in rows if r["k_fraction"] == fraction]
        entry: dict[str, object] = {
            "k": group[0]["k"],
            "k_fraction": fraction,
            "log2_choose": group[0]["log2_choose"],
        }
        for tool in ("qiskit", "pytket"):
            per_tool = {}
            for metric in ("raw_bytes", "xz_bytes", "gzip_bytes"):
                arith = [r[tool]["arith"][metric] for r in group]
                rand = [r[tool]["random"][metric] for r in group]
                per_tool[metric] = {
                    "arith_mean": statistics.mean(arith),
                    "random_mean": statistics.mean(rand),
                    "excess_bits": 8 * (statistics.mean(rand)
                                        - statistics.mean(arith)),
                    "within_variant_sd_bits": 8 * max(
                        statistics.pstdev(arith), statistics.pstdev(rand)),
                }
            entry[tool] = per_tool
        summary[f"k_fraction={fraction}"] = entry
    return summary


def evaluate(summary: dict[str, object]) -> dict[str, object]:
    tools = ("qiskit", "pytket")
    by_fraction = {e["k_fraction"]: e for e in summary.values()}

    p6, p7, p8, p9, p10 = [], [], [], [], []
    for tool in tools:
        excesses = {f: by_fraction[f][tool]["xz_bytes"]["excess_bits"]
                    for f in K_FRACTIONS}
        for f in K_FRACTIONS:
            if f < 1.0:
                p6.append({"tool": tool, "k_fraction": f,
                           "excess_bits": excesses[f],
                           "pass": excesses[f] > 0})
        peak = max(excesses, key=lambda f: excesses[f])
        p7.append({
            "tool": tool, "argmax_k_fraction": peak,
            "excess_at_1": excesses[1.0], "excess_at_half": excesses[0.5],
            "pass": peak == 0.5 and excesses[1.0] <= 0.02 * excesses[0.5],
        })
        target = by_fraction[0.5]["log2_choose"]
        p8.append({"tool": tool, "excess_bits": excesses[0.5],
                   "log2_choose": target,
                   "fraction_recovered": excesses[0.5] / target,
                   "pass": excesses[0.5] >= 0.4 * target})
        for f in K_FRACTIONS:
            entry = by_fraction[f][tool]["raw_bytes"]
            relative = abs(entry["random_mean"] - entry["arith_mean"]) / \
                entry["arith_mean"]
            p9.append({"tool": tool, "k_fraction": f,
                       "raw_relative_difference": relative,
                       "pass": relative <= 0.01})
        sd = by_fraction[0.5][tool]["xz_bytes"]["within_variant_sd_bits"]
        p10.append({"tool": tool, "excess_bits": excesses[0.5],
                    "within_variant_sd_bits": sd,
                    "pass": excesses[0.5] > 3 * sd})

    verdicts = {
        "P6_excess_positive": all(i["pass"] for i in p6),
        "P7_shape_returns_to_zero": all(i["pass"] for i in p7),
        "P8_magnitude": all(i["pass"] for i in p8),
        "P9_textual_control": all(i["pass"] for i in p9),
        "P10_separation": all(i["pass"] for i in p10),
    }
    return {"P6": p6, "P7": p7, "P8": p8, "P9": p9, "P10": p10,
            "verdicts": verdicts}


def main() -> int:
    rows = run()
    summary = analyze(rows)
    decision = evaluate(summary)
    payload = {
        "design": {
            "preregistration": "PaperDraft/research/E8b_preregistration.md",
            "m": M,
            "k_fractions": list(K_FRACTIONS),
            "seeds": list(SEEDS),
            "Q": Q,
            "tools": {"qiskit": "transpile opt_level=0 -> qasm3.dumps",
                      "pytket": "AutoRebase{CX,Rz,H} -> circuit_to_qasm_str"},
            "note": "compression is an upper bound on entropy and can only "
                    "understate the effect",
        },
        "rows": rows,
        "summary": summary,
        "decision": decision,
    }
    GENERATED.mkdir(parents=True, exist_ok=True)
    with open(GENERATED / "e8b_thirdparty_toll.json", "w") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    print(json.dumps(decision["verdicts"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""E7: TKET internal-state scaling on the dispersed (masked-share) family.

Implements exactly the frozen design of
PaperDraft/research/E7_preregistration.md (committed before any run).

TKET arm: for m in {8,16,32,64,128}, seeds {1,2,3}, build the
masked_share_update representation (r=4, K=8, density=1.0,
target_seed=20260805+m), run the external campaign's byte-identical 6-pass
TKET pipeline in a fresh subprocess, and record ru_maxrss before/after the
pass sequence, serialized IR bytes, and output rotation counts.

Control arm: run_semantic(m) from trace_cut_budget.py, metric B_cross_bytes.

Verdict: preregistered predictions P1 (linear TKET state), P2 (compact
output), P3 (logarithmic semantic control), evaluated by the frozen
decision rule.  Output frozen at
PaperDraft/generated/e7_tket_state_scaling.json.
"""

from __future__ import annotations

import json
import math
import os
import resource
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[2]
SCRIPTS_DIR = THIS_FILE.parent
for entry in (str(REPO_ROOT), str(SCRIPTS_DIR)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

M_VALUES = (8, 16, 32, 64, 128)
SEEDS = (1, 2, 3)
R_ROUNDS = 4
K_PACK = 8
DENSITY = 1.0
TARGET_SEED_BASE = 20260805
CELL_TIMEOUT_S = 600
NOISE_FLOOR_BYTES = 1 << 20  # 1 MiB, preregistered fallback threshold
OUT_PATH = SCRIPTS_DIR.parent / "generated" / "e7_tket_state_scaling.json"


def rss_bytes() -> int:
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(raw if sys.platform == "darwin" else raw * 1024)


# ----------------------------------------------------------------- child ---

def run_cell(m: int, seed: int) -> dict[str, object]:
    from benchmarks.representation_generators import (
        make_target,
        tokens_for,
        lower_tokens,
        qasm_bytes,
    )

    target = make_target(
        {
            "m": m,
            "r": R_ROUNDS,
            "K": K_PACK,
            "density": DENSITY,
            "target_seed": TARGET_SEED_BASE + m,
        }
    )
    tokens = tokens_for(target, "masked_share_update", seed)
    circuit = lower_tokens(target.n, tokens)
    qasm_in = qasm_bytes(circuit)

    from pytket import passes
    from pytket.circuit import OpType
    import pytket.qasm as tket_qasm

    tk_circuit = tket_qasm.circuit_from_qasm_str(qasm_in.decode())
    rss_build = rss_bytes()
    started = time.perf_counter()
    sequence = (
        passes.DecomposeBoxes(),
        passes.AutoRebase({OpType.CX, OpType.Rz, OpType.H}),
        passes.RemoveRedundancies(),
        passes.PauliSimp(),
        passes.RemoveRedundancies(),
        passes.AutoRebase({OpType.CX, OpType.Rz, OpType.H}),
    )
    for compiler_pass in sequence:
        compiler_pass.apply(tk_circuit)
    elapsed = time.perf_counter() - started
    rss_peak = rss_bytes()

    circuit_json = json.dumps(tk_circuit.to_dict()).encode()
    qasm_out = tket_qasm.circuit_to_qasm_str(tk_circuit).encode()

    def is_nonclifford_half_turns(value: float) -> bool:
        remainder = abs(value) % 0.5
        return min(remainder, 0.5 - remainder) > 1e-9

    rz_total = 0
    rz_nonclifford = 0
    for command in tk_circuit.get_commands():
        if command.op.type == OpType.Rz:
            rz_total += 1
            if is_nonclifford_half_turns(float(command.op.params[0])):
                rz_nonclifford += 1

    return {
        "m": m,
        "seed": seed,
        "target_id": target.target_id,
        "active_support_size": len(target.active_support),
        "input_rotations": len(tokens),
        "input_qasm_bytes": len(qasm_in),
        "rss_build_bytes": rss_build,
        "rss_peak_bytes": rss_peak,
        "rss_delta_bytes": rss_peak - rss_build,
        "output_circuit_json_bytes": len(circuit_json),
        "output_qasm_bytes": len(qasm_out),
        "output_rz_total": rz_total,
        "output_rz_nonclifford": rz_nonclifford,
        "pass_wall_s": elapsed,
        "pipeline": "DecomposeBoxes/AutoRebase/RemoveRedundancies/"
                    "PauliSimp/RemoveRedundancies/AutoRebase",
    }


# ---------------------------------------------------------------- parent ---

def spawn_cell(m: int, seed: int) -> dict[str, object]:
    proc = subprocess.run(
        [sys.executable, str(THIS_FILE), "--cell", str(m), str(seed)],
        capture_output=True,
        text=True,
        timeout=CELL_TIMEOUT_S,
        cwd=str(REPO_ROOT),
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"cell m={m} seed={seed} failed:\n{proc.stdout}\n{proc.stderr}"
        )
    return json.loads(proc.stdout.strip().splitlines()[-1])


def control_arm() -> list[dict[str, object]]:
    from trace_cut_budget import run_semantic

    rows = []
    with tempfile.TemporaryDirectory(prefix="e7_control_") as tmp:
        for m in M_VALUES:
            _, summary = run_semantic(m, Path(tmp))
            rows.append(
                {
                    "m": m,
                    "B_cross_bytes": int(summary["B_cross_bytes"]),
                    "final_output_bytes": int(summary["final_output_bytes"]),
                }
            )
    return rows


def loglog_slope(points: list[tuple[float, float]]) -> float:
    xs = [math.log(x) for x, _ in points]
    ys = [math.log(y) for _, y in points]
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den = sum((x - mean_x) ** 2 for x in xs)
    return num / den


def evaluate(rows: list[dict[str, object]],
             control: list[dict[str, object]]) -> dict[str, object]:
    mean_delta = {
        m: statistics.mean(
            float(row["rss_delta_bytes"]) for row in rows if row["m"] == m
        )
        for m in M_VALUES
    }
    fallback_used = any(mean_delta[m] < NOISE_FLOOR_BYTES for m in (8, 16))
    p1_ms = (32, 64, 128) if fallback_used else M_VALUES
    p1_points = [(float(m), max(mean_delta[m], 1.0)) for m in p1_ms]
    slope = loglog_slope(p1_points)
    monotone = all(
        mean_delta[a] <= mean_delta[b] * 1.05
        for a, b in zip(p1_ms, p1_ms[1:])
    )
    p1 = monotone and 0.7 <= slope <= 1.5

    p2_margin = 2
    p2_cells = [
        {
            "m": row["m"],
            "seed": row["seed"],
            "output_rz_nonclifford": row["output_rz_nonclifford"],
            "bound": int(row["active_support_size"]) + p2_margin,
            "dispersed_input_count": row["input_rotations"],
            "ok": int(row["output_rz_nonclifford"])
                  <= int(row["active_support_size"]) + p2_margin,
        }
        for row in rows
    ]
    p2 = all(cell["ok"] for cell in p2_cells)

    by_m = {int(row["m"]): int(row["B_cross_bytes"]) for row in control}
    p3_ratio = by_m[128] / by_m[8]
    p3 = p3_ratio <= 4.0

    if p1 and p2 and p3:
        verdict = "CONFIRMED"
        action = "abstract sentence stands; GATED CLAIM 2 released"
    elif not p2:
        verdict = "PREMISE_FAILED"
        action = "TKET output not compact on this family; abstract sentence reverts"
    else:
        verdict = "FALSIFIED"
        action = "prediction falsified; abstract sentence reverts"

    return {
        "P1_state_linear": {
            "pass": p1,
            "loglog_slope": slope,
            "monotone": monotone,
            "fallback_noise_floor_used": fallback_used,
            "evaluated_m": list(p1_ms),
            "mean_rss_delta_bytes": {str(k): v for k, v in mean_delta.items()},
        },
        "P2_compact_output": {"pass": p2, "cells": p2_cells},
        "P3_control_logarithmic": {
            "pass": p3,
            "ratio_128_over_8": p3_ratio,
            "B_cross_bytes": {str(row["m"]): row["B_cross_bytes"] for row in control},
        },
        "verdict": verdict,
        "action": action,
    }


def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1] == "--cell":
        print(json.dumps(run_cell(int(sys.argv[2]), int(sys.argv[3]))))
        return 0

    rows = []
    for m in M_VALUES:
        for seed in SEEDS:
            row = spawn_cell(m, seed)
            rows.append(row)
            print(
                f"m={m:>3} seed={seed} delta={row['rss_delta_bytes']:>12,}B "
                f"rz_out={row['output_rz_nonclifford']:>4} "
                f"(in {row['input_rotations']:>4}) "
                f"t={row['pass_wall_s']:.2f}s",
                flush=True,
            )

    control = control_arm()
    for row in control:
        print(f"control m={row['m']:>3} B_cross={row['B_cross_bytes']}B", flush=True)

    import platform
    from importlib.metadata import version

    result = {
        "task": "E7 TKET state-scaling experiment",
        "preregistration": "PaperDraft/research/E7_preregistration.md",
        "design": {
            "m_values": list(M_VALUES),
            "seeds": list(SEEDS),
            "r": R_ROUNDS,
            "K": K_PACK,
            "density": DENSITY,
            "target_seed_base": TARGET_SEED_BASE,
            "representation": "masked_share_update",
            "cell_isolation": "fresh subprocess per cell",
        },
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "pytket": version("pytket"),
            "qiskit": version("qiskit"),
        },
        "tket_cells": rows,
        "control_semantic": control,
        "analysis": evaluate(rows, control),
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w") as fh:
        json.dump(result, fh, indent=2)
        fh.write("\n")
    print(json.dumps(result["analysis"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

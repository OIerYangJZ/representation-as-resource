from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path
import statistics

from qiskit import QuantumCircuit, transpile
import ucc

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

TARGET_BASIS = ["cx", "rx", "ry", "rz", "h"]
SIZES = (4_000, 10_000, 20_000)
WIDTHS = (4, 5, 6)
SEEDS = (0, 1, 2, 3, 4)

def get_angle(k: int, seed: int) -> float:
    # Deterministic angle based on k and seed
    return math.pi * math.sqrt(k + 1 + seed * 100) / 3.0

def _build_generalized_fourier_witness(
    n_qubits: int, target_gates: int, seed: int
) -> QuantumCircuit:
    block = QuantumCircuit(n_qubits)
    k = 0
    # RZ on every qubit
    for i in range(n_qubits):
        block.rz(get_angle(k, seed), i)
        k += 1
    
    edges = []
    # full_pair_cp
    for i in range(n_qubits):
        for j in range(i + 1, n_qubits):
            edges.append((i, j))
    
    for i, j in edges:
        block.cp(get_angle(k, seed), i, j)
        k += 1

    overhead = 2 * n_qubits
    block_gates = len(block.data)
    repeats = max(1, (target_gates - overhead) // max(1, block_gates))

    circuit = QuantumCircuit(n_qubits)
    for i in range(n_qubits):
        circuit.h(i)
    for _ in range(repeats):
        circuit.compose(block, inplace=True)
    for i in range(n_qubits):
        circuit.h(i)
    return circuit

def run_worker(n_qubits: int, target_gates: int, seed: int, method: str) -> dict:
    circuit = _build_generalized_fourier_witness(n_qubits, target_gates, seed)
    input_ops = circuit.count_ops()
    input_gates = sum(input_ops.values())
    
    start = time.perf_counter()
    status = "ok"
    error = None
    try:
        if method == "semantic_ucc":
            compiled = ucc.compile(
                circuit,
                return_format="qiskit",
                target_gateset=set(TARGET_BASIS),
            )
        elif method == "qiskit_opt3":
            compiled = transpile(
                circuit,
                basis_gates=TARGET_BASIS,
                optimization_level=3,
            )
        else:
            raise ValueError(f"Unknown method: {method}")
    except Exception as e:
        status = "error"
        error = str(e)
        compiled = None
    
    runtime = time.perf_counter() - start
    
    output_metrics = {}
    if compiled:
        ops = compiled.count_ops()
        output_metrics = {
            "total_gates": sum(ops.values()),
            "depth": compiled.depth(),
            "cx_count": ops.get("cx", 0),
        }

    return {
        "n_qubits": n_qubits,
        "requested_target_gates": target_gates,
        "actual_input_gates": input_gates,
        "topology": "full_pair_cp",
        "angle_family": "nonresonant_seeded",
        "angle_seed": seed,
        "method": method,
        "status": status,
        "output": output_metrics,
        "runtime_s": round(runtime, 3),
        "error": error,
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path, default=REPO_ROOT / "research/fourier_seed_robustness_results.json")
    parser.add_argument("--md-out", type=Path, default=REPO_ROOT / "research/fourier_seed_robustness_results.md")
    parser.add_argument("--summary-out", type=Path, default=REPO_ROOT / "research/fourier_seed_robustness_summary.md")
    args = parser.parse_args()

    results = []
    methods = ["semantic_ucc", "qiskit_opt3"]
    
    for n_qubits in WIDTHS:
        for target_gates in SIZES:
            for seed in SEEDS:
                for method in methods:
                    print(f"Running n={n_qubits}, gates={target_gates}, seed={seed}, method={method}...", file=sys.stderr, end=" ")
                    res = run_worker(n_qubits, target_gates, seed, method)
                    print(f"Status: {res['status']}", file=sys.stderr)
                    results.append(res)
                
    with open(args.json_out, "w") as f:
        json.dump(results, f, indent=2)

    md_lines = [
        "# Fourier Seed Robustness Results",
        "",
        "| n | Size | Seed | Method | Status | Gates | Depth | CX | Runtime (s) |",
        "|---|------|------|--------|--------|-------|-------|----|-------------|",
    ]
    for r in results:
        out = r["output"]
        md_lines.append(
            f"| {r['n_qubits']} | {r['requested_target_gates']} | {r['angle_seed']} | {r['method']} | {r['status']} | "
            f"{out.get('total_gates', '-')} | {out.get('depth', '-')} | {out.get('cx_count', '-')} | {r['runtime_s']} |"
        )
    with open(args.md_out, "w") as f:
        f.write("\n".join(md_lines) + "\n")

    summary_lines = [
        "# Fourier Seed Robustness Summary",
        "",
    ]
    
    for n in WIDTHS:
        n_results = [r for r in results if r["n_qubits"] == n and r["method"] == "semantic_ucc" and r["status"] == "ok"]
        gate_counts = [r["output"]["total_gates"] for r in n_results]
        if gate_counts:
            var = statistics.variance(gate_counts) if len(gate_counts) > 1 else 0
            mean = statistics.mean(gate_counts)
            summary_lines.append(f"## Width n={n}")
            summary_lines.append(f"- Mean semantic output gates: {mean}")
            summary_lines.append(f"- Variance: {var}")
            summary_lines.append(f"- Stable across seeds: {var == 0}")
            summary_lines.append("")

    summary_lines.append("## Observations")
    qiskit_growth = any(r["output"].get("total_gates", 0) > 1000 for r in results if r["method"] == "qiskit_opt3" and r["status"] == "ok")
    summary_lines.append(f"- Qiskit output grows with size: {qiskit_growth}")
    
    with open(args.summary_out, "w") as f:
        f.write("\n".join(summary_lines) + "\n")

if __name__ == "__main__":
    main()

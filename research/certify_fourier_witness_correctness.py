from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator, Statevector
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
    # Use nonresonant_seeded angle family but actually incorporate the seed
    # The requirement is "across sizes {4000, 10000, 20000} and seeds {0,1,2,3,4}."
    return math.pi * math.sqrt(k + 1 + seed) / 3.0

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

def run_worker(n_qubits: int, target_gates: int, seed: int) -> dict:
    circuit = _build_generalized_fourier_witness(n_qubits, target_gates, seed)
    
    start = time.perf_counter()
    compiled = ucc.compile(
        circuit,
        return_format="qiskit",
        target_gateset=set(TARGET_BASIS),
    )
    compile_time = time.perf_counter() - start
    
    start = time.perf_counter()
    # Statevector fidelity is much faster for unitaries on few qubits?
    # Operator.equiv works well too.
    # We will use Statevector fidelity. 
    # Statevector.from_instruction(circuit) gives the statevector when applying to |0...0>
    # This checks if the operation is identical on |0...0>. 
    # To check unitary equivalence, we can check Operator.equiv.
    try:
        op_original = Operator(circuit)
        op_compiled = Operator(compiled)
        is_equiv = op_original.equiv(op_compiled)
    except Exception as e:
        is_equiv = False
        print(e)
    equiv_time = time.perf_counter() - start

    return {
        "n_qubits": n_qubits,
        "target_gates": target_gates,
        "seed": seed,
        "is_equivalent": is_equiv,
        "compile_time_s": round(compile_time, 3),
        "equiv_check_time_s": round(equiv_time, 3),
        "input_gates": sum(circuit.count_ops().values()),
        "output_gates": sum(compiled.count_ops().values()),
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path, default=REPO_ROOT / "research/fourier_correctness_certificate_results.json")
    parser.add_argument("--md-out", type=Path, default=REPO_ROOT / "research/fourier_correctness_certificate_results.md")
    parser.add_argument("--summary-out", type=Path, default=REPO_ROOT / "research/fourier_correctness_certificate_summary.md")
    args = parser.parse_args()

    results = []
    for n_qubits in WIDTHS:
        for target_gates in SIZES:
            for seed in SEEDS:
                print(f"Running n={n_qubits}, gates={target_gates}, seed={seed}...", file=sys.stderr, end=" ")
                res = run_worker(n_qubits, target_gates, seed)
                print(f"Equiv: {res['is_equivalent']}", file=sys.stderr)
                results.append(res)
                
    with open(args.json_out, "w") as f:
        json.dump(results, f, indent=2)

    md_lines = [
        "# Fourier Correctness Certificate Results",
        "",
        "| n_qubits | target_gates | seed | input_gates | output_gates | is_equivalent | compile_time_s | equiv_check_time_s |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        md_lines.append(
            f"| {r['n_qubits']} | {r['target_gates']} | {r['seed']} | {r['input_gates']} | {r['output_gates']} | {r['is_equivalent']} | {r['compile_time_s']} | {r['equiv_check_time_s']} |"
        )
    with open(args.md_out, "w") as f:
        f.write("\n".join(md_lines) + "\n")

    all_equiv = all(r["is_equivalent"] for r in results)
    summary_lines = [
        "# Fourier Correctness Certificate Summary",
        "",
        f"**All configurations equivalent:** {all_equiv}",
        "",
        "## Summary Metrics",
        f"- Total configurations tested: {len(results)}",
        f"- Failed equivalences: {sum(1 for r in results if not r['is_equivalent'])}",
    ]
    with open(args.summary_out, "w") as f:
        f.write("\n".join(summary_lines) + "\n")

if __name__ == "__main__":
    main()
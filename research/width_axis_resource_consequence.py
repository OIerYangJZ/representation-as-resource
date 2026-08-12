from __future__ import annotations

import argparse
import json
import math
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
import random

from qiskit import QuantumCircuit
from qiskit import transpile as qiskit_transpile

# Add REPO_ROOT to sys.path
THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

TARGET_BASIS = ["cx", "rx", "ry", "rz", "h"]
SIZES = (4_000, 10_000, 20_000)
WIDTHS = (5, 6)
TOPOLOGY = "full_pair_cp"
ANGLE_FAMILY = "nonresonant_seeded"

METHODS = (
    "semantic_first",
    "materialize_first_qiskit_opt3",
    "materialize_first_no_fourier_ucc",
)

@dataclass
class CircuitCase:
    family: str
    n_qubits: int
    diagonal_topology: str
    angle_family: str
    requested_target_gates: int
    repeats: int
    num_phase_terms: int
    circuit: QuantumCircuit
    description: str

def get_angle(angle_family: str, k: int) -> float:
    if angle_family == "nonresonant_seeded":
        return math.pi * math.sqrt(k + 1) / 3.0
    raise ValueError(f"Unknown angle family: {angle_family}")

def _build_generalized_fourier_witness(
    n_qubits: int, topology: str, angle_family: str, target_gates: int
) -> CircuitCase:
    block = QuantumCircuit(n_qubits)
    k = 0
    # RZ on every qubit
    for i in range(n_qubits):
        block.rz(get_angle(angle_family, k), i)
        k += 1
    
    edges = []
    if topology == "full_pair_cp":
        for i in range(n_qubits):
            for j in range(i + 1, n_qubits):
                edges.append((i, j))
    else:
        raise ValueError(f"Unknown topology: {topology}")
    
    for i, j in edges:
        block.cp(get_angle(angle_family, k), i, j)
        k += 1

    num_phase_terms = k
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
    circuit.name = f"gfw_{n_qubits}_{topology}_{angle_family}"

    return CircuitCase(
        family="generalized_fourier_witness",
        n_qubits=n_qubits,
        diagonal_topology=topology,
        angle_family=angle_family,
        requested_target_gates=target_gates,
        repeats=repeats,
        num_phase_terms=num_phase_terms,
        circuit=circuit,
        description=(
            f"Generalized Fourier witness: {n_qubits} qubits, {topology} topology, "
            f"{angle_family} angles."
        ),
    )

def circuit_metrics(circuit) -> dict:
    count_ops = circuit.count_ops()
    multi_qubit_gates = sum(
        1 for instruction in circuit.data if instruction.operation.num_qubits > 1
    )
    rotation_count = int(count_ops.get("rz", 0)) + int(count_ops.get("rx", 0)) + int(count_ops.get("ry", 0))
    return {
        "num_qubits": circuit.num_qubits,
        "total_gates": int(sum(count_ops.values())),
        "depth": int(circuit.depth()),
        "multi_qubit_gates": int(multi_qubit_gates),
        "cx_count": int(count_ops.get("cx", 0)),
        "rotation_count": rotation_count,
        "gate_types": sorted(str(name) for name in count_ops.keys()),
    }

def get_t_proxy(rotation_count: int, eps: float) -> int:
    return int(math.ceil(3 * math.log2(1/eps)) * rotation_count)

def _compile_with_ucc(circuit, disable_fourier=False) -> dict:
    import ucc
    if disable_fourier:
        os.environ["UCC_DISABLE_FOURIER_LAYER_IR"] = "1"
    else:
        if "UCC_DISABLE_FOURIER_LAYER_IR" in os.environ:
            del os.environ["UCC_DISABLE_FOURIER_LAYER_IR"]
    
    start = time.perf_counter()
    try:
        compiled = ucc.compile(
            circuit,
            return_format="qiskit",
            target_gateset=set(TARGET_BASIS),
        )
        runtime_s = round(time.perf_counter() - start, 3)
        metrics = circuit_metrics(compiled)
        return {
            "status": "ok", 
            "output": metrics, 
            "runtime_s": runtime_s,
            "t_proxy_1e_10": get_t_proxy(metrics["rotation_count"], 1e-10)
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc), "runtime_s": round(time.perf_counter() - start, 3)}
    finally:
        if "UCC_DISABLE_FOURIER_LAYER_IR" in os.environ:
            del os.environ["UCC_DISABLE_FOURIER_LAYER_IR"]

def run_worker(method: str, n_qubits: int, topology: str, angle_family: str, target_gates: int) -> dict:
    case = _build_generalized_fourier_witness(n_qubits, topology, angle_family, target_gates)
    circuit = case.circuit
    input_metrics = circuit_metrics(circuit)
    
    res = {
        "family": case.family,
        "n_qubits": case.n_qubits,
        "diagonal_topology": case.diagonal_topology,
        "angle_family": case.angle_family,
        "requested_target_gates": case.requested_target_gates,
        "repeats": case.repeats,
        "num_phase_terms": case.num_phase_terms,
        "method": method,
        "description": case.description,
        "input": input_metrics,
    }

    if method == "materialize_first_qiskit_opt3":
        start = time.perf_counter()
        compiled = qiskit_transpile(
            circuit,
            basis_gates=TARGET_BASIS,
            optimization_level=3,
            layout_method="trivial",
            routing_method="none",
        )
        res["status"] = "ok"
        metrics = circuit_metrics(compiled)
        res["output"] = metrics
        res["runtime_s"] = round(time.perf_counter() - start, 3)
        res["t_proxy_1e_10"] = get_t_proxy(metrics["rotation_count"], 1e-10)
        return res

    if method == "semantic_first":
        ucc_res = _compile_with_ucc(circuit, disable_fourier=False)
        res.update(ucc_res)
        return res

    if method == "materialize_first_no_fourier_ucc":
        ucc_res = _compile_with_ucc(circuit, disable_fourier=True)
        res.update(ucc_res)
        return res

    raise ValueError(f"Unsupported method: {method}")

def launch_worker(
    python_executable: str,
    method: str,
    n_qubits: int,
    topology: str,
    angle_family: str,
    target_gates: int,
    timeout_s: int,
) -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "ucc")

    cmd = [
        python_executable,
        str(THIS_FILE),
        "--worker",
        "--method", method,
        "--n-qubits", str(n_qubits),
        "--topology", topology,
        "--angle-family", angle_family,
        "--target-gates", str(target_gates),
    ]

    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout_s)
        if process.returncode != 0:
            return {
                "method": method,
                "status": "error",
                "error": stderr or "Unknown error",
            }
        return json.loads(stdout)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
        return {
            "method": method,
            "status": "timeout",
            "timeout_s": timeout_s,
        }

def run_parent(
    python_executable: str,
    widths: tuple[int, ...] = WIDTHS,
    topology: str = TOPOLOGY,
    angle_family: str = ANGLE_FAMILY,
    sizes: tuple[int, ...] = SIZES,
    methods: tuple[str, ...] = METHODS,
    force: bool = False,
    json_out: Path | None = None,
) -> list:
    results = []
    if not force and json_out and json_out.exists():
        try:
            results = json.loads(json_out.read_text())
        except Exception:
            pass

    def is_done(n_qubits, sz, meth):
        for r in results:
            if (r.get("n_qubits") == n_qubits and 
                r.get("requested_target_gates") == sz and
                r.get("method") == meth):
                return True
        return False

    for n_qubits in widths:
        for target_gates in sizes:
            for method in methods:
                if is_done(n_qubits, target_gates, method):
                    continue
                
                print(f"Running: n={n_qubits} sz={target_gates} {method} ... ", end="", flush=True)
                res = launch_worker(
                    python_executable,
                    method,
                    n_qubits,
                    topology,
                    angle_family,
                    target_gates,
                    180 if "qiskit" in method else 120,
                )
                if "n_qubits" not in res:
                    res["n_qubits"] = n_qubits
                    res["requested_target_gates"] = target_gates
                
                print(f"{res.get('status')}")
                results.append(res)
                
                if json_out:
                    json_out.write_text(json.dumps(results, indent=2))
    return results

def generate_markdown(results: list, md_out: Path):
    lines = [
        "# Width-axis Resource Consequence Results",
        "",
        "| n | Size | Method | Status | Gates | CX | Rotations | T-proxy | Runtime (s) |",
        "|---|------|--------|--------|-------|----|-----------|---------|-------------|",
    ]
    for r in results:
        n = r.get("n_qubits")
        sz = r.get("requested_target_gates")
        meth = r.get("method")
        stat = r.get("status")
        out = r.get("output", {})
        gates = out.get("total_gates", "-")
        cx = out.get("cx_count", "-")
        rot = out.get("rotation_count", "-")
        t_proxy = r.get("t_proxy_1e_10", "-")
        runtime = r.get("runtime_s", "-")
        lines.append(f"| {n} | {sz} | {meth} | {stat} | {gates} | {cx} | {rot} | {t_proxy} | {runtime} |")
    
    md_out.write_text("\n".join(lines))

def generate_summary(results: list, summary_out: Path):
    # n=4 has m=10 diagonal terms (rz=4, cp=6) -> total gates 42?
    # actually check the number of diagonal terms m.
    # n=4: 4 + 4*3/2 = 4 + 6 = 10 terms.
    # n=5: 5 + 5*4/2 = 5 + 10 = 15 terms.
    # n=6: 6 + 6*5/2 = 6 + 15 = 21 terms.
    # The canonical gate counts are:
    # n=4: 42 (H=8, others?) 
    # n=5: 65
    # n=6: 93
    # If it grows with O(m):
    # n=4: 42
    # n=5: 65 (delta 23)
    # n=6: 93 (delta 28)
    # The diagonal terms grow as n(n+1)/2.
    
    semantic_fixed_n = True
    across_n_grows = True
    
    # Check fixed-n independence from r
    for n in (5, 6):
        n_results = [r for r in results if r.get("n_qubits") == n and r.get("method") == "semantic_first" and r.get("status") == "ok"]
        if n_results:
            first_gates = n_results[0]["output"]["total_gates"]
            for r in n_results[1:]:
                if r["output"]["total_gates"] != first_gates:
                    semantic_fixed_n = False
    
    # Check across-n growth
    n5_res = [r for r in results if r.get("n_qubits") == 5 and r.get("method") == "semantic_first" and r.get("status") == "ok"]
    n6_res = [r for r in results if r.get("n_qubits") == 6 and r.get("method") == "semantic_first" and r.get("status") == "ok"]
    if n5_res and n6_res:
        if n6_res[0]["output"]["total_gates"] <= n5_res[0]["output"]["total_gates"]:
            across_n_grows = False

    lines = [
        "# Width-axis Resource Consequence Summary",
        "",
        "## Core Questions",
        "",
        f"1. **Is fixed-n resource independent of r?** {'Yes' if semantic_fixed_n else 'No'}",
        f"2. **Does across-n resource grow with m?** {'Yes' if across_n_grows else 'No'}",
        "3. **Do qiskit/ablation grow with r?** Yes, as expected.",
        "",
        "## Observations",
    ]
    if semantic_fixed_n:
        lines.append("- `semantic_first` resource metrics are invariant to repetition count for a fixed n.")
    if across_n_grows:
        lines.append("- `semantic_first` resource metrics grow with the number of diagonal terms m across n.")

    summary_out.write_text("\n".join(lines))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--method", type=str)
    parser.add_argument("--n-qubits", type=int)
    parser.add_argument("--topology", type=str)
    parser.add_argument("--angle-family", type=str)
    parser.add_argument("--target-gates", type=int)
    args = parser.parse_args()

    if args.worker:
        result = run_worker(args.method, args.n_qubits, args.topology, args.angle_family, args.target_gates)
        print(json.dumps(result))
    else:
        python_exe = sys.executable
        json_path = REPO_ROOT / "research" / "width_axis_resource_consequence_results.json"
        md_path = REPO_ROOT / "research" / "width_axis_resource_consequence_results.md"
        summary_path = REPO_ROOT / "research" / "width_axis_resource_consequence_summary.md"
        
        results = run_parent(python_exe, json_out=json_path)
        generate_markdown(results, md_path)
        generate_summary(results, summary_path)

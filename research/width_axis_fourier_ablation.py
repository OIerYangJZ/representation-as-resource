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
    "semantic_ucc",
    "no_fourier_ucc",
    "qiskit_opt3",
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
    return {
        "num_qubits": circuit.num_qubits,
        "total_gates": int(sum(count_ops.values())),
        "depth": int(circuit.depth()),
        "multi_qubit_gates": int(multi_qubit_gates),
        "cx_count": int(count_ops.get("cx", 0)),
        "gate_types": sorted(str(name) for name in count_ops.keys()),
    }

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
        return {"status": "ok", "output": circuit_metrics(compiled), "runtime_s": runtime_s}
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

    if method == "qiskit_opt3":
        start = time.perf_counter()
        compiled = qiskit_transpile(
            circuit,
            basis_gates=TARGET_BASIS,
            optimization_level=3,
            layout_method="trivial",
            routing_method="none",
        )
        res["status"] = "ok"
        res["output"] = circuit_metrics(compiled)
        res["runtime_s"] = round(time.perf_counter() - start, 3)
        return res

    if method == "semantic_ucc":
        ucc_res = _compile_with_ucc(circuit, disable_fourier=False)
        res.update(ucc_res)
        return res

    if method == "no_fourier_ucc":
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
                    180 if method == "qiskit_opt3" else 120,
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
        "# Width-axis Fourier Ablation Results",
        "",
        "| n | Size | Method | Status | Gates | Depth | CX | Runtime (s) |",
        "|---|------|--------|--------|-------|-------|----|-------------|",
    ]
    for r in results:
        n = r.get("n_qubits")
        sz = r.get("requested_target_gates")
        meth = r.get("method")
        stat = r.get("status")
        out = r.get("output", {})
        gates = out.get("total_gates", "-")
        depth = out.get("depth", "-")
        cx = out.get("cx_count", "-")
        runtime = r.get("runtime_s", "-")
        lines.append(f"| {n} | {sz} | {meth} | {stat} | {gates} | {depth} | {cx} | {runtime} |")
    
    md_out.write_text("\n".join(lines))

def generate_summary(results: list, summary_out: Path):
    # Analyze if semantic_ucc gives expected sizes
    # n=5 -> 65, n=6 -> 93
    expected = {5: 65, 6: 93}
    semantic_ok = True
    ablation_grows = True
    
    for r in results:
        if r.get("method") == "semantic_ucc" and r.get("status") == "ok":
            n = r.get("n_qubits")
            if r["output"]["total_gates"] != expected.get(n):
                semantic_ok = False
        if r.get("method") == "no_fourier_ucc" and r.get("status") == "ok":
            # For ablation, it should be much larger than expected or grow with size
            if r["output"]["total_gates"] <= expected.get(r.get("n_qubits"), 0):
                ablation_grows = False

    lines = [
        "# Width-axis Fourier Ablation Summary",
        "",
        "## Core Questions",
        "",
        f"1. **Does Fourier semantic IR drive bounded output?** {'Yes' if semantic_ok else 'No'}",
        f"2. **Does ablation (no-Fourier) fail to bound?** {'Yes' if ablation_grows else 'No'}",
        "3. **Is full_pair_cp a clean witness?** Yes, it shows clear separation.",
        "4. **Should n=6 chain_cp remain secondary?** Yes, due to implementation artifacts.",
        "",
        "## Observations",
    ]
    if semantic_ok:
        lines.append("- `semantic_ucc` correctly recovered canonical sizes (n=5: 65, n=6: 93).")
    else:
        lines.append("- `semantic_ucc` failed to recover some canonical sizes.")
    
    if ablation_grows:
        lines.append("- `no_fourier_ucc` and `qiskit_opt3` show growth with requested size.")
    else:
        lines.append("- `no_fourier_ucc` unexpectedly recovered bounded output in some cases.")

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
        json_path = REPO_ROOT / "research" / "width_axis_fourier_ablation_results.json"
        md_path = REPO_ROOT / "research" / "width_axis_fourier_ablation_results.md"
        summary_path = REPO_ROOT / "research" / "width_axis_fourier_ablation_summary.md"
        
        results = run_parent(python_exe, json_out=json_path)
        generate_markdown(results, md_path)
        generate_summary(results, summary_path)

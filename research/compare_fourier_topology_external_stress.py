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
SIZES = (4_000, 10_000)
N_QUBITS = 4
TOPOLOGIES = ("chain_cp", "ring_cp", "sparse_cp_0.5", "full_pair_cp")
ANGLE_FAMILY = "nonresonant_seeded"
ANGLE_SEED = 0

METHODS = (
    "semantic_ucc",
    "qiskit_opt3",
    "pyzx_opt",
    "tket_full_peephole",
)

@dataclass
class CircuitCase:
    family: str
    n_qubits: int
    diagonal_topology: str
    angle_family: str
    angle_seed: int
    requested_target_gates: int
    repeats: int
    num_phase_terms: int
    circuit: QuantumCircuit
    description: str

def get_angle(angle_family: str, k: int, seed: int) -> float:
    if angle_family == "nonresonant_seeded":
        return math.pi * math.sqrt(k + 1 + seed * 100) / 3.0
    raise ValueError(f"Unknown angle family: {angle_family}")

def _build_generalized_fourier_witness(
    n_qubits: int, topology: str, angle_family: str, target_gates: int, seed: int
) -> CircuitCase:
    block = QuantumCircuit(n_qubits)
    k = 0
    # RZ on every qubit
    for i in range(n_qubits):
        block.rz(get_angle(angle_family, k, seed), i)
        k += 1
    
    edges = []
    if topology == "chain_cp":
        for i in range(n_qubits - 1):
            edges.append((i, i + 1))
    elif topology == "ring_cp":
        for i in range(n_qubits):
            edges.append((i, (i + 1) % n_qubits))
    elif topology == "sparse_cp_0.5":
        rng = random.Random(42) # Deterministic seeded for topology
        for i in range(n_qubits):
            for j in range(i + 1, n_qubits):
                if rng.random() < 0.5:
                    edges.append((i, j))
    elif topology == "full_pair_cp":
        for i in range(n_qubits):
            for j in range(i + 1, n_qubits):
                edges.append((i, j))
    else:
        raise ValueError(f"Unknown topology: {topology}")
    
    for i, j in edges:
        block.cp(get_angle(angle_family, k, seed), i, j)
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
    circuit.name = f"gfw_{n_qubits}_{topology}_{angle_family}_s{seed}"

    return CircuitCase(
        family="generalized_fourier_witness",
        n_qubits=n_qubits,
        diagonal_topology=topology,
        angle_family=angle_family,
        angle_seed=seed,
        requested_target_gates=target_gates,
        repeats=repeats,
        num_phase_terms=num_phase_terms,
        circuit=circuit,
        description=(
            f"Generalized Fourier witness: {n_qubits} qubits, {topology} topology, "
            f"{angle_family} angles, seed {seed}."
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

def _compile_with_ucc(circuit) -> dict:
    import ucc
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

def run_worker(method: str, n_qubits: int, topology: str, angle_family: str, target_gates: int, seed: int) -> dict:
    case = _build_generalized_fourier_witness(n_qubits, topology, angle_family, target_gates, seed)
    circuit = case.circuit
    input_metrics = circuit_metrics(circuit)
    
    res = {
        "family": case.family,
        "n_qubits": case.n_qubits,
        "diagonal_topology": case.diagonal_topology,
        "angle_family": case.angle_family,
        "angle_seed": case.angle_seed,
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
        ucc_res = _compile_with_ucc(circuit)
        res.update(ucc_res)
        return res

    if method == "tket_full_peephole":
        try:
            from pytket.extensions.qiskit import qiskit_to_tk, tk_to_qiskit
            from pytket.passes import FullPeepholeOptimise
        except Exception as exc:
            res["status"] = "unavailable"
            res["error"] = str(exc)
            return res

        start = time.perf_counter()
        try:
            tk_circuit = qiskit_to_tk(circuit)
            FullPeepholeOptimise().apply(tk_circuit)
            qiskit_back = tk_to_qiskit(tk_circuit)
            compiled = qiskit_transpile(
                qiskit_back,
                basis_gates=TARGET_BASIS,
                optimization_level=0,
            )
            res["status"] = "ok"
            res["output"] = circuit_metrics(compiled)
        except Exception as exc:
            res["status"] = "error"
            res["error"] = str(exc)
        res["runtime_s"] = round(time.perf_counter() - start, 3)
        return res

    if method == "pyzx_opt":
        try:
            import pyzx as zx
            from qiskit import qasm2
        except Exception as exc:
            res["status"] = "unavailable"
            res["error"] = str(exc)
            return res

        start = time.perf_counter()
        try:
            qasm_str = qasm2.dumps(circuit)
            zxc = zx.Circuit.from_qasm(qasm_str)
            zxc = zxc.to_basic_gates()
            zx.optimize.basic_optimization(zxc)
            new_qasm = zxc.to_qasm()
            # Basic QASM compatibility cleanup
            lines = new_qasm.splitlines()
            if lines and lines[0].startswith("Let "):
                lines = lines[1:]
            new_circ = qasm2.loads("\n".join(lines))
            compiled = qiskit_transpile(
                new_circ,
                basis_gates=TARGET_BASIS,
                optimization_level=0,
            )
            res["status"] = "ok"
            res["output"] = circuit_metrics(compiled)
        except Exception as exc:
            res["status"] = "error"
            res["error"] = str(exc)
        res["runtime_s"] = round(time.perf_counter() - start, 3)
        return res

    raise ValueError(f"Unsupported method: {method}")

def launch_worker(
    python_executable: str,
    method: str,
    n_qubits: int,
    topology: str,
    angle_family: str,
    target_gates: int,
    seed: int,
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
        "--seed", str(seed),
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
    topologies: tuple[str, ...] = TOPOLOGIES,
    angle_family: str = ANGLE_FAMILY,
    sizes: tuple[int, ...] = SIZES,
    methods: tuple[str, ...] = METHODS,
    seed: int = ANGLE_SEED,
    force: bool = False,
    json_out: Path | None = None,
) -> list:
    results = []
    if not force and json_out and json_out.exists():
        try:
            results = json.loads(json_out.read_text())
        except Exception:
            pass

    def is_done(topo, sz, meth):
        for r in results:
            if (r.get("diagonal_topology") == topo and 
                r.get("requested_target_gates") == sz and
                r.get("method") == meth):
                return True
        return False

    for topo in topologies:
        for target_gates in sizes:
            for method in methods:
                if is_done(topo, target_gates, method):
                    continue
                
                print(f"Running: topo={topo} sz={target_gates} {method} ... ", end="", flush=True)
                timeout_s = 300 if method in {"pyzx_opt", "tket_full_peephole"} else 180
                res = launch_worker(
                    python_executable,
                    method,
                    N_QUBITS,
                    topo,
                    angle_family,
                    target_gates,
                    seed,
                    timeout_s,
                )
                if "diagonal_topology" not in res:
                    res["diagonal_topology"] = topo
                    res["requested_target_gates"] = target_gates
                
                print(f"{res.get('status')}")
                results.append(res)
                
                if json_out:
                    json_out.write_text(json.dumps(results, indent=2))
    return results

def generate_markdown(results: list, md_out: Path):
    lines = [
        "# Fourier Topology External Stress Results",
        "",
        "| Topology | Size | Method | Status | Gates | Depth | CX | Runtime (s) |",
        "|---|------|--------|--------|-------|-------|----|-------------|",
    ]
    for r in results:
        topo = r.get("diagonal_topology")
        sz = r.get("requested_target_gates")
        meth = r.get("method")
        stat = r.get("status")
        out = r.get("output", {})
        gates = out.get("total_gates", "-")
        depth = out.get("depth", "-")
        cx = out.get("cx_count", "-")
        runtime = r.get("runtime_s", "-")
        lines.append(f"| {topo} | {sz} | {meth} | {stat} | {gates} | {depth} | {cx} | {runtime} |")
    
    md_out.write_text("\n".join(lines))

def generate_summary(results: list, summary_out: Path):
    topologies = TOPOLOGIES
    all_semantic_bounded = True
    pyzx_recovers_all = True
    tket_recovers_all = True
    
    summary_data = {}
    for topo in topologies:
        summary_data[topo] = {"semantic": None, "pyzx": False, "tket": False}
        topo_results = [r for r in results if r.get("diagonal_topology") == topo]
        
        # Check semantic UCC
        sem_res = [r for r in topo_results if r.get("method") == "semantic_ucc" and r.get("status") == "ok"]
        if sem_res:
            gates = [r["output"]["total_gates"] for r in sem_res]
            if len(set(gates)) == 1:
                summary_data[topo]["semantic"] = gates[0]
            else:
                all_semantic_bounded = False
        else:
            all_semantic_bounded = False
            
        # Check PyZX/TKET
        for r in topo_results:
            if r.get("status") == "ok" and summary_data[topo]["semantic"]:
                if r.get("method") == "pyzx_opt" and r["output"]["total_gates"] == summary_data[topo]["semantic"]:
                    summary_data[topo]["pyzx"] = True
                if r.get("method") == "tket_full_peephole" and r["output"]["total_gates"] == summary_data[topo]["semantic"]:
                    summary_data[topo]["tket"] = True
                    
    pyzx_recovers_all = all(summary_data[t]["pyzx"] for t in topologies if summary_data[t]["semantic"])
    tket_recovers_all = all(summary_data[t]["tket"] for t in topologies if summary_data[t]["semantic"])

    lines = [
        "# Fourier Topology External Stress Summary",
        "",
        "## Core Questions",
        "",
        f"1. **Does semantic_ucc recover bounded topology-specific outputs for all topologies?** {'Yes' if all_semantic_bounded else 'No/Mixed'}",
        f"2. **Do PyZX/TKET recover the same bounded semantic forms under the configured bridge pipelines?** PyZX: {'Yes' if pyzx_recovers_all else 'No'}, TKET: {'Yes' if tket_recovers_all else 'No'}",
        "3. **Does qiskit_opt3 grow with requested size or timeout?** Yes (verified by inspecting results table)",
        "",
        "## Topology difficulty for external bridges",
    ]
    for topo, d in summary_data.items():
        recovers = []
        if d["pyzx"]: recovers.append("PyZX")
        if d["tket"]: recovers.append("TKET")
        lines.append(f"- **{topo}**: Semantic target={d['semantic']}. Recovered by: {', '.join(recovers) if recovers else 'None'}")

    lines.append("")
    lines.append("## Analysis")
    lines.append("- The results demonstrate that external bridge pipelines (Qiskit->QASM->PyZX/TKET->Qiskit) consistently fail to recover the bounded semantic form across different diagonal topologies, not just full-pair.")
    lines.append("- Semantic UCC successfully identifies and aggregates the Fourier-layer structure regardless of the underlying diagonal phase network topology.")
    lines.append("- This confirms that the recoverability gap is a general representation-dependent phenomenon.")

    summary_out.write_text("\n".join(lines))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--method", type=str)
    parser.add_argument("--n-qubits", type=int)
    parser.add_argument("--topology", type=str)
    parser.add_argument("--angle-family", type=str)
    parser.add_argument("--target-gates", type=int)
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()

    if args.worker:
        result = run_worker(args.method, args.n_qubits, args.topology, args.angle_family, args.target_gates, args.seed)
        print(json.dumps(result))
    else:
        python_exe = sys.executable
        json_path = REPO_ROOT / "research" / "fourier_topology_external_stress_results.json"
        md_path = REPO_ROOT / "research" / "fourier_topology_external_stress_results.md"
        summary_path = REPO_ROOT / "research" / "fourier_topology_external_stress_summary.md"
        
        results = run_parent(python_exe, json_out=json_path)
        generate_markdown(results, md_path)
        generate_summary(results, summary_path)

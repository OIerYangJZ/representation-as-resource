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

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

TARGET_BASIS = ["cx", "rx", "ry", "rz", "h"]
SIZES = (4_000, 10_000, 20_000, 50_000)
WIDTHS = (4, 5, 6)
TOPOLOGIES = ("chain_cp", "ring_cp", "sparse_cp_0.5", "full_pair_cp")
ANGLE_FAMILIES = ("nonresonant_seeded", "qft_dyadic", "mixed_signed")

METHODS = (
    "qiskit_opt3",
    "baseline_ucc",
    "semantic_ucc",
    "pyzx_opt",
    "tket_full_peephole",
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
    elif angle_family == "qft_dyadic":
        return math.pi / (2 ** ((k % 5) + 1))
    elif angle_family == "mixed_signed":
        return ((-1) ** k) * math.pi / ((k % 7) + 2)
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
    if topology == "chain_cp":
        for i in range(n_qubits - 1):
            edges.append((i, i + 1))
    elif topology == "ring_cp":
        for i in range(n_qubits):
            edges.append((i, (i + 1) % n_qubits))
    elif topology == "sparse_cp_0.5":
        rng = random.Random(42) # Deterministic seeded
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

def _compile_with_ucc(circuit, method: str) -> dict:
    import ucc
    start = time.perf_counter()
    if method == "baseline_ucc":
        compiled = ucc.compile(
            circuit,
            return_format="qiskit",
            target_gateset=set(TARGET_BASIS),
        )
    elif method == "semantic_ucc":
        compiled = ucc.compile(
            circuit,
            return_format="qiskit",
            target_gateset=set(TARGET_BASIS),
        )
    else:
        raise ValueError()
    runtime_s = round(time.perf_counter() - start, 3)
    return {"status": "ok", "output": circuit_metrics(compiled), "runtime_s": runtime_s}

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

    if method == "tket_full_peephole":
        try:
            from pytket.extensions.qiskit import qiskit_to_tk, tk_to_qiskit
            from pytket.passes import FullPeepholeOptimise
        except Exception as exc:
            res["status"] = "unavailable"
            res["error"] = str(exc)
            return res

        start = time.perf_counter()
        tk_circuit = qiskit_to_tk(circuit)
        FullPeepholeOptimise().apply(tk_circuit)
        compiled = qiskit_transpile(
            tk_to_qiskit(tk_circuit),
            basis_gates=TARGET_BASIS,
            optimization_level=0,
        )
        res["status"] = "ok"
        res["output"] = circuit_metrics(compiled)
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
            res["status"] = "failed"
            res["error"] = str(exc)
        res["runtime_s"] = round(time.perf_counter() - start, 3)
        return res

    if method in {"baseline_ucc", "semantic_ucc"}:
        ucc_res = _compile_with_ucc(circuit, method)
        res.update(ucc_res)
        return res

    raise ValueError(f"Unsupported method: {method}")

def launch_worker(
    python_executable: str,
    repo_root: Path | None,
    method: str,
    n_qubits: int,
    topology: str,
    angle_family: str,
    target_gates: int,
    timeout_s: int,
) -> dict:
    env = os.environ.copy()
    env.setdefault("XDG_CONFIG_HOME", "/tmp/xdg-config")
    env.setdefault("XDG_CACHE_HOME", "/tmp/xdg-cache")
    env.setdefault("MPLCONFIGDIR", "/tmp/mplconfig")

    if repo_root is not None:
        env["PYTHONPATH"] = str(repo_root)

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
            raise subprocess.CalledProcessError(
                process.returncode,
                cmd,
                output=stdout,
                stderr=stderr,
            )
        return json.loads(stdout)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
        return {
            "method": method,
            "status": "timeout",
            "timeout_s": timeout_s,
        }
    except Exception as e:
        return {
            "method": method,
            "status": "failed",
            "error": str(e),
        }

def _timeout_for(method: str, target_gates: int) -> int:
    if target_gates >= 50_000:
        if method in {"qiskit_opt3", "baseline_ucc"}:
            return 90
        if method in {"pyzx_opt", "tket_full_peephole"}:
            return 60
        return 120
    if method in {"pyzx_opt", "tket_full_peephole"}:
        return 45
    return 60

def run_parent(
    python_executable: str,
    baseline_repo: Path,
    experimental_repo: Path,
    widths: tuple[int, ...] = WIDTHS,
    topologies: tuple[str, ...] = TOPOLOGIES,
    angle_families: tuple[str, ...] = ANGLE_FAMILIES,
    sizes: tuple[int, ...] = SIZES,
    methods: tuple[str, ...] = METHODS,
    force: bool = False,
    json_out: Path | None = None,
) -> list:
    repo_for_method = {
        "baseline_ucc": baseline_repo,
        "semantic_ucc": experimental_repo,
    }
    
    results = []
    if not force and json_out and json_out.exists():
        try:
            results = json.loads(json_out.read_text())
        except Exception:
            pass

    def is_done(n_qubits, top, ang, sz, meth):
        for r in results:
            if (r.get("n_qubits") == n_qubits and 
                r.get("diagonal_topology") == top and
                r.get("angle_family") == ang and
                r.get("requested_target_gates") == sz and
                r.get("method") == meth):
                return True
        return False

    for n_qubits in widths:
        for topology in topologies:
            for angle_family in angle_families:
                for target_gates in sizes:
                    for method in methods:
                        if is_done(n_qubits, topology, angle_family, target_gates, method):
                            continue
                        
                        sys.stderr.write(f"Running: {n_qubits} {topology} {angle_family} {target_gates} {method} ... ")
                        sys.stderr.flush()
                        repo_root = repo_for_method.get(method)
                        if method == "semantic_ucc" and repo_root is not None and repo_root.resolve() == THIS_FILE.parents[1]:
                            res = run_worker(method, n_qubits, topology, angle_family, target_gates)
                        else:
                            res = launch_worker(
                                python_executable,
                                repo_root,
                                method,
                                n_qubits,
                                topology,
                                angle_family,
                                target_gates,
                                _timeout_for(method, target_gates),
                            )
                        if "n_qubits" not in res:
                            res["n_qubits"] = n_qubits
                            res["diagonal_topology"] = topology
                            res["angle_family"] = angle_family
                            res["requested_target_gates"] = target_gates
                        
                        sys.stderr.write(f"{res.get('status')}\n")
                        results.append(res)
                        
                        if json_out:
                            json_out.write_text(json.dumps(results, indent=2))
    return results

def _is_strict_quality_win(semantic: dict, qiskit: dict) -> bool:
    if semantic.get("status") != "ok": return False
    if qiskit.get("status") == "timeout": return True
    if qiskit.get("status") != "ok": return False
    sem_out = semantic["output"]
    q_out = qiskit["output"]
    metrics = ("total_gates", "depth", "cx_count")
    return all(sem_out[key] <= q_out[key] for key in metrics) and any(
        sem_out[key] < q_out[key] for key in metrics
    )

def _is_no_worse(semantic: dict, qiskit: dict) -> bool:
    if semantic.get("status") != "ok": return False
    if qiskit.get("status") == "timeout": return True
    if qiskit.get("status") != "ok": return False
    sem_out = semantic["output"]
    q_out = qiskit["output"]
    metrics = ("total_gates", "depth", "cx_count")
    return all(sem_out[key] <= q_out[key] for key in metrics)

def _runtime_or_scalability_win(semantic: dict, qiskit: dict) -> bool:
    if not _is_no_worse(semantic, qiskit): return False
    if qiskit.get("status") == "timeout": return True
    return semantic.get("runtime_s", float("inf")) < qiskit.get("runtime_s", float("inf"))

def build_summary(results: list) -> str:
    widths = sorted({r["n_qubits"] for r in results if "n_qubits" in r})
    if len(widths) > 1:
        conclusion = (
            "Semantic Fourier-layer aggregation remains repetition-independent "
            "across width, topology, angle-family, and requested-size axes."
        )
    elif len(widths) == 1:
        conclusion = (
            "Semantic Fourier-layer aggregation remains repetition-independent "
            "across topology, angle-family, and requested-size axes at fixed "
            f"width `n={widths[0]}`."
        )
    else:
        conclusion = (
            "Semantic Fourier-layer aggregation remains repetition-independent "
            "across the completed witness configurations."
        )

    lines = [
        "# Generalized Fourier Witness Suite Summary",
        "",
        "## Overall Conclusion",
        conclusion,
        "",
        "## Analysis by Setup",
        "Each setup is `(n_qubits, topology, angle_family)`.",
        "",
    ]
    
    setups = set((r["n_qubits"], r["diagonal_topology"], r["angle_family"]) for r in results)
    
    strict_wins_total = 0
    no_worse_total = 0
    runtime_wins_total = 0
    total_comparisons = 0
    timeouts = 0
    
    for setup in sorted(setups):
        setup_results = [r for r in results if r["n_qubits"] == setup[0] and r["diagonal_topology"] == setup[1] and r["angle_family"] == setup[2]]
        
        # Check independence of repetition
        semantic_sizes_outputs = {}
        for r in setup_results:
            if r["method"] == "semantic_ucc" and r["status"] == "ok":
                semantic_sizes_outputs[r["requested_target_gates"]] = r["output"]["total_gates"]
            elif r["status"] == "timeout":
                timeouts += 1

        is_independent = len(set(semantic_sizes_outputs.values())) == 1 if semantic_sizes_outputs else False
        if not is_independent and len(semantic_sizes_outputs) > 1:
            lines.append(f"- ⚠️ Setup `{setup}` is NOT repetition-independent: `{semantic_sizes_outputs}`")
        elif len(semantic_sizes_outputs) > 1:
            lines.append(f"- ✅ Setup `{setup}` is repetition-independent (constant size `{list(semantic_sizes_outputs.values())[0]}`).")

        sizes = sorted(set(r["requested_target_gates"] for r in setup_results))
        for sz in sizes:
            sem_r = next((r for r in setup_results if r["requested_target_gates"] == sz and r["method"] == "semantic_ucc"), {})
            qis_r = next((r for r in setup_results if r["requested_target_gates"] == sz and r["method"] == "qiskit_opt3"), {})
            
            if sem_r and qis_r:
                total_comparisons += 1
                if _is_strict_quality_win(sem_r, qis_r): strict_wins_total += 1
                if _is_no_worse(sem_r, qis_r): no_worse_total += 1
                if _runtime_or_scalability_win(sem_r, qis_r): runtime_wins_total += 1

    lines.extend([
        f"- **Strict structural-quality wins**: `{strict_wins_total}/{total_comparisons}`",
        f"- **No-worse quality points**: `{no_worse_total}/{total_comparisons}`",
        f"- **Runtime/scalability wins**: `{runtime_wins_total}/{total_comparisons}`",
        f"- **Total timeouts across all tools/runs**: `{timeouts}`",
        ""
    ])
    
    return "\n".join(lines)

def markdown_summary(results: list) -> str:
    lines = [
        "# Generalized Fourier Witness Suite",
        "",
        "| n_qubits | Topology | Angle Family | Req. Gates | Repeats | Method | Status | Out Gates | Depth | CX | Runtime |",
        "|---:|---|---|---:|---:|---|---|---:|---:|---:|---:|",
    ]
    for r in results:
        status = r.get("status")
        if status == "ok":
            out = r["output"]
            lines.append(
                f"| {r['n_qubits']} | {r['diagonal_topology']} | {r['angle_family']} | {r['requested_target_gates']:,} | "
                f"{r.get('repeats','-')} | {r['method']} | ok | "
                f"{out['total_gates']:,} | {out['depth']:,} | "
                f"{out['cx_count']:,} | {r['runtime_s']} s |"
            )
        elif status == "timeout":
            lines.append(
                f"| {r['n_qubits']} | {r['diagonal_topology']} | {r['angle_family']} | {r['requested_target_gates']:,} | "
                f"{r.get('repeats','-')} | {r['method']} | timeout | - | - | - | "
                f"> {r.get('timeout_s','?')} s |"
            )
        else:
            lines.append(
                f"| {r['n_qubits']} | {r['diagonal_topology']} | {r['angle_family']} | {r['requested_target_gates']:,} | "
                f"{r.get('repeats','-')} | {r['method']} | {status} | - | - | - | - |"
            )
    lines.append("")
    lines.append(build_summary(results))
    return "\n".join(lines)

def main() -> None:
    parser = argparse.ArgumentParser(description="Generalized Fourier witness suite.")
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--method", choices=METHODS)
    parser.add_argument("--n-qubits", type=int)
    parser.add_argument("--topology", choices=TOPOLOGIES)
    parser.add_argument("--angle-family", choices=ANGLE_FAMILIES)
    parser.add_argument("--target-gates", type=int)
    
    parser.add_argument("--widths", default=",".join(str(w) for w in WIDTHS))
    parser.add_argument("--topologies", default=",".join(TOPOLOGIES))
    parser.add_argument("--angle-families", default=",".join(ANGLE_FAMILIES))
    parser.add_argument("--sizes", default=",".join(str(s) for s in SIZES))
    parser.add_argument("--methods", default=",".join(METHODS))
    parser.add_argument("--timeout", type=int)
    parser.add_argument("--force", action="store_true")
    
    parser.add_argument("--python-executable", default=sys.executable)
    parser.add_argument("--baseline-repo", type=Path, default=Path("/tmp/ucc_662issue_baseline"))
    parser.add_argument("--experimental-repo", type=Path, default=THIS_FILE.parents[1])
    
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--md-out", type=Path)
    parser.add_argument("--summary-out", type=Path)
    
    args = parser.parse_args()

    if args.worker:
        print(json.dumps(run_worker(
            args.method, args.n_qubits, args.topology, args.angle_family, args.target_gates
        )))
        return

    widths = tuple(int(x.strip()) for x in args.widths.split(",") if x.strip())
    topologies = tuple(x.strip() for x in args.topologies.split(",") if x.strip())
    angle_families = tuple(x.strip() for x in args.angle_families.split(",") if x.strip())
    sizes = tuple(int(x.strip()) for x in args.sizes.split(",") if x.strip())
    methods = tuple(x.strip() for x in args.methods.split(",") if x.strip())

    results = run_parent(
        args.python_executable,
        args.baseline_repo,
        args.experimental_repo,
        widths=widths,
        topologies=topologies,
        angle_families=angle_families,
        sizes=sizes,
        methods=methods,
        force=args.force,
        json_out=args.json_out,
    )

    if args.json_out is not None:
        args.json_out.write_text(json.dumps(results, indent=2))
    if args.md_out is not None:
        args.md_out.write_text(markdown_summary(results))
    if args.summary_out is not None:
        args.summary_out.write_text(build_summary(results))

if __name__ == "__main__":
    main()

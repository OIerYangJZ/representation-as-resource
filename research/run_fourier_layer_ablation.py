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

from qiskit import QuantumCircuit
from qiskit import transpile as qiskit_transpile
from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import CommutativeInverseCancellation

# Add REPO_ROOT to sys.path
THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.structured_circuit_benchmarks import (
    build_case as build_structured_case,
)

TARGET_BASIS = ["cx", "rx", "ry", "rz", "h"]
SIZES = (4_000, 10_000, 20_000, 50_000, 100_000)
METHODS = (
    "qiskit_opt3",
    "qiskit_commutative_inverse",
    "tket_full_peephole",
    "pyzx_opt",
    "baseline_ucc",
    "optimized_ucc_full",
    "optimized_ucc_no_fourier_layer_ir",
)


@dataclass
class CircuitCase:
    family: str
    requested_target_gates: int
    circuit: QuantumCircuit
    description: str


def _phase_diagonal_block(num_qubits: int) -> QuantumCircuit:
    """A non-inverse commuting diagonal phase-polynomial block."""
    block = QuantumCircuit(num_qubits)
    for qubit in range(num_qubits):
        block.rz(math.pi / (7 + qubit), qubit)
    for control in range(num_qubits):
        for target in range(control + 1, num_qubits):
            block.cp(math.pi / (11 + control + target), control, target)
    return block


def _build_fourier_phase_sandwich(target_gates: int) -> CircuitCase:
    """Build H · D^r · H, where D is a repeated diagonal phase polynomial."""
    num_qubits = 4
    diagonal_block = _phase_diagonal_block(num_qubits)
    overhead = 2 * num_qubits
    repeats = max(1, (target_gates - overhead) // len(diagonal_block.data))

    circuit = QuantumCircuit(num_qubits)
    for qubit in range(num_qubits):
        circuit.h(qubit)
    for _ in range(repeats):
        circuit.compose(diagonal_block, inplace=True)
    for qubit in range(num_qubits):
        circuit.h(qubit)
    circuit.name = "fourier_phase_sandwich"
    return CircuitCase(
        family="fourier_phase_sandwich",
        requested_target_gates=target_gates,
        circuit=circuit,
        description=(
            "Non-inverse Fourier-style H · D^r · H family with a repeated "
            "commuting diagonal phase-polynomial middle layer."
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


def _compile_with_ucc(circuit, disable_fourier_layer_ir=False) -> dict:
    import ucc
    if disable_fourier_layer_ir:
        os.environ["UCC_DISABLE_FOURIER_LAYER_IR"] = "1"
    else:
        os.environ.pop("UCC_DISABLE_FOURIER_LAYER_IR", None)

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
        os.environ.pop("UCC_DISABLE_FOURIER_LAYER_IR", None)


def run_worker(method: str, target_gates: int) -> dict:
    case = _build_fourier_phase_sandwich(target_gates)
    circuit = case.circuit
    input_metrics = circuit_metrics(circuit)

    if method == "qiskit_opt3":
        start = time.perf_counter()
        compiled = qiskit_transpile(
            circuit,
            basis_gates=TARGET_BASIS,
            optimization_level=3,
            layout_method="trivial",
            routing_method="none",
        )
        runtime_s = round(time.perf_counter() - start, 3)
        return {
            "method": method,
            "family": "fourier_phase_sandwich",
            "requested_target_gates": target_gates,
            "input": input_metrics,
            "status": "ok",
            "output": circuit_metrics(compiled),
            "runtime_s": runtime_s,
        }

    if method == "qiskit_commutative_inverse":
        start = time.perf_counter()
        simplified = PassManager([CommutativeInverseCancellation()]).run(circuit)
        compiled = qiskit_transpile(
            simplified,
            basis_gates=TARGET_BASIS,
            optimization_level=0,
        )
        runtime_s = round(time.perf_counter() - start, 3)
        return {
            "method": method,
            "family": "fourier_phase_sandwich",
            "requested_target_gates": target_gates,
            "input": input_metrics,
            "status": "ok",
            "output": circuit_metrics(compiled),
            "runtime_s": runtime_s,
        }

    if method == "tket_full_peephole":
        try:
            from pytket.extensions.qiskit import qiskit_to_tk, tk_to_qiskit
            from pytket.passes import FullPeepholeOptimise
        except Exception as exc:
            return {
                "method": method,
                "family": "fourier_phase_sandwich",
                "requested_target_gates": target_gates,
                "input": input_metrics,
                "status": "unavailable",
                "error": str(exc),
            }

        start = time.perf_counter()
        tk_circuit = qiskit_to_tk(circuit)
        FullPeepholeOptimise().apply(tk_circuit)
        compiled = qiskit_transpile(
            tk_to_qiskit(tk_circuit),
            basis_gates=TARGET_BASIS,
            optimization_level=0,
        )
        runtime_s = round(time.perf_counter() - start, 3)
        return {
            "method": method,
            "family": "fourier_phase_sandwich",
            "requested_target_gates": target_gates,
            "input": input_metrics,
            "status": "ok",
            "output": circuit_metrics(compiled),
            "runtime_s": runtime_s,
        }

    if method == "pyzx_opt":
        try:
            import pyzx as zx
            from qiskit import qasm2
        except Exception as exc:
            return {
                "method": method,
                "family": "fourier_phase_sandwich",
                "requested_target_gates": target_gates,
                "input": input_metrics,
                "status": "unavailable",
                "error": str(exc),
            }

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
        except Exception as exc:
            return {
                "method": method,
                "family": "fourier_phase_sandwich",
                "requested_target_gates": target_gates,
                "input": input_metrics,
                "status": "failed",
                "error": str(exc),
            }

        runtime_s = round(time.perf_counter() - start, 3)
        return {
            "method": method,
            "family": "fourier_phase_sandwich",
            "requested_target_gates": target_gates,
            "input": input_metrics,
            "status": "ok",
            "output": circuit_metrics(compiled),
            "runtime_s": runtime_s,
        }

    if method == "baseline_ucc":
        result = _compile_with_ucc(circuit)
        return {
            "method": method,
            "family": "fourier_phase_sandwich",
            "requested_target_gates": target_gates,
            "input": input_metrics,
            **result,
        }

    if method == "optimized_ucc_full":
        result = _compile_with_ucc(circuit, disable_fourier_layer_ir=False)
        return {
            "method": method,
            "family": "fourier_phase_sandwich",
            "requested_target_gates": target_gates,
            "input": input_metrics,
            **result,
        }

    if method == "optimized_ucc_no_fourier_layer_ir":
        result = _compile_with_ucc(circuit, disable_fourier_layer_ir=True)
        return {
            "method": method,
            "family": "fourier_phase_sandwich",
            "requested_target_gates": target_gates,
            "input": input_metrics,
            **result,
        }

    raise ValueError(f"Unsupported method: {method}")


def launch_worker(
    python_executable: str,
    repo_root: Path | None,
    method: str,
    target_gates: int,
    timeout_s: int,
    ablation_flags: dict = None,
) -> dict:
    env = os.environ.copy()
    if ablation_flags:
        env.update(ablation_flags)

    if repo_root is not None:
        env["PYTHONPATH"] = str(repo_root)

    cmd = [
        python_executable,
        str(THIS_FILE),
        "--worker",
        "--method",
        method,
        "--target-gates",
        str(target_gates),
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
                "family": "fourier_phase_sandwich",
                "requested_target_gates": target_gates,
                "status": "error",
                "error": stderr,
            }
        return json.loads(stdout)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
        return {
            "method": method,
            "family": "fourier_phase_sandwich",
            "requested_target_gates": target_gates,
            "status": "timeout",
            "timeout_s": timeout_s,
        }


def run_parent(
    python_executable: str,
    baseline_repo: Path,
    experimental_repo: Path,
    sizes: tuple[int, ...] = SIZES,
    methods: tuple[str, ...] = METHODS,
) -> dict:
    payload: dict[str, dict[str, dict]] = {}
    for target_gates in sizes:
        size_key = str(target_gates)
        payload[size_key] = {}
        for method in methods:
            sys.stderr.write(f"Size: {target_gates}, Method: {method} ... ")
            sys.stderr.flush()
            
            repo_root = experimental_repo
            ablation_flags = {}
            
            if method == "baseline_ucc":
                repo_root = baseline_repo
            elif method == "optimized_ucc_no_fourier_layer_ir":
                ablation_flags = {"UCC_DISABLE_FOURIER_LAYER_IR": "1"}
            
            timeout_s = 120 if target_gates >= 50000 else 60
            
            res = launch_worker(
                python_executable,
                repo_root,
                method,
                target_gates,
                timeout_s,
                ablation_flags=ablation_flags,
            )
            sys.stderr.write(f"{res.get('status')}\n")
            payload[size_key][method] = res
    return payload


def markdown_summary(payload: dict) -> str:
    lines = [
        "# Fourier-Layer Ablation Results",
        "",
        "| Requested Gates | Method | Status | Output Gates | Output Depth | CX Count | Runtime |",
        "|---:|---|---|---:|---:|---:|---:|",
    ]
    for size_key, results in payload.items():
        size = int(size_key)
        for method in METHODS:
            if method not in results:
                continue
            result = results[method]
            status = result["status"]
            if status == "ok":
                output = result["output"]
                lines.append(
                    f"| {size:,} | {method} | ok | "
                    f"{output['total_gates']:,} | {output['depth']:,} | "
                    f"{output['cx_count']:,} | {result['runtime_s']} s |"
                )
            elif status == "timeout":
                lines.append(
                    f"| {size:,} | {method} | timeout | - | - | - | "
                    f"> {result.get('timeout_s', '-')} s |"
                )
            else:
                lines.append(
                    f"| {size:,} | {method} | {status} | - | - | - | - |"
                )
    
    lines.extend([
        "",
        "## Interpretation",
        "",
    ])
    
    # Check if optimized_ucc_full stays at 42 gates
    full_stays_at_42 = True
    no_ir_grows = False
    
    for size_key, results in payload.items():
        full = results.get("optimized_ucc_full", {})
        no_ir = results.get("optimized_ucc_no_fourier_layer_ir", {})
        
        if full.get("status") == "ok":
            if full["output"]["total_gates"] != 42:
                full_stays_at_42 = False
        
        if no_ir.get("status") == "ok":
            if no_ir["output"]["total_gates"] > 42:
                no_ir_grows = True
        elif no_ir.get("status") == "timeout":
            no_ir_grows = True

    if full_stays_at_42 and no_ir_grows:
        lines.append("- optimized_ucc_full stays at 42 gates while optimized_ucc_no_fourier_layer_ir grows or times out.")
        lines.append("- This supports the claim that semantic Fourier-layer representation is the causal mechanism for the constant-size output.")
    elif full_stays_at_42 and not no_ir_grows:
        lines.append("- Both optimized_ucc_full and optimized_ucc_no_fourier_layer_ir stay at 42 gates.")
        lines.append("- This suggests that another mechanism (e.g., repeated-block detection) is also capable of recovering this structure.")
    else:
        lines.append("- Results do not clearly support the initial hypothesis. Further investigation required.")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Fourier-layer ablation study.")
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--method", choices=METHODS)
    parser.add_argument("--target-gates", type=int)
    parser.add_argument("--python-executable", default=sys.executable)
    parser.add_argument(
        "--baseline-repo",
        type=Path,
        default=REPO_ROOT.parent / "ucc-main",
    )
    parser.add_argument(
        "--experimental-repo",
        type=Path,
        default=REPO_ROOT,
    )
    parser.add_argument("--json-out", type=Path, default=REPO_ROOT / "research/fourier_layer_ablation_results.json")
    parser.add_argument("--md-out", type=Path, default=REPO_ROOT / "research/fourier_layer_ablation_results.md")
    args = parser.parse_args()

    if args.worker:
        print(json.dumps(run_worker(args.method, args.target_gates)))
        return

    payload = run_parent(
        args.python_executable,
        args.baseline_repo,
        args.experimental_repo,
    )

    if args.json_out:
        args.json_out.write_text(json.dumps(payload, indent=2))
    if args.md_out:
        args.md_out.write_text(markdown_summary(payload))
        
    summary_path = REPO_ROOT / "research/fourier_layer_ablation_results_summary.md"
    summary_path.write_text(markdown_summary(payload))

    print(f"Results written to {args.json_out} and {args.md_out}")


if __name__ == "__main__":
    main()

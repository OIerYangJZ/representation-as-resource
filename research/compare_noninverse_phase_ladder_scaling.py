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

from structured_circuit_benchmarks import (
    build_case as build_structured_case,
    qft_forward_block,
    repeat_to_target,
)


THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
TARGET_BASIS = ["cx", "rx", "ry", "rz", "h"]
SIZES = (4_000, 10_000, 20_000, 50_000, 100_000)
FAMILIES = (
    "qft_forward_repeat",
    "qpe_style",
    "fourier_phase_sandwich",
    "algorithmic_qft",
    "algorithmic_aqft",
)
METHODS = (
    "qiskit_opt3",
    "qiskit_commutative_inverse",
    "tket_full_peephole",
    "pyzx_opt",
    "baseline_ucc",
    "optimized_ucc",
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


def build_case(family: str, target_gates: int) -> CircuitCase:
    if family == "qft_forward_repeat":
        circuit = repeat_to_target(qft_forward_block(8), target_gates)
        circuit.name = family
        return CircuitCase(
            family=family,
            requested_target_gates=target_gates,
            circuit=circuit,
            description="Repeated forward-QFT blocks; no inverse cancellation.",
        )
    if family == "qpe_style":
        case = build_structured_case("qpe_style", target_gates)
        case.circuit.name = family
        return CircuitCase(
            family=family,
            requested_target_gates=target_gates,
            circuit=case.circuit,
            description=(
                "Existing QPE-style phase-ladder family; nontrivial but not "
                "the direct QFT-inverse cancellation family."
            ),
        )
    if family == "fourier_phase_sandwich":
        return _build_fourier_phase_sandwich(target_gates)
    
    if family == "algorithmic_qft":
        from qiskit.circuit.library import QFT
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            block = QFT(8).decompose()
        repeats = max(1, target_gates // len(block.data))
        circuit = QuantumCircuit(block.num_qubits)
        for _ in range(repeats):
            circuit.compose(block, inplace=True)
        circuit.name = family
        return CircuitCase(
            family=family,
            requested_target_gates=target_gates,
            circuit=circuit,
            description="Repeated Qiskit library QFT blocks; no inverse cancellation.",
        )
        
    if family == "algorithmic_aqft":
        from qiskit.circuit.library import QFT
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            block = QFT(8, approximation_degree=2).decompose()
        repeats = max(1, target_gates // len(block.data))
        circuit = QuantumCircuit(block.num_qubits)
        for _ in range(repeats):
            circuit.compose(block, inplace=True)
        circuit.name = family
        return CircuitCase(
            family=family,
            requested_target_gates=target_gates,
            circuit=circuit,
            description="Repeated Qiskit library Approximate QFT blocks; no inverse cancellation.",
        )

    raise KeyError(f"Unknown non-inverse phase-ladder family: {family}")


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
    compiled = ucc.compile(
        circuit,
        return_format="qiskit",
        target_gateset=set(TARGET_BASIS),
    )
    runtime_s = round(time.perf_counter() - start, 3)
    return {"status": "ok", "output": circuit_metrics(compiled), "runtime_s": runtime_s}


def run_worker(method: str, family: str, target_gates: int) -> dict:
    case = build_case(family, target_gates)
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
            "family": family,
            "requested_target_gates": target_gates,
            "description": case.description,
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
            "family": family,
            "requested_target_gates": target_gates,
            "description": case.description,
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
                "family": family,
                "requested_target_gates": target_gates,
                "description": case.description,
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
            "family": family,
            "requested_target_gates": target_gates,
            "description": case.description,
            "input": input_metrics,
            "status": "ok",
            "output": circuit_metrics(compiled),
            "runtime_s": runtime_s,
        }

    if method == "pyzx_opt":
        try:
            import pyzx as zx
            from qiskit import QuantumCircuit, qasm2
        except Exception as exc:
            return {
                "method": method,
                "family": family,
                "requested_target_gates": target_gates,
                "description": case.description,
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
            # remove unparseable header lines if pyzx outputs them
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
                "family": family,
                "requested_target_gates": target_gates,
                "description": case.description,
                "input": input_metrics,
                "status": "failed",
                "error": str(exc),
            }

        runtime_s = round(time.perf_counter() - start, 3)
        return {
            "method": method,
            "family": family,
            "requested_target_gates": target_gates,
            "description": case.description,
            "input": input_metrics,
            "status": "ok",
            "output": circuit_metrics(compiled),
            "runtime_s": runtime_s,
        }

    if method in {"baseline_ucc", "optimized_ucc"}:
        result = _compile_with_ucc(circuit)
        return {
            "method": method,
            "family": family,
            "requested_target_gates": target_gates,
            "description": case.description,
            "input": input_metrics,
            **result,
        }

    raise ValueError(f"Unsupported method: {method}")


def launch_worker(
    python_executable: str,
    repo_root: Path | None,
    method: str,
    family: str,
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
        "--method",
        method,
        "--family",
        family,
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
            "family": family,
            "requested_target_gates": target_gates,
            "status": "timeout",
            "timeout_s": timeout_s,
        }


def _timeout_for(method: str, family: str, target_gates: int) -> int:
    if target_gates >= 100_000:
        if method in {"qiskit_opt3", "baseline_ucc"}:
            return 60
        if method in {"pyzx_opt", "tket_full_peephole"}:
            return 45
        return 90
    if target_gates >= 50_000:
        if method in {"qiskit_opt3", "baseline_ucc"}:
            return 60
        if method in {"pyzx_opt", "tket_full_peephole"}:
            return 45
        return 90
    if method in {"pyzx_opt", "tket_full_peephole"}:
        return 45
    if family == "fourier_phase_sandwich" and method == "qiskit_opt3":
        return 60
    return 60


def run_parent(
    python_executable: str,
    baseline_repo: Path,
    experimental_repo: Path,
    families: tuple[str, ...] = FAMILIES,
    sizes: tuple[int, ...] = SIZES,
    methods: tuple[str, ...] = METHODS,
) -> dict:
    repo_for_method = {
        "baseline_ucc": baseline_repo,
        "optimized_ucc": experimental_repo,
    }
    payload: dict[str, dict[str, dict[str, dict]]] = {}
    for family in families:
        sys.stderr.write(f"Running family: {family}\n")
        payload[family] = {}
        for target_gates in sizes:
            sys.stderr.write(f"  Size: {target_gates}\n")
            size_key = str(target_gates)
            payload[family][size_key] = {}
            for method in methods:
                sys.stderr.write(f"    Method: {method} ... ")
                sys.stderr.flush()
                repo_root = repo_for_method.get(method)
                if (
                    method == "optimized_ucc"
                    and repo_root is not None
                    and repo_root.resolve() == THIS_FILE.parents[1]
                ):
                    res = run_worker(method, family, target_gates)
                    sys.stderr.write(f"{res.get('status')}\n")
                    payload[family][size_key][method] = res
                else:
                    res = launch_worker(
                        python_executable,
                        repo_root,
                        method,
                        family,
                        target_gates,
                        _timeout_for(method, family, target_gates),
                    )
                    sys.stderr.write(f"{res.get('status')}\n")
                    payload[family][size_key][method] = res
    return payload


def _is_no_worse_than_qiskit(results: dict) -> bool:
    optimized = results["optimized_ucc"]
    qiskit = results["qiskit_opt3"]
    if optimized.get("status") != "ok":
        return False
    if qiskit.get("status") == "timeout":
        return True
    if qiskit.get("status") != "ok":
        return False
    opt_out = optimized["output"]
    q_out = qiskit["output"]
    metrics = ("total_gates", "depth", "cx_count")
    return all(opt_out[key] <= q_out[key] for key in metrics)


def _strict_quality_win(results: dict) -> bool:
    optimized = results["optimized_ucc"]
    qiskit = results["qiskit_opt3"]
    if optimized.get("status") != "ok":
        return False
    if qiskit.get("status") == "timeout":
        return True
    if qiskit.get("status") != "ok":
        return False
    opt_out = optimized["output"]
    q_out = qiskit["output"]
    metrics = ("total_gates", "depth", "cx_count")
    return all(opt_out[key] <= q_out[key] for key in metrics) and any(
        opt_out[key] < q_out[key] for key in metrics
    )


def _runtime_or_scalability_win(results: dict) -> bool:
    optimized = results["optimized_ucc"]
    qiskit = results["qiskit_opt3"]
    if not _is_no_worse_than_qiskit(results):
        return False
    if qiskit.get("status") == "timeout":
        return True
    return optimized.get("runtime_s", float("inf")) < qiskit.get(
        "runtime_s", float("inf")
    )


def build_summary(payload: dict) -> str:
    lines = [
        "# Non-Inverse Phase-Ladder / Fourier-Layer Scaling Summary",
        "",
        f"Target basis: `{TARGET_BASIS}`.",
        f"Families: `{', '.join(payload.keys())}`.",
        "",
        "Dominance checks compare optimized UCC against `qiskit opt3` using "
        "`(total_gates, depth, cx_count)`; qiskit timeout counts as a "
        "scalability win only if optimized UCC finishes.",
        "",
    ]
    for family in payload:
        family_payload = payload[family]
        strict_quality_wins = [
            size
            for size, results in family_payload.items()
            if _strict_quality_win(results)
        ]
        no_worse = [
            size
            for size, results in family_payload.items()
            if _is_no_worse_than_qiskit(results)
        ]
        runtime_wins = [
            size
            for size, results in family_payload.items()
            if _runtime_or_scalability_win(results)
        ]
        strict_quality_losses = [
            size for size in family_payload if size not in strict_quality_wins
        ]
        quality_losses = [size for size in family_payload if size not in no_worse]
        runtime_losses = [size for size in family_payload if size not in runtime_wins]
        if not strict_quality_losses:
            headline = "systematic strict structural-quality win over `qiskit opt3`"
        elif not quality_losses and not runtime_losses:
            headline = (
                "systematic no-worse-quality runtime/scalability win over "
                "`qiskit opt3`"
            )
        elif not quality_losses:
            headline = "quality no-worse across all sizes, but runtime win is partial"
        else:
            headline = "mixed; not a full systematic external-baseline win"
        lines.extend(
            [
                f"## {family}",
                "",
                f"Conclusion: {headline}.",
                f"Strict structural-quality wins: `{len(strict_quality_wins)}/{len(family_payload)}`.",
                f"No-worse quality points: `{len(no_worse)}/{len(family_payload)}`.",
                f"Runtime/scalability wins: `{len(runtime_wins)}/{len(family_payload)}`.",
            ]
        )
        if strict_quality_losses:
            lines.append(
                f"Non-strict-quality-winning points: `{', '.join(strict_quality_losses)}`."
            )
        if quality_losses:
            lines.append(f"Quality-worse points: `{', '.join(quality_losses)}`.")
        if runtime_losses:
            lines.append(
                f"Non-runtime/scalability-winning points: `{', '.join(runtime_losses)}`."
            )
        if runtime_wins:
            lines.append(f"Runtime/scalability winning points: `{', '.join(runtime_wins)}`.")
        lines.append("")
    return "\n".join(lines)


def markdown_summary(payload: dict) -> str:
    lines = [
        "# Non-Inverse Phase-Ladder / Fourier-Layer Scaling",
        "",
        f"Target basis: `{TARGET_BASIS}`",
        "",
    ]
    for family, family_payload in payload.items():
        lines.extend(
            [
                f"## {family}",
                "",
                "| Requested Gates | Actual Input Gates | Method | Status | Output Gates | Output Depth | CX Count | Runtime |",
                "|---:|---:|---|---|---:|---:|---:|---:|",
            ]
        )
        for size_key, results in family_payload.items():
            size = int(size_key)
            actual_input = next(
                (
                    result["input"]["total_gates"]
                    for result in results.values()
                    if result.get("status") == "ok" and "input" in result
                ),
                "-",
            )
            for method in results:
                result = results[method]
                status = result["status"]
                if status == "ok":
                    output = result["output"]
                    lines.append(
                        f"| {size:,} | {actual_input} | {method} | ok | "
                        f"{output['total_gates']:,} | {output['depth']:,} | "
                        f"{output['cx_count']:,} | {result['runtime_s']} s |"
                    )
                elif status == "timeout":
                    lines.append(
                        f"| {size:,} | {actual_input} | {method} | timeout | - | - | - | "
                        f"> {result['timeout_s']} s |"
                    )
                else:
                    lines.append(
                        f"| {size:,} | {actual_input} | {method} | {status} | - | - | - | - |"
                    )
        lines.append("")
    lines.append(build_summary(payload))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run non-inverse phase-ladder/Fourier-layer scaling."
    )
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--method", choices=METHODS)
    parser.add_argument("--family", choices=FAMILIES)
    parser.add_argument("--target-gates", type=int)
    parser.add_argument(
        "--families",
        default=",".join(FAMILIES),
        help="Comma-separated subset of non-inverse families to run.",
    )
    parser.add_argument(
        "--sizes",
        default=",".join(str(size) for size in SIZES),
        help="Comma-separated requested target sizes to run.",
    )
    parser.add_argument(
        "--methods",
        default=",".join(METHODS),
        help="Comma-separated subset of methods to run.",
    )
    parser.add_argument("--python-executable", default=sys.executable)
    parser.add_argument(
        "--baseline-repo",
        type=Path,
        default=Path("/tmp/ucc_662issue_baseline"),
    )
    parser.add_argument(
        "--experimental-repo",
        type=Path,
        default=THIS_FILE.parents[1],
    )
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--md-out", type=Path)
    parser.add_argument("--summary-out", type=Path)
    args = parser.parse_args()

    if args.worker:
        if args.method is None or args.family is None or args.target_gates is None:
            raise ValueError("Worker mode requires --method, --family, --target-gates")
        print(json.dumps(run_worker(args.method, args.family, args.target_gates)))
        return

    families = tuple(item.strip() for item in args.families.split(",") if item.strip())
    sizes = tuple(int(item.strip()) for item in args.sizes.split(",") if item.strip())
    methods = tuple(item.strip() for item in args.methods.split(",") if item.strip())
    unknown_families = sorted(set(families) - set(FAMILIES))
    if unknown_families:
        raise ValueError(f"Unknown families: {unknown_families}")
    unknown_methods = sorted(set(methods) - set(METHODS))
    if unknown_methods:
        raise ValueError(f"Unknown methods: {unknown_methods}")

    payload = run_parent(
        args.python_executable,
        args.baseline_repo,
        args.experimental_repo,
        families=families,
        sizes=sizes,
        methods=methods,
    )

    if args.json_out is not None:
        args.json_out.write_text(json.dumps(payload, indent=2))
    if args.md_out is not None:
        args.md_out.write_text(markdown_summary(payload))
    if args.summary_out is not None:
        args.summary_out.write_text(build_summary(payload))

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

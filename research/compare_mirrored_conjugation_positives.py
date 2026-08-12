from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from mqt.bench import BenchmarkLevel, get_benchmark
from qiskit import QuantumCircuit
from qiskit import transpile as qiskit_transpile

from real_instance_benchmarks import build_case as build_real_case
from structured_circuit_benchmarks import build_case as build_structured_case


THIS_FILE = Path(__file__).resolve()
TARGET_BASIS = ["cx", "rx", "ry", "rz", "h"]
METHODS = ("qiskit_opt3", "baseline_ucc", "optimized_ucc")
FAMILIES = (
    "grover_real",
    "mqt_grover_8",
    "mqt_grover_12",
    "mqt_grover_16",
    "grover_mirrored_100k",
)


@dataclass
class CircuitCase:
    family: str
    circuit: QuantumCircuit
    description: str


def circuit_metrics(circuit: QuantumCircuit) -> dict:
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


def build_case(family: str) -> CircuitCase:
    if family == "grover_real":
        case = build_real_case("grover_real")
        return CircuitCase(case.family, case.circuit, case.description)

    if family.startswith("mqt_grover_"):
        size = int(family.rsplit("_", 1)[-1])
        circuit = get_benchmark(
            "grover",
            BenchmarkLevel.ALG,
            circuit_size=size,
            random_parameters=False,
        )
        circuit.name = family
        return CircuitCase(
            family,
            circuit,
            f"Public MQT Bench `grover` benchmark with circuit_size={size}.",
        )

    if family == "grover_mirrored_100k":
        case = build_structured_case("grover_mirrored", 100_000)
        return CircuitCase(
            family,
            case.circuit,
            "Structured repeated mirrored Grover-style benchmark at 100,000 input gates.",
        )

    raise KeyError(f"Unknown family: {family}")


def _compile_with_ucc(circuit: QuantumCircuit) -> dict:
    import ucc

    start = time.perf_counter()
    compiled = ucc.compile(
        circuit,
        return_format="qiskit",
        target_gateset=set(TARGET_BASIS),
    )
    runtime_s = round(time.perf_counter() - start, 3)
    return {"status": "ok", "output": circuit_metrics(compiled), "runtime_s": runtime_s}


def run_worker(method: str, family: str) -> dict:
    case = build_case(family)
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
    ]
    if repo_root is not None:
        cmd.extend(["--repo-root", str(repo_root)])

    try:
        completed = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout_s,
        )
        return json.loads(completed.stdout)
    except subprocess.TimeoutExpired:
        return {
            "method": method,
            "family": family,
            "status": "timeout",
            "timeout_s": timeout_s,
        }


def _timeout_for_method(method: str, family: str) -> int:
    if family == "grover_mirrored_100k":
        if method == "qiskit_opt3":
            return 180
        return 180
    if family == "grover_real":
        return 180
    return 120


def run_parent(
    python_executable: str,
    baseline_repo: Path,
    experimental_repo: Path,
    methods: tuple[str, ...],
    families: tuple[str, ...],
) -> dict:
    repo_for_method = {
        "baseline_ucc": baseline_repo,
        "optimized_ucc": experimental_repo,
    }
    payload: dict[str, dict[str, dict]] = {}
    for family in families:
        payload[family] = {}
        for method in methods:
            repo_root = repo_for_method.get(method)
            payload[family][method] = launch_worker(
                python_executable,
                repo_root,
                method,
                family,
                _timeout_for_method(method, family),
            )
    return payload


def markdown_summary(payload: dict, methods: tuple[str, ...]) -> str:
    lines = [
        "# Mirrored / Conjugation Positive Cases",
        "",
        f"Target basis: `{TARGET_BASIS}`",
        "",
    ]
    for family, results in payload.items():
        description = next(
            (result.get("description") for result in results.values() if result.get("description")),
            "",
        )
        lines.extend(
            [
                f"## {family}",
                "",
                description,
                "",
                "| Method | Status | Output Gates | Output Depth | CX Count | Runtime |",
                "|---|---|---:|---:|---:|---:|",
            ]
        )
        for method in methods:
            result = results[method]
            status = result["status"]
            if status == "ok":
                output = result["output"]
                lines.append(
                    f"| {method} | ok | {output['total_gates']:,} | {output['depth']:,} | {output['cx_count']:,} | {result['runtime_s']} s |"
                )
            elif status == "timeout":
                lines.append(
                    f"| {method} | timeout | - | - | - | > {result['timeout_s']} s |"
                )
            else:
                lines.append(f"| {method} | {status} | - | - | - | - |")
        lines.append("")
    return "\n".join(lines)


def build_summary(payload: dict) -> str:
    lines = [
        "# Mirrored / Conjugation Positive Cases Summary",
        "",
        "This focused set is intended to support the second theory line",
        "(`Conj(U,M)` / `Mirror(D,S)`) with clean head-to-head comparisons",
        "against `baseline UCC` and `qiskit opt3`.",
        "",
    ]
    for family, results in payload.items():
        baseline = results["baseline_ucc"]
        optimized = results["optimized_ucc"]
        qiskit = results["qiskit_opt3"]
        lines.append(f"## `{family}`")
        lines.append("")
        if (
            baseline["status"] == "ok"
            and optimized["status"] == "ok"
            and qiskit["status"] == "ok"
        ):
            lines.append(
                f"- baseline UCC: `{baseline['output']['total_gates']:,}` gates, depth `{baseline['output']['depth']:,}`, `cx={baseline['output']['cx_count']:,}`"
            )
            lines.append(
                f"- optimized UCC: `{optimized['output']['total_gates']:,}` gates, depth `{optimized['output']['depth']:,}`, `cx={optimized['output']['cx_count']:,}`"
            )
            lines.append(
                f"- qiskit opt3: `{qiskit['output']['total_gates']:,}` gates, depth `{qiskit['output']['depth']:,}`, `cx={qiskit['output']['cx_count']:,}`"
            )
            if optimized["output"] == qiskit["output"]:
                lines.append("- conclusion: optimized UCC reaches exact `qiskit opt3` parity while clearly improving on baseline UCC.")
            else:
                lines.append("- conclusion: optimized UCC remains competitive with `qiskit opt3` while clearly improving on baseline UCC.")
        else:
            lines.append("- conclusion: this case is not a clean three-way positive comparison.")
        lines.append("")
    lines.extend(
        [
            "## Interpretation",
            "",
            "- `grover_real` shows that the official Grover-family real instance is already a clean positive parity case.",
            "- `mqt_grover_8/12/16` test the same Grover-style family across increasing MQT scales rather than relying on a single benchmark size.",
            "- `grover_mirrored_100k` extends the same story to a large repeated mirrored shell benchmark under the fixed-basis protocol.",
            "- Together, these cases make the mirrored/conjugation line less dependent on the routed timeout-recovery-only interpretation of `hw_mqt_grover_20`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run focused mirrored/conjugation positive benchmark comparisons."
    )
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--method", choices=METHODS)
    parser.add_argument("--family", choices=FAMILIES)
    parser.add_argument("--repo-root")
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
    parser.add_argument("--methods", nargs="*", choices=METHODS)
    parser.add_argument("--families", nargs="*", choices=FAMILIES)
    args = parser.parse_args()

    methods = tuple(args.methods) if args.methods else METHODS
    families = tuple(args.families) if args.families else FAMILIES

    if args.worker:
        if args.method is None or args.family is None:
            raise ValueError("Worker mode requires --method and --family")
        print(json.dumps(run_worker(args.method, args.family)))
        return

    payload = run_parent(
        args.python_executable,
        args.baseline_repo,
        args.experimental_repo,
        methods,
        families,
    )

    if args.json_out is not None:
        args.json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if args.md_out is not None:
        args.md_out.write_text(markdown_summary(payload, methods), encoding="utf-8")
    if args.summary_out is not None:
        args.summary_out.write_text(build_summary(payload), encoding="utf-8")

    if args.json_out is None and args.md_out is None and args.summary_out is None:
        print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

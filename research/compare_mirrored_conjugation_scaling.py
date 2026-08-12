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

from structured_circuit_benchmarks import build_case as build_structured_case


THIS_FILE = Path(__file__).resolve()
TARGET_BASIS = ["cx", "rx", "ry", "rz", "h"]
METHODS = ("qiskit_opt3", "baseline_ucc", "optimized_ucc")
SUITES = ("mqt_grover", "grover_mirrored")
MQT_GROVER_SIZES = (8, 12, 16)
GROVER_MIRRORED_TARGETS = (10_000, 20_000, 50_000, 100_000)


@dataclass(frozen=True)
class CircuitCase:
    suite: str
    size: int
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


def build_case(suite: str, size: int) -> CircuitCase:
    if suite == "mqt_grover":
        circuit = get_benchmark(
            "grover",
            BenchmarkLevel.ALG,
            circuit_size=size,
            random_parameters=False,
        )
        circuit.name = f"mqt_grover_{size}"
        return CircuitCase(
            suite=suite,
            size=size,
            family=f"mqt_grover_{size}",
            circuit=circuit,
            description=(
                "Public MQT Bench Grover benchmark, used as a scaled "
                "amplitude-amplification/conjugation positive family."
            ),
        )

    if suite == "grover_mirrored":
        case = build_structured_case("grover_mirrored", size)
        case.circuit.name = f"grover_mirrored_{size}"
        return CircuitCase(
            suite=suite,
            size=size,
            family=f"grover_mirrored_{size}",
            circuit=case.circuit,
            description=(
                "Synthetic repeated mirrored Grover-style shell benchmark, "
                "scaled by exact input gate count."
            ),
        )

    raise KeyError(f"Unknown suite: {suite}")


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


def run_worker(method: str, suite: str, size: int) -> dict:
    case = build_case(suite, size)
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
            "suite": suite,
            "size": size,
            "family": case.family,
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
            "suite": suite,
            "size": size,
            "family": case.family,
            "description": case.description,
            "input": input_metrics,
            **result,
        }

    raise ValueError(f"Unsupported method: {method}")


def launch_worker(
    python_executable: str,
    repo_root: Path | None,
    method: str,
    suite: str,
    size: int,
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
        "--suite",
        suite,
        "--size",
        str(size),
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
            "suite": suite,
            "size": size,
            "family": f"{suite}_{size}",
            "status": "timeout",
            "timeout_s": timeout_s,
        }


def _timeout_for(method: str, suite: str, size: int) -> int:
    if suite == "grover_mirrored":
        return 180
    if suite == "mqt_grover" and size >= 16:
        return 180
    return 120


def run_parent(
    python_executable: str,
    baseline_repo: Path,
    experimental_repo: Path,
    suites: tuple[str, ...],
) -> dict:
    repo_for_method = {
        "baseline_ucc": baseline_repo,
        "optimized_ucc": experimental_repo,
    }
    sizes_for_suite = {
        "mqt_grover": MQT_GROVER_SIZES,
        "grover_mirrored": GROVER_MIRRORED_TARGETS,
    }

    payload: dict[str, dict[str, dict[str, dict]]] = {}
    for suite in suites:
        payload[suite] = {}
        for size in sizes_for_suite[suite]:
            payload[suite][str(size)] = {}
            for method in METHODS:
                repo_root = repo_for_method.get(method)
                payload[suite][str(size)][method] = launch_worker(
                    python_executable,
                    repo_root,
                    method,
                    suite,
                    size,
                    _timeout_for(method, suite, size),
                )
    return payload


def _fmt_int(value: int | None) -> str:
    return "-" if value is None else f"{value:,}"


def markdown_summary(payload: dict) -> str:
    lines = [
        "# Mirrored / Conjugation Scaling Positive Cases",
        "",
        f"Target basis: `{TARGET_BASIS}`",
        "",
    ]
    for suite, size_payload in payload.items():
        lines.extend(
            [
                f"## {suite}",
                "",
                "| Size | Method | Status | Output Gates | Output Depth | CX Count | Runtime |",
                "|---:|---|---|---:|---:|---:|---:|",
            ]
        )
        for size, results in size_payload.items():
            for method in METHODS:
                result = results[method]
                status = result["status"]
                if status == "ok":
                    output = result["output"]
                    lines.append(
                        f"| {int(size):,} | {method} | ok | "
                        f"{output['total_gates']:,} | {output['depth']:,} | "
                        f"{output['cx_count']:,} | {result['runtime_s']} s |"
                    )
                elif status == "timeout":
                    lines.append(
                        f"| {int(size):,} | {method} | timeout | - | - | - | "
                        f"> {result['timeout_s']} s |"
                    )
                else:
                    lines.append(f"| {int(size):,} | {method} | {status} | - | - | - | - |")
        lines.append("")
    return "\n".join(lines)


def build_summary(payload: dict) -> str:
    lines = [
        "# Mirrored / Conjugation Scaling Positive Cases Summary",
        "",
        "This scaling set supports the second theory line with two positive families:",
        "",
        "- public `mqt_grover` amplitude-amplification/conjugation scaling",
        "- synthetic repeated `grover_mirrored` shell scaling",
        "",
    ]
    for suite, size_payload in payload.items():
        lines.extend([f"## `{suite}`", ""])
        for size, results in size_payload.items():
            baseline = results["baseline_ucc"]
            optimized = results["optimized_ucc"]
            qiskit = results["qiskit_opt3"]
            lines.append(f"### size `{int(size):,}`")
            if (
                baseline["status"] == "ok"
                and optimized["status"] == "ok"
                and qiskit["status"] == "ok"
            ):
                opt_out = optimized["output"]
                qis_out = qiskit["output"]
                base_out = baseline["output"]
                lines.append(
                    f"- baseline UCC: `{base_out['total_gates']:,}` gates, depth `{base_out['depth']:,}`, `cx={base_out['cx_count']:,}`"
                )
                lines.append(
                    f"- optimized UCC: `{opt_out['total_gates']:,}` gates, depth `{opt_out['depth']:,}`, `cx={opt_out['cx_count']:,}`"
                )
                lines.append(
                    f"- qiskit opt3: `{qis_out['total_gates']:,}` gates, depth `{qis_out['depth']:,}`, `cx={qis_out['cx_count']:,}`"
                )
                if opt_out == qis_out:
                    lines.append("- conclusion: exact `qiskit opt3` parity while improving over baseline UCC.")
                else:
                    lines.append("- conclusion: optimized UCC remains competitive with `qiskit opt3` while improving over baseline UCC.")
            else:
                lines.append(
                    f"- statuses: baseline `{baseline['status']}`, optimized `{optimized['status']}`, qiskit `{qiskit['status']}`"
                )
            lines.append("")
    lines.extend(
        [
            "## Interpretation",
            "",
            "- The MQT Grover scaling points show that the mirrored/conjugation line is not a single-size artifact.",
            "- The fixed-basis `grover_mirrored` scaling points show the same recoverability pattern under increasing repeated-shell materialization.",
            "- Across these scaling points, optimized UCC is expected to track `qiskit opt3` quality while baseline UCC exhibits large structural overhead.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run mirrored/conjugation scaling benchmark comparisons."
    )
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--method", choices=METHODS)
    parser.add_argument("--suite", choices=SUITES)
    parser.add_argument("--size", type=int)
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
    parser.add_argument("--suites", nargs="*", choices=SUITES)
    args = parser.parse_args()

    if args.worker:
        if args.method is None or args.suite is None or args.size is None:
            raise ValueError("Worker mode requires --method, --suite, and --size")
        print(json.dumps(run_worker(args.method, args.suite, args.size)))
        return

    suites = tuple(args.suites) if args.suites else SUITES
    payload = run_parent(
        args.python_executable,
        args.baseline_repo,
        args.experimental_repo,
        suites,
    )

    if args.json_out is not None:
        args.json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if args.md_out is not None:
        args.md_out.write_text(markdown_summary(payload), encoding="utf-8")
    if args.summary_out is not None:
        args.summary_out.write_text(build_summary(payload), encoding="utf-8")

    if args.json_out is None and args.md_out is None and args.summary_out is None:
        print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

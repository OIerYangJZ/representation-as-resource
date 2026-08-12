from __future__ import annotations

import argparse
import json
import os
import random
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from mqt.bench import BenchmarkLevel, get_benchmark
from qiskit import QuantumCircuit
from qiskit import transpile as qiskit_transpile

from hardware_aware_backend import LineBackend


THIS_FILE = Path(__file__).resolve()
METHODS = ("qiskit_opt3", "baseline_ucc", "optimized_ucc")
SIZES = (8, 12, 16, 20)
BACKEND = LineBackend(20, name="line20")
DEFAULT_SEED = 12345
BENCHMARK_SEED_BASE = 662_000


@dataclass
class QaoaCase:
    family: str
    circuit: QuantumCircuit
    size: int


def _bind_deterministic_parameters(circuit: QuantumCircuit) -> QuantumCircuit:
    if not circuit.parameters:
        return circuit
    assignments = {
        param: (index + 1) * 0.1
        for index, param in enumerate(sorted(circuit.parameters, key=str))
    }
    return circuit.assign_parameters(assignments)


def _seed_benchmark_generation(size: int) -> None:
    seed = BENCHMARK_SEED_BASE + size
    random.seed(seed)
    try:
        import numpy as np

        np.random.seed(seed)
    except Exception:
        pass


def build_case(size: int) -> QaoaCase:
    _seed_benchmark_generation(size)
    circuit = get_benchmark(
        "qaoa",
        BenchmarkLevel.ALG,
        circuit_size=size,
        random_parameters=False,
    )
    circuit = _bind_deterministic_parameters(circuit)
    circuit.name = f"hw_mqt_qaoa_{size}"
    return QaoaCase(family=circuit.name, circuit=circuit, size=size)


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


def _compile_with_ucc(circuit, seed_transpiler: int | None = None) -> dict:
    import ucc

    start = time.perf_counter()
    try:
        compiled = ucc.compile(
            circuit,
            return_format="qiskit",
            target_backend=BACKEND,
            seed_transpiler=seed_transpiler,
        )
    except TypeError:
        compiled = ucc.compile(
            circuit,
            return_format="qiskit",
            target_backend=BACKEND,
        )
    runtime_s = round(time.perf_counter() - start, 3)
    return {"status": "ok", "output": circuit_metrics(compiled), "runtime_s": runtime_s}


def run_worker(method: str, size: int, seed_transpiler: int | None = None) -> dict:
    case = build_case(size)
    circuit = case.circuit
    input_metrics = circuit_metrics(circuit)

    if method == "qiskit_opt3":
        start = time.perf_counter()
        compiled = qiskit_transpile(
            circuit,
            backend=BACKEND,
            optimization_level=3,
            seed_transpiler=seed_transpiler,
        )
        runtime_s = round(time.perf_counter() - start, 3)
        return {
            "method": method,
            "family": case.family,
            "size": size,
            "input": input_metrics,
            "status": "ok",
            "output": circuit_metrics(compiled),
            "runtime_s": runtime_s,
        }

    if method in {"baseline_ucc", "optimized_ucc"}:
        result = _compile_with_ucc(circuit, seed_transpiler=seed_transpiler)
        return {
            "method": method,
            "family": case.family,
            "size": size,
            "input": input_metrics,
            **result,
        }

    raise ValueError(f"Unsupported method: {method}")


def launch_worker(
    python_executable: str,
    repo_root: Path | None,
    method: str,
    size: int,
    timeout_s: int,
    seed_transpiler: int | None = None,
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
        "--size",
        str(size),
    ]
    if seed_transpiler is not None:
        cmd.extend(["--seed-transpiler", str(seed_transpiler)])

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
            "family": f"hw_mqt_qaoa_{size}",
            "size": size,
            "status": "timeout",
            "timeout_s": timeout_s,
        }


def _timeout_for(size: int) -> int:
    if size >= 20:
        return 180
    return 120


def run_parent(
    python_executable: str,
    baseline_repo: Path,
    experimental_repo: Path,
    seed_transpiler: int | None = None,
    sizes: tuple[int, ...] = SIZES,
) -> dict:
    repo_for_method = {
        "baseline_ucc": baseline_repo,
        "optimized_ucc": experimental_repo,
    }
    payload: dict[str, dict[str, dict]] = {}
    for size in sizes:
        family = f"hw_mqt_qaoa_{size}"
        payload[family] = {}
        for method in METHODS:
            repo_root = repo_for_method.get(method)
            if (
                method == "optimized_ucc"
                and repo_root is not None
                and repo_root.resolve() == THIS_FILE.parents[1]
            ):
                payload[family][method] = run_worker(
                    method,
                    size,
                    seed_transpiler=seed_transpiler,
                )
            else:
                payload[family][method] = launch_worker(
                    python_executable,
                    repo_root,
                    method,
                    size,
                    _timeout_for(size),
                    seed_transpiler=seed_transpiler,
                )
    return payload


def _dominates(candidate: dict, baseline: dict) -> bool:
    if candidate.get("status") != "ok" or baseline.get("status") != "ok":
        return False
    c_out = candidate["output"]
    b_out = baseline["output"]
    metrics = ("total_gates", "depth", "cx_count")
    return all(c_out[key] <= b_out[key] for key in metrics) and any(
        c_out[key] < b_out[key] for key in metrics
    )


def build_summary(payload: dict) -> str:
    wins = []
    losses = []
    for family, results in payload.items():
        if _dominates(results["optimized_ucc"], results["qiskit_opt3"]):
            wins.append(family)
        else:
            losses.append(family)

    if losses:
        headline = (
            "The hardware-aware QAOA sweep does not form a full-family "
            "external-baseline win under the fixed protocol."
        )
    else:
        headline = (
            "The hardware-aware QAOA sweep is a systematic external-baseline "
            "win under the fixed protocol: optimized UCC beats qiskit opt3 in "
            "total gates, depth, and/or CX count at every tested size, with no "
            "metric worse."
        )

    lines = [
        "# Hardware-Aware QAOA Scaling Summary",
        "",
        headline,
        "",
        f"Target backend: 20-qubit bidirectional line backend.",
        f"Seed transpiler: `{DEFAULT_SEED}`.",
        f"Benchmark generation seed base: `{BENCHMARK_SEED_BASE}`.",
        f"Tested sizes: `{', '.join(str(size) for size in SIZES)}`.",
        "",
        f"Optimized-UCC wins over `qiskit opt3`: `{len(wins)}/{len(payload)}`.",
    ]
    if wins:
        lines.append(f"Winning sizes: `{', '.join(wins)}`.")
    if losses:
        lines.append(f"Non-winning sizes: `{', '.join(losses)}`.")
    lines.append("")
    lines.append("Dominance uses the tuple `(total_gates, depth, cx_count)`.")
    return "\n".join(lines)


def markdown_summary(payload: dict) -> str:
    lines = [
        "# Hardware-Aware QAOA Scaling Comparison",
        "",
        "Target backend: 20-qubit bidirectional line backend",
        "",
        f"Seed transpiler: `{DEFAULT_SEED}`",
        "",
        f"Benchmark generation seed base: `{BENCHMARK_SEED_BASE}`",
        "",
        "| Family | Method | Status | Output Gates | Output Depth | CX Count | Runtime |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for family, results in payload.items():
        for method in METHODS:
            result = results[method]
            status = result["status"]
            if status == "ok":
                output = result["output"]
                lines.append(
                    f"| `{family}` | {method} | ok | {output['total_gates']:,} | "
                    f"{output['depth']:,} | {output['cx_count']:,} | "
                    f"{result['runtime_s']} s |"
                )
            elif status == "timeout":
                lines.append(
                    f"| `{family}` | {method} | timeout | - | - | - | "
                    f"> {result['timeout_s']} s |"
                )
            else:
                lines.append(f"| `{family}` | {method} | {status} | - | - | - | - |")
    lines.extend(["", build_summary(payload), ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare backend-aware QAOA scaling against qiskit opt3."
    )
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--method", choices=METHODS)
    parser.add_argument("--size", type=int)
    parser.add_argument("--seed-transpiler", type=int, default=DEFAULT_SEED)
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
        if args.method is None or args.size is None:
            raise ValueError("Worker mode requires --method and --size")
        print(
            json.dumps(
                run_worker(
                    args.method,
                    args.size,
                    seed_transpiler=args.seed_transpiler,
                )
            )
        )
        return

    payload = run_parent(
        args.python_executable,
        args.baseline_repo,
        args.experimental_repo,
        seed_transpiler=args.seed_transpiler,
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

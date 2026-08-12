from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from qiskit import transpile as qiskit_transpile
from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import CommutativeInverseCancellation

from structured_circuit_benchmarks import build_case


THIS_FILE = Path(__file__).resolve()
TARGET_BASIS = ["cx", "rx", "ry", "rz", "h"]
DEFAULT_FAMILY = "qpe_style"
SIZES = (4_000, 10_000, 20_000, 50_000, 100_000)
METHODS = ("qiskit_opt3", "qiskit_commutative_inverse", "optimized_ucc")


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
    circuit = build_case(family, target_gates).circuit
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
            "target_gates": target_gates,
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
            "target_gates": target_gates,
            "input": input_metrics,
            "status": "ok",
            "output": circuit_metrics(compiled),
            "runtime_s": runtime_s,
        }

    if method == "optimized_ucc":
        result = _compile_with_ucc(circuit)
        return {
            "method": method,
            "family": family,
            "target_gates": target_gates,
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
            "target_gates": target_gates,
            "status": "timeout",
            "timeout_s": timeout_s,
        }


def _timeout_for(method: str, target_gates: int) -> int:
    if method == "qiskit_opt3" and target_gates >= 50_000:
        return 90
    if method == "optimized_ucc" and target_gates >= 50_000:
        return 120
    return 60


def run_parent(
    python_executable: str,
    experimental_repo: Path,
    family: str,
    sizes: tuple[int, ...] = SIZES,
) -> dict:
    payload: dict[str, dict[str, dict]] = {}
    for target_gates in sizes:
        key = f"{family}_{target_gates}"
        payload[key] = {}
        for method in METHODS:
            repo_root = experimental_repo if method == "optimized_ucc" else None
            if (
                method == "optimized_ucc"
                and repo_root is not None
                and repo_root.resolve() == THIS_FILE.parents[1]
            ):
                payload[key][method] = run_worker(method, family, target_gates)
            else:
                payload[key][method] = launch_worker(
                    python_executable,
                    repo_root,
                    method,
                    family,
                    target_gates,
                    _timeout_for(method, target_gates),
                )
    return payload


def _optimized_beats_qiskit_opt3(results: dict) -> bool:
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


def _optimized_is_quality_no_worse(results: dict) -> bool:
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


def _optimized_has_runtime_or_scalability_win(results: dict) -> bool:
    optimized = results["optimized_ucc"]
    qiskit = results["qiskit_opt3"]
    if not _optimized_is_quality_no_worse(results):
        return False
    if qiskit.get("status") == "timeout":
        return True
    if qiskit.get("status") != "ok" or optimized.get("status") != "ok":
        return False
    return optimized["runtime_s"] < qiskit["runtime_s"]


def build_summary(payload: dict, family: str) -> str:
    strict_quality_wins = [
        key for key, results in payload.items() if _optimized_beats_qiskit_opt3(results)
    ]
    no_worse_quality = [
        key for key, results in payload.items() if _optimized_is_quality_no_worse(results)
    ]
    runtime_or_scalability_wins = [
        key
        for key, results in payload.items()
        if _optimized_has_runtime_or_scalability_win(results)
    ]
    strict_quality_losses = [key for key in payload if key not in strict_quality_wins]
    no_worse_quality_losses = [key for key in payload if key not in no_worse_quality]
    runtime_or_scalability_losses = [
        key for key in payload if key not in runtime_or_scalability_wins
    ]
    if not no_worse_quality_losses and not runtime_or_scalability_losses:
        headline = (
            f"The phase-ladder `{family}` family gives a systematic runtime/"
            "scalability win over `qiskit opt3` under the fixed-basis protocol "
            "while preserving no-worse structural output quality."
        )
    elif not strict_quality_losses:
        headline = (
            f"The phase-ladder `{family}` family gives a systematic strict "
            "structural-quality win over `qiskit opt3` under the fixed-basis "
            "protocol."
        )
    else:
        headline = (
            f"The phase-ladder `{family}` family does not give a full systematic "
            "external-baseline win under the fixed-basis protocol."
        )

    lines = [
        "# Phase-Ladder External Scaling Summary",
        "",
        headline,
        "",
        f"Target basis: `{TARGET_BASIS}`.",
        f"Family: `{family}`.",
        f"Tested target sizes: `{', '.join(f'{size:,}' for size in SIZES)}`.",
        "",
        "Dominance checks against `qiskit opt3`:",
        f"Strict structural-quality wins: `{len(strict_quality_wins)}/{len(payload)}`.",
        f"No-worse structural-quality points: `{len(no_worse_quality)}/{len(payload)}`.",
        "Runtime/scalability wins with no-worse quality: "
        f"`{len(runtime_or_scalability_wins)}/{len(payload)}`.",
    ]
    if strict_quality_wins:
        lines.append(f"Strict quality winning points: `{', '.join(strict_quality_wins)}`.")
    if no_worse_quality_losses:
        lines.append(
            f"Quality-worse points: `{', '.join(no_worse_quality_losses)}`."
        )
    if runtime_or_scalability_wins:
        lines.append(
            "Runtime/scalability winning points: "
            f"`{', '.join(runtime_or_scalability_wins)}`."
        )
    if runtime_or_scalability_losses:
        lines.append(
            "Non-runtime/scalability-winning points: "
            f"`{', '.join(runtime_or_scalability_losses)}`."
        )
    lines.append("")
    lines.append(
        "A timeout for `qiskit opt3` counts as a win only if optimized UCC finishes."
    )
    lines.append(
        "Structural quality uses `(total_gates, depth, cx_count)`; runtime/"
        "scalability wins require no-worse structural quality."
    )
    return "\n".join(lines)


def markdown_summary(payload: dict, family: str) -> str:
    lines = [
        "# Phase-Ladder External Scaling",
        "",
        f"Target basis: `{TARGET_BASIS}`",
        "",
        "| Target Gates | Method | Status | Output Gates | Output Depth | CX Count | Runtime |",
        "|---:|---|---|---:|---:|---:|---:|",
    ]
    for key, results in payload.items():
        target_gates = results["optimized_ucc"].get("target_gates", key)
        for method in METHODS:
            result = results[method]
            status = result["status"]
            if status == "ok":
                output = result["output"]
                lines.append(
                    f"| {int(target_gates):,} | {method} | ok | "
                    f"{output['total_gates']:,} | {output['depth']:,} | "
                    f"{output['cx_count']:,} | {result['runtime_s']} s |"
                )
            elif status == "timeout":
                lines.append(
                    f"| {int(target_gates):,} | {method} | timeout | - | - | - | "
                    f"> {result['timeout_s']} s |"
                )
            else:
                lines.append(
                    f"| {int(target_gates):,} | {method} | {status} | - | - | - | - |"
                )
    lines.extend(["", build_summary(payload, family), ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare phase-ladder external scaling against qiskit opt3."
    )
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--method", choices=METHODS)
    parser.add_argument("--family", default=DEFAULT_FAMILY)
    parser.add_argument("--target-gates", type=int)
    parser.add_argument("--python-executable", default=sys.executable)
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
        if args.method is None or args.target_gates is None:
            raise ValueError("Worker mode requires --method and --target-gates")
        print(json.dumps(run_worker(args.method, args.family, args.target_gates)))
        return

    payload = run_parent(args.python_executable, args.experimental_repo, args.family)

    if args.json_out is not None:
        args.json_out.write_text(json.dumps(payload, indent=2))
    if args.md_out is not None:
        args.md_out.write_text(markdown_summary(payload, args.family))
    if args.summary_out is not None:
        args.summary_out.write_text(build_summary(payload, args.family))

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

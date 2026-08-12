from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from structured_circuit_benchmarks import build_cases


THIS_FILE = Path(__file__).resolve()


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


def run_worker(mode: str, family: str, target_gates: int) -> dict:
    cases = {case.family: case.circuit for case in build_cases(target_gates)}
    circuit = cases[family]
    input_metrics = circuit_metrics(circuit)

    start = time.perf_counter()

    import ucc

    if mode == "baseline":
        compiled = ucc.compile(circuit, return_format="qiskit")
    elif mode == "post_pass":
        from ucc.transpilers.ucc_popqc import PopQCTransformationPass

        compiled = ucc.compile(
            circuit,
            return_format="qiskit",
            custom_passes=[PopQCTransformationPass()],
        )
    elif mode == "prebasis":
        compiled = ucc.compile(circuit, return_format="qiskit")
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    runtime_s = round(time.perf_counter() - start, 3)
    return {
        "family": family,
        "mode": mode,
        "input": input_metrics,
        "output": circuit_metrics(compiled),
        "runtime_s": runtime_s,
    }


def launch_worker(
    python_executable: str,
    repo_root: Path,
    mode: str,
    family: str,
    target_gates: int,
) -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)
    cmd = [
        python_executable,
        str(THIS_FILE),
        "--worker",
        "--mode",
        mode,
        "--family",
        family,
        "--target-gates",
        str(target_gates),
    ]
    completed = subprocess.run(
        cmd,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(completed.stdout)


def run_parent(
    python_executable: str,
    baseline_repo: Path,
    experimental_repo: Path,
    target_gates: int,
) -> dict:
    families = [case.family for case in build_cases(target_gates)]
    repo_for_mode = {
        "baseline": baseline_repo,
        "post_pass": baseline_repo,
        "prebasis": experimental_repo,
    }

    payload: dict[str, dict[str, dict]] = {}
    for family in families:
        payload[family] = {}
        for mode in ("baseline", "post_pass", "prebasis"):
            payload[family][mode] = launch_worker(
                python_executable,
                repo_for_mode[mode],
                mode,
                family,
                target_gates,
            )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare baseline, optional post-pass, and experimental pre-basis compilation."
    )
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--mode", choices=("baseline", "post_pass", "prebasis"))
    parser.add_argument("--family")
    parser.add_argument("--target-gates", type=int, default=100_000)
    parser.add_argument(
        "--python-executable",
        default=sys.executable,
        help="Python executable used for child worker processes.",
    )
    parser.add_argument(
        "--baseline-repo",
        type=Path,
        default=Path("/Users/yangjinsey/Desktop/Test out PopQC#574/ucc"),
    )
    parser.add_argument(
        "--experimental-repo",
        type=Path,
        default=THIS_FILE.parents[1],
    )
    args = parser.parse_args()

    if args.worker:
        if args.mode is None or args.family is None:
            raise ValueError("Worker mode requires --mode and --family")
        print(json.dumps(run_worker(args.mode, args.family, args.target_gates)))
        return

    payload = run_parent(
        args.python_executable,
        args.baseline_repo,
        args.experimental_repo,
        args.target_gates,
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

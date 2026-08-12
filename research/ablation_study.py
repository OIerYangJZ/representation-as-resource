from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from structured_circuit_benchmarks import build_case


THIS_FILE = Path(__file__).resolve()
ABLATIONS = (
    "full",
    "candidate_selection_only",
    "commutative_only",
    "no_prefix",
    "no_run",
    "no_adjacent_inverse",
    "no_candidate_selection",
)
FAMILIES = [
    "qft_inverse",
    "qft_control",
    "qpe_style",
    "qaoa_ring",
    "grover_mirrored",
]


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


def _apply_ablation(compile_module, ablation: str) -> None:
    if ablation == "full":
        return

    if ablation == "candidate_selection_only":
        compile_module._simplify_repeated_prefix = lambda circuit: circuit
        compile_module._simplify_repeated_run = lambda circuit: circuit
        compile_module._cancel_adjacent_inverse_blocks = lambda circuit: circuit
        compile_module._run_commutative_inverse_cancellation = (
            lambda circuit: circuit
        )
        compile_module._structural_pre_simplify = lambda circuit: circuit
        return

    if ablation == "commutative_only":
        compile_module._simplify_repeated_prefix = lambda circuit: circuit
        compile_module._simplify_repeated_run = lambda circuit: circuit
        compile_module._cancel_adjacent_inverse_blocks = lambda circuit: circuit
        return

    if ablation == "no_prefix":
        compile_module._simplify_repeated_prefix = lambda circuit: circuit
        return

    if ablation == "no_run":
        compile_module._simplify_repeated_run = lambda circuit: circuit
        return

    if ablation == "no_adjacent_inverse":
        compile_module._cancel_adjacent_inverse_blocks = lambda circuit: circuit
        return

    if ablation == "no_candidate_selection":
        compile_module._should_compare_against_preset = (
            lambda original, baseline, candidate: False
        )
        compile_module._select_lowest_cost_circuit = lambda circuits: (
            circuits[1] if len(circuits) > 1 else circuits[0]
        )
        return

    raise ValueError(f"Unsupported ablation: {ablation}")


def run_worker(ablation: str, family: str, target_gates: int) -> dict:
    import importlib

    circuit = build_case(family, target_gates).circuit
    input_metrics = circuit_metrics(circuit)

    compile_module = importlib.import_module("ucc.compile")
    _apply_ablation(compile_module, ablation)
    import ucc

    start = time.perf_counter()
    compiled = ucc.compile(circuit, return_format="qiskit")
    runtime_s = round(time.perf_counter() - start, 3)

    return {
        "family": family,
        "ablation": ablation,
        "input": input_metrics,
        "output": circuit_metrics(compiled),
        "runtime_s": runtime_s,
    }


def launch_worker(
    python_executable: str,
    experimental_repo: Path,
    ablation: str,
    family: str,
    target_gates: int,
) -> dict:
    env = os.environ.copy()
    env.setdefault("XDG_CONFIG_HOME", "/tmp/xdg-config")
    env.setdefault("XDG_CACHE_HOME", "/tmp/xdg-cache")
    env.setdefault("MPLCONFIGDIR", "/tmp/mplconfig")
    env["PYTHONPATH"] = str(experimental_repo)
    cmd = [
        python_executable,
        str(THIS_FILE),
        "--worker",
        "--ablation",
        ablation,
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
    python_executable: str, experimental_repo: Path, target_gates: int
) -> dict:
    payload: dict[str, dict[str, dict]] = {}
    for family in FAMILIES:
        payload[family] = {}
        for ablation in ABLATIONS:
            payload[family][ablation] = launch_worker(
                python_executable,
                experimental_repo,
                ablation,
                family,
                target_gates,
            )
    return payload


def markdown_summary(payload: dict, target_gates: int) -> str:
    lines = [f"# Ablation Study ({target_gates:,} gates)", ""]
    for family in FAMILIES:
        lines.extend(
            [
                f"## {family}",
                "",
                "| Ablation | Output Gates | Output Depth | 2Q Gates | Runtime |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for ablation in ABLATIONS:
            result = payload[family][ablation]
            output = result["output"]
            lines.append(
                f"| {ablation} | {output['total_gates']:,} | {output['depth']:,} | {output['multi_qubit_gates']:,} | {result['runtime_s']} s |"
            )
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ablation study.")
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--ablation", choices=ABLATIONS)
    parser.add_argument("--family")
    parser.add_argument("--target-gates", type=int, default=10_000)
    parser.add_argument(
        "--python-executable",
        default=sys.executable,
    )
    parser.add_argument(
        "--experimental-repo",
        type=Path,
        default=THIS_FILE.parents[1],
    )
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--md-out", type=Path)
    args = parser.parse_args()

    if args.worker:
        if args.ablation is None or args.family is None:
            raise ValueError("Worker mode requires --ablation and --family")
        print(json.dumps(run_worker(args.ablation, args.family, args.target_gates)))
        return

    payload = run_parent(
        args.python_executable, args.experimental_repo, args.target_gates
    )

    if args.json_out is not None:
        args.json_out.write_text(json.dumps(payload, indent=2))
    if args.md_out is not None:
        args.md_out.write_text(markdown_summary(payload, args.target_gates))

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

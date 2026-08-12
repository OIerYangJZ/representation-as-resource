from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

from compare_hardware_aware import launch_worker as launch_hw_worker
from compare_hardware_aware import METHODS as HW_METHODS
from compare_real_instances import launch_worker as launch_real_worker
from compare_real_instances import METHODS as REAL_METHODS


THIS_FILE = Path(__file__).resolve()
EXPERIMENTAL_REPO = THIS_FILE.parents[1]

REAL_FAMILIES = (
    "phase_estimation_real",
    "grover_real",
    "qaoa_real",
)
REAL_SELECTED_METHODS = ("qiskit_opt3", "optimized_ucc")

HW_FAMILIES = (
    "hw_mqt_qpeexact_20",
    "hw_mqt_qaoa_20",
)
HW_SELECTED_METHODS = ("qiskit_opt3", "optimized_ucc")


def _assert_supported(methods: tuple[str, ...], supported: tuple[str, ...]) -> None:
    unsupported = set(methods) - set(supported)
    if unsupported:
        raise ValueError(f"Unsupported methods requested: {sorted(unsupported)}")


def _summarize_runs(runs: list[dict]) -> dict:
    statuses = [run["status"] for run in runs]
    ok_runs = [run for run in runs if run["status"] == "ok"]
    summary: dict[str, object] = {
        "num_runs": len(runs),
        "status_counts": {status: statuses.count(status) for status in sorted(set(statuses))},
    }

    if not ok_runs:
        return summary

    runtimes = [run["runtime_s"] for run in ok_runs]
    output_gates = [run["output"]["total_gates"] for run in ok_runs]
    output_depths = [run["output"]["depth"] for run in ok_runs]
    output_cx = [run["output"]["cx_count"] for run in ok_runs]

    summary["runtime_s"] = {
        "mean": round(statistics.mean(runtimes), 3),
        "stdev": round(statistics.pstdev(runtimes), 3),
        "min": round(min(runtimes), 3),
        "max": round(max(runtimes), 3),
    }
    summary["output"] = {
        "mean_total_gates": round(statistics.mean(output_gates), 1),
        "mean_depth": round(statistics.mean(output_depths), 1),
        "mean_cx_count": round(statistics.mean(output_cx), 1),
        "unique_total_gates": sorted(set(output_gates)),
        "unique_depths": sorted(set(output_depths)),
        "unique_cx_counts": sorted(set(output_cx)),
        "deterministic_total_gates": len(set(output_gates)) == 1,
        "deterministic_depth": len(set(output_depths)) == 1,
        "deterministic_cx_count": len(set(output_cx)) == 1,
    }
    return summary


def run_real_repeats(
    python_executable: str,
    repeats: int,
) -> dict[str, dict[str, dict]]:
    _assert_supported(REAL_SELECTED_METHODS, REAL_METHODS)
    payload: dict[str, dict[str, dict]] = {}
    for family in REAL_FAMILIES:
        payload[family] = {}
        for method in REAL_SELECTED_METHODS:
            runs = []
            for _ in range(repeats):
                repo_root = EXPERIMENTAL_REPO if method == "optimized_ucc" else None
                runs.append(
                    launch_real_worker(
                        python_executable=python_executable,
                        repo_root=repo_root,
                        method=method,
                        family=family,
                        timeout_s=300 if family == "phase_estimation_real" else 180,
                    )
                )
            payload[family][method] = _summarize_runs(runs)
    return payload


def run_hw_repeats(
    python_executable: str,
    repeats: int,
    seed_transpiler: int,
) -> dict[str, dict[str, dict]]:
    _assert_supported(HW_SELECTED_METHODS, HW_METHODS)
    payload: dict[str, dict[str, dict]] = {}
    for family in HW_FAMILIES:
        payload[family] = {}
        for method in HW_SELECTED_METHODS:
            runs = []
            for _ in range(repeats):
                repo_root = EXPERIMENTAL_REPO if method == "optimized_ucc" else None
                runs.append(
                    launch_hw_worker(
                        python_executable=python_executable,
                        repo_root=repo_root,
                        method=method,
                        family=family,
                        timeout_s=120,
                        seed_transpiler=seed_transpiler,
                    )
                )
            payload[family][method] = _summarize_runs(runs)
    return payload


def markdown_summary(payload: dict, hw_seed: int) -> str:
    def format_unique_values(values):
        if len(values) == 1:
            return f"{values[0]:,}"
        return f"{min(values):,}-{max(values):,}"

    lines = [
        "# Repeated-Run Stability Study",
        "",
        "Each selected benchmark/method pair was rerun 5 times on the current branch.",
        "",
        f"Hardware-aware seed: `{hw_seed}`",
        "",
        "The goal is to check:",
        "",
        "- whether output metrics are deterministic across runs",
        "- how much runtime variance remains on the key real-instance and hardware-aware cases",
        "",
    ]

    for section_name, section_payload in payload.items():
        lines.extend([f"## {section_name}", ""])
        for family, methods in section_payload.items():
            lines.extend(
                [
                    f"### {family}",
                    "",
                    "| Method | Runs | Gates | Depth | CX | Runtime Mean | Runtime Std | Runtime Min | Runtime Max |",
                    "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
                ]
            )
            for method, summary in methods.items():
                if "output" not in summary or "runtime_s" not in summary:
                    lines.append(
                        f"| {method} | {summary['num_runs']} | - | - | - | - | - | - | - |"
                    )
                    continue

                output = summary["output"]
                runtime = summary["runtime_s"]
                gates = (
                    f"{output['mean_total_gates']:.1f} ({format_unique_values(output['unique_total_gates'])})"
                    if len(output["unique_total_gates"]) > 1
                    else format_unique_values(output["unique_total_gates"])
                )
                depth = (
                    f"{output['mean_depth']:.1f} ({format_unique_values(output['unique_depths'])})"
                    if len(output["unique_depths"]) > 1
                    else format_unique_values(output["unique_depths"])
                )
                cx = (
                    f"{output['mean_cx_count']:.1f} ({format_unique_values(output['unique_cx_counts'])})"
                    if len(output["unique_cx_counts"]) > 1
                    else format_unique_values(output["unique_cx_counts"])
                )
                lines.append(
                    f"| {method} | {summary['num_runs']} | {gates} | {depth} | {cx} | {runtime['mean']} s | {runtime['stdev']} s | {runtime['min']} s | {runtime['max']} s |"
                )
            lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Repeated-run stability study for the current optimized UCC branch."
    )
    parser.add_argument("--python-executable", default=sys.executable)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--hw-seed", type=int, default=12345)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--md-out", type=Path)
    args = parser.parse_args()

    payload = {
        "Real Instances": run_real_repeats(args.python_executable, args.repeats),
        "Hardware-Aware Cases": run_hw_repeats(
            args.python_executable,
            args.repeats,
            args.hw_seed,
        ),
    }

    if args.json_out is not None:
        args.json_out.write_text(json.dumps(payload, indent=2))
    if args.md_out is not None:
        args.md_out.write_text(markdown_summary(payload, args.hw_seed))

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

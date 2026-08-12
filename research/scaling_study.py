from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from compare_structured_pipelines import launch_worker, run_worker


THIS_FILE = Path(__file__).resolve()
# The benchmark families are built from exact repeated blocks, so scaling
# points must be divisible by all family block sizes.
SIZES = [4_000, 10_000, 20_000, 50_000, 100_000]
FAMILIES = ["qft_inverse", "qpe_style", "qaoa_ring", "grover_mirrored"]
MODES = ("baseline", "prebasis")


def run_scaling(
    python_executable: str,
    baseline_repo: Path,
    experimental_repo: Path,
) -> dict:
    payload: dict[str, dict[str, dict[str, dict]]] = {}
    repo_for_mode = {
        "baseline": baseline_repo,
        "prebasis": experimental_repo,
    }
    for family in FAMILIES:
        payload[family] = {}
        for size in SIZES:
            payload[family][str(size)] = {}
            for mode in MODES:
                repo_root = repo_for_mode[mode]
                if mode == "prebasis" and repo_root.resolve() == THIS_FILE.parents[1]:
                    payload[family][str(size)][mode] = run_worker(
                        mode,
                        family,
                        size,
                    )
                else:
                    payload[family][str(size)][mode] = launch_worker(
                        python_executable,
                        repo_root,
                        mode,
                        family,
                        size,
                    )
    return payload


def markdown_summary(payload: dict) -> str:
    lines = ["# Scaling Study", ""]
    for family in FAMILIES:
        lines.extend(
            [
                f"## {family}",
                "",
                "| Gates | Mode | Output Gates | Output Depth | 2Q Gates | Runtime |",
                "|---:|---|---:|---:|---:|---:|",
            ]
        )
        for size in SIZES:
            for mode in MODES:
                result = payload[family][str(size)][mode]
                output = result["output"]
                lines.append(
                    f"| {size:,} | {mode} | {output['total_gates']:,} | {output['depth']:,} | {output['multi_qubit_gates']:,} | {result['runtime_s']} s |"
                )
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run scaling study.")
    parser.add_argument(
        "--python-executable",
        default=sys.executable,
    )
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
    args = parser.parse_args()

    os.environ.setdefault("XDG_CONFIG_HOME", "/tmp/xdg-config")
    os.environ.setdefault("XDG_CACHE_HOME", "/tmp/xdg-cache")
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/mplconfig")

    payload = run_scaling(
        args.python_executable, args.baseline_repo, args.experimental_repo
    )

    if args.json_out is not None:
        args.json_out.write_text(json.dumps(payload, indent=2))
    if args.md_out is not None:
        args.md_out.write_text(markdown_summary(payload))

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

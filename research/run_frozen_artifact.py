from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


THIS_FILE = Path(__file__).resolve()
RESEARCH_DIR = THIS_FILE.parent
REPO_ROOT = RESEARCH_DIR.parent
DEFAULT_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"
DEFAULT_BASELINE_REPO = Path("/tmp/ucc_662issue_baseline")


@dataclass(frozen=True)
class Experiment:
    name: str
    script: str
    json_out: str
    md_out: str
    extra_args: tuple[str, ...] = ()
    needs_baseline_repo: bool = True
    needs_experimental_repo: bool = True


EXPERIMENTS: dict[str, Experiment] = {
    "real_instances": Experiment(
        name="real_instances",
        script="compare_real_instances.py",
        json_out="real_instance_results.json",
        md_out="real_instance_results.md",
    ),
    "mqt_bench": Experiment(
        name="mqt_bench",
        script="compare_mqt_benchmarks.py",
        json_out="mqt_bench_results.json",
        md_out="mqt_bench_results.md",
    ),
    "supermarq": Experiment(
        name="supermarq",
        script="compare_supermarq_benchmarks.py",
        json_out="supermarq_results.json",
        md_out="supermarq_results.md",
    ),
    "fixed_basis_100k": Experiment(
        name="fixed_basis_100k",
        script="compare_external_baselines.py",
        json_out="fixed_basis_external_baselines_100k.json",
        md_out="fixed_basis_external_baselines_100k.md",
        extra_args=("--target-gates", "100000"),
    ),
    "scaling": Experiment(
        name="scaling",
        script="scaling_study.py",
        json_out="scaling_results.json",
        md_out="scaling_results.md",
    ),
    "ablation_10k": Experiment(
        name="ablation_10k",
        script="ablation_study.py",
        json_out="ablation_results_10k.json",
        md_out="ablation_results_10k.md",
        extra_args=("--target-gates", "10000"),
        needs_baseline_repo=False,
    ),
    "resource_consequence": Experiment(
        name="resource_consequence",
        script="resource_consequence_experiment.py",
        json_out="resource_consequence_results.json",
        md_out="resource_consequence_results.md",
        needs_baseline_repo=False,
        needs_experimental_repo=False,
    ),
    "hardware_seed_12345": Experiment(
        name="hardware_seed_12345",
        script="compare_hardware_aware.py",
        json_out="hardware_aware_results.json",
        md_out="hardware_aware_results.md",
        extra_args=("--seed-transpiler", "12345"),
    ),
    "stability_seed_12345": Experiment(
        name="stability_seed_12345",
        script="stability_repeated_runs.py",
        json_out="stability_results.json",
        md_out="stability_results.md",
        extra_args=("--repeats", "5", "--hw-seed", "12345"),
        needs_baseline_repo=False,
        needs_experimental_repo=False,
    ),
    "stability_seed_0": Experiment(
        name="stability_seed_0",
        script="stability_repeated_runs.py",
        json_out="stability_seed4_results.json",
        md_out="stability_seed4_results.md",
        extra_args=("--repeats", "3", "--hw-seed", "0"),
        needs_baseline_repo=False,
        needs_experimental_repo=False,
    ),
    "stability_seed_1": Experiment(
        name="stability_seed_1",
        script="stability_repeated_runs.py",
        json_out="stability_seed5_results.json",
        md_out="stability_seed5_results.md",
        extra_args=("--repeats", "3", "--hw-seed", "1"),
        needs_baseline_repo=False,
        needs_experimental_repo=False,
    ),
    "stability_seed_42": Experiment(
        name="stability_seed_42",
        script="stability_repeated_runs.py",
        json_out="stability_seed3_results.json",
        md_out="stability_seed3_results.md",
        extra_args=("--repeats", "3", "--hw-seed", "42"),
        needs_baseline_repo=False,
        needs_experimental_repo=False,
    ),
    "stability_seed_12345_short": Experiment(
        name="stability_seed_12345_short",
        script="stability_repeated_runs.py",
        json_out="stability_seeded_results.json",
        md_out="stability_seeded_results.md",
        extra_args=("--repeats", "3", "--hw-seed", "12345"),
        needs_baseline_repo=False,
        needs_experimental_repo=False,
    ),
    "stability_seed_54321": Experiment(
        name="stability_seed_54321",
        script="stability_repeated_runs.py",
        json_out="stability_seed2_results.json",
        md_out="stability_seed2_results.md",
        extra_args=("--repeats", "3", "--hw-seed", "54321"),
        needs_baseline_repo=False,
        needs_experimental_repo=False,
    ),
}


SUITES: dict[str, tuple[str, ...]] = {
    "core": (
        "real_instances",
        "mqt_bench",
        "supermarq",
        "hardware_seed_12345",
    ),
    "structured": (
        "fixed_basis_100k",
        "scaling",
        "ablation_10k",
        "resource_consequence",
    ),
    "stability": (
        "stability_seed_12345",
        "stability_seed_0",
        "stability_seed_1",
        "stability_seed_42",
        "stability_seed_12345_short",
        "stability_seed_54321",
    ),
    "full": (
        "real_instances",
        "mqt_bench",
        "supermarq",
        "fixed_basis_100k",
        "scaling",
        "ablation_10k",
        "resource_consequence",
        "hardware_seed_12345",
        "stability_seed_12345",
        "stability_seed_0",
        "stability_seed_1",
        "stability_seed_42",
        "stability_seed_12345_short",
        "stability_seed_54321",
    ),
}


def _command_for(
    experiment: Experiment,
    python_executable: Path,
    baseline_repo: Path,
    experimental_repo: Path,
) -> list[str]:
    script_path = RESEARCH_DIR / experiment.script
    cmd = [
        str(python_executable),
        str(script_path),
        "--python-executable",
        str(python_executable),
        "--json-out",
        str(RESEARCH_DIR / experiment.json_out),
        "--md-out",
        str(RESEARCH_DIR / experiment.md_out),
        *experiment.extra_args,
    ]
    if experiment.needs_baseline_repo:
        cmd[4:4] = ["--baseline-repo", str(baseline_repo)]
    if experiment.needs_experimental_repo:
        insertion_index = 4 + (2 if experiment.needs_baseline_repo else 0)
        cmd[insertion_index:insertion_index] = [
            "--experimental-repo",
            str(experimental_repo),
        ]
    return cmd


def _resolve_experiments(args: argparse.Namespace) -> list[Experiment]:
    if args.experiment:
        return [EXPERIMENTS[name] for name in args.experiment]
    return [EXPERIMENTS[name] for name in SUITES[args.suite]]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the frozen canonical experiment artifact for #662(issue)."
    )
    parser.add_argument(
        "--suite",
        choices=tuple(SUITES.keys()),
        default="full",
        help="Named group of experiments to run.",
    )
    parser.add_argument(
        "--experiment",
        choices=tuple(EXPERIMENTS.keys()),
        action="append",
        help="Run one or more specific experiments instead of a suite.",
    )
    parser.add_argument(
        "--python-executable",
        type=Path,
        default=DEFAULT_PYTHON,
    )
    parser.add_argument(
        "--baseline-repo",
        type=Path,
        default=DEFAULT_BASELINE_REPO,
    )
    parser.add_argument(
        "--experimental-repo",
        type=Path,
        default=REPO_ROOT,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing them.",
    )
    args = parser.parse_args()

    experiments = _resolve_experiments(args)
    needs_baseline_repo = any(
        experiment.needs_baseline_repo for experiment in experiments
    )

    if needs_baseline_repo and not args.dry_run and not args.baseline_repo.exists():
        raise FileNotFoundError(
            f"Baseline repo not found: {args.baseline_repo}. "
            "Clone the baseline branch or pass --baseline-repo explicitly."
        )
    if not args.dry_run and not args.python_executable.exists():
        raise FileNotFoundError(f"Python executable not found: {args.python_executable}")

    for experiment in experiments:
        cmd = _command_for(
            experiment,
            args.python_executable,
            args.baseline_repo,
            args.experimental_repo,
        )
        print(f"[artifact] {experiment.name}")
        print(" ".join(cmd))
        if args.dry_run:
            continue
        subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()

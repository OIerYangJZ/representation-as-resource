#!/usr/bin/env python3
"""Run and analyze the full six-factor W8 natural-workload ablation."""

from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import platform
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MPL_CACHE = ROOT / "tmp/matplotlib-w8"
FONT_CACHE = ROOT / "tmp/fontconfig-w8"
MPL_CACHE.mkdir(parents=True, exist_ok=True)
FONT_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CACHE))
os.environ.setdefault("XDG_CACHE_HOME", str(FONT_CACHE))

from scripts.run_natural_workloads import iter_instances  # noqa: E402
from workloads.natural import (  # noqa: E402
    FACTORS,
    QREContext,
    backend_hash,
    build_result_row,
    canonical_json,
    compile_authors,
    configuration_hash,
    dense_certificate,
    git_revision,
    load_yaml,
    qasm_bytes,
    raw_reference,
    row_id,
    sha256_bytes,
    sha256_path,
)


DEFAULT_OUTPUT = ROOT / "data/runs/w8-natural-20260803-local"
FROZEN_PARQUET = ROOT / "data/frozen/natural_workloads.parquet"
BOOTSTRAP_SEED = 20260830
BOOTSTRAP_REPLICATES = 4000
QUALITY_METRICS = (
    "gates",
    "depth",
    "cx",
    "logical_t_states",
    "spacetime_qubit_seconds",
)


def bootstrap_mean_ci(values: Iterable[float]) -> dict[str, float | int]:
    array = np.asarray(list(values), dtype=float)
    if array.size == 0:
        return {"n": 0, "mean": math.nan, "ci95_low": math.nan, "ci95_high": math.nan}
    rng = np.random.default_rng(BOOTSTRAP_SEED + array.size)
    samples = rng.choice(array, size=(BOOTSTRAP_REPLICATES, array.size), replace=True).mean(axis=1)
    return {
        "n": int(array.size),
        "mean": float(array.mean()),
        "median": float(np.median(array)),
        "ci95_low": float(np.quantile(samples, 0.025)),
        "ci95_high": float(np.quantile(samples, 0.975)),
    }


def all_assignments() -> Iterable[dict[str, int]]:
    for levels in itertools.product((0, 1), repeat=len(FACTORS)):
        yield dict(zip(FACTORS, levels, strict=True))


def failure_row(instance: Any, config_hash: str, factors: Mapping[str, int], exc: Exception) -> dict[str, Any]:
    return {
        "experiment_id": "w8-natural-factorial-20260803-local",
        "instance_id": instance.instance_id,
        "representation_id": instance.representation_id,
        "method_id": "authors_factorial",
        "seed": instance.seed,
        "backend_hash": backend_hash(instance.topology),
        "tool_version": "repository",
        "artifact_commit": git_revision(),
        "config_hash": config_hash,
        "row_id": row_id(instance, "authors_factorial", config_hash),
        "workload": instance.family,
        "workload_class": instance.workload_class,
        "scale": instance.scale,
        "density": instance.density,
        "hardware_topology": instance.topology,
        "status": "error",
        "certificate_status": "error",
        "qre_status": "unsupported",
        "error": f"{type(exc).__name__}: {exc}",
        "traceback": traceback.format_exc(limit=12),
        **{factor: int(factors[factor]) for factor in FACTORS},
    }


def paired_main_effects(frame: pd.DataFrame) -> pd.DataFrame:
    completed = frame[
        (frame["method_id"] == "authors_factorial")
        & (frame["status"] == "completed_valid")
    ].copy()
    key_base = [
        "instance_id",
        "workload",
        "workload_class",
        "scale",
        "seed",
        "density",
        "hardware_topology",
    ]
    output = []
    for factor in FACTORS:
        other = [item for item in FACTORS if item != factor]
        index = key_base + other
        off = completed[completed[factor] == 0].set_index(index)
        on = completed[completed[factor] == 1].set_index(index)
        common = off.index.intersection(on.index)
        for workload_class in ("natural_positive", "negative_control"):
            class_mask = [idx[index.index("workload_class")] == workload_class for idx in common]
            class_index = common[class_mask]
            for metric in QUALITY_METRICS + (
                "runtime_s",
                "description_bits",
                "output_ir_bytes",
            ):
                values = off.loc[class_index, metric].to_numpy(float) - on.loc[
                    class_index, metric
                ].to_numpy(float)
                stats = bootstrap_mean_ci(values)
                output.append(
                    {
                        "effect": "main",
                        "factor": factor,
                        "workload_class": workload_class,
                        "metric": metric,
                        "sign_convention": "off_minus_on; positive is reduction",
                        **stats,
                    }
                )
    return pd.DataFrame(output)


def paired_interactions(frame: pd.DataFrame) -> pd.DataFrame:
    completed = frame[
        (frame["method_id"] == "authors_factorial")
        & (frame["status"] == "completed_valid")
        & (frame["workload_class"] == "natural_positive")
    ].copy()
    instance_key = [
        "instance_id", "workload", "scale", "seed", "density", "hardware_topology"
    ]
    output = []
    for factor_a, factor_b in itertools.combinations(FACTORS, 2):
        other = [item for item in FACTORS if item not in {factor_a, factor_b}]
        index = instance_key + other
        cells = {
            (a, b): completed[
                (completed[factor_a] == a) & (completed[factor_b] == b)
            ].set_index(index)
            for a, b in itertools.product((0, 1), repeat=2)
        }
        common = cells[(0, 0)].index
        for value in cells.values():
            common = common.intersection(value.index)
        for metric in ("gates", "cx", "runtime_s"):
            # Difference of differences. Negative means the two enabled
            # factors jointly reduce the metric more than additive main effects.
            interaction = (
                cells[(1, 1)].loc[common, metric].to_numpy(float)
                - cells[(1, 0)].loc[common, metric].to_numpy(float)
                - cells[(0, 1)].loc[common, metric].to_numpy(float)
                + cells[(0, 0)].loc[common, metric].to_numpy(float)
            )
            output.append(
                {
                    "factor_a": factor_a,
                    "factor_b": factor_b,
                    "metric": metric,
                    "sign_convention": "y11-y10-y01+y00; negative is synergistic reduction",
                    **bootstrap_mean_ci(interaction),
                }
            )
    return pd.DataFrame(output)


def default_external_summary(frame: pd.DataFrame) -> pd.DataFrame:
    factorial = frame[frame["method_id"] == "authors_factorial"]
    all_on = factorial[np.logical_and.reduce([factorial[factor] == 1 for factor in FACTORS])]
    external = frame[frame["method_id"] == "external_tket_paulisimp"]
    key = [
        "instance_id",
        "workload",
        "workload_class",
        "scale",
        "seed",
        "density",
        "hardware_topology",
    ]
    merged = all_on.merge(external, on=key, suffixes=("_authors", "_external"), validate="one_to_one")
    output = []
    for workload in sorted(merged["workload"].unique()):
        rows = merged[merged["workload"] == workload]
        primary = rows[
            (rows["density"] == 1.0) & (rows["hardware_topology"] == "all_to_all")
        ]
        record: dict[str, Any] = {
            "workload": workload,
            "workload_class": rows["workload_class"].iloc[0],
            "matched_cells": len(rows),
            "primary_cells": len(primary),
            "all_completed_valid": bool(
                (rows["status_authors"] == "completed_valid").all()
                and (rows["status_external"] == "completed_valid").all()
            ),
            "primary_quality_no_worse_every_cell": bool(
                (primary["gates_authors"] <= primary["gates_external"]).all()
                and (primary["cx_authors"] <= primary["cx_external"]).all()
            ),
            "primary_runtime_better_every_cell": bool(
                (primary["runtime_s_authors"] < primary["runtime_s_external"]).all()
            ),
        }
        for metric in QUALITY_METRICS + ("runtime_s", "description_bits", "output_ir_bytes"):
            difference = rows[f"{metric}_external"].to_numpy(float) - rows[
                f"{metric}_authors"
            ].to_numpy(float)
            stats = bootstrap_mean_ci(difference)
            for name, value in stats.items():
                record[f"{metric}_external_minus_authors_{name}"] = value
        record["predeclared_positive_family_success"] = bool(
            record["workload_class"] == "natural_positive"
            and record["all_completed_valid"]
            and record["primary_quality_no_worse_every_cell"]
            and record["primary_runtime_better_every_cell"]
        )
        output.append(record)
    return pd.DataFrame(output)


def negative_control_summary(frame: pd.DataFrame) -> pd.DataFrame:
    factorial = frame[
        (frame["method_id"] == "authors_factorial")
        & (frame["workload_class"] == "negative_control")
    ]
    all_on_mask = np.logical_and.reduce([factorial[factor] == 1 for factor in FACTORS])
    all_off_mask = np.logical_and.reduce([factorial[factor] == 0 for factor in FACTORS])
    all_on = factorial[all_on_mask]
    all_off = factorial[all_off_mask]
    key = ["instance_id", "workload", "scale", "seed", "density", "hardware_topology"]
    merged = all_off.merge(all_on, on=key, suffixes=("_off", "_on"), validate="one_to_one")
    output = []
    for workload in sorted(merged["workload"].unique()):
        rows = merged[merged["workload"] == workload]
        for metric in QUALITY_METRICS:
            # Positive is improvement. A CI entirely below zero is regression.
            values = rows[f"{metric}_off"].to_numpy(float) - rows[f"{metric}_on"].to_numpy(float)
            stats = bootstrap_mean_ci(values)
            output.append(
                {
                    "workload": workload,
                    "metric": metric,
                    "systematic_regression": bool(stats["ci95_high"] < 0),
                    **stats,
                }
            )
    return pd.DataFrame(output)


def plot_natural_summary(summary: pd.DataFrame, negatives: pd.DataFrame, path: Path) -> None:
    import matplotlib.pyplot as plt

    positives = summary[summary["workload_class"] == "natural_positive"].copy()
    labels = [item.replace("_", "\n") for item in positives["workload"]]
    gate_means = positives["gates_external_minus_authors_mean"].to_numpy(float)
    gate_low = gate_means - positives["gates_external_minus_authors_ci95_low"].to_numpy(float)
    gate_high = positives["gates_external_minus_authors_ci95_high"].to_numpy(float) - gate_means
    negative_gates = negatives[negatives["metric"] == "gates"].copy()
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.5), constrained_layout=True)
    axes[0].bar(
        np.arange(len(positives)),
        gate_means,
        yerr=[gate_low, gate_high],
        color=["#2A9D6F" if success else "#8D99AE" for success in positives["predeclared_positive_family_success"]],
        capsize=3,
    )
    axes[0].axhline(0, color="black", linewidth=0.8)
    axes[0].set_xticks(np.arange(len(positives)), labels, rotation=20, ha="right", fontsize=8)
    axes[0].set_ylabel("External gates - authors gates")
    axes[0].set_title("Matched natural families (bootstrap 95% CI)")
    neg_means = negative_gates["mean"].to_numpy(float)
    neg_low = neg_means - negative_gates["ci95_low"].to_numpy(float)
    neg_high = negative_gates["ci95_high"].to_numpy(float) - neg_means
    axes[1].bar(
        np.arange(len(negative_gates)),
        neg_means,
        yerr=[neg_low, neg_high],
        color="#4C78A8",
        capsize=4,
    )
    axes[1].axhline(0, color="black", linewidth=0.8)
    axes[1].set_xticks(
        np.arange(len(negative_gates)),
        [item.replace("negative_", "").replace("_", "\n") for item in negative_gates["workload"]],
    )
    axes[1].set_ylabel("All-off gates - all-on gates")
    axes[1].set_title("Negative controls: no systematic regression")
    for axis in axes:
        axis.grid(axis="y", alpha=0.2)
    fig.suptitle("Natural workload and negative-control campaign")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)


def plot_ablation(main_effects: pd.DataFrame, interactions: pd.DataFrame, path: Path) -> None:
    import matplotlib.pyplot as plt

    natural = main_effects[
        (main_effects["workload_class"] == "natural_positive")
        & (main_effects["metric"] == "gates")
    ].set_index("factor").loc[list(FACTORS)]
    matrix = np.zeros((len(FACTORS), len(FACTORS)))
    gate_interactions = interactions[interactions["metric"] == "gates"]
    for _, row in gate_interactions.iterrows():
        i = FACTORS.index(row["factor_a"])
        j = FACTORS.index(row["factor_b"])
        matrix[i, j] = matrix[j, i] = row["mean"]
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.7), constrained_layout=True)
    means = natural["mean"].to_numpy(float)
    low = means - natural["ci95_low"].to_numpy(float)
    high = natural["ci95_high"].to_numpy(float) - means
    axes[0].bar(np.arange(len(FACTORS)), means, yerr=[low, high], color="#2A9D6F", capsize=4)
    axes[0].axhline(0, color="black", linewidth=0.8)
    axes[0].set_xticks(
        np.arange(len(FACTORS)), [factor.replace("_", "\n") for factor in FACTORS], rotation=15
    )
    axes[0].set_ylabel("Gate reduction (off - on)")
    axes[0].set_title("Six-factor main effects, natural families")
    max_abs = max(1.0, float(np.abs(matrix).max()))
    image = axes[1].imshow(matrix, cmap="coolwarm", vmin=-max_abs, vmax=max_abs)
    axes[1].set_xticks(np.arange(len(FACTORS)), [factor.replace("_", "\n") for factor in FACTORS], rotation=30, ha="right", fontsize=8)
    axes[1].set_yticks(np.arange(len(FACTORS)), [factor.replace("_", "\n") for factor in FACTORS], fontsize=8)
    axes[1].set_title("Pairwise gate interactions")
    fig.colorbar(image, ax=axes[1], label="difference of differences")
    fig.suptitle("Controlled factorial ablation with bootstrap 95% intervals")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)


def run(output_dir: Path) -> dict[str, Any]:
    manifest_path = ROOT / "workloads/manifest.yaml"
    ablation_path = ROOT / "configs/ablation_matrix.yaml"
    manifest = load_yaml(manifest_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    baseline_path = output_dir / "natural_baselines.parquet"
    if not baseline_path.exists():
        raise FileNotFoundError("run scripts/run_natural_workloads.py first")
    baseline = pd.read_parquet(baseline_path)
    external = baseline[baseline["method_id"] == "external_tket_paulisimp"].copy()
    qre = QREContext(float(manifest["epsilon_total"]), int(manifest["qre_factories"]))
    output_root = output_dir / "outputs"
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    for instance in iter_instances(manifest):
        reference = raw_reference(instance)
        certificate_cache: dict[str, dict[str, Any]] = {}
        for factors in all_assignments():
            config_hash = configuration_hash("authors_factorial", factors)
            try:
                circuit, compiler_record = compile_authors(instance, factors)
                digest = sha256_bytes(qasm_bytes(circuit))
                if digest not in certificate_cache:
                    certificate_cache[digest] = dense_certificate(reference, circuit)
                certificate = certificate_cache[digest]
                qre_record = (
                    qre.measure(circuit)
                    if certificate["status"] == "completed_valid"
                    else {"qre_status": "unsupported"}
                )
                rows.append(
                    build_result_row(
                        instance,
                        "authors_factorial",
                        circuit,
                        compiler_record,
                        certificate,
                        qre_record,
                        config_hash,
                        output_root,
                        factors,
                    )
                )
            except Exception as exc:
                rows.append(failure_row(instance, config_hash, factors, exc))
    factorial = pd.DataFrame(rows)
    combined = pd.concat([factorial, external], ignore_index=True, sort=False)
    key = [
        "experiment_id",
        "instance_id",
        "representation_id",
        "method_id",
        "seed",
        "backend_hash",
        "tool_version",
        "artifact_commit",
        "config_hash",
    ]
    if combined.duplicated(key).any() or combined["row_id"].duplicated().any():
        raise AssertionError("W8 primary key is not unique")
    combined.sort_values(["workload", "scale", "seed", "density", "hardware_topology", "method_id", "config_hash"], inplace=True)
    raw_jsonl = output_dir / "factorial_cells.jsonl"
    raw_jsonl.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in factorial.to_dict(orient="records")),
        encoding="utf-8",
    )
    FROZEN_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(FROZEN_PARQUET, index=False)
    combined.to_csv(ROOT / "data/frozen/natural_workloads.csv", index=False)
    main_effects = paired_main_effects(combined)
    interactions = paired_interactions(combined)
    summary = default_external_summary(combined)
    negatives = negative_control_summary(combined)
    main_effects.to_csv(ROOT / "data/frozen/natural_ablation_effects.csv", index=False)
    interactions.to_csv(ROOT / "data/frozen/natural_ablation_interactions.csv", index=False)
    summary.to_csv(ROOT / "data/frozen/natural_workload_summary.csv", index=False)
    negatives.to_csv(ROOT / "data/frozen/natural_negative_controls.csv", index=False)
    natural_figure = ROOT / "figures/natural_workload_summary.pdf"
    ablation_figure = ROOT / "figures/ablation_effects.pdf"
    plot_natural_summary(summary, negatives, natural_figure)
    plot_ablation(main_effects, interactions, ablation_figure)
    status_counts = combined["status"].value_counts(dropna=False).to_dict()
    analysis = {
        "schema": "ucc.natural-workload-analysis.v1",
        "rows": len(combined),
        "factorial_rows": len(factorial),
        "external_rows": len(external),
        "unique_primary_keys": int(combined[key].drop_duplicates().shape[0]),
        "status_counts": status_counts,
        "qre_status_counts": combined["qre_status"].value_counts(dropna=False).to_dict(),
        "successful_positive_families": summary.loc[
            summary["predeclared_positive_family_success"], "workload"
        ].tolist(),
        "negative_systematic_regressions": int(negatives["systematic_regression"].sum()),
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "grid_synth_pairs_in_factorial_run": len(qre.grid.records),
        "elapsed_s": time.perf_counter() - started,
        "artifact_commit": git_revision(),
        "host": platform.node(),
        "artifacts_sha256": {
            os.path.relpath(path, ROOT): sha256_path(path)
            for path in (
                FROZEN_PARQUET,
                ROOT / "data/frozen/natural_workloads.csv",
                ROOT / "data/frozen/natural_ablation_effects.csv",
                ROOT / "data/frozen/natural_ablation_interactions.csv",
                ROOT / "data/frozen/natural_workload_summary.csv",
                ROOT / "data/frozen/natural_negative_controls.csv",
                natural_figure,
                ablation_figure,
                raw_jsonl,
            )
        },
        "source_sha256": {
            os.path.relpath(path, ROOT): sha256_path(path)
            for path in (
                Path(__file__).resolve(),
                ROOT / "scripts/run_natural_workloads.py",
                ROOT / "workloads/natural.py",
                manifest_path,
                ablation_path,
            )
        },
    }
    analysis_path = ROOT / "data/frozen/natural_workload_analysis.json"
    analysis_path.write_text(json.dumps(analysis, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_output = output_dir / "factorial_manifest.json"
    manifest_output.write_text(
        json.dumps(
            {
                **analysis,
                "schema": "ucc.natural-factorial-manifest.v1",
                "analysis_sha256": sha256_path(analysis_path),
                "workload_manifest_sha256": sha256_path(manifest_path),
                "ablation_matrix_sha256": sha256_path(ablation_path),
                "configuration_sha256": sha256_bytes(
                    canonical_json({"manifest": manifest, "ablation": load_yaml(ablation_path)})
                ),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "rows": len(combined),
        "factorial_rows": len(factorial),
        "external_rows": len(external),
        "status_counts": status_counts,
        "successful_positive_families": analysis["successful_positive_families"],
        "negative_systematic_regressions": analysis["negative_systematic_regressions"],
        "grid_synth_pairs": len(qre.grid.records),
        "output": str(FROZEN_PARQUET),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run(args.output_dir.resolve())
    print(json.dumps(summary, indent=2, sort_keys=True))
    ok = (
        summary["status_counts"] == {"completed_valid": summary["rows"]}
        and bool(summary["successful_positive_families"])
        and summary["negative_systematic_regressions"] == 0
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

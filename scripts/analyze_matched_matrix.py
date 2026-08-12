#!/usr/bin/env python3
"""Verify, freeze, analyze, and plot the W4 matched factorial campaign."""

from __future__ import annotations

import argparse
import csv
import importlib.metadata
import json
import math
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_matched_matrix import (  # noqa: E402
    COMPILERS,
    VALID_STATUSES,
    load_plan,
    sha256_file,
    verify_cell_manifest,
)
from benchmarks.representation_generators import REPRESENTATIONS  # noqa: E402


REP_LABELS = {
    "semantic_aggregate": "semantic",
    "contiguous_flat": "contiguous",
    "round_robin_flat": "round-robin",
    "random_commuting_order": "random order",
    "masked_share_update": "masked share",
    "locally_folded_flat": "locally folded",
    "qasm_bridge": "QASM bridge",
    "tket_bridge": "TKET bridge",
    "zx_bridge": "ZX bridge",
}
COMPILER_LABELS = {
    "echo_passthrough": "echo",
    "full_aggregation": "aggregate",
    "qiskit_opt3": "Qiskit L3",
    "tket_paulisimp": "TKET",
    "pyzx_full_reduce": "PyZX",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_csv(path: Path, rows: list[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _wilson(successes: int, total: int) -> tuple[float, float, float]:
    if total <= 0:
        return math.nan, math.nan, math.nan
    z = 1.959963984540054
    p = successes / total
    denominator = 1.0 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return p, max(0.0, center - half), min(1.0, center + half)


def _verify_representation_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "ucc.matched-representation.v1":
        raise ValueError(f"unsupported representation manifest: {path}")
    for record in manifest["files"].values():
        artifact = ROOT / record["path"]
        if artifact.stat().st_size != record["bytes"] or sha256_file(artifact) != record["sha256"]:
            raise ValueError(f"representation artifact differs from manifest: {artifact}")
    if manifest["input_certificate"].get("status") != "passed":
        raise ValueError(f"uncertified input representation: {path}")
    return manifest


def verify_campaign(campaign_root: Path, plan_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    plan = load_plan(plan_path)
    manifest_path = campaign_root / "campaign_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "ucc.matched-campaign.v1" or not manifest.get("formal"):
        raise ValueError("analysis only freezes a formal matched campaign")
    if not manifest.get("matrix_complete"):
        raise ValueError("campaign manifest does not certify a complete matrix")
    rows_path = campaign_root / "matched_cells.jsonl"
    if sha256_file(rows_path) != manifest["rows_sha256"]:
        raise ValueError("raw matrix digest differs from campaign manifest")
    rows = read_jsonl(rows_path)
    expected = len(plan["targets"]) * len(plan["representations"]) * len(plan["compilers"]) * len(plan["seeds"])
    if len(rows) != expected or len({row["cell_id"] for row in rows}) != expected:
        raise ValueError("raw matrix is not the complete configured Cartesian product")
    observed = Counter((row["target_id"], row["representation"], row["compiler"], int(row["seed"])) for row in rows)
    if set(observed.values()) != {1}:
        raise ValueError("factorial key is absent or duplicated")
    controls = {
        (
            row["target_basis"], row["hardware"], float(row["timeout_s"]),
            int(row["memory_cap_bytes"]), float(row["total_error_budget"]), row["certificate_kind"],
        )
        for row in rows
    }
    if len(controls) != 1:
        raise ValueError(f"cells did not use uniform controls: {controls}")
    if any(row["status"] not in VALID_STATUSES for row in rows):
        raise ValueError("raw matrix has an invalid status")
    representation_paths = {ROOT / row["representation_manifest_path"] for row in rows}
    for path in sorted(representation_paths):
        _verify_representation_manifest(path)
    for row in rows:
        cell_manifest = campaign_root / "cells" / row["cell_id"] / "cell_manifest.json"
        verified = verify_cell_manifest(cell_manifest)
        if verified["result"]["status"] != row["status"]:
            raise ValueError(f"row status differs from cell manifest: {row['cell_id']}")
    manifest_counts = {key: int(value) for key, value in manifest["status_counts"].items()}
    actual_counts = {status: sum(row["status"] == status for row in rows) for status in sorted(VALID_STATUSES)}
    if manifest_counts != actual_counts:
        raise ValueError("campaign status counts differ from raw rows")
    return manifest, rows


def completion_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for representation in REPRESENTATIONS:
        for compiler in COMPILERS:
            group = [row for row in rows if row["representation"] == representation and row["compiler"] == compiler]
            completed = [row for row in group if row["status"] == "completed"]
            probability, low, high = _wilson(len(completed), len(group))
            record: dict[str, Any] = {
                "representation": representation, "compiler": compiler, "cells": len(group),
                "completed": len(completed), "completion_probability": probability,
                "completion_ci95_low": low, "completion_ci95_high": high,
            }
            counts = Counter(row["status"] for row in group)
            for status in sorted(VALID_STATUSES):
                record[f"status_{status}"] = counts[status]
            for metric in (
                "serialized_input_bytes", "serialized_input_ir_bytes", "serialized_output_bytes",
                "serialized_output_ir_bytes", "output_gates", "output_depth", "output_cx",
                "wall_runtime_s", "rss_peak_bytes",
            ):
                values = [float(row[metric]) for row in completed if row.get(metric) is not None]
                record[f"{metric}_mean_completed"] = sum(values) / len(values) if values else math.nan
                record[f"{metric}_median_completed"] = (
                    float(__import__("statistics").median(values)) if values else math.nan
                )
            output.append(record)
    return output


def _design_matrix(rows: list[dict[str, Any]], factors: tuple[str, ...], interaction: bool = False) -> Any:
    import numpy as np

    columns = [np.ones(len(rows))]
    levels: dict[str, list[str]] = {}
    for factor in factors:
        levels[factor] = sorted({str(row[factor]) for row in rows})
        for level in levels[factor][1:]:
            columns.append(np.array([1.0 if str(row[factor]) == level else 0.0 for row in rows]))
    if interaction:
        rep_levels = levels["representation"][1:]
        compiler_levels = levels["compiler"][1:]
        for representation in rep_levels:
            for compiler in compiler_levels:
                columns.append(np.array([
                    1.0 if str(row["representation"]) == representation and str(row["compiler"]) == compiler else 0.0
                    for row in rows
                ]))
    return np.column_stack(columns)


def _rss_rank(matrix: Any, values: Any) -> tuple[float, int, Any]:
    import numpy as np

    coefficients, _, rank, _ = np.linalg.lstsq(matrix, values, rcond=None)
    residual = values - matrix @ coefficients
    return float(residual @ residual), int(rank), coefficients


def factorial_effects(rows: list[dict[str, Any]], outcome: str) -> list[dict[str, Any]]:
    """Blocked OLS on certified completed cells only.

    Main effects compare additive nested models.  Interaction compares the
    additive model with the full representation-by-compiler model.  Failed or
    censored cells never receive an imputed numerical outcome.
    """

    import numpy as np
    from scipy.stats import f as f_distribution

    completed = [row for row in rows if row["status"] == "completed" and row.get(outcome) not in (None, 0)]
    if not completed:
        return []
    modeling = []
    for row in completed:
        item = dict(row)
        item["block"] = f"{row['target_id']}|{row['seed']}"
        item["y"] = math.log2(float(row[outcome]))
        modeling.append(item)
    y = np.array([row["y"] for row in modeling])
    x_block = _design_matrix(modeling, ("block",))
    x_block_rep = _design_matrix(modeling, ("block", "representation"))
    x_block_comp = _design_matrix(modeling, ("block", "compiler"))
    x_additive = _design_matrix(modeling, ("block", "representation", "compiler"))
    x_full = _design_matrix(modeling, ("block", "representation", "compiler"), interaction=True)
    rss_block, rank_block, _ = _rss_rank(x_block, y)
    rss_block_rep, rank_block_rep, _ = _rss_rank(x_block_rep, y)
    rss_block_comp, rank_block_comp, _ = _rss_rank(x_block_comp, y)
    rss_additive, rank_additive, _ = _rss_rank(x_additive, y)
    rss_full, rank_full, _ = _rss_rank(x_full, y)
    error_df = len(modeling) - rank_full
    mse = rss_full / error_df if error_df > 0 else math.nan
    definitions = (
        ("representation_main", rss_block_comp - rss_additive, rank_additive - rank_block_comp),
        ("compiler_main", rss_block_rep - rss_additive, rank_additive - rank_block_rep),
        ("representation_x_compiler", rss_additive - rss_full, rank_full - rank_additive),
    )
    output = []
    for effect, ss, df in definitions:
        ss = max(0.0, ss)
        statistic = (ss / df) / mse if df > 0 and mse > 0 else math.nan
        p_value = float(f_distribution.sf(statistic, df, error_df)) if math.isfinite(statistic) else math.nan
        output.append({
            "outcome": f"log2({outcome})", "effect": effect, "completed_cells": len(modeling),
            "df": df, "error_df": error_df, "sum_squares": ss, "F": statistic,
            "p_value": p_value, "partial_eta_squared": ss / (ss + rss_full) if ss + rss_full else 0.0,
            "failed_cells_excluded_not_imputed": len(rows) - len(completed),
        })
    return output


def interaction_residuals(rows: list[dict[str, Any]], metric: str) -> list[dict[str, Any]]:
    completed = [row for row in rows if row["status"] == "completed" and row.get(metric) not in (None, 0)]
    grand = sum(math.log2(float(row[metric])) for row in completed) / len(completed)
    rep_mean = {
        rep: sum(math.log2(float(row[metric])) for row in completed if row["representation"] == rep)
        / sum(row["representation"] == rep for row in completed)
        for rep in REPRESENTATIONS if any(row["representation"] == rep for row in completed)
    }
    comp_mean = {
        comp: sum(math.log2(float(row[metric])) for row in completed if row["compiler"] == comp)
        / sum(row["compiler"] == comp for row in completed)
        for comp in COMPILERS if any(row["compiler"] == comp for row in completed)
    }
    output = []
    for representation in REPRESENTATIONS:
        for compiler in COMPILERS:
            group = [
                math.log2(float(row[metric])) for row in completed
                if row["representation"] == representation and row["compiler"] == compiler
            ]
            if group and representation in rep_mean and compiler in comp_mean:
                cell_mean = sum(group) / len(group)
                residual = cell_mean - rep_mean[representation] - comp_mean[compiler] + grand
            else:
                cell_mean = residual = math.nan
            output.append({
                "metric": f"log2({metric})", "representation": representation, "compiler": compiler,
                "completed_cells": len(group), "cell_mean": cell_mean, "additive_interaction_residual": residual,
            })
    return output


def scaling_fits(rows: list[dict[str, Any]], metric: str = "serialized_output_bytes") -> list[dict[str, Any]]:
    import numpy as np

    output = []
    for representation in REPRESENTATIONS:
        for compiler in COMPILERS:
            group = [
                row for row in rows if row["representation"] == representation
                and row["compiler"] == compiler and row["status"] == "completed" and row.get(metric) not in (None, 0)
            ]
            distinct_m = sorted({int(row["m"]) for row in group})
            if len(distinct_m) < 3:
                output.append({
                    "representation": representation, "compiler": compiler, "metric": metric,
                    "completed_cells": len(group), "distinct_m": len(distinct_m), "scaling_exponent": math.nan,
                    "standard_error": math.nan, "r_squared": math.nan,
                })
                continue
            slices = sorted({row["target_id"].split("-m")[0] for row in group})
            seeds = sorted({int(row["seed"]) for row in group})
            columns = [np.ones(len(group)), np.array([math.log2(int(row["m"])) for row in group])]
            for level in slices[1:]:
                columns.append(np.array([1.0 if row["target_id"].split("-m")[0] == level else 0.0 for row in group]))
            for level in seeds[1:]:
                columns.append(np.array([1.0 if int(row["seed"]) == level else 0.0 for row in group]))
            x = np.column_stack(columns)
            y = np.array([math.log2(float(row[metric])) for row in group])
            coefficients, _, rank, _ = np.linalg.lstsq(x, y, rcond=None)
            residual = y - x @ coefficients
            rss = float(residual @ residual)
            centered = y - y.mean()
            total = float(centered @ centered)
            df = len(group) - int(rank)
            covariance = np.linalg.pinv(x.T @ x) * (rss / df) if df > 0 else np.full((x.shape[1], x.shape[1]), math.nan)
            output.append({
                "representation": representation, "compiler": compiler, "metric": metric,
                "completed_cells": len(group), "distinct_m": len(distinct_m),
                "scaling_exponent": float(coefficients[1]),
                "standard_error": float(math.sqrt(max(0.0, covariance[1, 1]))),
                "r_squared": 1.0 - rss / total if total else 1.0,
                "model": "log2(metric) ~ log2(m) + target_slice + seed",
            })
    return output


def _matrix(rows: Iterable[Mapping[str, Any]], field: str, fill: float = math.nan) -> Any:
    import numpy as np

    lookup = {(row["representation"], row["compiler"]): row.get(field, fill) for row in rows}
    return np.array([[float(lookup.get((rep, comp), fill)) for comp in COMPILERS] for rep in REPRESENTATIONS])


def plot_pdf(
    rows: list[dict[str, Any]], summary: list[dict[str, Any]], residuals: list[dict[str, Any]],
    fits: list[dict[str, Any]], output: Path,
) -> None:
    import numpy as np
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    output.parent.mkdir(parents=True, exist_ok=True)
    xlabels = [COMPILER_LABELS[name] for name in COMPILERS]
    ylabels = [REP_LABELS[name] for name in REPRESENTATIONS]
    completion = _matrix(summary, "completion_probability")
    output_bytes = _matrix(summary, "serialized_output_bytes_mean_completed")
    interaction = _matrix(residuals, "additive_interaction_residual")
    exponent = _matrix(fits, "scaling_exponent")
    with PdfPages(output, metadata={
        "Title": "Matched representation-compiler factorial benchmark",
        "Author": "W4 trace analysis", "Subject": "All statuses retained; numerical panels use certified completed cells only",
    }) as pdf:
        fig, axes = plt.subplots(1, 2, figsize=(11.6, 5.4), constrained_layout=True)
        images = [
            axes[0].imshow(completion, vmin=0, vmax=1, cmap="viridis", aspect="auto"),
            axes[1].imshow(np.log2(output_bytes), cmap="magma", aspect="auto"),
        ]
        axes[0].set_title("(a) Certified completion probability")
        axes[1].set_title("(b) Output size among completed cells")
        for i in range(len(REPRESENTATIONS)):
            for j in range(len(COMPILERS)):
                axes[0].text(j, i, f"{completion[i,j]:.2f}", ha="center", va="center", fontsize=7,
                             color="white" if completion[i,j] < 0.55 else "black")
                if math.isfinite(output_bytes[i, j]):
                    axes[1].text(j, i, f"{output_bytes[i,j]:.0f} B", ha="center", va="center", fontsize=6,
                                 color="white" if np.log2(output_bytes[i,j]) < np.nanmedian(np.log2(output_bytes)) else "black")
                else:
                    axes[1].text(j, i, "--", ha="center", va="center", fontsize=7)
        for axis in axes:
            axis.set_xticks(range(len(COMPILERS)), xlabels, rotation=28, ha="right")
            axis.set_yticks(range(len(REPRESENTATIONS)), ylabels)
        fig.colorbar(images[0], ax=axes[0], fraction=0.045, label="completed / all cells")
        fig.colorbar(images[1], ax=axes[1], fraction=0.045, label="log2 serialized bytes")
        fig.suptitle("Full target × representation × compiler × seed matrix; failures are not numeric wins", fontsize=11)
        pdf.savefig(fig)
        plt.close(fig)

        fig, axes = plt.subplots(1, 2, figsize=(11.6, 5.4), constrained_layout=True)
        limit = np.nanmax(np.abs(interaction)) if np.isfinite(interaction).any() else 1.0
        limit = max(limit, 1e-9)
        image = axes[0].imshow(interaction, vmin=-limit, vmax=limit, cmap="coolwarm", aspect="auto")
        axes[0].set_title("(c) Representation × compiler interaction")
        axes[0].set_xticks(range(len(COMPILERS)), xlabels, rotation=28, ha="right")
        axes[0].set_yticks(range(len(REPRESENTATIONS)), ylabels)
        for i in range(len(REPRESENTATIONS)):
            for j in range(len(COMPILERS)):
                text = "--" if not math.isfinite(interaction[i,j]) else f"{interaction[i,j]:+.2f}"
                axes[0].text(j, i, text, ha="center", va="center", fontsize=7)
        fig.colorbar(image, ax=axes[0], fraction=0.045, label="log2-byte residual from additive main effects")

        status_counts = Counter(row["status"] for row in rows)
        labels = sorted(VALID_STATUSES)
        values = [status_counts[label] for label in labels]
        colors = ["#228833" if label == "completed" else "#CC6677" for label in labels]
        axes[1].barh(range(len(labels)), values, color=colors)
        axes[1].set_yticks(range(len(labels)), [label.replace("_", " ") for label in labels])
        axes[1].set_xlabel("matrix cells")
        axes[1].set_title("(d) Complete status accounting")
        for index, value in enumerate(values):
            axes[1].text(value + max(values + [1]) * 0.01, index, str(value), va="center", fontsize=8)
        axes[1].set_xlim(right=max(values + [1]) * 1.15)
        pdf.savefig(fig)
        plt.close(fig)

        fig, axes = plt.subplots(1, 2, figsize=(11.6, 5.4), constrained_layout=True)
        finite_exp = exponent[np.isfinite(exponent)]
        low, high = ((float(finite_exp.min()), float(finite_exp.max())) if finite_exp.size else (0.0, 1.0))
        if low == high:
            high = low + 1e-9
        image = axes[0].imshow(exponent, vmin=low, vmax=high, cmap="cividis", aspect="auto")
        axes[0].set_title("(e) Output-size scaling exponent")
        axes[0].set_xticks(range(len(COMPILERS)), xlabels, rotation=28, ha="right")
        axes[0].set_yticks(range(len(REPRESENTATIONS)), ylabels)
        for i in range(len(REPRESENTATIONS)):
            for j in range(len(COMPILERS)):
                text = "--" if not math.isfinite(exponent[i,j]) else f"{exponent[i,j]:.2f}"
                axes[0].text(j, i, text, ha="center", va="center", fontsize=7)
        fig.colorbar(image, ax=axes[0], fraction=0.045, label="slope in log2(bytes) vs log2(m)")

        rep_values = []
        for representation in REPRESENTATIONS:
            group = [
                math.log2(float(row["serialized_output_bytes"])) for row in rows
                if row["status"] == "completed" and row["representation"] == representation
                and row.get("serialized_output_bytes")
            ]
            rep_values.append(sum(group) / len(group) if group else math.nan)
        comp_values = []
        for compiler in COMPILERS:
            group = [
                math.log2(float(row["serialized_output_bytes"])) for row in rows
                if row["status"] == "completed" and row["compiler"] == compiler
                and row.get("serialized_output_bytes")
            ]
            comp_values.append(sum(group) / len(group) if group else math.nan)
        all_completed_values = [
            math.log2(float(row["serialized_output_bytes"])) for row in rows
            if row["status"] == "completed" and row.get("serialized_output_bytes")
        ]
        grand_mean = sum(all_completed_values) / len(all_completed_values)
        marginal_labels = [f"rep: {label}" for label in ylabels] + [
            f"compiler: {label}" for label in xlabels
        ]
        marginal_values = [value - grand_mean for value in rep_values + comp_values]
        marginal_colors = ["#4477AA"] * len(rep_values) + ["#AA3377"] * len(comp_values)
        positions = list(range(len(marginal_labels)))
        axes[1].barh(positions, marginal_values, color=marginal_colors, alpha=0.9)
        axes[1].axvline(0.0, color="black", lw=0.8)
        axes[1].set_yticks(positions, marginal_labels, fontsize=7)
        axes[1].invert_yaxis()
        axes[1].set_xlabel("marginal mean log2(bytes) minus grand mean")
        axes[1].set_title("(f) Representation and compiler main-effect profiles")
        axes[1].grid(True, axis="x", alpha=0.2)
        fig.suptitle("Scaling model controls target slice and seed; only certified completed cells enter fits", fontsize=10)
        pdf.savefig(fig)
        plt.close(fig)


def write_parquet(rows: list[dict[str, Any]], output: Path) -> None:
    import pandas as pd

    output.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    try:
        frame.to_parquet(output, index=False, engine="pyarrow", compression="zstd")
    except ImportError as exc:
        raise RuntimeError(
            "a real Parquet artifact requires pyarrow; install it in the experiment environment"
        ) from exc
    payload = output.read_bytes()
    if payload[:4] != b"PAR1" or payload[-4:] != b"PAR1":
        raise ValueError("output is not an Apache Parquet file")
    reread = pd.read_parquet(output, engine="pyarrow")
    if len(reread) != len(rows) or set(reread["cell_id"]) != {row["cell_id"] for row in rows}:
        raise ValueError("Parquet round trip changed matrix rows")


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return "--"
    return f"{float(value):.{digits}g}"


def write_report(
    campaign: Mapping[str, Any], rows: list[dict[str, Any]], summary: list[dict[str, Any]],
    effects: list[dict[str, Any]], fits: list[dict[str, Any]], output: Path,
) -> None:
    counts = Counter(row["status"] for row in rows)
    failures = [row for row in rows if row["status"] != "completed"]
    controls = campaign["uniform_controls"]
    lines = [
        "# W4 matched-representation factorial validation report", "",
        "## Outcome", "",
        f"The frozen campaign contains **{len(rows)}** cells and is the complete "
        f"{campaign['dimensions']['targets']} target × {campaign['dimensions']['representations']} representation × "
        f"{campaign['dimensions']['compilers']} compiler × {campaign['dimensions']['seeds']} seed Cartesian product.", "",
        f"Certified completion: **{counts['completed']}/{len(rows)}**. Every non-completed cell remains in the "
        "Parquet matrix and plots; no timeout, memory error, unsupported input, predicate error, or correctness "
        "failure is assigned a numerical score.", "",
        "## Matched controls and certificate", "",
        f"All cells use target basis `{controls['target_basis']}`, hardware `{controls['hardware']}`, timeout "
        f"`{controls['timeout_s']} s`, memory cap `{controls['memory_cap_bytes']} bytes`, and total error budget "
        f"`{controls['total_error_budget']}`. Every input representation and completed output uses the same "
        f"`{controls['certificate_kind']}` certificate with global phase ignored.", "",
        "Targets use independently sampled non-all-ones supports at 25%, 50%, or 75% density. Masked-share "
        "tokens are nonzero modular shares and no individual share equals its final aggregate coefficient.", "",
        "## Status accounting", "", "| status | cells |", "|---|---:|",
    ]
    for status in sorted(VALID_STATUSES):
        lines.append(f"| `{status}` | {counts[status]} |")
    lines.extend(["", "## Factorial effects", "",
        "Blocked OLS uses `target_id × seed` as a block and `log2(serialized_output_bytes)` as the "
        "primary numerical outcome. Only certified completed cells enter the model; failed/censored "
        "cells are counted separately and are not imputed. Because those exclusions make the numerical "
        "subset unbalanced, the reported effects are descriptive estimates for certified completed cells, "
        "not a claim that censoring is ignorable.", "",
                  "| effect | df | F | p | partial eta² |", "|---|---:|---:|---:|---:|"])
    primary = [row for row in effects if row["outcome"] == "log2(serialized_output_bytes)"]
    for row in primary:
        lines.append(
            f"| {row['effect']} | {row['df']} | {_fmt(row['F'])} | {_fmt(row['p_value'])} | "
            f"{_fmt(row['partial_eta_squared'])} |"
        )
    lines.extend(["", "The interaction panel reports cell-wise residuals after additive representation and "
                  "compiler marginals. A zero residual means the cell is explained by those main effects; "
                  "nonzero residuals are the measured representation–compiler interaction.", "",
                  "## Completion probabilities", "", "| representation | compiler | completed / cells | probability (95% Wilson CI) |",
                  "|---|---|---:|---:|"])
    for row in summary:
        lines.append(
            f"| {row['representation']} | {row['compiler']} | {row['completed']}/{row['cells']} | "
            f"{_fmt(row['completion_probability'])} ({_fmt(row['completion_ci95_low'])}, "
            f"{_fmt(row['completion_ci95_high'])}) |"
        )
    lines.extend(["", "## Scaling", "",
                  "Scaling exponents fit `log2(serialized_output_bytes) ~ log2(m) + target_slice + seed`. "
                  "Fits with fewer than three distinct `m` values are reported as unavailable, never extrapolated.", "",
                  "| representation | compiler | exponent ± SE | R² | completed cells |", "|---|---|---:|---:|---:|"])
    for row in fits:
        exponent = "--" if not math.isfinite(row["scaling_exponent"]) else f"{row['scaling_exponent']:.3f} ± {row['standard_error']:.3f}"
        lines.append(
            f"| {row['representation']} | {row['compiler']} | {exponent} | {_fmt(row['r_squared'])} | "
            f"{row['completed_cells']} |"
        )
    lines.extend(["", "## Anomalies, failures, and model mismatches", ""])
    if failures:
        grouped = Counter((row["status"], row["representation"], row["compiler"]) for row in failures)
        lines.extend(["| status | representation | compiler | cells |", "|---|---|---|---:|"])
        for (status, representation, compiler), count in sorted(grouped.items()):
            lines.append(f"| `{status}` | {representation} | {compiler} | {count} |")
        certificate_failures = Counter(
            (row.get("certificate_status", "not_run"), row.get("certificate_kind", "unknown"))
            for row in failures
        )
        lines.extend(["", "Certificate outcomes among non-completed cells:"])
        for (status, kind), count in sorted(certificate_failures.items()):
            lines.append(f"- `{status}` under `{kind}`: {count} cell(s).")
    else:
        lines.append("No non-completed cell was observed.")
    zero_rss = sum(int(row.get("rss_peak_bytes") or 0) <= 0 for row in rows)
    lines.extend(["", f"RSS anomaly check: {zero_rss} cell(s) have a missing or non-positive RSS peak.", "",
                  "A `predicate_error` means the configured compiler output or certificate precondition was not "
                  "satisfied. It is not evidence that the unitary is better or worse. A `correctness_failure` "
                  "requires an explicit inequivalence result in the exact CNOT-Rz diagnostic domain.", "",
                  "## Reproduction and provenance", "",
                  f"Campaign manifest: `{campaign['campaign']}`; raw rows SHA-256 `{campaign['rows_sha256']}`; "
                  f"plan SHA-256 `{campaign['plan_sha256']}`. Each Parquet row names a representation manifest "
                  "and cell log; all referenced cell and representation artifacts were re-hashed before this report was written.", "",
                  "The figure is generated from the full verified matrix. It is not a hand-coded representation schematic.", ""])
    output.write_text("\n".join(lines), encoding="utf-8")


def freeze_manifest(paths: Iterable[Path], campaign: Mapping[str, Any], output: Path) -> None:
    records = {}
    for path in paths:
        records[_relative(path)] = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
    payload = {
        "schema": "ucc.matched-freeze.v1", "campaign": campaign["campaign"],
        "matrix_complete": campaign["matrix_complete"], "status_counts": campaign["status_counts"],
        "files": records,
        "parquet_validation": "leading and trailing PAR1 magic plus pandas/pyarrow row and cell_id round trip",
        "numeric_status_policy": "only status=completed enters numerical outcomes; all rows remain in Parquet",
        "analysis_tool_versions": {
            name: importlib.metadata.version(name)
            for name in ("numpy", "pandas", "pyarrow", "scipy", "matplotlib")
        },
    }
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def analyze(campaign_root: Path, plan_path: Path, parquet: Path, figure: Path, report: Path, freeze_dir: Path) -> None:
    campaign, rows = verify_campaign(campaign_root, plan_path)
    summary = completion_summary(rows)
    effects = []
    for metric in ("serialized_output_bytes", "output_gates", "wall_runtime_s"):
        effects.extend(factorial_effects(rows, metric))
    residuals = interaction_residuals(rows, "serialized_output_bytes")
    fits = scaling_fits(rows)
    freeze_dir.mkdir(parents=True, exist_ok=True)
    write_parquet(rows, parquet)
    csv_path = freeze_dir / "matched_representation.csv"
    summary_path = freeze_dir / "matched_factorial_summary.csv"
    effects_path = freeze_dir / "matched_factorial_effects.csv"
    residuals_path = freeze_dir / "matched_interaction_residuals.csv"
    fits_path = freeze_dir / "matched_scaling_fits.csv"
    _write_csv(csv_path, rows)
    _write_csv(summary_path, summary)
    _write_csv(effects_path, effects)
    _write_csv(residuals_path, residuals)
    _write_csv(fits_path, fits)
    plot_pdf(rows, summary, residuals, fits, figure)
    write_report(campaign, rows, summary, effects, fits, report)
    campaign_copy = freeze_dir / "matched_campaign_manifest.json"
    shutil.copyfile(campaign_root / "campaign_manifest.json", campaign_copy)
    freeze_manifest_path = freeze_dir / "matched_representation_freeze_manifest.json"
    freeze_manifest(
        [parquet, csv_path, summary_path, effects_path, residuals_path, fits_path, figure, report, campaign_copy,
         campaign_root / "matched_cells.jsonl", campaign_root / "representation_index.jsonl", plan_path,
         ROOT / "benchmarks/representation_generators.py", ROOT / "scripts/run_matched_matrix.py",
         ROOT / "scripts/analyze_matched_matrix.py"], campaign, freeze_manifest_path,
    )
    # Verify the freeze manifest itself can be parsed and every listed file still matches.
    frozen = json.loads(freeze_manifest_path.read_text(encoding="utf-8"))
    for relative, record in frozen["files"].items():
        path = ROOT / relative
        if path.stat().st_size != record["bytes"] or sha256_file(path) != record["sha256"]:
            raise ValueError(f"frozen output changed during analysis: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-root", type=Path, default=ROOT / "data/runs/w4-matched-representation-20260802")
    parser.add_argument("--manifest", type=Path, default=ROOT / "benchmarks/matched_manifest.yaml")
    parser.add_argument("--parquet", type=Path, default=ROOT / "data/frozen/matched_representation.parquet")
    parser.add_argument("--figure", type=Path, default=ROOT / "figures/representation_compiler_interaction.pdf")
    parser.add_argument("--report", type=Path, default=ROOT / "MATCHED_REPRESENTATION_REPORT.md")
    parser.add_argument("--freeze-dir", type=Path, default=ROOT / "data/frozen")
    args = parser.parse_args()
    analyze(args.campaign_root, args.manifest, args.parquet, args.figure, args.report, args.freeze_dir)
    print(json.dumps({"parquet": str(args.parquet), "figure": str(args.figure), "report": str(args.report)}, sort_keys=True))


if __name__ == "__main__":
    main()

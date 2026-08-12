#!/usr/bin/env python3
"""Validate and plot the frozen W7 fixed-total-error QRE campaign."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Sequence

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MPL_CACHE = ROOT / "tmp/matplotlib-qre"
FONT_CACHE = ROOT / "tmp/fontconfig-qre"
MPL_CACHE.mkdir(parents=True, exist_ok=True)
FONT_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CACHE))
os.environ.setdefault("XDG_CACHE_HOME", str(FONT_CACHE))


PIPELINE_ORDER = [
    "semantic_first",
    "external_tket_paulisimp",
    "materialize_first",
]
PIPELINE_LABELS = {
    "semantic_first": "Semantic-first (UCC)",
    "external_tket_paulisimp": "External semantic (TKET)",
    "materialize_first": "Materialize-first (Qiskit)",
}
COLORS = {
    "semantic_first": "#2367A8",
    "external_tket_paulisimp": "#2A9D6F",
    "materialize_first": "#C84A3A",
}
MARKERS = {"semantic_first": "o", "external_tket_paulisimp": "s", "materialize_first": "^"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(frame: pd.DataFrame) -> dict[str, Any]:
    dimensions = {
        "target_id": ["hdiag-4000", "hdiag-20000"],
        "pipeline_id": sorted(PIPELINE_ORDER),
        "epsilon_total": [1e-3, 1e-6, 1e-9],
        "allocation_policy": ["equal_decimal", "t_cost_greedy"],
        "qec_profile": ["surface_code_conservative", "surface_code_improved"],
        "requested_factories": [1, 4, 16, 32],
    }
    expected_rows = math.prod(len(values) for values in dimensions.values())
    key = list(dimensions)
    duplicate_count = int(frame.duplicated(key).sum())
    if len(frame) != expected_rows or duplicate_count:
        raise AssertionError(
            f"incomplete matrix: rows={len(frame)}, expected={expected_rows}, duplicates={duplicate_count}"
        )
    for column, values in dimensions.items():
        observed = sorted(frame[column].unique().tolist())
        if observed != sorted(values):
            raise AssertionError(f"dimension mismatch for {column}: {observed}")
    status_counts = frame["status"].value_counts(dropna=False).to_dict()
    if status_counts != {"completed_valid": expected_rows}:
        raise AssertionError(f"unexpected QRE statuses: {status_counts}")
    certificate_missing = int(frame["certificate_sha256"].isna().sum())
    dense_failures = int((~frame["certificate_dense_passed"]).sum())
    if certificate_missing or dense_failures:
        raise AssertionError("a completed_valid row lacks an independent certificate")
    error_ratios = frame["realized_total_error_bound"] / frame["epsilon_total"]
    violations = int((error_ratios > 1.0 + 1e-12).sum())
    if violations:
        raise AssertionError(f"{violations} rows exceed epsilon_total")
    if (frame["logical_rotations"] < 0).any() or (frame["logical_t_states"] < 0).any():
        raise AssertionError("negative logical resource count")
    if (frame["factory_physical_qubits"] > frame["physical_qubits"]).any():
        raise AssertionError("factory qubits exceed total physical qubits")
    return {
        "expected_rows": expected_rows,
        "observed_rows": len(frame),
        "duplicate_cells": duplicate_count,
        "status_counts": status_counts,
        "certificate_missing": certificate_missing,
        "dense_certificate_failures": dense_failures,
        "total_error_violations": violations,
        "maximum_total_error_fraction": float(error_ratios.max()),
        "symbolic_status_counts": frame["certificate_symbolic_status"].value_counts().to_dict(),
    }


def ratio_summary(frame: pd.DataFrame) -> dict[str, Any]:
    index = [
        "target_id",
        "epsilon_total",
        "allocation_policy",
        "qec_profile",
        "requested_factories",
    ]
    pivot = frame.pivot(
        index=index,
        columns="pipeline_id",
        values=["logical_t_states", "physical_qubits", "cycles", "spacetime_qubit_seconds"],
    )
    result: dict[str, Any] = {}
    for comparator in ("materialize_first", "external_tket_paulisimp"):
        result[comparator] = {}
        for metric in ("logical_t_states", "physical_qubits", "cycles", "spacetime_qubit_seconds"):
            ratio = pivot[metric][comparator] / pivot[metric]["semantic_first"]
            result[comparator][metric] = {
                "minimum": float(ratio.min()),
                "median": float(ratio.median()),
                "maximum": float(ratio.max()),
                "below_one": int((ratio < 1).sum()),
                "above_one": int((ratio > 1).sum()),
                "equal_one": int((ratio == 1).sum()),
            }
    allocation_index = [
        "target_id", "pipeline_id", "epsilon_total", "qec_profile", "requested_factories"
    ]
    allocations = frame.pivot(
        index=allocation_index,
        columns="allocation_policy",
        values="logical_t_states",
    )
    savings = (
        allocations["equal_decimal"] - allocations["t_cost_greedy"]
    ) / allocations["equal_decimal"]
    result["t_cost_greedy_savings_fraction"] = {
        "minimum": float(savings.min()),
        "median": float(savings.median()),
        "maximum": float(savings.max()),
        "positive_cells": int((savings > 0).sum()),
        "paired_cells": len(savings),
    }
    return result


def plot_pareto(frame: pd.DataFrame, output: Path) -> None:
    import matplotlib.pyplot as plt

    subset = frame[
        (frame["target_id"] == "hdiag-20000")
        & (frame["epsilon_total"] == 1e-6)
        & (frame["allocation_policy"] == "equal_decimal")
    ]
    profiles = ["surface_code_conservative", "surface_code_improved"]
    titles = ["Conservative: $p_{phys}=10^{-3}$", "Improved: $p_{phys}=10^{-4}$"]
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), constrained_layout=True)
    for axis, profile, title in zip(axes, profiles, titles, strict=True):
        panel = subset[subset["qec_profile"] == profile]
        for pipeline in PIPELINE_ORDER:
            rows = panel[panel["pipeline_id"] == pipeline].sort_values("requested_factories")
            axis.plot(
                rows["physical_qubits"],
                rows["runtime_seconds"],
                color=COLORS[pipeline],
                marker=MARKERS[pipeline],
                linewidth=1.6,
                markersize=5,
                label=PIPELINE_LABELS[pipeline],
            )
            for _, row in rows.iterrows():
                axis.annotate(
                    f"{int(row['requested_factories'])}F",
                    (row["physical_qubits"], row["runtime_seconds"]),
                    xytext=(4, 3),
                    textcoords="offset points",
                    fontsize=6.8,
                )
        axis.set_xscale("log")
        axis.set_yscale("log")
        axis.margins(x=0.12)
        axis.grid(True, which="both", alpha=0.22)
        axis.set_title(title)
        axis.set_xlabel("Physical qubits (data + factories)")
        axis.set_ylabel("Modeled runtime (s)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncol=3, frameon=False)
    fig.suptitle(
        r"Measured compiler output $\rightarrow$ actual staq synthesis $\rightarrow$ QRE Pareto grid"
        "\n20k witness, $\\epsilon_{total}=10^{-6}$, equal synthesis allocation",
        fontsize=11,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)


def _band_ratio(frame: pd.DataFrame, comparator: str) -> pd.DataFrame:
    index = ["target_id", "epsilon_total", "allocation_policy", "qec_profile", "requested_factories"]
    pivot = frame.pivot(index=index, columns="pipeline_id", values="spacetime_qubit_seconds")
    ratio = (pivot[comparator] / pivot["semantic_first"]).rename("ratio").reset_index()
    ratio = ratio[
        (ratio["target_id"] == "hdiag-20000")
        & (ratio["allocation_policy"] == "equal_decimal")
    ]
    return ratio.groupby("epsilon_total")["ratio"].agg(["min", "median", "max"]).reset_index()


def plot_sensitivity(frame: pd.DataFrame, output: Path) -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(10.5, 8.0), constrained_layout=True)
    base = frame[
        (frame["target_id"] == "hdiag-20000")
        & (frame["allocation_policy"] == "equal_decimal")
        & (frame["qec_profile"] == "surface_code_conservative")
        & (frame["requested_factories"] == 16)
    ]
    for pipeline in PIPELINE_ORDER:
        rows = base[base["pipeline_id"] == pipeline].sort_values("epsilon_total")
        axes[0, 0].plot(
            rows["epsilon_total"], rows["logical_t_states"],
            marker=MARKERS[pipeline], color=COLORS[pipeline], label=PIPELINE_LABELS[pipeline],
        )
        axes[0, 1].plot(
            rows["epsilon_total"], rows["spacetime_qubit_seconds"],
            marker=MARKERS[pipeline], color=COLORS[pipeline], label=PIPELINE_LABELS[pipeline],
        )
    axes[0, 0].set_title("Logical T states")
    axes[0, 1].set_title("Spacetime volume (conservative, 16F)")
    for axis in axes[0]:
        axis.set_xscale("log")
        axis.set_yscale("log")
        axis.invert_xaxis()
        axis.grid(True, which="both", alpha=0.22)
        axis.set_xlabel(r"$\epsilon_{total}$")
    axes[0, 0].set_ylabel("Logical T states")
    axes[0, 1].set_ylabel("Physical qubit-seconds")
    comparisons = [
        ("materialize_first", axes[1, 0], "Materialize-first / semantic-first"),
        ("external_tket_paulisimp", axes[1, 1], "External semantic / semantic-first"),
    ]
    for comparator, axis, title in comparisons:
        band = _band_ratio(frame, comparator).sort_values("epsilon_total")
        x = band["epsilon_total"].to_numpy(dtype=float)
        axis.fill_between(
            x,
            band["min"].to_numpy(dtype=float),
            band["max"].to_numpy(dtype=float),
            alpha=0.2,
            color=COLORS[comparator],
            label="range over QEC/factory profiles",
        )
        axis.plot(x, band["median"], color=COLORS[comparator], marker="o", label="median")
        axis.axhline(1.0, color="#333333", linestyle="--", linewidth=1)
        axis.set_xscale("log")
        axis.set_yscale("log")
        axis.invert_xaxis()
        axis.grid(True, which="both", alpha=0.22)
        axis.set_title(title)
        axis.set_xlabel(r"$\epsilon_{total}$")
        axis.set_ylabel("Spacetime ratio")
        axis.legend(frameon=False, fontsize=8)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncol=3, frameon=False)
    fig.suptitle("Fixed-total-error QRE sensitivity: 20k commuting-phase witness", fontsize=12)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)


def run(input_path: Path, pareto_path: Path, sensitivity_path: Path) -> dict[str, Any]:
    frame = pd.read_parquet(input_path)
    validation = validate(frame)
    ratios = ratio_summary(frame)
    plot_pareto(frame, pareto_path)
    plot_sensitivity(frame, sensitivity_path)
    main_slice = frame[
        (frame["target_id"] == "hdiag-20000")
        & (frame["epsilon_total"] == 1e-6)
        & (frame["allocation_policy"] == "equal_decimal")
        & (frame["qec_profile"] == "surface_code_conservative")
        & (frame["requested_factories"] == 16)
    ][[
        "pipeline_id", "logical_rotations", "logical_t_states", "code_distance",
        "physical_qubits", "factory_physical_qubits", "factories", "cycles",
        "runtime_seconds", "spacetime_qubit_seconds",
    ]].sort_values("pipeline_id")
    summary_path = ROOT / "data/frozen/qre_summary.csv"
    main_slice.to_csv(summary_path, index=False)
    audit = {
        "schema": "ucc.qre.analysis.v1",
        "validation": validation,
        "ratios": ratios,
        "main_slice": main_slice.to_dict(orient="records"),
        "artifacts_sha256": {
            os.path.relpath(input_path, ROOT): sha256(input_path),
            os.path.relpath(pareto_path, ROOT): sha256(pareto_path),
            os.path.relpath(sensitivity_path, ROOT): sha256(sensitivity_path),
            os.path.relpath(summary_path, ROOT): sha256(summary_path),
        },
    }
    audit_path = ROOT / "data/frozen/qre_analysis.json"
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {**validation, "analysis": str(audit_path), "figures": [str(pareto_path), str(sensitivity_path)]}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/frozen/qre_results.parquet")
    parser.add_argument("--pareto", type=Path, default=ROOT / "figures/qre_pareto.pdf")
    parser.add_argument("--sensitivity", type=Path, default=ROOT / "figures/qre_sensitivity.pdf")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run(args.input.resolve(), args.pareto.resolve(), args.sensitivity.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

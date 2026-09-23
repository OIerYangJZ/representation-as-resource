#!/usr/bin/env python3
"""Rebuild every submission figure directly from canonical frozen tables."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "tmp/matplotlib-w9"))
os.environ.setdefault("XDG_CACHE_HOME", str(ROOT / "tmp/fontconfig-w9"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    from scripts.analyze_matched_matrix import plot_pdf as plot_matched
    from scripts.analyze_qre_campaign import run as plot_qre
    from scripts.analyze_tradeoff import _plot_pdf as plot_tradeoff
    from scripts.run_factorial_ablation import plot_ablation, plot_natural_summary

    figures = ROOT / "figures"
    figures.mkdir(parents=True, exist_ok=True)

    tradeoff = pd.read_csv(ROOT / "data/frozen/tradeoff_summary.csv").to_dict(orient="records")
    fits = pd.read_csv(ROOT / "data/frozen/tradeoff_scaling_fits.csv").to_dict(orient="records")
    plot_tradeoff(tradeoff, fits, figures / "measured_tradeoff_frontier.pdf")

    matched = pd.read_parquet(ROOT / "data/frozen/matched_representation.parquet").to_dict(orient="records")
    matched_summary = pd.read_csv(ROOT / "data/frozen/matched_factorial_summary.csv").to_dict(orient="records")
    residuals = pd.read_csv(ROOT / "data/frozen/matched_interaction_residuals.csv").to_dict(orient="records")
    matched_fits = pd.read_csv(ROOT / "data/frozen/matched_scaling_fits.csv").to_dict(orient="records")
    plot_matched(matched, matched_summary, residuals, matched_fits, figures / "representation_compiler_interaction.pdf")

    plot_qre(
        ROOT / "data/frozen/qre_results.parquet",
        figures / "qre_pareto.pdf",
        figures / "qre_sensitivity.pdf",
    )

    natural = pd.read_csv(ROOT / "data/frozen/natural_workload_summary.csv")
    negative = pd.read_csv(ROOT / "data/frozen/natural_negative_controls.csv")
    effects = pd.read_csv(ROOT / "data/frozen/natural_ablation_effects.csv")
    interactions = pd.read_csv(ROOT / "data/frozen/natural_ablation_interactions.csv")
    plot_natural_summary(natural, negative, figures / "natural_workload_summary.pdf")
    plot_ablation(effects, interactions, figures / "ablation_effects.pdf")

    import importlib.util
    import shutil

    spec = importlib.util.spec_from_file_location(
        "run_eta_sweep", ROOT / "PaperDraft/scripts/run_eta_sweep.py"
    )
    eta_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(eta_module)
    eta_rows = json.loads((ROOT / "data/frozen/eta_sweep_pareto.json").read_text())["rows"]
    eta_module.figure(eta_rows, figures / "eta_sweep_pareto.pdf")
    shutil.copyfile(
        figures / "eta_sweep_pareto.pdf",
        ROOT / "PaperDraft/figures/eta_sweep_pareto.pdf",
    )

    cleanup_spec = importlib.util.spec_from_file_location(
        "generate_round3_cleanup_figures",
        ROOT / "research/round3_protocol_repair/generate_round3_cleanup_figures.py",
    )
    cleanup_module = importlib.util.module_from_spec(cleanup_spec)
    cleanup_spec.loader.exec_module(cleanup_module)
    cleanup_module.generate_real_instance_bars()

    outputs = sorted(figures.glob("*.pdf"))
    source_map = {
        "measured_tradeoff_frontier.pdf": ["data/frozen/tradeoff_summary.csv", "data/frozen/tradeoff_scaling_fits.csv"],
        "representation_compiler_interaction.pdf": ["data/frozen/matched_representation.parquet", "data/frozen/matched_factorial_summary.csv", "data/frozen/matched_interaction_residuals.csv", "data/frozen/matched_scaling_fits.csv"],
        "qre_pareto.pdf": ["data/frozen/qre_results.parquet"],
        "qre_sensitivity.pdf": ["data/frozen/qre_results.parquet"],
        "natural_workload_summary.pdf": ["data/frozen/natural_workload_summary.csv", "data/frozen/natural_negative_controls.csv"],
        "ablation_effects.pdf": ["data/frozen/natural_ablation_effects.csv", "data/frozen/natural_ablation_interactions.csv"],
        "eta_sweep_pareto.pdf": ["data/frozen/eta_sweep_pareto.json"],
    }
    figure_records = {
            path.name: {
                "path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size,
                "sha256": sha256(path), "sources": source_map[path.name],
                "source_sha256": {source: sha256(ROOT / source) for source in source_map[path.name]},
            }
            for path in outputs if path.name in source_map
    }
    real_instance_figure = ROOT / "PaperDraft/figures/real_instance_grouped_bar.png"
    real_instance_sources = [
        "research/real_instance_results.json",
        "research/round3_protocol_repair/generate_round3_cleanup_figures.py",
    ]
    figure_records[real_instance_figure.name] = {
        "path": str(real_instance_figure.relative_to(ROOT)),
        "bytes": real_instance_figure.stat().st_size,
        "sha256": sha256(real_instance_figure),
        "sources": real_instance_sources,
        "source_sha256": {source: sha256(ROOT / source) for source in real_instance_sources},
    }
    manifest = {"schema": "ucc.figure-build.v1", "figures": figure_records}
    target = ROOT / "data/frozen/figure_build_manifest.json"
    target.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

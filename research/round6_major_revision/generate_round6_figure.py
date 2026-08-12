#!/usr/bin/env python3
"""Generate the publication-facing unbounded-witness scaling figure."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

METHOD_STYLE = {
    "semantic_ucc": ("semantic UCC", "#2F855A", "o", 2.8),
    "qiskit_opt3": ("qiskit opt3", "#4C78A8", "s", 1.8),
    "pyzx_full_reduce": ("PyZX full_reduce", "#9C6ADE", "^", 1.8),
    "tket_guided_paulisimp": ("TKET GuidedPauliSimp", "#F2A541", "D", 1.8),
    "tket_paulisimp_rebased": ("TKET PauliSimp (rebased)", "#6B7280", "P", 2.0),
    "staq_rotation_folding": ("staq rotation folding", "#D1495B", "X", 3.0),
}


def generate(results_path: Path, title: str, stem: str, manuscript_name: str) -> None:
    import matplotlib.pyplot as plt

    rows = json.loads(results_path.read_text(encoding="utf-8"))
    if not rows:
        raise SystemExit("no result rows")
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    for method, (label, color, marker, width) in METHOD_STYLE.items():
        selected = sorted(
            (
                row
                for row in rows
                if row["method_key"] == method
                and row["status"] == "completed"
                and row["gate_count"] is not None
            ),
            key=lambda row: row["requested_gates"],
        )
        if not selected:
            continue
        ax.plot(
            [row["requested_gates"] for row in selected],
            [row["gate_count"] for row in selected],
            label=label,
            color=color,
            marker=marker,
            linewidth=width,
            markersize=6.5,
        )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xticks([4_000, 10_000, 20_000, 50_000, 100_000])
    ax.set_xticklabels(["4k", "10k", "20k", "50k", "100k"])
    ax.set_xlabel("Requested input gates")
    ax.set_ylabel("Completed output gates")
    ax.set_title(title)
    ax.grid(True, which="both", linewidth=0.6, alpha=0.3)
    ax.legend(frameon=False, fontsize=8, ncol=2)
    fig.tight_layout()
    local_pdf = HERE / "figures" / f"{stem}.pdf"
    local_png = HERE / "figures" / f"{stem}.png"
    local_pdf.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(local_pdf, bbox_inches="tight")
    fig.savefig(local_png, dpi=220, bbox_inches="tight")
    plt.close(fig)
    manuscript_pdf = ROOT / "PaperDraft" / "figures" / manuscript_name
    shutil.copyfile(local_pdf, manuscript_pdf)
    print(local_pdf.relative_to(ROOT))
    print(manuscript_pdf.relative_to(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--unbounded-results", type=Path, default=HERE / "unbounded_witness_results.json")
    parser.add_argument("--rational-results", type=Path, default=HERE / "rational_cp_round6_results.json")
    args = parser.parse_args()
    generate(
        args.unbounded_results,
        "Irrational independent-Pauli witness scaling",
        "unbounded_witness_scaling",
        "unbounded_witness_scaling.pdf",
    )
    generate(
        args.rational_results,
        "Rational CP finite-range pipeline scaling",
        "rational_cp_scaling",
        "fourier_separation.pdf",
    )


if __name__ == "__main__":
    main()

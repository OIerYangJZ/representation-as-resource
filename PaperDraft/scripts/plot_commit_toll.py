#!/usr/bin/env python3
"""Figure for E8 Arm A, drawn from the frozen artifact only.

Reads PaperDraft/generated/e8_commit_toll.json and writes
PaperDraft/figures/commit_toll.pdf.  Runs no experiment.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
GENERATED = THIS_FILE.parent.parent / "generated"
FIGURES = THIS_FILE.parent.parent / "figures"

COLORS = {128: "#0072B2", 512: "#E69F00", 2048: "#009E73"}


def main() -> int:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    payload = json.load(open(GENERATED / "e8_commit_toll.json"))
    summary = payload["summary"]

    fig, axes = plt.subplots(1, 2, figsize=(5.8, 2.6))

    # Left: the toll itself, against the schedule-entropy prediction.
    for m in (128, 512, 2048):
        cells = sorted(
            (e for e in summary.values() if e["m"] == m and "toll_bytegranular" in e),
            key=lambda e: e["eta"],
        )
        etas = [e["eta"] for e in cells]
        axes[0].plot(etas, [e["predicted_toll_bits_per_gen"] for e in cells],
                     "--", color="0.25", linewidth=1.1, zorder=1)
        axes[0].plot(etas, [e["toll_bytegranular"] for e in cells], "o",
                     color=COLORS[m], markersize=5, label=f"$m={m}$", zorder=3)
    axes[0].set_ylabel("commitment toll (bits/gen)")
    axes[0].set_title("toll $=$ schedule entropy", fontsize=9)
    axes[0].legend(frameon=False, fontsize=7, loc="upper right")

    # Right: exchange rate, identity-optimal vs the varint serializer.
    for m in (128, 512, 2048):
        cells = sorted(
            (e for e in summary.values()
             if e["m"] == m and "stream_opt_selfid" in e),
            key=lambda e: e["eta"],
        )
        etas = [e["eta"] for e in cells]
        state = [e["deferred"]["bits_per_gen_bytegranular"] for e in cells]
        opt = [e["stream_opt_selfid"]["bits_per_gen_bytegranular"] for e in cells]
        varint = [e["stream_varint"]["bits_per_gen_bytegranular"] for e in cells]
        axes[1].plot(etas, [a / b for a, b in zip(opt, state)], "o-",
                     color=COLORS[m], linewidth=2, markersize=4)
        axes[1].plot(etas, [a / b for a, b in zip(varint, state)], ":",
                     color=COLORS[m], linewidth=1.2, alpha=0.75)
    axes[1].axhline(1.0, color="0.4", linewidth=0.8)
    axes[1].set_ylabel("committed $/$ state (per gen.)")
    axes[1].set_title("solid: irreducible; dotted: as serialized", fontsize=9)

    for ax in axes:
        ax.set_xlabel(r"dispersal fraction $\eta$")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(True, linewidth=0.3, alpha=0.4)

    fig.text(0.5, -0.04,
             "dashed: $\\log_2\\binom{m}{k}/k$; horizontal line: par pricing",
             ha="center", fontsize=7)
    fig.tight_layout()
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / "commit_toll.pdf", bbox_inches="tight")
    plt.close(fig)
    print("wrote", FIGURES / "commit_toll.pdf")
    return 0


if __name__ == "__main__":
    sys.exit(main())

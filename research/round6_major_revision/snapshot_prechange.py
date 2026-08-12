#!/usr/bin/env python3
"""Create the immutable pre-change inventory for the major-revision run."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def command(*args: str) -> str:
    return subprocess.run(
        args, cwd=ROOT, check=True, text=True, capture_output=True
    ).stdout.strip()


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unavailable"


def main() -> None:
    prior_json = sorted(
        path
        for path in (ROOT / "research").rglob("*.json")
        if HERE not in path.parents
    )
    frozen_hashes = {
        str(path.relative_to(ROOT)): sha256(path) for path in prior_json
    }
    hash_path = HERE / "prechange_frozen_hashes.json"
    hash_path.write_text(
        json.dumps(frozen_hashes, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    pdf = ROOT / "PaperDraft/ucc_paper_draft_latex.pdf"
    pdf_info = command("pdfinfo", str(pdf))
    pages = next(
        line.split(":", 1)[1].strip()
        for line in pdf_info.splitlines()
        if line.startswith("Pages:")
    )

    key_files = [
        "PaperDraft/ucc_paper_draft_latex.tex",
        "PaperDraft/appendix/appendix_A.tex",
        "PaperDraft/appendix/appendix_B.tex",
        "PaperDraft/appendix/appendix_C.tex",
        "PaperDraft/ucc_paper_draft_latex.pdf",
        "research/round3_protocol_repair/run_round3_protocol_repair.py",
        "research/round3_protocol_repair/validate_round3_outputs.py",
        "research/round3_protocol_repair/generate_round3_manuscript_figures.py",
        "research/round3_protocol_repair/generate_round3_cleanup_figures.py",
        "ROUND5_FINAL_MINOR_CLEANUP_REPORT.md",
        "ROUND5_CLAIM_SCOPE_MICROPATCH_REPORT.md",
    ]
    key_rows = [
        (name, sha256(ROOT / name), (ROOT / name).stat().st_size)
        for name in key_files
    ]

    canonical_json = [
        "research/round3_protocol_repair/ssh_full_run_20260706_165733/round3_main_external_baselines_results.json",
        "research/round3_protocol_repair/ssh_full_run_20260706_165733/round3_fourier_ablation_completion_results.json",
        "research/round3_protocol_repair/ssh_full_run_20260706_165733/round3_resource_consequence_check_results.json",
        "research/round3_protocol_repair/ssh_full_run_20260706_165733/round3_correctness_extension_results.json",
        "research/noninverse_phase_ladder_scaling_results.json",
        "research/generalized_fourier_witness_results.json",
        "research/fourier_correctness_certificate_results.json",
        "research/fourier_seed_robustness_results.json",
        "research/fourier_topology_external_stress_results.json",
        "research/width_axis_external_stress_results.json",
        "research/resource_consequence_results.json",
        "research/scaling_results.json",
        "research/real_instance_results.json",
    ]

    lines = [
        "# Round 6 Pre-change Inventory",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        "## Repository and manuscript",
        "",
        f"- Repository root: `{ROOT}`",
        f"- Git commit at inventory: `{command('git', 'rev-parse', 'HEAD')}`",
        "- Main TeX: `PaperDraft/ucc_paper_draft_latex.tex`",
        "- Appendices A--C: `PaperDraft/appendix/appendix_A.tex`, `appendix_B.tex`, `appendix_C.tex`",
        "- Final PDF: `PaperDraft/ucc_paper_draft_latex.pdf`",
        f"- Current PDF: {pages} pages, {pdf.stat().st_size} bytes",
        "- Latest cleanup reports: `ROUND5_FINAL_MINOR_CLEANUP_REPORT.md` and `ROUND5_CLAIM_SCOPE_MICROPATCH_REPORT.md`",
        "- Canonical experiment harness: `research/round3_protocol_repair/run_round3_protocol_repair.py`",
        "- Canonical validators and figure generators: `validate_round3_outputs.py`, `generate_round3_manuscript_figures.py`, and `generate_round3_cleanup_figures.py` in the same directory.",
        "",
        "## Gate convention and theorem hooks",
        "",
        "- Canonical rational witness source: `_phase_diagonal_block` and `build_fourier_phase_sandwich` in `research/round3_protocol_repair/run_round3_protocol_repair.py`.",
        "- Its middle layer uses Qiskit `RZ(theta)` and `CP(theta)` gates. Qiskit `RZ(theta)=exp(-i theta Z/2)`; `CP(phi)=diag(1,1,1,exp(i phi))`.",
        "- The fixed-width family is `H D^r H` with all four leading and trailing Hadamards explicit.",
        "- Proposition 1 is `prop:fooling-set` in the main TeX; its coefficient-uniqueness dependency is `lem:pauli-uniqueness`.",
        "- The validated pumping architecture is Theorem `thm:final-output`, Corollary `cor:finite-tail`, and Appendix A's restated pumping chain; these are preserved structurally.",
        "- The canonical rational witness remains finite-range only: `T=131040`, reported maximum `R=9999`, and `rank_F2(A)=4<10`.",
        "",
        "## Local environment",
        "",
        f"- Python: `{sys.version.splitlines()[0]}`",
        f"- Platform: `{platform.platform()}`",
        f"- qiskit: `{package_version('qiskit')}`",
        f"- PyZX: `{package_version('pyzx')}`",
        f"- pytket: `{package_version('pytket')}`",
        f"- pytket-qiskit: `{package_version('pytket-qiskit')}`",
        f"- UCC: `{package_version('ucc')}`",
        "",
        "## Existing SSH execution environment",
        "",
        "- Alias: `school-server`; remote project root used previously: `/home/lyy/ucc_paper_round3`.",
        "- Recorded host: `327-cloudhin-3090`, Ubuntu 22.04 kernel 6.8, Intel i7-13700KF, 24 cores, 65,676,560 kB RAM.",
        "- Recorded runtime: Python 3.10.12, qiskit 2.5.0, PyZX 0.10.4, pytket 2.18.0, pytket-qiskit 0.77.0, UCC 0.4.12.",
        "- Previous canonical command: `./.venv/bin/python research/round3_protocol_repair/run_round3_protocol_repair.py --full --timeout-s 600`.",
        "- Round 6 will use a new remote root and new result paths; the old remote/local Round 3 outputs will not be overwritten.",
        "",
        "## Key file hashes",
        "",
        "| Path | SHA-256 | Bytes |",
        "|---|---|---:|",
    ]
    lines.extend(f"| `{name}` | `{digest}` | {size} |" for name, digest, size in key_rows)
    lines.extend(
        [
            "",
            "## Frozen JSON baseline",
            "",
            f"- `{hash_path.relative_to(ROOT)}` records SHA-256 for all {len(frozen_hashes)} pre-existing JSON files under `research/`.",
            "- The following canonical sources are explicitly frozen and will remain byte-for-byte unchanged:",
            "",
        ]
    )
    lines.extend(f"  - `{name}` (`{frozen_hashes[name]}`)" for name in canonical_json)
    lines.extend(
        [
            "",
            "## Isolation rule",
            "",
            "All new scripts, logs, JSON, provenance records, validators, and experimental figures are written under `research/round6_major_revision/`. Existing JSON is read-only. Manuscript and named publication-facing figure assets are edited only after new results validate.",
            "",
        ]
    )
    (HERE / "ROUND6_PRECHANGE_INVENTORY.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


if __name__ == "__main__":
    main()

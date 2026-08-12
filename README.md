# Representation as a Computational Resource in Quantum Compilation

Manuscript source, analysis code, and frozen data for:

> **Representation as a Computational Resource in Quantum Compilation:
> Approximate Recoverability Tradeoffs and Model-Specific Fault-Tolerant
> Consequences**
> Jinze Yang, Yangyang Li, Xiu-Hao Deng

| | |
|---|---|
| Manuscript | `PaperDraft/main.tex` → `PaperDraft/main.pdf` |
| Supplement | `PaperDraft/supplement.tex` → `PaperDraft/supplement.pdf` |
| arXiv variant | `PaperDraft/main_arXiv.tex` |
| Canonical data | `data/frozen/`, registered in `data/manifest.yaml` |
| Rebuild everything | `./reproducibility/run_submission.sh` |

## Reproducing the submission

```bash
uv sync                          # creates .venv from uv.lock
./reproducibility/run_submission.sh
```

The script runs the data audit, regenerates every table and figure from frozen
data, checks each registered W3–W9 headline number against
`data/provenance_map.yaml`, runs the clean-room subset and the full test suite,
builds both TeX documents, and fails if either LaTeX log has unresolved
references. No network access is needed.

For the clean-room subset alone:

```bash
.venv/bin/python reproducibility/run_clean_room.py
```

Exact package versions and the deterministic grid-synthesis binary hash are
frozen in `reproducibility/environment.lock`.

## Data policy

`data/manifest.yaml` is the authority on which datasets may support a number in
the manuscript. Only entries with role `canonical_source` or
`canonical_summary` qualify, and all of them live in `data/frozen/`.

Raw campaign trees are provenance, not canonical data, and are **not** included
in this repository — with one exception:
`data/runs/w7-fixed-total-error-20260803-local/` is kept because
`PaperDraft/appendix/appendix_B.tex` cites that path directly. The other raw
trees (w3, w4, w5, w8; roughly 550 MB) are archived outside version control.

## Layout

```
PaperDraft/       manuscript, supplement, appendices, figures, generated tables
  research/       preregistrations (E7, E8, E8b), claim-evidence and registries
  scripts/        per-experiment drivers and table generators
theory/           theorem environments included by main.tex
scripts/          campaign runners, analyzers, audit and build entry points
data/frozen/      canonical datasets
data/manifest.yaml, data/provenance_map.yaml
schema/           normalized experiment schema
reproducibility/  submission rebuild and clean-room entry points
tests/            certificate, codec, workload, and provenance tests
research/         exploratory work and the round-3 / round-6 revision campaigns
ucc/              the compiler package this work builds on
benchmarks/ certificates/ compiler/ encoding/ instrumentation/ qre/ workloads/
figures/          figures rendered outside PaperDraft/figures/
```

## Third-party tools

The round-6 validation calls two external compilers. They are **not** vendored
here; rebuild them from these upstream commits to reproduce that campaign:

| Tool | Upstream | Commit |
|---|---|---|
| staq | https://github.com/softwareQinc/staq | `a2acd39e60ed0e5f1978fa530df7e1e0c7cedf7a` (v3.5-36) |
| feynman | https://github.com/meamy/feynman | `d2c382a2ab43a40a87f12f4255645bbb55f704f8` (v0.1.0-221) |

Place the builds under `research/round6_major_revision/tools/`, which is
gitignored.

## Relationship to UCC

The `ucc/` package derives from the [Unitary Compiler
Collection](https://github.com/unitaryfoundation/ucc) and remains under
AGPL-3.0 (see `LICENSE`). This repository is a research fork: it is not the
upstream distribution, is not published to PyPI, and carries modifications made
for the experiments in this manuscript. For the maintained library, use
upstream.

## Status

Under review at PRX Quantum. Numbers, figures, and claims here track the
submitted version; see `CHANGELOG.md` for the revision history.

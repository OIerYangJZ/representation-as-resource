# Representation as a Resource

This repository contains the manuscript, frozen experimental evidence, and
reproduction code for *Representation as a Resource*.

## Reproduce the submitted artifact

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and a TeX
distribution providing `latexmk`, then run from the repository root:

```bash
./reproducibility/run_submission.sh
```

On a fresh clone the command creates `.venv` from the committed `uv.lock`.
It audits the committed frozen W3--W9 datasets, regenerates registered tables
and figures, runs the full test suite and clean-room subset, and builds the
canonical, arXiv, Quantum-submission, and supplement PDFs. The first run can
require network access to populate uv's package cache; subsequent runs can use
the locked local environment without network access.

The approximately 700 MB raw run tree is archived separately in the private
[`OIerYangJZ/paper1-data`](https://github.com/OIerYangJZ/paper1-data)
repository. It is not required to regenerate the submitted tables and figures
from the immutable frozen datasets. Authorized users can fetch it with:

```bash
./reproducibility/fetch_raw_data.sh
```

See [`reproducibility/README.md`](reproducibility/README.md) for the precise
scope and limitations of each reproduction level.

## Repository layout

| Path | Contents |
|---|---|
| `PaperDraft/` | Manuscript sources (canonical, arXiv, Quantum, supplement) and per-experiment frozen records |
| `data/` | Frozen datasets, manifest, and provenance map cited by the paper |
| `scripts/`, `tests/` | Table/figure generation, data audits, and paper-number provenance tests |
| `compiler/`, `encoding/`, `certificates/`, `instrumentation/`, `workloads/`, `benchmarks/`, `baselines/`, `qre/`, `schema/`, `configs/` | Experiment code for the W3--W9 campaigns |
| `theory/` | Proof notes |
| `research/` | Earlier experiment records cited by the paper or its round-3/round-6 revision audits |
| `ucc/` | Frozen snapshot of the UCC-based compiler used in the experiments |

`ucc/` is the exact compiler version the experiments ran against. It is a
modified copy of the [Unitary Compiler Collection](https://github.com/unitaryfoundation/ucc),
kept here only so the campaigns can be rerun; it is not maintained in this
repository. The code is distributed under the AGPL-3.0 license in `LICENSE`.

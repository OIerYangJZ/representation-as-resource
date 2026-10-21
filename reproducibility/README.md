# Reproducibility entry points

The repository contains immutable frozen W3--W9 datasets sufficient to audit
every headline number and regenerate all registered submission tables and
figures. The canonical datasets are registered in `data/manifest.yaml`; the
normalized schema is `schema/experiment.schema.json`; data-derived manuscript
numbers are registered in `data/provenance_map.yaml`.

## Submission rebuild from a fresh clone

Install `uv` and a TeX distribution providing `latexmk`, then run:

```bash
./reproducibility/run_submission.sh
```

If `.venv` is absent, the script first runs
`uv sync --frozen --all-extras --all-groups`. The first execution can therefore
need network access to populate uv's cache. It then performs the frozen-data
audit, regenerates tables and figures, checks every registered W3--W9 headline
number, runs the independent-directory theorem/benchmark/QRE subset, executes
the full test suite, builds all four TeX deliverables, and fails on unresolved
references.

This rebuild starts from the committed frozen datasets; it does not rerun the
full W3--W8 measurement campaigns.

## Optional raw provenance archive

The approximately 700 MB raw run tree is stored in the separate private
`OIerYangJZ/paper1-data` repository. Authorized users can materialize it under
`data/raw-archive/` without overwriting the canonical frozen data:

```bash
./reproducibility/fetch_raw_data.sh
```

The data audit reports whether this optional archive is present and verifies
its registered receipt hashes when available. Archive absence is reported but
does not invalidate a frozen-data rebuild.

The campaign scripts' built-in defaults still point at the original
`data/runs/<campaign>/` layout. To rerun an analysis against the archive, pass
the archived directory explicitly, e.g.
`--campaign-root data/raw-archive/runs/w4-matched-representation-20260802`.

## Clean-room subset

To run only the clean-room subset:

```bash
.venv/bin/python reproducibility/run_clean_room.py
```

No network access is needed after the locked project environment exists. The clean-room environment is a new virtual
environment explicitly bound to the locked project `.venv` site-packages;
therefore this proves independence from the working directory, not binary
independence from the host Python installation.  Exact package versions and
the deterministic grid-synthesis binary hash are frozen in `environment.lock`.

## Platform requirement

The W7 QRE subset of the clean room (and therefore `run_submission.sh`)
executes `PaperDraft/research/fixed_budget_qre/tools/staq_grid_synth`, a
committed macOS arm64 binary whose SHA256 is pinned in `environment.lock`.
`run_submission.sh` stops early on any other platform. To rebuild the binary
elsewhere, compile `tools/grid_synth_deterministic.cpp` (C++17, GMP) against
the public staq headers at the commit recorded in `environment.lock`; see
`PaperDraft/research/fixed_budget_qre/README.md`. A rebuilt binary will not
match the pinned hash, so record its hash alongside any results it produces.

## Notes on the freeze manifests

The `files` entries of `data/frozen/*_freeze_manifest.json` were recorded when
each campaign was frozen. Three kinds of entries no longer match a file in this
repository's working tree; none of them affects the frozen datasets or any
reported number.

- **Code edited after the W5 freeze.** `scripts/run_external_baselines.py`
  and `baselines/configs/campaign.yaml` were changed in commit `a94c8b8`
  only to let the 216-input W5 matrix expansion fall back to
  `data/frozen/external_baselines.parquet` when the raw W4 index is absent.
  The freeze-time versions, which match the recorded hashes, are in commit
  `11e2ca0` (`git show 11e2ca0:scripts/run_external_baselines.py`).
- **Regenerated figure.** `figures/representation_compiler_interaction.pdf` is
  rebuilt from the frozen tables by `scripts/build_all_figures.py`; its current
  hash is recorded in `data/frozen/figure_build_manifest.json`.
- **Files outside this repository.** The raw `data/runs/w4-*/…jsonl` and
  `data/runs/w5-*/…jsonl` files are in the optional raw archive under
  `data/raw-archive/runs/` and match the recorded hashes. The
  `MATCHED_REPRESENTATION_REPORT.md` and `EXTERNAL_BASELINE_REPORT.md` reports
  were written in the original working repository and are not part of this
  artifact; the W4 and W5 results they summarized are reported in the paper and supplement.

`frozen_artifact_commit` in `environment.lock` and `data/manifest.yaml` refers
to that original working repository, not to this one.

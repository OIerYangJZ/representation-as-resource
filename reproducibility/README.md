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

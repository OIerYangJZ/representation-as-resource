# Reproducibility entry point

The canonical datasets are registered in `data/manifest.yaml`; the normalized
schema is `schema/experiment.schema.json`; data-derived manuscript numbers are
registered in `data/provenance_map.yaml`.

Run the complete submission rebuild from the repository root:

```bash
./reproducibility/run_submission.sh
```

The command performs the data audit, regenerates tables and figures from frozen
data, checks every registered W3--W9 headline paper number, runs the
independent-directory
theorem/benchmark/QRE subset, executes the full local test suite, builds both
TeX documents, and fails if either LaTeX log has unresolved references.

To run only the clean-room subset:

```bash
.venv/bin/python reproducibility/run_clean_room.py
```

No network access is needed.  The clean-room environment is a new virtual
environment explicitly bound to the locked project `.venv` site-packages;
therefore this proves independence from the working directory, not binary
independence from the host Python installation.  Exact package versions and
the deterministic grid-synthesis binary hash are frozen in `environment.lock`.

# Files Selected For SSH Upload

Generated: 2026-07-06

## Roots

- Local project root: `/Users/yangjinsey/Desktop/QFT + inverse-QFT circuits #662(issue)`
- Remote project root: `/home/lyy/ucc_paper_round3`

## Upload Strategy

Compact dependency-closure upload with `rsync`, preserving relative paths.

This was chosen because `run_round3_protocol_repair.py` and
`validate_round3_outputs.py` do not read old experiment result files as inputs.
The runner generates Fourier-phase-sandwich circuits in memory, imports the
local `ucc` package, imports external quantum toolchains from the virtual
environment, and writes all new outputs under
`research/round3_protocol_repair/`.

The remote root did not already exist during preflight, so running the fixed
Round 3 command there will not overwrite prior full-run outputs.

## Selected Files And Directories

| Path | Reason |
|---|---|
| `pyproject.toml` | Project metadata and dependency declarations, including the `research` dependency group used for the server install. |
| `uv.lock` | Lock data available if `uv` is present on the server. |
| `README.md` | Required by `pyproject.toml` metadata during editable install/build backend setup. |
| `LICENSE` | Project metadata/provenance file for the editable package. |
| `research/round3_protocol_repair/run_round3_protocol_repair.py` | Primary Round 3 repaired protocol runner. |
| `research/round3_protocol_repair/validate_round3_outputs.py` | Output schema/row validator requested after smoke and after full run. |
| `research/round3_protocol_repair/FILES_SELECTED_FOR_SSH_UPLOAD.md` | This provenance record. |
| `ucc/__init__.py` | Local package import surface used by the runner via `import ucc`. |
| `ucc/_version.py` | Local package version helper imported by `ucc.__init__`. |
| `ucc/compile.py` | `ucc.compile(...)` implementation used by semantic UCC and no-Fourier ablation rows. |
| `ucc/transpilers/*.py` | Default compiler/pass source imported by `ucc.compile`. |
| `ucc/transpilers/aqc/*.py` and `ucc/transpilers/aqc/README.md` | Included as package-source closure for the local `ucc.transpilers` package, although the Round 3 runner's default path does not directly call AQC. |

## Dependency Inspection Summary

- `run_round3_protocol_repair.py` imports standard-library modules, `qiskit`,
  `pyzx`, `pytket`, optional `pytket.extensions.qiskit`, and local `ucc`.
- The runner constructs the benchmark circuits directly; no old JSON/MD result
  files are read as inputs.
- The validator scans only `round3_*_results.json` and
  `smoke_round3_*_results.json` under `research/round3_protocol_repair/`.
- The runner writes method maps, call-sequence provenance, result JSON/MD,
  environment snapshots, summary guidance, and run logs under
  `research/round3_protocol_repair/`.

## Excluded Directories And Patterns

- `.git/`
- `.venv/`
- `__pycache__/`
- `.pytest_cache/`
- `.mypy_cache/`
- `.ruff_cache/`
- `.DS_Store`
- `Paper/`, `PaperDraft/`, formal proof/patch files, manuscript PDFs, and
  LaTeX temporary files
- `Graph Materials/`, generated figures, render outputs, and PDF/PNG artifacts
- Old frozen experiment outputs outside `research/round3_protocol_repair/`
- Existing smoke/full Round 3 JSON/MD outputs; the remote run will regenerate
  outputs in the fresh remote project root
- Nested duplicate checkout artifacts under `ucc/.git/`, `ucc/PaperDraft/`,
  `ucc/Graph Materials/`, `ucc/RelatedWorks/`, `ucc/out/`, `ucc/research/`,
  and `ucc/tests/`

## Uncertainty

- Server package installation depends on the server's Python version and PyPI
  access. The project requires Python `>=3.12,<3.14`.
- `pytket-qiskit` may not install or import in the server environment. The
  runner discloses and uses a QASM fallback when
  `pytket.extensions.qiskit` is unavailable.
- `TKET PauliSimp` and `GuidedPauliSimp` are version-dependent; their
  importability is recorded in `ssh_environment_setup.md`.

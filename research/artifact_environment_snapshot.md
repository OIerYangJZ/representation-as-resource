# Artifact Environment Snapshot

This snapshot records the frozen local environment used for the final
`#662(issue)` experiment rerun.

## Python

- Python `3.12.12`

## Key Packages

- `qiskit`: `2.3.1`
- `qbraid`: `0.11.1`
- `numpy`: `2.3.3`
- `scipy`: `1.16.2`
- `mqt.bench`: `2.2.1`
- `supermarq`: `0.5.64`

## Repository Layout Assumptions

- experimental repo:
  - `/Users/yangjinsey/Desktop/QFT + inverse-QFT circuits #662(issue)/ucc`
- default baseline repo used in the artifact scripts:
  - `/tmp/ucc_662issue_baseline`

## Notes

- The canonical experiment rerun uses the local `.venv` inside the experimental
  repo.
- The hardware-aware canonical run uses `seed_transpiler = 12345`.
- The hardware-aware seed sweep additionally covers:
  - `0`
  - `1`
  - `42`
  - `54321`

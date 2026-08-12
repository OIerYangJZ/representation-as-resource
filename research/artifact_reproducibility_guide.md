# Artifact Reproducibility Guide

## Purpose

This document describes the frozen reproducibility workflow for the
`#662(issue)` research workspace.

The goal is simple:

- one wrapper script
- one environment snapshot
- one output manifest
- canonical JSON/Markdown outputs that match the frozen rerun used to update
  the paper draft and submission checklists

## Artifact Files

The reproducibility entry points are now:

- `run_frozen_artifact.py`
- `artifact_environment_snapshot.md`
- `artifact_output_manifest.md`

The core experiment scripts remain:

- `compare_real_instances.py`
- `compare_mqt_benchmarks.py`
- `compare_supermarq_benchmarks.py`
- `compare_external_baselines.py`
- `compare_hardware_aware.py`
- `scaling_study.py`
- `ablation_study.py`
- `resource_consequence_experiment.py`
- `stability_repeated_runs.py`

## Environment Assumptions

The frozen local setup is documented in:

- `artifact_environment_snapshot.md`

The canonical local assumptions are:

- experimental repo:
  - `/Users/yangjinsey/Desktop/QFT + inverse-QFT circuits #662(issue)/ucc`
- experimental virtual environment:
  - `./.venv`
- baseline repo:
  - `/tmp/ucc_662issue_baseline`

If the baseline repo is elsewhere, pass `--baseline-repo` explicitly.

## Unified Reproduction Entry Point

The artifact can now be rerun through a single wrapper script:

```bash
./.venv/bin/python research/run_frozen_artifact.py --suite full
```

Supported suites:

- `core`
  - official real instances
  - `MQT Bench`
  - `SupermarQ`
  - canonical hardware-aware run
- `structured`
  - fixed-basis `100k` baselines
  - scaling
  - ablation
- `stability`
  - canonical repeated-run table
  - 5-seed hardware-aware sweep
- `full`
  - all of the above

To preview commands without running them:

```bash
./.venv/bin/python research/run_frozen_artifact.py --suite full --dry-run
```

## Canonical Output Files

The output-to-script mapping is documented in:

- `artifact_output_manifest.md`

The main canonical outputs are:

- `real_instance_results.json` / `.md`
- `mqt_bench_results.json` / `.md`
- `supermarq_results.json` / `.md`
- `fixed_basis_external_baselines_100k.json` / `.md`
- `scaling_results.json` / `.md`
- `ablation_results_10k.json` / `.md`
- `resource_consequence_results.json` / `.md` / `_summary.md`
- `hardware_aware_results.json` / `.md`
- `stability_results.json` / `.md`
- `stability_seeded_results.json` / `.md`
- `stability_seed2_results.json` / `.md`
- `stability_seed3_results.json` / `.md`
- `stability_seed4_results.json` / `.md`
- `stability_seed5_results.json` / `.md`

## Determinism Notes

The artifact should be interpreted with the following reproducibility rules:

- official real-instance outputs are deterministic across repeated runs
- canonical hardware-aware results are deterministic for each fixed seed
- the canonical hardware-aware table uses:
  - `seed_transpiler = 12345`
- the hardware-aware seed sweep additionally records:
  - `0`
  - `1`
  - `42`
  - `54321`

This is important because the final paper distinguishes:

- deterministic repeated-run stability
- fixed-seed reproducibility
- cross-seed stability on the `hw_mqt_qaoa_20` workload family

## Expected Reviewer Workflow

A reviewer should be able to:

1. activate the experimental repo virtual environment
2. ensure the baseline repo exists
3. run:

```bash
./.venv/bin/python research/run_frozen_artifact.py --suite full
```

4. compare the regenerated files in `research/` against the paper tables and
   summary documents

## Remaining Non-Artifact Work

The artifact is now standardized enough for paper use, but the following are
still outside the current scope:

- figure plotting scripts
- archival packaging into a separate `artifact/` tarball
- CI automation for rerunning the full frozen suite

These are packaging tasks, not reproducibility blockers for the current draft.

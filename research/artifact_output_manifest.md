# Artifact Output Manifest

This manifest maps each canonical output file to the script that regenerates
it in the frozen `#662(issue)` artifact.

| Output | Script |
|---|---|
| `real_instance_results.json` / `.md` | `compare_real_instances.py` |
| `mqt_bench_results.json` / `.md` | `compare_mqt_benchmarks.py` |
| `supermarq_results.json` / `.md` | `compare_supermarq_benchmarks.py` |
| `fixed_basis_external_baselines_100k.json` / `.md` | `compare_external_baselines.py --target-gates 100000` |
| `scaling_results.json` / `.md` | `scaling_study.py` |
| `ablation_results_10k.json` / `.md` | `ablation_study.py --target-gates 10000` |
| `resource_consequence_results.json` / `.md` / `_summary.md` | `resource_consequence_experiment.py` |
| `hardware_aware_results.json` / `.md` | `compare_hardware_aware.py --seed-transpiler 12345` |
| `stability_results.json` / `.md` | `stability_repeated_runs.py --repeats 5 --hw-seed 12345` |
| `stability_seed4_results.json` / `.md` | `stability_repeated_runs.py --repeats 3 --hw-seed 0` |
| `stability_seed5_results.json` / `.md` | `stability_repeated_runs.py --repeats 3 --hw-seed 1` |
| `stability_seed3_results.json` / `.md` | `stability_repeated_runs.py --repeats 3 --hw-seed 42` |
| `stability_seeded_results.json` / `.md` | `stability_repeated_runs.py --repeats 3 --hw-seed 12345` |
| `stability_seed2_results.json` / `.md` | `stability_repeated_runs.py --repeats 3 --hw-seed 54321` |

## Unified Entry Point

Use:

```bash
./.venv/bin/python research/run_frozen_artifact.py --suite full
```

or a narrower suite:

```bash
./.venv/bin/python research/run_frozen_artifact.py --suite core
./.venv/bin/python research/run_frozen_artifact.py --suite structured
./.venv/bin/python research/run_frozen_artifact.py --suite stability
```

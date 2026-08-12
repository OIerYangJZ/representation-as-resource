# Round 3 Run Log

Generated: `2026-07-06T08:57:32+00:00`
Mode: `full`
Python executable: `/home/lyy/ucc_paper_round3/.venv/bin/python`
Uniform timeout: `600` seconds
Sizes: `4000, 10000, 20000, 50000, 100000`
Correctness repeats: `9999`

## Entry Points

Smoke:

```bash
./.venv/bin/python research/round3_protocol_repair/run_round3_protocol_repair.py --smoke
```

Full:

```bash
./.venv/bin/python research/round3_protocol_repair/run_round3_protocol_repair.py --full --timeout-s 600
```

Full with shorter disclosed budget:

```bash
./.venv/bin/python research/round3_protocol_repair/run_round3_protocol_repair.py --full --timeout-s 300
```

## Files Written

- `research/round3_protocol_repair/method_name_map.md`
- `research/round3_protocol_repair/baseline_call_sequences.md`
- `research/round3_protocol_repair/round3_main_external_baselines_results.json`
- `research/round3_protocol_repair/round3_main_external_baselines_results.md`
- `research/round3_protocol_repair/round3_fourier_ablation_completion_results.json`
- `research/round3_protocol_repair/round3_fourier_ablation_completion_results.md`
- `research/round3_protocol_repair/round3_resource_consequence_check_results.json`
- `research/round3_protocol_repair/round3_resource_consequence_check_results.md`
- `research/round3_protocol_repair/round3_correctness_extension_results.json`
- `research/round3_protocol_repair/round3_correctness_extension_results.md`
- `research/round3_protocol_repair/round3_table_provenance_map.md`
- `research/round3_protocol_repair/round3_environment_snapshot.md`
- `research/round3_protocol_repair/round3_summary_for_paper_patch.md`
- `research/round3_protocol_repair/round3_run_log.md`

Old frozen result files were not overwritten by this workflow.

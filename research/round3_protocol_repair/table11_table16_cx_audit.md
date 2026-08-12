# Table 11 / Table 16 CX Audit

Generated: `2026-07-07T08:14:40.947273+00:00`

## Source Files Inspected

- `research/real_instance_results.json` (json, present)
- `Graph Materials/baseline vs optimized vs qiskit opt3/real_instance_results.json` (json, present)
- `research/real_instance_results.md` (md, present)
- `research/real_instance_results_summary.md` (md, present)
- `Graph Materials/baseline vs optimized vs qiskit opt3/real_instance_results_summary.md` (md, present)
- `research/round3_protocol_repair/round3_table_provenance_map.md` (md, present)
- `research/round3_protocol_repair/ssh_full_run_20260706_165733/round3_table_provenance_map.md` (md, present)
- `PaperDraft/ucc_paper_draft_latex.tex` (tex, present)
- `PaperDraft/appendix/appendix_C.tex` (tex, present)

## Extracted Table Rows

| Table | Method key | Paper method | Gates | Depth | Table CX | Source CX | Source | Status |
|---|---|---|---:|---:|---:|---:|---|---|
| Table 11 | `translation_only` | translation only | 159,838 | 121,214 | 67,608 | 67,608 | `research/real_instance_results.json` | matched_json_row |
| Table 11 | `qiskit_opt3` | qiskit opt3 | 166,805 | 119,204 | 58,491 | 58,491 | `research/real_instance_results.json` | matched_json_row |
| Table 11 | `baseline_ucc` | upstream UCC v0.4.12 pre-semantic default | 471,819 | 328,271 | 58,491 | 58,491 | `research/real_instance_results.json` | matched_json_row |
| Table 11 | `optimized_ucc` | semantic UCC | 166,805 | 119,204 | 58,491 | 58,491 | `research/real_instance_results.json` | matched_json_row |
| Appendix C Table 16 | `baseline_ucc` | baseline UCC | 471,819 | 328,271 | 81,906 | 58,491 | `Graph Materials/baseline vs optimized vs qiskit opt3/real_instance_results.json` | matched_json_row |
| Appendix C Table 16 | `defaults_preinverse_only` | defaults_preinverse_only | 485,780 | 332,924 | 82,925 |  | `` | no_json_source_for_method |
| Appendix C Table 16 | `defaults_reordered_only` | defaults_reordered_only | 485,780 | 332,924 | 82,925 |  | `` | no_json_source_for_method |
| Appendix C Table 16 | `defaults_minimal_bundle` | defaults_minimal_bundle | 485,780 | 332,924 | 82,925 |  | `` | no_json_source_for_method |
| Appendix C Table 16 | `optimized_ucc` | semantic UCC | 166,805 | 119,204 | 27,303 | 58,491 | `Graph Materials/baseline vs optimized vs qiskit opt3/real_instance_results.json` | matched_json_row |
| Appendix C Table 16 | `qiskit_opt3` | qiskit opt3 | 166,805 | 119,204 | 27,303 | 58,491 | `Graph Materials/baseline vs optimized vs qiskit opt3/real_instance_results.json` | matched_json_row |

## Table 11 vs Table 16 Comparison

| Method key | Same gates/depth | Table 11 CX | Table 16 CX | Inconsistent table |
|---|---:|---:|---:|---|
| `baseline_ucc` | True | 58,491 | 81,906 | Appendix C Table 16 |
| `optimized_ucc` | True | 58,491 | 27,303 | Appendix C Table 16 |
| `qiskit_opt3` | True | 58,491 | 27,303 | Appendix C Table 16 |

## Verdict

Appendix C Table 16 is inconsistent with the frozen real-instance JSON for overlapping phase_estimation_real rows; Table 11 matches the frozen JSON. No JSON source was found for the defaults_* reorder-probe rows.

## Selector kappa Arithmetic

The selector score is `kappa = gates + depth + 10 * multi_qubit`.

| Method key | Gates | Depth | Multi-qubit/CX | kappa |
|---|---:|---:|---:|---:|
| `translation_only` | 159,838 | 121,214 | 67,608 | 957,132 |
| `qiskit_opt3` | 166,805 | 119,204 | 58,491 | 870,919 |
| `baseline_ucc` | 471,819 | 328,271 | 58,491 | 1,385,000 |
| `optimized_ucc` | 166,805 | 119,204 | 58,491 | 870,919 |

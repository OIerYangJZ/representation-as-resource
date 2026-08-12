# Round 3 Repair Run Report

Generated locally: `2026-07-06T11:37:40+00:00` UTC

## Source Note

- The SSH server did not contain a file named `ROUND3_REPAIR_RUN_REPORT.md`.
- This local report was generated from the pulled Round 3 full-run JSON files, logs, `round3_summary_for_paper_patch.md`, and environment reports in this extraction folder.
- The original pulled files are preserved alongside this report.

## Run Status

```text
full_status=0
validate_status=0
finished_at=2026-07-06T16:57:33+08:00
```

Full-run validator: passed with exit code 0; see `logs/ssh_validate_after_full.log`.

## Full JSON Row Counts

| File | Rows | Status counts |
|---|---:|---|
| `round3_main_external_baselines_results.json` | 45 | `{'completed': 28, 'timeout': 12, 'error': 5}` |
| `round3_fourier_ablation_completion_results.json` | 25 | `{'completed': 21, 'timeout': 4}` |
| `round3_resource_consequence_check_results.json` | 20 | `{'completed': 18, 'timeout': 2}` |
| `round3_correctness_extension_results.json` | 2 | `{'completed': 2}` |

## Main Result Summary

- `semantic_ucc` completed all 5 main sizes with constant output metrics: `42` gates, depth `24`, `12` CX.
- `qiskit_opt3` completed all 5 main sizes but grows linearly; at size `100000` it produced `239988` gates, depth `139993`, `119988` CX.
- `phase_poly_reference` completed all 5 main sizes with the same `42/24/12` structural metrics as semantic UCC.
- `pyzx_full_reduce` completed only size `4000`; larger sizes timed out under the uniform 600 s budget.
- `tket_fullpeephole` timed out for all 5 main sizes.
- `tket_paulisimp` errored for all 5 main sizes with TKET predicate-requirement failures.
- `tket_guided_paulisimp` completed all 5 main sizes but did not recover the bounded semantic form.

## Ablation And Correctness

- `no_fourier_ucc` completed sizes `4000`, `10000`, and `20000`; it timed out at `50000` and `100000`.
- Correctness extension completed for both `semantic_ucc` and `phase_poly_reference`; both reported `Operator.equiv=True`.

## Paper-Facing Guidance

- Use `round3_summary_for_paper_patch.md` as the canonical wording guide.
- Strict completed-pair `semantic_ucc` vs `qiskit_opt3` structural wins are `5/5` in this run.
- Timeout cells must not be counted as lexicographic structural wins.
- Disclose the uniform `600` second per-method per-instance timeout and the Python 3.10 fallback environment caveat.

## Requested Files In This Folder

- `ssh_environment_snapshot.md`
- `method_name_map.md`
- `baseline_call_sequences.md`
- `round3_summary_for_paper_patch.md`
- `round3_*_results.json` and `.md`
- `logs/ssh_validate_after_full.log`

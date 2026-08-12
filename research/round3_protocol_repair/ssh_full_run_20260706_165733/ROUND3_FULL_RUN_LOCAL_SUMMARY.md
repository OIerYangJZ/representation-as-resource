# Round 3 Full Run Local Summary

Generated: `2026-07-06T10:03:55+00:00` UTC

## Location

- Local extraction directory: `research/round3_protocol_repair/ssh_full_run_20260706_165733/`
- Remote run root: `/home/lyy/ucc_paper_round3`
- Full-run exit status: `full_status=0`, `validate_status=0` from `logs/ssh_full_exit_status.txt`.
- Full validator log: `logs/ssh_validate_after_full.log`.

## Environment Caveat

The server run used the documented Python 3.10 fallback because the server did not have Python 3.12/3.13 and the `uv` managed-Python download stalled. `pytket-qiskit` and all three requested TKET passes imported successfully. This caveat is recorded in `ssh_environment_setup.md` and `round3_environment_snapshot.md`.

## Validator Result

The full-run validator completed with exit code 0. All four full JSON files were valid and had no malformed rows.

## Row Counts And Statuses

| File | Rows | Status counts |
|---|---:|---|
| `round3_main_external_baselines_results.json` | 45 | `{'completed': 28, 'timeout': 12, 'error': 5}` |
| `round3_fourier_ablation_completion_results.json` | 25 | `{'completed': 21, 'timeout': 4}` |
| `round3_resource_consequence_check_results.json` | 20 | `{'completed': 18, 'timeout': 2}` |
| `round3_correctness_extension_results.json` | 2 | `{'completed': 2}` |

## Status By Method

### round3_main_external_baselines_results.json

| Method | Status counts |
|---|---|
| `phase_poly_reference` | `{'completed': 5}` |
| `pyzx_configured` | `{'completed': 4, 'timeout': 1}` |
| `pyzx_full_reduce` | `{'completed': 1, 'timeout': 4}` |
| `qiskit_commutative_inverse` | `{'completed': 3, 'timeout': 2}` |
| `qiskit_opt3` | `{'completed': 5}` |
| `semantic_ucc` | `{'completed': 5}` |
| `tket_fullpeephole` | `{'timeout': 5}` |
| `tket_guided_paulisimp` | `{'completed': 5}` |
| `tket_paulisimp` | `{'error': 5}` |

### round3_fourier_ablation_completion_results.json

| Method | Status counts |
|---|---|
| `no_fourier_ucc` | `{'completed': 3, 'timeout': 2}` |
| `phase_poly_reference` | `{'completed': 5}` |
| `qiskit_commutative_inverse` | `{'completed': 3, 'timeout': 2}` |
| `qiskit_opt3` | `{'completed': 5}` |
| `semantic_ucc` | `{'completed': 5}` |

### round3_resource_consequence_check_results.json

| Method | Status counts |
|---|---|
| `no_fourier_ucc` | `{'completed': 3, 'timeout': 2}` |
| `phase_poly_reference` | `{'completed': 5}` |
| `qiskit_opt3` | `{'completed': 5}` |
| `semantic_ucc` | `{'completed': 5}` |

### round3_correctness_extension_results.json

| Method | Status counts |
|---|---|
| `phase_poly_reference` | `{'completed': 1}` |
| `semantic_ucc` | `{'completed': 1}` |

## Main External Baselines: Selected Metrics

| Size | Method | Status | Gates | Depth | CX | Wall time s |
|---:|---|---|---:|---:|---:|---:|
| 4000 | `semantic_ucc` | `completed` | 42 | 24 | 12 | 2.93 |
| 4000 | `phase_poly_reference` | `completed` | 42 | 24 | 12 | 0.215 |
| 4000 | `qiskit_opt3` | `completed` | 9588 | 5593 | 4788 | 1.004 |
| 4000 | `pyzx_full_reduce` | `completed` | 107 | 59 | 31 | 97.676 |
| 4000 | `tket_fullpeephole` | `timeout` | - | - | - | 600.264 |
| 4000 | `tket_paulisimp` | `error` | - | - | - | 0.818 |
| 4000 | `tket_guided_paulisimp` | `completed` | 13574 | 6392 | 4788 | 1.046 |
| 10000 | `semantic_ucc` | `completed` | 42 | 24 | 12 | 8.774 |
| 10000 | `phase_poly_reference` | `completed` | 42 | 24 | 12 | 0.252 |
| 10000 | `qiskit_opt3` | `completed` | 23988 | 13993 | 11988 | 4.967 |
| 10000 | `pyzx_full_reduce` | `timeout` | - | - | - | 600.112 |
| 10000 | `tket_fullpeephole` | `timeout` | - | - | - | 600.127 |
| 10000 | `tket_paulisimp` | `error` | - | - | - | 1.022 |
| 10000 | `tket_guided_paulisimp` | `completed` | 33974 | 15992 | 11988 | 1.606 |
| 20000 | `semantic_ucc` | `completed` | 42 | 24 | 12 | 28.314 |
| 20000 | `phase_poly_reference` | `completed` | 42 | 24 | 12 | 0.293 |
| 20000 | `qiskit_opt3` | `completed` | 47988 | 27993 | 23988 | 19.768 |
| 20000 | `pyzx_full_reduce` | `timeout` | - | - | - | 600.12 |
| 20000 | `tket_fullpeephole` | `timeout` | - | - | - | 600.129 |
| 20000 | `tket_paulisimp` | `error` | - | - | - | 1.357 |
| 20000 | `tket_guided_paulisimp` | `completed` | 67974 | 31992 | 23988 | 2.509 |
| 50000 | `semantic_ucc` | `completed` | 42 | 24 | 12 | 20.934 |
| 50000 | `phase_poly_reference` | `completed` | 42 | 24 | 12 | 0.45 |
| 50000 | `qiskit_opt3` | `completed` | 119988 | 69993 | 59988 | 120.937 |
| 50000 | `pyzx_full_reduce` | `timeout` | - | - | - | 600.138 |
| 50000 | `tket_fullpeephole` | `timeout` | - | - | - | 600.141 |
| 50000 | `tket_paulisimp` | `error` | - | - | - | 2.395 |
| 50000 | `tket_guided_paulisimp` | `completed` | 169974 | 79992 | 59988 | 5.461 |
| 100000 | `semantic_ucc` | `completed` | 42 | 24 | 12 | 28.613 |
| 100000 | `phase_poly_reference` | `completed` | 42 | 24 | 12 | 0.754 |
| 100000 | `qiskit_opt3` | `completed` | 239988 | 139993 | 119988 | 485.265 |
| 100000 | `pyzx_full_reduce` | `timeout` | - | - | - | 600.173 |
| 100000 | `tket_fullpeephole` | `timeout` | - | - | - | 600.174 |
| 100000 | `tket_paulisimp` | `error` | - | - | - | 4.0 |
| 100000 | `tket_guided_paulisimp` | `completed` | 339974 | 159992 | 119988 | 10.381 |

## No-Fourier Ablation Rows

| Size | Status | Gates | Depth | CX | Wall time s | Notes |
|---:|---|---:|---:|---:|---:|---|
| 4000 | `completed` | 9588 | 5593 | 4788 | 18.198 | ucc.compile with UCC_DISABLE_FOURIER_LAYER_IR=1 |
| 10000 | `completed` | 23988 | 13993 | 11988 | 94.195 | ucc.compile with UCC_DISABLE_FOURIER_LAYER_IR=1 |
| 20000 | `completed` | 47988 | 27993 | 23988 | 339.339 | ucc.compile with UCC_DISABLE_FOURIER_LAYER_IR=1 |
| 50000 | `timeout` | - | - | - | 600.139 | worker exceeded uniform timeout budget of 600 s |
| 100000 | `timeout` | - | - | - | 600.169 | worker exceeded uniform timeout budget of 600 s |

## Correctness Extension

| Method | Status | Equivalent up to global phase | Wall time s | Notes |
|---|---|---|---:|---|
| `semantic_ucc` | `completed` | `True` | 31.916 | ucc.compile with Fourier IR enabled; Operator.equiv=True |
| `phase_poly_reference` | `completed` | `True` | 4.036 | aggregated 10 active commuting phase terms before lowering; Operator.equiv=True |

## Non-Completed Or Error Rows

| File | Family | Size | r | Method | Status | Notes |
|---|---|---:|---:|---|---|---|
| `round3_main_external_baselines_results.json` | `main_external_baselines` | 4000 | 399 | `tket_fullpeephole` | `timeout` | worker exceeded uniform timeout budget of 600 s |
| `round3_main_external_baselines_results.json` | `main_external_baselines` | 4000 | 399 | `tket_paulisimp` | `error` | Predicate requirements are not satisfied: GateSetPredicate:{ SXdg PhasedX PhasedXX Measure SX PhaseGadget ZZMax Tdg T Ry Rx Z X TwinPhasedX PauliExpBox Rz Y S Sdg V Vdg SWAP H YYPhase CY XXPhase CX ZZPhase CZ } |
| `round3_main_external_baselines_results.json` | `main_external_baselines` | 10000 | 999 | `pyzx_full_reduce` | `timeout` | worker exceeded uniform timeout budget of 600 s |
| `round3_main_external_baselines_results.json` | `main_external_baselines` | 10000 | 999 | `tket_fullpeephole` | `timeout` | worker exceeded uniform timeout budget of 600 s |
| `round3_main_external_baselines_results.json` | `main_external_baselines` | 10000 | 999 | `tket_paulisimp` | `error` | Predicate requirements are not satisfied: GateSetPredicate:{ SXdg PhasedX PhasedXX Measure SX PhaseGadget ZZMax Tdg T Ry Rx Z X TwinPhasedX PauliExpBox Rz Y S Sdg V Vdg SWAP H YYPhase CY XXPhase CX ZZPhase CZ } |
| `round3_main_external_baselines_results.json` | `main_external_baselines` | 20000 | 1999 | `pyzx_full_reduce` | `timeout` | worker exceeded uniform timeout budget of 600 s |
| `round3_main_external_baselines_results.json` | `main_external_baselines` | 20000 | 1999 | `tket_fullpeephole` | `timeout` | worker exceeded uniform timeout budget of 600 s |
| `round3_main_external_baselines_results.json` | `main_external_baselines` | 20000 | 1999 | `tket_paulisimp` | `error` | Predicate requirements are not satisfied: GateSetPredicate:{ SXdg PhasedX PhasedXX Measure SX PhaseGadget ZZMax Tdg T Ry Rx Z X TwinPhasedX PauliExpBox Rz Y S Sdg V Vdg SWAP H YYPhase CY XXPhase CX ZZPhase CZ } |
| `round3_main_external_baselines_results.json` | `main_external_baselines` | 50000 | 4999 | `qiskit_commutative_inverse` | `timeout` | worker exceeded uniform timeout budget of 600 s |
| `round3_main_external_baselines_results.json` | `main_external_baselines` | 50000 | 4999 | `pyzx_full_reduce` | `timeout` | worker exceeded uniform timeout budget of 600 s |
| `round3_main_external_baselines_results.json` | `main_external_baselines` | 50000 | 4999 | `tket_fullpeephole` | `timeout` | worker exceeded uniform timeout budget of 600 s |
| `round3_main_external_baselines_results.json` | `main_external_baselines` | 50000 | 4999 | `tket_paulisimp` | `error` | Predicate requirements are not satisfied: GateSetPredicate:{ SXdg PhasedX PhasedXX Measure SX PhaseGadget ZZMax Tdg T Ry Rx Z X TwinPhasedX PauliExpBox Rz Y S Sdg V Vdg SWAP H YYPhase CY XXPhase CX ZZPhase CZ } |
| `round3_main_external_baselines_results.json` | `main_external_baselines` | 100000 | 9999 | `qiskit_commutative_inverse` | `timeout` | worker exceeded uniform timeout budget of 600 s |
| `round3_main_external_baselines_results.json` | `main_external_baselines` | 100000 | 9999 | `pyzx_configured` | `timeout` | worker exceeded uniform timeout budget of 600 s |
| `round3_main_external_baselines_results.json` | `main_external_baselines` | 100000 | 9999 | `pyzx_full_reduce` | `timeout` | worker exceeded uniform timeout budget of 600 s |
| `round3_main_external_baselines_results.json` | `main_external_baselines` | 100000 | 9999 | `tket_fullpeephole` | `timeout` | worker exceeded uniform timeout budget of 600 s |
| `round3_main_external_baselines_results.json` | `main_external_baselines` | 100000 | 9999 | `tket_paulisimp` | `error` | Predicate requirements are not satisfied: GateSetPredicate:{ SXdg PhasedX PhasedXX Measure SX PhaseGadget ZZMax Tdg T Ry Rx Z X TwinPhasedX PauliExpBox Rz Y S Sdg V Vdg SWAP H YYPhase CY XXPhase CX ZZPhase CZ } |
| `round3_fourier_ablation_completion_results.json` | `fourier_ablation_completion` | 50000 | 4999 | `no_fourier_ucc` | `timeout` | worker exceeded uniform timeout budget of 600 s |
| `round3_fourier_ablation_completion_results.json` | `fourier_ablation_completion` | 50000 | 4999 | `qiskit_commutative_inverse` | `timeout` | worker exceeded uniform timeout budget of 600 s |
| `round3_fourier_ablation_completion_results.json` | `fourier_ablation_completion` | 100000 | 9999 | `no_fourier_ucc` | `timeout` | worker exceeded uniform timeout budget of 600 s |
| `round3_fourier_ablation_completion_results.json` | `fourier_ablation_completion` | 100000 | 9999 | `qiskit_commutative_inverse` | `timeout` | worker exceeded uniform timeout budget of 600 s |
| `round3_resource_consequence_check_results.json` | `resource_consequence_check` | 50000 | 4999 | `no_fourier_ucc` | `timeout` | worker exceeded uniform timeout budget of 600 s |
| `round3_resource_consequence_check_results.json` | `resource_consequence_check` | 100000 | 9999 | `no_fourier_ucc` | `timeout` | worker exceeded uniform timeout budget of 600 s |

## Paper-Facing Takeaways

- Use the generated `round3_summary_for_paper_patch.md` as the canonical patch guidance for wording.
- The runner reports strict completed-pair `semantic_ucc` vs `qiskit_opt3` structural wins as `5/5`.
- Timeout cells are not structural wins; disclose the uniform `600` second per-method per-instance timeout.
- Report unfavorable rows directly: TKET FullPeephole timed out across the main table, TKET PauliSimp errored across the main table, and PyZX full_reduce timed out except at size 4000.
- The no-Fourier ablation completed through size 20000 and timed out at 50000 and 100000.

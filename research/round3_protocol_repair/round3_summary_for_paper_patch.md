# Round 3 Summary For Paper Patch

This file is the manuscript-change checklist for the full Round 3 protocol
repair. It is intentionally experiment/provenance guidance only. Do not edit
theorem statements, formal proof text, or the formal-core patch from this file.

## Rewrite The 42/42 Claim

Replace timeout-inclusive win language with a timeout-aware statement computed
from `round3_main_external_baselines_results.json`:

- strict structural wins are counted only among completed paired cells;
- a timeout cell is not a lexicographic structural win;
- cells where semantic UCC completes and qiskit opt3 times out should be
  reported separately as scalability evidence under the disclosed timeout.

The generated `.md` summary reports the completed-pair win fraction and the
separate timeout/scalability count.

## Timeout Budgets

Every caption-facing table summary must state the row-level timeout budget.
The default full-run budget is `600` seconds per method per instance. If the
repair run is executed with `--timeout-s 300`, state `300` seconds everywhere
and rely on the per-row `timeout_s` field.

## Method Names

Use `method_name_map.md` as the source of truth. In particular:

- `semantic_ucc`: semantic UCC (Fourier-layer IR enabled)
- `no_fourier_ucc`: artifact UCC (Fourier-layer IR disabled)
- `qiskit_opt3`: qiskit opt3
- `pyzx_configured`: PyZX configured bridge
- `pyzx_full_reduce`: PyZX full_reduce
- `tket_fullpeephole`: TKET FullPeephole
- `tket_paulisimp`: TKET PauliSimp
- `tket_guided_paulisimp`: TKET GuidedPauliSimp
- `phase_poly_reference`: phase-polynomial reference

Avoid old labels such as `baseline UCC`, `optimized UCC`, `Qiskit O3`, or
mixed-case qiskit names unless the prose explicitly maps them.

## Figure Legends

Use the canonical paper names above consistently in legends. Do not mix
`Optimized UCC` with `semantic UCC`, and do not mix `Qiskit O3` with
`qiskit opt3`.

## PyZX And TKET

Describe PyZX configured bridge and PyZX full_reduce as separate baselines.
Describe TKET FullPeephole, TKET PauliSimp, and TKET GuidedPauliSimp
separately. Disclose whether the run used `pytket.extensions.qiskit` or the
QASM fallback recorded in `baseline_call_sequences.md`.

If PyZX full_reduce or either TKET Pauli simplification recovers the bounded
form, report that directly. The framing should become: default configured
pipelines fail unless they instantiate or reconstruct the aggregation
capability; semantic-capable modes pay the information toll and can succeed.

## Phase-Polynomial Reference

Describe `phase_poly_reference` as a narrow semantic-capable reference that
aggregates explicit commuting-diagonal coefficients before lowering. Known
rotation-merging approaches, including Nam-style rotation aggregation when the
phase polynomial is available or reconstructed, belong on the semantic-capable
side of the classification rather than as a local flat-pipeline counterexample.

## No-Fourier Ablation

Update the ablation table from
`round3_fourier_ablation_completion_results.json`. For no-Fourier UCC,
completed rows must report completed output gate counts, depth, `cx`, and
rotation counts. Timeout rows should remain timeout rows with the disclosed
budget, and should not be used as structural win cells.


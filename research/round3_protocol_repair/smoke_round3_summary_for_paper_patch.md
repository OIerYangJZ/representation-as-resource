# Round 3 Summary For Paper Patch

Generated: `2026-07-06T03:15:50+00:00`
Mode: `smoke`
Uniform timeout budget used by these generated rows: `20` seconds per method per instance.

Do not edit theorem statements, formal proof text, or formal-core patch from this file. This is experiment/provenance patch guidance only.

## Rewrite the 42/42 claim

Replace timeout-inclusive win language with: strict structural wins among completed paired `semantic_ucc` vs `qiskit_opt3` cells are `1/1` in this run. Separately report qiskit timeout cells with completed semantic UCC as scalability evidence: `0` cells.

Timeout cells must not be counted as lexicographic wins. The lexicographic metric applies only when both compared rows have status `completed` and all structural metrics are present.

## Timeout budgets

Every caption-facing statement should say that comparable external-baseline cells used a uniform `20` second per-method per-instance timeout in this repair run. If the full run is rerun with `--timeout-s 300`, replace the number everywhere and rely on row-level `timeout_s` values.

## Method names

Use the JSON keys and paper names in `method_name_map.md`. Avoid old labels such as `baseline UCC`, `optimized UCC`, `Qiskit O3`, or mixed-case `qiskit opt3` variants unless they are explicitly mapped.

## Figure legends

Use `semantic UCC (Fourier-layer IR enabled)`, `artifact UCC (Fourier-layer IR disabled)`, `qiskit opt3`, `PyZX configured bridge`, `PyZX full_reduce`, `TKET FullPeephole`, `TKET PauliSimp`, and `TKET GuidedPauliSimp` consistently.

## PyZX and TKET descriptions

Describe PyZX configured bridge and PyZX full_reduce as separate baselines. Describe TKET FullPeephole, PauliSimp, and GuidedPauliSimp separately, and disclose whether the run used the qiskit extension bridge or the qasm fallback recorded in `baseline_call_sequences.md`.

## Phase-polynomial reference and Nam-style merging

Describe `phase_poly_reference` as a narrow semantic-capable reference that aggregates explicit commuting-diagonal coefficients before lowering. Known rotation-merging approaches, including Nam-style rotation aggregation when the phase polynomial is available or reconstructed, belong on the semantic-capable side of the classification rather than as a local flat-pipeline counterexample.

## No-Fourier ablation

Report no-Fourier UCC completed output gate counts whenever the row completes. In this run, completed no-Fourier rows: `1`. Timeout rows should remain timeout rows, with the disclosed budget, and should not be used as structural win cells.

## Unfavorable results

If PyZX full_reduce, TKET PauliSimp, or TKET GuidedPauliSimp recovers the bounded form, report that directly. The framing should become: default configured pipelines fail unless they instantiate or reconstruct the aggregation capability; semantic-capable modes pay the information toll and can succeed.

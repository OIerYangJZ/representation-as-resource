# E7 Preregistration — TKET internal-state scaling on the dispersed family

Date: 2026-08-05.  **This file is committed before any E7 experiment run; the
git commit order is the timestamp.**  Execution-plan task E7
(`PaperDraft/Comments on new proposal-Opus-5.md`, Section 9.3).

## Hypothesis under test

From `cor:physical-lower-bounds` / `thm:w1-unified-frontier`: any compiler
achieving family-relative compact output on the $r$-round dispersed
(masked modular share) family must carry $\Omega(m\log K)$ bits of internal
state across the inter-round boundary.  TKET PauliSimp achieves compact
output on this family (external campaign, W5).  **Therefore TKET must pay
internal state growing at least linearly in $m$**, while the authors'
semantic path on semantic input pays $O(\log m)$ crossing state.  This is a
prediction about a third-party compiler the authors do not control.

## Frozen design

- **Family**: `masked_share_update` representation from
  `benchmarks/representation_generators.py` (the genuinely hiding stream:
  no share equals the final coefficient modulo $Q$); parameters `r=4`,
  `K=8`, `density=1.0` (active support of size $m-1$), `target_seed =
  20260805 + m`; representation seeds $\{1,2,3\}$ per $m$.
- **Scan**: $m \in \{8, 16, 32, 64, 128\}$ (pinned by the execution plan).
- **TKET pipeline**: byte-identical 6-pass sequence used by the external
  campaign (`run_matched_representation_benchmark.py`):
  DecomposeBoxes → AutoRebase{CX,Rz,H} → RemoveRedundancies → PauliSimp →
  RemoveRedundancies → AutoRebase{CX,Rz,H}; pytket 2.16.0; each cell in a
  fresh subprocess.
- **Measurements per cell**:
  - M1 `rss_build_bytes`: `ru_maxrss` after imports and circuit build,
    before the pass sequence;
  - M2 `rss_peak_bytes`: `ru_maxrss` after the pass sequence (process
    lifetime peak); `rss_delta_bytes` = M2 − M1;
  - M3 input QASM bytes; M4 post-pipeline circuit JSON bytes
    (`Circuit.to_dict()`) and QASM bytes;
  - M5 output non-Clifford `rz` rotation count (compactness check against
    the dispersed input count $r\cdot(m-1)$);
  - M6 wall time.
- **Control arm**: `run_semantic(m)` from
  `PaperDraft/scripts/trace_cut_budget.py` at the same $m$ values; metric
  `B_cross_bytes` (peak measured crossing state of the five-field
  serializer on semantic input).

## Preregistered predictions

- **P1 (primary, TKET state linear)**: mean `rss_delta_bytes` is
  monotonically nondecreasing in $m$, and the log–log OLS slope of mean
  delta vs $m$ over the five $m$ values lies in $[0.7, 1.5]$.
  *Fallback (noise floor)*: if mean delta at any $m \le 16$ is below 1 MiB,
  P1 is evaluated on $m \in \{32, 64, 128\}$.
- **P2 (premise, compact output)**: in every cell the output non-Clifford
  rotation count is $\le (m-1) + O(1)$ (aggregation across rounds
  happened), i.e. it is NOT $\approx r(m-1)$.
- **P3 (control, semantic path logarithmic)**: `B_cross_bytes(128) /
  B_cross_bytes(8)` $\le 4$ across the 16-fold growth in $m$ (log-like),
  exhibiting the predicted contrast with the linear TKET arm.

## Decision rule (frozen)

- P1 ∧ P2 ∧ P3 → the abstract sentence ("an independent third-party
  pipeline … is shown to pay the predicted linear state") **stands**;
  GATED CLAIM 2 is released; TKET is framed in the text as an
  author-independent confirmation of the bound.
- ¬P2 → TKET did not achieve compact output on this family; the abstract
  sentence **reverts**; reported as a scope finding (theorems impose no
  cost without compact output).
- P2 ∧ ¬P1 → the prediction is falsified; the abstract sentence
  **reverts**; the negative result is reported as-is.

## Outputs

Frozen results at `PaperDraft/generated/e7_tket_state_scaling.json` (full
per-cell rows + summary + verdict), produced by
`PaperDraft/scripts/run_tket_state_scaling.py`.  Analysis code and decision
evaluation are in the same script; no post-hoc metric substitution.

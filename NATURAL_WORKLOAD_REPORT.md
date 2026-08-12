# W8 natural-workload and factorial-ablation report

## Verdict

The frozen W8 campaign is complete and auditable.  It contains 21,060 measured
compiler cells: 20,736 cells from the full (2^6) authors-method factorial
design and 324 matched cells from the strongest available external semantic
baseline (TKET `PauliSimp`).  Every cell has status `completed_valid`, every
completed output passed the independent dense projective-unitary certificate,
and every cell produced a fixed-total-error QRE record.

This is a local reference campaign, not a claim about every quantum compiler.
The instances use six qubits so that the dense certificate is independent and
exactly repeatable on every completed output.  The extrapolation question is
addressed by the three size levels and by reporting all cells rather than by
relaxing correctness checking at larger widths.

## Frozen design

The campaign crosses nine workload families, scales 1/2/4, three seeds,
densities 0.5/1.0, and all-to-all/line hardware topologies.  Seven families are
natural positive workloads: QAOA/Ising, diagonal-Hamiltonian simulation,
commuting-block Trotterization, QPE controlled powers, QFT arithmetic,
controlled-power ladders, and phase-polynomial blocks.  The two negative
controls are random Clifford+Rz and routing-dominated circuits.

The authors' reference compiler is evaluated at every cell of the independent
toggle matrix

`semantic_lift × aggregation × selector × cache_reuse × preset_recognizer × projected_block_selection`.

The external baseline uses `DecomposeBoxes`, `RemoveRedundancies`,
`PauliSimp`, a common `{CX,Rz,H}` rebase, and final redundancy removal.  The
same target unitary, topology, seed, dense certificate, and total QRE error
budget are used in matched comparisons.  The QRE slice fixes
`epsilon_total=1e-6`, the conservative surface-code profile, and 16 factories;
this campaign calls the W7 estimator rather than substituting T count for QRE.

## Results

Five natural families satisfy the predeclared strict criterion at every
primary cell (all-to-all, density 1.0, every scale and seed):

- `controlled_power_ladder`
- `diagonal_hamiltonian`
- `qaoa_ising`
- `qpe_controlled_powers`
- `trotter_commuting_blocks`

The criterion requires both completed-valid outputs, no worse authors gate and
CX counts at every primary cell, and strictly lower measured compiler runtime
at every primary scale/seed.  `qft_arithmetic` and
`phase_polynomial_blocks` do not satisfy all parts of this criterion and are
retained in the data and figure.  In particular, the result does not support a
claim that semantic-first wins on every structured circuit.

Across the seven natural families, the largest gate-count main effect is the
preset recognizer: mean off-minus-on reduction 364.907 gates with bootstrap
95% interval [349.754, 380.482].  Aggregation reduces 80.427 gates on average
[74.570, 86.362], and semantic lift reduces 72.224 [66.301, 78.141].  Selector,
cache/reuse, and projected block selection have zero isolated gate effect in
this controlled implementation; their operational effects and all pairwise
interactions remain in the frozen tables.  Thus the principal measured
contribution is the explicit preset recognizer, not an undifferentiated claim
about the full stack.

For both negative controls, the all-on versus all-off paired differences are
zero for gates, depth, CX, logical T states, and spacetime volume, with bootstrap
95% intervals [0,0].  No negative-control systematic regression is observed.
This means “no regression in this tested grid,” not a universal safety proof.

## Measurement and provenance

Each row records the full experiment key, workload and representation
identifiers, factor settings, backend hash, artifact commit, configuration hash,
input/output gate metrics, compiler time, peak RSS, serialized IR bytes,
description bits, certificate distance/status, and the W7 QRE fields.  Raw
event outputs are retained under `data/runs/w8-natural-20260803-local/`; the
canonical combined table is `data/frozen/natural_workloads.parquet` (SHA-256
`25cf0f8c107b2e17ad2c7a402de6d9ef72c5d9ac0398f79b19fcdb910aa7b563`).
The analysis uses 4,000 paired bootstrap replicates with seed 20260830.

The recorded source hashes, frozen-artifact hashes, host, elapsed time, row
counts, and status counts are in
`data/frozen/natural_workload_analysis.json`.  The two PDF figures were rendered
from the frozen table and visually inspected after the formal run.

## Anomalies and limitations

- The first line-topology preflight exposed a correctness failure in a
  layout-tracking router: the emitted circuit implemented the right operation
  in a permuted final layout.  That implementation was rejected, replaced by
  an explicit adjacent-CX SWAP construction that restores the identity layout,
  and the complete campaign was rerun.  No rejected preflight row was deleted
  from a completed campaign because it preceded the frozen campaign.
- The external comparison is the strongest semantic-capable tool available in
  this frozen environment, not evidence against unavailable proprietary tools.
- Wall-time differences are local-machine observations and are not used as a
  stand-alone quality claim.
- Six-qubit dense certification bounds circuit width; the size scan increases
  repeated structure, density, and routed interaction count.
- The zero main effect of three toggles is a substantive negative result of the
  reference implementation and is not hidden.

## Reproduction

From the project root with the frozen `.venv`:

```bash
.venv/bin/python scripts/run_natural_workloads.py
.venv/bin/python scripts/run_factorial_ablation.py
.venv/bin/python -m pytest tests/test_natural_workloads.py -q
```

The first command generates the matched base records and raw outputs; the
second executes all 64 authors configurations per instance, adds the matched
external cells, performs the bootstrap analysis, and writes both figures.

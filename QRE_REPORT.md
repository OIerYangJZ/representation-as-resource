# Fixed-total-error fault-tolerant QRE campaign

## Executive result

W7 replaces the historical fixed-per-rotation T proxy with an executable,
fixed-total-error pipeline:

1. compile one four-qubit target through a measured compiler pipeline;
2. require an independent correctness certificate;
3. allocate one common total error budget;
4. synthesize every unique arbitrary angle with the frozen deterministic staq
   `grid_synth` executable and its built-in checker;
5. schedule the resulting logical T demand in two disclosed surface-code
   scenarios and four factory-parallelism configurations.

The frozen matrix contains **288/288 completed_valid rows**, no duplicate cells,
no missing certificate, and no row whose conservative additive error bound
exceeds its requested `epsilon_total`.  The maximum observed fraction of the
requested total bound is `0.9808348`.

The main comparison is stable across all 96 matched combinations of target,
total error, allocation policy, QEC profile, and factory count:

- materialize-first uses between **385.2x and 1753.4x** the logical T states of
  semantic-first;
- materialize-first uses between **537.8x and 5572.7x** its spacetime volume;
- the external TKET semantic-capable pipeline is never treated as a local
  baseline: it reconstructs a compact phase form before synthesis and, on this
  witness, uses `0.443x`-`0.536x` the semantic-first T states and
  `0.212x`-`0.596x` its spacetime volume.

The last result is important: the campaign does not claim that the authors'
pipeline is universally best.  It supports the representation-ordering claim
while correctly crediting a strong external semantic-capable tool.

## Frozen factorial design

| dimension | values |
|---|---|
| requested witness size | 4,000; 20,000 gates before compilation |
| pipeline | semantic-first UCC; materialize-first Qiskit; external TKET `PauliSimp` |
| `epsilon_total` | `1e-3`, `1e-6`, `1e-9` |
| synthesis allocation | equal decimal; measured-T-cost greedy |
| physical/QEC scenario | `surface_code_conservative`; `surface_code_improved` |
| factory parallelism | 1, 4, 16, 32 factories |

This is exactly `2 x 3 x 3 x 2 x 2 x 4 = 288` QRE rows.  The compiler,
representation bridge, target basis, seed, correctness rule, error split, and
QRE/factory configuration are frozen in `qre/configs/` and the freeze manifest.

## Total-error rule

Every pipeline receives the same additive budget

```text
epsilon_total = epsilon_algorithmic + epsilon_synthesis + epsilon_logical
fractions      = 0.10              + 0.45              + 0.45
```

The algorithmic share is a conservative reservation for the certified compiler
stage.  The synthesis share is allocated over the measured number of output
rotations, not fixed independently per rotation.  The logical share bounds the
union of data-patch failures, active factory-patch failures, and the disclosed
15-to-1-style distillation-output term.

For equal allocation with `N_rot` rotations, the runner uses

```text
p = ceil(log10(N_rot / epsilon_synthesis))
epsilon_i = 10^(-p)
```

and checks `N_rot * epsilon_i <= epsilon_synthesis`.  The measured-cost greedy
variant starts at this safe allocation, spends only the unused decimal slack,
and accepts a relaxation only if measured staq T cost decreases while the
additive budget remains satisfied.  It is a reproducible upper construction,
not a claim of globally optimal allocation.  It reduced T states in all 144
paired cells, by `0.71%` to `11.59%` (median `3.01%`).

The old `t_proxy_1e_10` fields are never read.  The freeze manifest records
`old_fixed_per_rotation_proxy_consumed: false`.

## Measured synthesis and representative QRE point

The runner executed and checked **670 unique angle/precision pairs**.  Each
approximate branch was required to report `Check flag = 1`, a T count, and an
error no larger than its decimal allocation.  Exact multiples of pi/4 use
staq's exact branch: the runner requires `Check flag = 1`, counts the emitted T
tokens, and assigns exact synthesis error zero.

The following is the predeclared main slice: 20k target,
`epsilon_total=1e-6`, equal allocation, conservative physical-error profile,
and 16 factories.

| pipeline | rotations | logical T | distance | physical qubits | factory qubits | cycles | runtime (s) | qubit-s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| external TKET semantic | 29 | 798 | 23 | 258,152 | 253,920 | 13,317 | 0.013317 | 3,437.81 |
| materialize-first Qiskit | 23,992 | 2,679,110 | 31 | 468,968 | 461,280 | 57,966,528 | 57.966528 | 27,184,446.70 |
| semantic-first UCC | 22 | 1,800 | 25 | 305,000 | 300,000 | 31,675 | 0.031675 | 9,660.88 |

The figure `figures/qre_pareto.pdf` shows the physical-qubit/runtime frontier;
every factory count is retained.  Sixteen factories minimizes spacetime volume
for all three pipelines in the displayed 20k/`1e-6` slice, while 32 factories
reduces runtime further at increased qubit and spacetime cost.  Thus no single
factory count is silently presented as universally optimal.

## QEC scenarios

Both profiles use an explicitly versioned phenomenological surface-code model,
with the least odd distance satisfying the logical union bound.

| parameter | conservative | improved |
|---|---:|---:|
| physical error | `1e-3` | `1e-4` |
| threshold | `1e-2` | `1e-2` |
| logical error per patch-cycle | `0.1*(p/p_th)^((d+1)/2)` | same form |
| data patch qubits | `2 d^2` | `2 d^2` |
| factory qubits | `30 d^2` | `24 d^2` |
| factory period | `11 d` cycles | `9 d` cycles |
| code cycle time | `1 us` | `0.5 us` |

These are executable sensitivity scenarios, not vendor forecasts.  Routing,
feed-forward congestion, correlated faults, heterogeneous code distances, and
a hardware-specific factory layout remain out of domain.  Absolute physical
numbers should not be transferred to a machine without replacing these
profiles.

## Correctness and conversion status

All six compiled target/pipeline outputs pass an independent dense unitary
certificate up to global phase.  The exact W6 symbolic checker is additionally
recorded, but its intentionally incomplete domain is not hidden:

- 144 QRE rows inherit an exact-symbolic `completed_valid` certificate;
- 96 rows inherit a symbolic `predicate_error` from TKET outputs whose extracted
  rotations are not pairwise commuting in that gate order;
- 48 rows inherit a symbolic `completed_invalid` from the 20k materialized
  output's different canonical record.

Those 144 non-symbolic accepts use a separate content-addressed
`dense_unitary_projective_n_le_6_v1` certificate.  They are not relabelled as
symbolic successes.  This is permitted because every campaign target has
`n=4`; outputs wider than six qubits are outside this dense-certificate path and
would be `unsupported` rather than inserted into numerical means.

The external bridge is recorded before and after TKET.  At 20k it receives a
67,974-gate CX-Rz-H materialization and returns a 62-gate, 29-rotation circuit
before synthesis.  It is therefore classified as `external-semantic-capable`,
not as local/standard.

## Sensitivity and reversals

No materialize-first versus semantic-capable reversal occurs in the measured
grid.  Materialize-first remains worse in logical T states, cycles, physical
qubits, and spacetime volume under both physical error rates, all four factory
counts, all three total errors, both sizes, and both synthesis allocations.

The relative ordering *within* the semantic-capable side is not used as a
general claim.  TKET is better than the authors' semantic-first path throughout
this particular witness grid because it returns fewer/harder-angle-dependent
rotation tasks.  That advantage may disappear or reverse on non-phase-polynomial
workloads, wider circuits where dense certification is unavailable, or
architecture-specific routing/factory models.  W7 establishes robustness of
the semantic-before-synthesis conclusion on the declared witness, not universal
dominance of one semantic tool.

## Anomalies retained

Two preflight failures are preserved under the run directory:

1. The first run produced 48 `synthesis_error` rows because the parser expected
   approximate-branch fields from staq's exact pi/4 branch.  The exact branch
   was explicitly recognized and the entire campaign rerun.
2. The second run exposed the symbolic checker's incomplete domain and produced
   only 144 of the required 288 QRE rows.  A separate dense n<=6 certificate was
   added; symbolic outcomes remain visible, and the entire matrix was rerun.

No point from either preflight was silently deleted.  The final frozen artifact
contains the complete matrix; the anomaly JSON files document why the earlier
attempts were not accepted as final evidence.

## Reproduction

From the project root, using the frozen local environment:

```bash
.venv/bin/python scripts/allocate_synthesis_error.py \
  --epsilon-total 1e-6 --rotation-count 1800
.venv/bin/python scripts/run_qre_campaign.py \
  --config qre/configs/campaign.yaml
.venv/bin/python scripts/analyze_qre_campaign.py
.venv/bin/python -m pytest -q tests/test_qre_campaign.py
```

Primary frozen artifacts:

- `data/frozen/qre_results.parquet` and `qre_results.csv`;
- `data/frozen/qre_freeze_manifest.json`;
- `data/frozen/qre_analysis.json` and `qre_summary.csv`;
- `data/runs/w7-fixed-total-error-20260803-local/` raw compilation,
  angle-synthesis, QRE, manifest, and anomaly records;
- `figures/qre_pareto.pdf` and `figures/qre_sensitivity.pdf`.

Frozen package versions include Qiskit 2.4.0, UCC 0.4.12, TKET 2.16.0,
NumPy 2.3.3, pandas 2.3.3, and PyArrow 25.0.0.  The synthesizer records staq
upstream commit `a2acd39e60ed0e5f1978fa530df7e1e0c7cedf7a` and the deterministic
seed patch in the manifest.

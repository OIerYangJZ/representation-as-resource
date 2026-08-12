# Repeated-Run Stability Summary

This summary reflects the refreshed 5-run stability study written to:

- `stability_results.json`
- `stability_results.md`

The repeated-run study covers:

- the three official real instances
- the canonical hardware-aware fixed-seed cases with `seed_transpiler = 12345`

## Main conclusions

### 1. Real-instance results are fully deterministic

For:

- `phase_estimation_real`
- `grover_real`
- `qaoa_real`

both `qiskit opt3` and `optimized_ucc` return identical output metrics across
all five runs:

- total gates: deterministic
- depth: deterministic
- `cx` count: deterministic

The runtime variance is small. In the refreshed 5-run table:

- `phase_estimation_real`
  - `qiskit opt3`: `1.279 ± 0.037 s`
  - `optimized_ucc`: `1.290 ± 0.074 s`
- `grover_real`
  - `qiskit opt3`: `0.541 ± 0.016 s`
  - `optimized_ucc`: `0.524 ± 0.019 s`
- `qaoa_real`
  - `qiskit opt3`: `0.289 ± 0.013 s`
  - `optimized_ucc`: `0.289 ± 0.024 s`

So the official real-instance story is stable both structurally and
operationally.

### 2. Canonical hardware-aware outputs are deterministic for a fixed seed

For the canonical hardware-aware table with `seed_transpiler = 12345`:

- `hw_mqt_qpeexact_20`
  - `qiskit opt3`: `1572 / depth 407 / cx 812`
  - `optimized_ucc`: `1572 / depth 407 / cx 812`
- `hw_mqt_qaoa_20`
  - `qiskit opt3`: `2091 / depth 532 / cx 1530`
  - `optimized_ucc`: `2050 / depth 487 / cx 1458`

These outputs are deterministic across repeated runs for that fixed seed.

### 3. The hardware-aware QAOA win is reproducible

For `hw_mqt_qaoa_20`, the refreshed repeated-run study preserves the routed
quality win on every run:

- `qiskit opt3`: `2091 / depth 532 / cx 1530`
- `optimized_ucc`: `2050 / depth 487 / cx 1458`

The corresponding runtime statistics are:

- `qiskit opt3`: `0.057 ± 0.003 s`
- `optimized_ucc`: `0.181 ± 0.028 s`

So this result is not a one-off runtime or routing accident inside the current
fixed-seed evaluation protocol.

### 4. Hardware-aware QPE is now a fixed-seed parity case

For `hw_mqt_qpeexact_20`, the refreshed repeated-run study shows exact parity
with `qiskit opt3` on the current canonical seed:

- `qiskit opt3`: `1572 / depth 407 / cx 812`
- `optimized_ucc`: `1572 / depth 407 / cx 812`

The runtime statistics are:

- `qiskit opt3`: `0.043 ± 0.008 s`
- `optimized_ucc`: `0.227 ± 0.010 s`

This should now be described as a reproducible parity case rather than as a
clean routed-quality win.

## Practical takeaway

The refreshed stability study supports three clean claims:

1. the official real-instance results are reproducible
2. the canonical hardware-aware outputs are reproducible for a fixed seed
3. the `hw_mqt_qaoa_20` backend-aware win is stable under repeated runs

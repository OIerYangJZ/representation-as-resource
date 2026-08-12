# Mirrored / Conjugation Positive Cases Summary

This focused set is intended to support the second theory line
(`Conj(U,M)` / `Mirror(D,S)`) with clean head-to-head comparisons
against `baseline UCC` and `qiskit opt3`.

## `grover_real`

- baseline UCC: `287,047` gates, depth `152,298`, `cx=32,544`
- optimized UCC: `79,029` gates, depth `54,163`, `cx=32,544`
- qiskit opt3: `79,029` gates, depth `54,163`, `cx=32,544`
- conclusion: optimized UCC reaches exact `qiskit opt3` parity while clearly improving on baseline UCC.

## `mqt_grover_8`

- baseline UCC: `18,992` gates, depth `10,990`, `cx=2,192`
- optimized UCC: `5,170` gates, depth `3,788`, `cx=2,192`
- qiskit opt3: `5,170` gates, depth `3,788`, `cx=2,192`
- conclusion: optimized UCC reaches exact `qiskit opt3` parity while clearly improving on baseline UCC.

## `mqt_grover_12`

- baseline UCC: `259,797` gates, depth `150,911`, `cx=29,190`
- optimized UCC: `71,706` gates, depth `55,801`, `cx=29,190`
- qiskit opt3: `71,706` gates, depth `55,801`, `cx=29,190`
- conclusion: optimized UCC reaches exact `qiskit opt3` parity while clearly improving on baseline UCC.

## `mqt_grover_16`

- baseline UCC: `2,112,285` gates, depth `1,255,608`, `cx=234,300`
- optimized UCC: `581,098` gates, depth `476,428`, `cx=234,300`
- qiskit opt3: `581,098` gates, depth `476,428`, `cx=234,300`
- conclusion: optimized UCC reaches exact `qiskit opt3` parity while clearly improving on baseline UCC.

## `grover_mirrored_100k`

- baseline UCC: `4,122,006` gates, depth `2,166,021`, `cx=468,000`
- optimized UCC: `1,158,011` gates, depth `762,010`, `cx=468,000`
- qiskit opt3: `1,158,011` gates, depth `762,010`, `cx=468,000`
- conclusion: optimized UCC reaches exact `qiskit opt3` parity while clearly improving on baseline UCC.

## Interpretation

- `grover_real` shows that the official Grover-family real instance is already a clean positive parity case.
- `mqt_grover_8/12/16` test the same Grover-style family across increasing MQT scales rather than relying on a single benchmark size.
- `grover_mirrored_100k` extends the same story to a large repeated mirrored shell benchmark under the fixed-basis protocol.
- Together, these cases make the mirrored/conjugation line less dependent on the routed timeout-recovery-only interpretation of `hw_mqt_grover_20`.

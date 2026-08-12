# Phase-Ladder External Scaling Summary

The phase-ladder `qft_inverse` family gives a systematic runtime/scalability win over `qiskit opt3` under the fixed-basis protocol while preserving no-worse structural output quality.

Target basis: `['cx', 'rx', 'ry', 'rz', 'h']`.
Family: `qft_inverse`.
Tested target sizes: `4,000, 10,000, 20,000, 50,000, 100,000`.

Dominance checks against `qiskit opt3`:
Strict structural-quality wins: `2/5`.
No-worse structural-quality points: `5/5`.
Runtime/scalability wins with no-worse quality: `5/5`.
Strict quality winning points: `qft_inverse_50000, qft_inverse_100000`.
Runtime/scalability winning points: `qft_inverse_4000, qft_inverse_10000, qft_inverse_20000, qft_inverse_50000, qft_inverse_100000`.

Additional control: optimized UCC also matches the zero-gate output of `qiskit_commutative_inverse` at every tested size and is faster at every tested size.

A timeout for `qiskit opt3` counts as a win only if optimized UCC finishes.
Structural quality uses `(total_gates, depth, cx_count)`; runtime/scalability wins require no-worse structural quality.

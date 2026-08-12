# Non-Inverse Phase-Ladder / Fourier-Layer Scaling Summary

Target basis: `['cx', 'rx', 'ry', 'rz', 'h']`.
Families: `qft_forward_repeat, qpe_style, fourier_phase_sandwich, algorithmic_qft, algorithmic_aqft`.

Dominance checks compare optimized UCC against `qiskit opt3` using `(total_gates, depth, cx_count)`; qiskit timeout counts as a scalability win only if optimized UCC finishes.

## qft_forward_repeat

Conclusion: quality no-worse across all sizes, but runtime win is partial.
Strict structural-quality wins: `0/5`.
No-worse quality points: `5/5`.
Runtime/scalability wins: `3/5`.
Non-strict-quality-winning points: `4000, 10000, 20000, 50000, 100000`.
Non-runtime/scalability-winning points: `50000, 100000`.
Runtime/scalability winning points: `4000, 10000, 20000`.

## qpe_style

Conclusion: mixed; not a full systematic external-baseline win.
Strict structural-quality wins: `1/5`.
No-worse quality points: `1/5`.
Runtime/scalability wins: `1/5`.
Non-strict-quality-winning points: `4000, 10000, 20000, 50000`.
Quality-worse points: `4000, 10000, 20000, 50000`.
Non-runtime/scalability-winning points: `4000, 10000, 20000, 50000`.
Runtime/scalability winning points: `100000`.

## fourier_phase_sandwich

Conclusion: systematic strict structural-quality win over `qiskit opt3`.
Strict structural-quality wins: `5/5`.
No-worse quality points: `5/5`.
Runtime/scalability wins: `2/5`.
Non-runtime/scalability-winning points: `4000, 10000, 20000`.
Runtime/scalability winning points: `50000, 100000`.

## algorithmic_qft

Conclusion: quality no-worse across all sizes, but runtime win is partial.
Strict structural-quality wins: `0/5`.
No-worse quality points: `5/5`.
Runtime/scalability wins: `3/5`.
Non-strict-quality-winning points: `4000, 10000, 20000, 50000, 100000`.
Non-runtime/scalability-winning points: `50000, 100000`.
Runtime/scalability winning points: `4000, 10000, 20000`.

## algorithmic_aqft

Conclusion: quality no-worse across all sizes, but runtime win is partial.
Strict structural-quality wins: `0/5`.
No-worse quality points: `5/5`.
Runtime/scalability wins: `2/5`.
Non-strict-quality-winning points: `4000, 10000, 20000, 50000, 100000`.
Non-runtime/scalability-winning points: `20000, 50000, 100000`.
Runtime/scalability winning points: `4000, 10000`.

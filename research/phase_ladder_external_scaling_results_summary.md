# Phase-Ladder External Scaling Summary

The phase-ladder `qpe_style` family does not give a full systematic external-baseline win under the fixed-basis protocol.

Target basis: `['cx', 'rx', 'ry', 'rz', 'h']`.
Family: `qpe_style`.
Tested target sizes: `4,000, 10,000, 20,000, 50,000, 100,000`.

Dominance checks against `qiskit opt3`:
Strict structural-quality wins: `1/5`.
No-worse structural-quality points: `4/5`.
Runtime/scalability wins with no-worse quality: `1/5`.
Strict quality winning points: `qpe_style_100000`.
Quality-worse points: `qpe_style_50000`.
Runtime/scalability winning points: `qpe_style_100000`.
Non-runtime/scalability-winning points: `qpe_style_4000, qpe_style_10000, qpe_style_20000, qpe_style_50000`.

A timeout for `qiskit opt3` counts as a win only if optimized UCC finishes.
Structural quality uses `(total_gates, depth, cx_count)`; runtime/scalability wins require no-worse structural quality.

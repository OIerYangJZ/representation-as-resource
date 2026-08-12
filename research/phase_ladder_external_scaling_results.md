# Phase-Ladder External Scaling

Target basis: `['cx', 'rx', 'ry', 'rz', 'h']`

| Target Gates | Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---:|---|---|---:|---:|---:|---:|
| 4,000 | qiskit_opt3 | ok | 8,486 | 5,602 | 2,402 | 0.468 s |
| 4,000 | qiskit_commutative_inverse | ok | 15,840 | 11,841 | 6,240 | 0.084 s |
| 4,000 | optimized_ucc | ok | 8,486 | 5,602 | 2,402 | 4.257 s |
| 10,000 | qiskit_opt3 | ok | 21,206 | 14,002 | 6,002 | 2.543 s |
| 10,000 | qiskit_commutative_inverse | ok | 39,600 | 29,601 | 15,600 | 0.195 s |
| 10,000 | optimized_ucc | ok | 21,206 | 14,002 | 6,002 | 12.316 s |
| 20,000 | qiskit_opt3 | ok | 42,406 | 28,002 | 12,002 | 9.482 s |
| 20,000 | qiskit_commutative_inverse | ok | 79,200 | 59,201 | 31,200 | 0.368 s |
| 20,000 | optimized_ucc | ok | 42,406 | 28,002 | 12,002 | 29.024 s |
| 50,000 | qiskit_opt3 | ok | 106,006 | 70,002 | 30,002 | 58.656 s |
| 50,000 | qiskit_commutative_inverse | ok | 198,000 | 148,001 | 78,000 | 0.978 s |
| 50,000 | optimized_ucc | ok | 107,200 | 70,201 | 30,400 | 49.114 s |
| 100,000 | qiskit_opt3 | timeout | - | - | - | > 90 s |
| 100,000 | qiskit_commutative_inverse | ok | 396,000 | 296,001 | 156,000 | 1.956 s |
| 100,000 | optimized_ucc | ok | 214,400 | 140,401 | 60,800 | 5.634 s |

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

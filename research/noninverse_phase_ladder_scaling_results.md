# Non-Inverse Phase-Ladder / Fourier-Layer Scaling

Target basis: `['cx', 'rx', 'ry', 'rz', 'h']`

## qft_forward_repeat

| Requested Gates | Actual Input Gates | Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---:|---:|---|---|---:|---:|---:|---:|
| 4,000 | 4000 | qiskit_opt3 | ok | 13,900 | 5,000 | 6,800 | 0.426 s |
| 4,000 | 4000 | qiskit_commutative_inverse | ok | 16,000 | 5,600 | 6,800 | 0.451 s |
| 4,000 | 4000 | tket_full_peephole | ok | 32,883 | 11,423 | 5,303 | 35.231 s |
| 4,000 | 4000 | pyzx_opt | ok | 16,000 | 5,600 | 6,800 | 2.672 s |
| 4,000 | 4000 | baseline_ucc | ok | 48,304 | 12,701 | 6,800 | 0.475 s |
| 4,000 | 4000 | optimized_ucc | ok | 13,900 | 5,000 | 6,800 | 0.316 s |
| 10,000 | 10000 | qiskit_opt3 | ok | 34,750 | 12,500 | 17,000 | 0.429 s |
| 10,000 | 10000 | qiskit_commutative_inverse | ok | 40,000 | 14,000 | 17,000 | 0.453 s |
| 10,000 | 10000 | tket_full_peephole | timeout | - | - | - | > 45 s |
| 10,000 | 10000 | pyzx_opt | ok | 40,000 | 14,000 | 17,000 | 11.641 s |
| 10,000 | 10000 | baseline_ucc | ok | 120,754 | 31,751 | 17,000 | 0.826 s |
| 10,000 | 10000 | optimized_ucc | ok | 34,750 | 12,500 | 17,000 | 0.267 s |
| 20,000 | 20000 | qiskit_opt3 | ok | 69,500 | 25,000 | 34,000 | 0.544 s |
| 20,000 | 20000 | qiskit_commutative_inverse | ok | 80,000 | 28,000 | 34,000 | 0.638 s |
| 20,000 | 20000 | tket_full_peephole | timeout | - | - | - | > 45 s |
| 20,000 | 20000 | pyzx_opt | ok | 80,000 | 28,000 | 34,000 | 41.68 s |
| 20,000 | 20000 | baseline_ucc | ok | 241,504 | 63,501 | 34,000 | 1.478 s |
| 20,000 | 20000 | optimized_ucc | ok | 69,500 | 25,000 | 34,000 | 0.455 s |
| 50,000 | 50000 | qiskit_opt3 | ok | 173,750 | 62,500 | 85,000 | 1.028 s |
| 50,000 | 50000 | qiskit_commutative_inverse | ok | 200,000 | 70,000 | 85,000 | 1.232 s |
| 50,000 | 50000 | tket_full_peephole | timeout | - | - | - | > 45 s |
| 50,000 | 50000 | pyzx_opt | timeout | - | - | - | > 45 s |
| 50,000 | 50000 | baseline_ucc | ok | 603,754 | 158,751 | 85,000 | 2.965 s |
| 50,000 | 50000 | optimized_ucc | ok | 173,750 | 62,500 | 85,000 | 2.586 s |
| 100,000 | 100000 | qiskit_opt3 | ok | 347,500 | 125,000 | 170,000 | 1.655 s |
| 100,000 | 100000 | qiskit_commutative_inverse | ok | 400,000 | 140,000 | 170,000 | 1.96 s |
| 100,000 | 100000 | tket_full_peephole | timeout | - | - | - | > 45 s |
| 100,000 | 100000 | pyzx_opt | timeout | - | - | - | > 45 s |
| 100,000 | 100000 | baseline_ucc | ok | 1,207,504 | 317,501 | 170,000 | 5.639 s |
| 100,000 | 100000 | optimized_ucc | ok | 347,500 | 125,000 | 170,000 | 3.971 s |

## qpe_style

| Requested Gates | Actual Input Gates | Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---:|---:|---|---|---:|---:|---:|---:|
| 4,000 | 4000 | qiskit_opt3 | ok | 8,486 | 5,602 | 2,402 | 0.537 s |
| 4,000 | 4000 | qiskit_commutative_inverse | ok | 15,840 | 11,841 | 6,240 | 0.284 s |
| 4,000 | 4000 | tket_full_peephole | ok | 12,278 | 7,308 | 1,843 | 24.798 s |
| 4,000 | 4000 | pyzx_opt | ok | 15,840 | 11,841 | 6,240 | 1.015 s |
| 4,000 | 4000 | baseline_ucc | ok | 18,253 | 9,451 | 2,402 | 0.281 s |
| 4,000 | 4000 | optimized_ucc | ok | 6,560 | 4,401 | 2,560 | 4.465 s |
| 10,000 | 10000 | qiskit_opt3 | ok | 21,206 | 14,002 | 6,002 | 1.867 s |
| 10,000 | 10000 | qiskit_commutative_inverse | ok | 39,600 | 29,601 | 15,600 | 0.398 s |
| 10,000 | 10000 | tket_full_peephole | timeout | - | - | - | > 45 s |
| 10,000 | 10000 | pyzx_opt | ok | 39,600 | 29,601 | 15,600 | 4.018 s |
| 10,000 | 10000 | baseline_ucc | ok | 45,613 | 23,611 | 6,002 | 0.448 s |
| 10,000 | 10000 | optimized_ucc | ok | 16,440 | 11,001 | 6,020 | 1.015 s |
| 20,000 | 20000 | qiskit_opt3 | ok | 42,406 | 28,002 | 12,002 | 6.27 s |
| 20,000 | 20000 | qiskit_commutative_inverse | ok | 79,200 | 59,201 | 31,200 | 0.554 s |
| 20,000 | 20000 | tket_full_peephole | timeout | - | - | - | > 45 s |
| 20,000 | 20000 | pyzx_opt | ok | 79,200 | 59,201 | 31,200 | 14.255 s |
| 20,000 | 20000 | baseline_ucc | ok | 91,213 | 47,211 | 12,002 | 0.704 s |
| 20,000 | 20000 | optimized_ucc | ok | 32,880 | 22,001 | 12,040 | 1.375 s |
| 50,000 | 50000 | qiskit_opt3 | ok | 106,006 | 70,002 | 30,002 | 36.272 s |
| 50,000 | 50000 | qiskit_commutative_inverse | ok | 198,000 | 148,001 | 78,000 | 1.082 s |
| 50,000 | 50000 | tket_full_peephole | timeout | - | - | - | > 45 s |
| 50,000 | 50000 | pyzx_opt | timeout | - | - | - | > 45 s |
| 50,000 | 50000 | baseline_ucc | ok | 228,013 | 118,011 | 30,002 | 1.422 s |
| 50,000 | 50000 | optimized_ucc | ok | 82,200 | 55,001 | 30,100 | 2.574 s |
| 100,000 | 100000 | qiskit_opt3 | timeout | - | - | - | > 60 s |
| 100,000 | 100000 | qiskit_commutative_inverse | ok | 396,000 | 296,001 | 156,000 | 1.952 s |
| 100,000 | 100000 | tket_full_peephole | timeout | - | - | - | > 45 s |
| 100,000 | 100000 | pyzx_opt | timeout | - | - | - | > 45 s |
| 100,000 | 100000 | baseline_ucc | ok | 456,013 | 236,011 | 60,002 | 2.861 s |
| 100,000 | 100000 | optimized_ucc | ok | 164,400 | 110,001 | 60,200 | 4.993 s |

## fourier_phase_sandwich

| Requested Gates | Actual Input Gates | Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---:|---:|---|---|---:|---:|---:|---:|
| 4,000 | 3998 | qiskit_opt3 | ok | 9,588 | 5,593 | 4,788 | 1.397 s |
| 4,000 | 3998 | qiskit_commutative_inverse | ok | 13,574 | 6,392 | 4,788 | 9.526 s |
| 4,000 | 3998 | tket_full_peephole | timeout | - | - | - | > 45 s |
| 4,000 | 3998 | pyzx_opt | ok | 13,574 | 6,392 | 4,788 | 1.95 s |
| 4,000 | 3998 | baseline_ucc | ok | 35,117 | 14,374 | 4,788 | 0.852 s |
| 4,000 | 3998 | optimized_ucc | ok | 42 | 24 | 12 | 2.143 s |
| 10,000 | 9998 | qiskit_opt3 | ok | 23,988 | 13,993 | 11,988 | 7.45 s |
| 10,000 | 9998 | qiskit_commutative_inverse | ok | 33,974 | 15,992 | 11,988 | 58.157 s |
| 10,000 | 9998 | tket_full_peephole | timeout | - | - | - | > 45 s |
| 10,000 | 9998 | pyzx_opt | ok | 33,974 | 15,992 | 11,988 | 10.176 s |
| 10,000 | 9998 | baseline_ucc | ok | 87,916 | 35,973 | 11,988 | 3.85 s |
| 10,000 | 9998 | optimized_ucc | ok | 42 | 24 | 12 | 9.859 s |
| 20,000 | 19998 | qiskit_opt3 | ok | 47,988 | 27,993 | 23,988 | 29.0 s |
| 20,000 | 19998 | qiskit_commutative_inverse | timeout | - | - | - | > 60 s |
| 20,000 | 19998 | tket_full_peephole | timeout | - | - | - | > 45 s |
| 20,000 | 19998 | pyzx_opt | ok | 67,974 | 31,992 | 23,988 | 39.756 s |
| 20,000 | 19998 | baseline_ucc | ok | 175,917 | 71,974 | 23,988 | 14.244 s |
| 20,000 | 19998 | optimized_ucc | ok | 42 | 24 | 12 | 37.002 s |
| 50,000 | 49998 | qiskit_opt3 | timeout | - | - | - | > 60 s |
| 50,000 | 49998 | qiskit_commutative_inverse | timeout | - | - | - | > 90 s |
| 50,000 | 49998 | tket_full_peephole | timeout | - | - | - | > 45 s |
| 50,000 | 49998 | pyzx_opt | timeout | - | - | - | > 45 s |
| 50,000 | 49998 | baseline_ucc | timeout | - | - | - | > 60 s |
| 50,000 | 49998 | optimized_ucc | ok | 42 | 24 | 12 | 20.484 s |
| 100,000 | 99998 | qiskit_opt3 | timeout | - | - | - | > 60 s |
| 100,000 | 99998 | qiskit_commutative_inverse | timeout | - | - | - | > 90 s |
| 100,000 | 99998 | tket_full_peephole | timeout | - | - | - | > 45 s |
| 100,000 | 99998 | pyzx_opt | timeout | - | - | - | > 45 s |
| 100,000 | 99998 | baseline_ucc | timeout | - | - | - | > 60 s |
| 100,000 | 99998 | optimized_ucc | ok | 42 | 24 | 12 | 27.207 s |

## algorithmic_qft

| Requested Gates | Actual Input Gates | Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---:|---:|---|---|---:|---:|---:|---:|
| 4,000 | 4000 | qiskit_opt3 | ok | 13,900 | 5,200 | 6,800 | 0.299 s |
| 4,000 | 4000 | qiskit_commutative_inverse | ok | 16,000 | 5,800 | 6,800 | 0.328 s |
| 4,000 | 4000 | tket_full_peephole | ok | 32,318 | 11,318 | 5,303 | 30.227 s |
| 4,000 | 4000 | pyzx_opt | ok | 16,000 | 5,800 | 6,800 | 2.245 s |
| 4,000 | 4000 | baseline_ucc | ok | 49,501 | 13,300 | 6,800 | 0.391 s |
| 4,000 | 4000 | optimized_ucc | ok | 13,900 | 5,200 | 6,800 | 0.089 s |
| 10,000 | 10000 | qiskit_opt3 | ok | 34,750 | 13,000 | 17,000 | 0.359 s |
| 10,000 | 10000 | qiskit_commutative_inverse | ok | 40,000 | 14,500 | 17,000 | 0.408 s |
| 10,000 | 10000 | tket_full_peephole | timeout | - | - | - | > 45 s |
| 10,000 | 10000 | pyzx_opt | ok | 40,000 | 14,500 | 17,000 | 10.301 s |
| 10,000 | 10000 | baseline_ucc | ok | 123,751 | 33,250 | 17,000 | 0.78 s |
| 10,000 | 10000 | optimized_ucc | ok | 34,750 | 13,000 | 17,000 | 0.232 s |
| 20,000 | 20000 | qiskit_opt3 | ok | 69,500 | 26,000 | 34,000 | 0.516 s |
| 20,000 | 20000 | qiskit_commutative_inverse | ok | 80,000 | 29,000 | 34,000 | 0.538 s |
| 20,000 | 20000 | tket_full_peephole | timeout | - | - | - | > 45 s |
| 20,000 | 20000 | pyzx_opt | ok | 80,000 | 29,000 | 34,000 | 40.77 s |
| 20,000 | 20000 | baseline_ucc | ok | 247,501 | 66,500 | 34,000 | 1.379 s |
| 20,000 | 20000 | optimized_ucc | ok | 69,500 | 26,000 | 34,000 | 0.459 s |
| 50,000 | 50000 | qiskit_opt3 | ok | 173,750 | 65,000 | 85,000 | 0.936 s |
| 50,000 | 50000 | qiskit_commutative_inverse | ok | 200,000 | 72,500 | 85,000 | 1.137 s |
| 50,000 | 50000 | tket_full_peephole | timeout | - | - | - | > 45 s |
| 50,000 | 50000 | pyzx_opt | timeout | - | - | - | > 45 s |
| 50,000 | 50000 | baseline_ucc | ok | 618,751 | 166,250 | 85,000 | 3.099 s |
| 50,000 | 50000 | optimized_ucc | ok | 173,750 | 65,000 | 85,000 | 2.833 s |
| 100,000 | 100000 | qiskit_opt3 | ok | 347,500 | 130,000 | 170,000 | 1.68 s |
| 100,000 | 100000 | qiskit_commutative_inverse | ok | 400,000 | 145,000 | 170,000 | 2.12 s |
| 100,000 | 100000 | tket_full_peephole | timeout | - | - | - | > 45 s |
| 100,000 | 100000 | pyzx_opt | timeout | - | - | - | > 45 s |
| 100,000 | 100000 | baseline_ucc | ok | 1,237,501 | 332,500 | 170,000 | 5.909 s |
| 100,000 | 100000 | optimized_ucc | ok | 347,500 | 130,000 | 170,000 | 4.134 s |

## algorithmic_aqft

| Requested Gates | Actual Input Gates | Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---:|---:|---|---|---:|---:|---:|---:|
| 4,000 | 3996 | qiskit_opt3 | ok | 13,716 | 5,616 | 6,696 | 0.267 s |
| 4,000 | 3996 | qiskit_commutative_inverse | ok | 15,660 | 6,264 | 6,696 | 0.309 s |
| 4,000 | 3996 | tket_full_peephole | ok | 31,014 | 12,222 | 5,079 | 24.852 s |
| 4,000 | 3996 | pyzx_opt | ok | 15,660 | 6,264 | 6,696 | 1.513 s |
| 4,000 | 3996 | baseline_ucc | ok | 48,924 | 14,364 | 6,696 | 0.413 s |
| 4,000 | 3996 | optimized_ucc | ok | 13,716 | 5,616 | 6,696 | 0.089 s |
| 10,000 | 9990 | qiskit_opt3 | ok | 34,290 | 14,040 | 16,740 | 0.399 s |
| 10,000 | 9990 | qiskit_commutative_inverse | ok | 39,150 | 15,660 | 16,740 | 0.382 s |
| 10,000 | 9990 | tket_full_peephole | timeout | - | - | - | > 45 s |
| 10,000 | 9990 | pyzx_opt | ok | 39,150 | 15,660 | 16,740 | 6.964 s |
| 10,000 | 9990 | baseline_ucc | ok | 122,310 | 35,910 | 16,740 | 0.8 s |
| 10,000 | 9990 | optimized_ucc | ok | 34,290 | 14,040 | 16,740 | 0.253 s |
| 20,000 | 19980 | qiskit_opt3 | ok | 68,580 | 28,080 | 33,480 | 0.492 s |
| 20,000 | 19980 | qiskit_commutative_inverse | ok | 78,300 | 31,320 | 33,480 | 0.558 s |
| 20,000 | 19980 | tket_full_peephole | timeout | - | - | - | > 45 s |
| 20,000 | 19980 | pyzx_opt | ok | 78,300 | 31,320 | 33,480 | 29.338 s |
| 20,000 | 19980 | baseline_ucc | ok | 244,620 | 71,820 | 33,480 | 1.592 s |
| 20,000 | 19980 | optimized_ucc | ok | 68,580 | 28,080 | 33,480 | 0.56 s |
| 50,000 | 49987 | qiskit_opt3 | ok | 171,577 | 70,252 | 83,762 | 1.252 s |
| 50,000 | 49987 | qiskit_commutative_inverse | ok | 195,895 | 78,358 | 83,762 | 1.236 s |
| 50,000 | 49987 | tket_full_peephole | timeout | - | - | - | > 45 s |
| 50,000 | 49987 | pyzx_opt | timeout | - | - | - | > 45 s |
| 50,000 | 49987 | baseline_ucc | ok | 612,003 | 179,683 | 83,762 | 3.376 s |
| 50,000 | 49987 | optimized_ucc | ok | 171,577 | 70,252 | 83,762 | 2.94 s |
| 100,000 | 99974 | qiskit_opt3 | ok | 343,154 | 140,504 | 167,524 | 1.838 s |
| 100,000 | 99974 | qiskit_commutative_inverse | ok | 391,790 | 156,716 | 167,524 | 2.134 s |
| 100,000 | 99974 | tket_full_peephole | timeout | - | - | - | > 45 s |
| 100,000 | 99974 | pyzx_opt | timeout | - | - | - | > 45 s |
| 100,000 | 99974 | baseline_ucc | ok | 1,224,006 | 359,366 | 167,524 | 5.932 s |
| 100,000 | 99974 | optimized_ucc | ok | 343,154 | 140,504 | 167,524 | 3.866 s |

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

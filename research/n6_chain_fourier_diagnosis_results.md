# n=6 chain_cp Fourier Diagnosis

| Angle Family | Target | Method | Status | Out Gates | Expected | Depth | CX | Equiv |
|---|---:|---|---|---:|---:|---:|---:|---|
| nonresonant_seeded | 4000 | semantic_ucc | ok | 68 | 43 | 21 | 8 | True |
| nonresonant_seeded | 4000 | qiskit_opt3 | ok | 8338 | - | 2910 | 3258 | True |
| nonresonant_seeded | 4000 | baseline_ucc | skipped (focusing on semantic) | - | - | - | - | - |
| nonresonant_seeded | 10000 | semantic_ucc | ok | 43 | 43 | 28 | 10 | - |
| nonresonant_seeded | 10000 | qiskit_opt3 | ok | 20900 | - | 7279 | 8172 | - |
| nonresonant_seeded | 10000 | baseline_ucc | skipped (focusing on semantic) | - | - | - | - | - |
| nonresonant_seeded | 20000 | semantic_ucc | ok | 43 | 43 | 28 | 10 | - |
| nonresonant_seeded | 20000 | qiskit_opt3 | ok | 41807 | - | 14551 | 16353 | - |
| nonresonant_seeded | 20000 | baseline_ucc | skipped (focusing on semantic) | - | - | - | - | - |
| nonresonant_seeded | 50000 | semantic_ucc | ok | 43 | 43 | 28 | 10 | - |
| nonresonant_seeded | 50000 | qiskit_opt3 | ok | 104524 | - | 36366 | 40896 | - |
| nonresonant_seeded | 50000 | baseline_ucc | skipped (focusing on semantic) | - | - | - | - | - |
| qft_dyadic | 4000 | semantic_ucc | ok | 43 | 43 | 28 | 10 | True |
| qft_dyadic | 4000 | qiskit_opt3 | ok | 7257 | - | 2550 | 3620 | True |
| qft_dyadic | 4000 | baseline_ucc | skipped (focusing on semantic) | - | - | - | - | - |
| qft_dyadic | 10000 | semantic_ucc | ok | 41 | 43 | 27 | 10 | - |
| qft_dyadic | 10000 | qiskit_opt3 | ok | 18176 | - | 6372 | 9080 | - |
| qft_dyadic | 10000 | baseline_ucc | skipped (focusing on semantic) | - | - | - | - | - |
| qft_dyadic | 20000 | semantic_ucc | ok | 43 | 43 | 28 | 10 | - |
| qft_dyadic | 20000 | qiskit_opt3 | ok | 36358 | - | 12735 | 18170 | - |
| qft_dyadic | 20000 | baseline_ucc | skipped (focusing on semantic) | - | - | - | - | - |
| qft_dyadic | 50000 | semantic_ucc | ok | 31 | 43 | 26 | 10 | - |
| qft_dyadic | 50000 | qiskit_opt3 | ok | 90892 | - | 31823 | 45440 | - |
| qft_dyadic | 50000 | baseline_ucc | skipped (focusing on semantic) | - | - | - | - | - |
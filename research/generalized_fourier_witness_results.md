# Generalized Fourier Witness Suite

| n_qubits | Topology | Angle Family | Req. Gates | Repeats | Method | Status | Out Gates | Depth | CX | Runtime |
|---:|---|---|---:|---:|---|---|---:|---:|---:|---:|
| 4 | chain_cp | nonresonant_seeded | 4,000 | 570 | qiskit_opt3 | ok | 6,851 | 3,998 | 3,420 | 1.794 s |
| 4 | chain_cp | nonresonant_seeded | 4,000 | 570 | baseline_ucc | ok | 27 | 18 | 6 | 5.441 s |
| 4 | chain_cp | nonresonant_seeded | 4,000 | 570 | semantic_ucc | ok | 27 | 18 | 6 | 5.451 s |
| 4 | chain_cp | nonresonant_seeded | 4,000 | 570 | pyzx_opt | unavailable | - | - | - | - |
| 4 | chain_cp | nonresonant_seeded | 4,000 | 570 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | chain_cp | nonresonant_seeded | 10,000 | 1427 | qiskit_opt3 | ok | 17,136 | 9,997 | 8,562 | 10.31 s |
| 4 | chain_cp | nonresonant_seeded | 10,000 | 1427 | baseline_ucc | ok | 27 | 18 | 6 | 22.101 s |
| 4 | chain_cp | nonresonant_seeded | 10,000 | 1427 | semantic_ucc | ok | 27 | 18 | 6 | 20.291 s |
| 4 | chain_cp | nonresonant_seeded | 10,000 | 1427 | pyzx_opt | unavailable | - | - | - | - |
| 4 | chain_cp | nonresonant_seeded | 10,000 | 1427 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | chain_cp | nonresonant_seeded | 20,000 | 2856 | qiskit_opt3 | ok | 34,283 | 20,000 | 17,136 | 41.376 s |
| 4 | chain_cp | nonresonant_seeded | 20,000 | - | baseline_ucc | timeout | - | - | - | > 60 s |
| 4 | chain_cp | nonresonant_seeded | 20,000 | 2856 | semantic_ucc | ok | 27 | 18 | 6 | 71.208 s |
| 4 | chain_cp | nonresonant_seeded | 20,000 | 2856 | pyzx_opt | unavailable | - | - | - | - |
| 4 | chain_cp | nonresonant_seeded | 20,000 | 2856 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | chain_cp | nonresonant_seeded | 50,000 | - | qiskit_opt3 | timeout | - | - | - | > 90 s |
| 4 | chain_cp | nonresonant_seeded | 50,000 | 7141 | baseline_ucc | ok | 27 | 18 | 6 | 71.383 s |
| 4 | chain_cp | nonresonant_seeded | 50,000 | 7141 | semantic_ucc | ok | 27 | 18 | 6 | 68.568 s |
| 4 | chain_cp | nonresonant_seeded | 50,000 | 7141 | pyzx_opt | unavailable | - | - | - | - |
| 4 | chain_cp | nonresonant_seeded | 50,000 | 7141 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | chain_cp | qft_dyadic | 4,000 | 570 | qiskit_opt3 | ok | 6,852 | 3,998 | 3,420 | 1.684 s |
| 4 | chain_cp | qft_dyadic | 4,000 | 570 | baseline_ucc | ok | 27 | 18 | 6 | 5.79 s |
| 4 | chain_cp | qft_dyadic | 4,000 | 570 | semantic_ucc | ok | 27 | 18 | 6 | 7.035 s |
| 4 | chain_cp | qft_dyadic | 4,000 | 570 | pyzx_opt | unavailable | - | - | - | - |
| 4 | chain_cp | qft_dyadic | 4,000 | 570 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | chain_cp | qft_dyadic | 10,000 | 1427 | qiskit_opt3 | ok | 17,136 | 9,997 | 8,562 | 10.731 s |
| 4 | chain_cp | qft_dyadic | 10,000 | 1427 | baseline_ucc | ok | 27 | 18 | 6 | 20.102 s |
| 4 | chain_cp | qft_dyadic | 10,000 | 1427 | semantic_ucc | ok | 27 | 18 | 6 | 20.02 s |
| 4 | chain_cp | qft_dyadic | 10,000 | 1427 | pyzx_opt | unavailable | - | - | - | - |
| 4 | chain_cp | qft_dyadic | 10,000 | 1427 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | chain_cp | qft_dyadic | 20,000 | 2856 | qiskit_opt3 | ok | 34,283 | 20,000 | 17,136 | 42.455 s |
| 4 | chain_cp | qft_dyadic | 20,000 | - | baseline_ucc | timeout | - | - | - | > 60 s |
| 4 | chain_cp | qft_dyadic | 20,000 | 2856 | semantic_ucc | ok | 27 | 18 | 6 | 72.93 s |
| 4 | chain_cp | qft_dyadic | 20,000 | 2856 | pyzx_opt | unavailable | - | - | - | - |
| 4 | chain_cp | qft_dyadic | 20,000 | 2856 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | chain_cp | qft_dyadic | 50,000 | - | qiskit_opt3 | timeout | - | - | - | > 90 s |
| 4 | chain_cp | qft_dyadic | 50,000 | 7141 | baseline_ucc | ok | 27 | 18 | 6 | 70.455 s |
| 4 | chain_cp | qft_dyadic | 50,000 | 7141 | semantic_ucc | ok | 27 | 18 | 6 | 72.374 s |
| 4 | chain_cp | qft_dyadic | 50,000 | 7141 | pyzx_opt | unavailable | - | - | - | - |
| 4 | chain_cp | qft_dyadic | 50,000 | 7141 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | chain_cp | mixed_signed | 4,000 | 570 | qiskit_opt3 | ok | 6,850 | 3,998 | 3,420 | 1.681 s |
| 4 | chain_cp | mixed_signed | 4,000 | 570 | baseline_ucc | ok | 27 | 18 | 6 | 5.731 s |
| 4 | chain_cp | mixed_signed | 4,000 | 570 | semantic_ucc | ok | 27 | 18 | 6 | 5.654 s |
| 4 | chain_cp | mixed_signed | 4,000 | 570 | pyzx_opt | unavailable | - | - | - | - |
| 4 | chain_cp | mixed_signed | 4,000 | 570 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | chain_cp | mixed_signed | 10,000 | 1427 | qiskit_opt3 | ok | 17,136 | 9,997 | 8,562 | 9.912 s |
| 4 | chain_cp | mixed_signed | 10,000 | 1427 | baseline_ucc | ok | 27 | 18 | 6 | 20.032 s |
| 4 | chain_cp | mixed_signed | 10,000 | 1427 | semantic_ucc | ok | 27 | 18 | 6 | 19.789 s |
| 4 | chain_cp | mixed_signed | 10,000 | 1427 | pyzx_opt | unavailable | - | - | - | - |
| 4 | chain_cp | mixed_signed | 10,000 | 1427 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | chain_cp | mixed_signed | 20,000 | 2856 | qiskit_opt3 | ok | 34,281 | 19,999 | 17,136 | 43.012 s |
| 4 | chain_cp | mixed_signed | 20,000 | - | baseline_ucc | timeout | - | - | - | > 60 s |
| 4 | chain_cp | mixed_signed | 20,000 | 2856 | semantic_ucc | ok | 23 | 17 | 6 | 68.221 s |
| 4 | chain_cp | mixed_signed | 20,000 | 2856 | pyzx_opt | unavailable | - | - | - | - |
| 4 | chain_cp | mixed_signed | 20,000 | 2856 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | chain_cp | mixed_signed | 50,000 | - | qiskit_opt3 | timeout | - | - | - | > 90 s |
| 4 | chain_cp | mixed_signed | 50,000 | 7141 | baseline_ucc | ok | 27 | 18 | 6 | 74.872 s |
| 4 | chain_cp | mixed_signed | 50,000 | 7141 | semantic_ucc | ok | 27 | 18 | 6 | 73.013 s |
| 4 | chain_cp | mixed_signed | 50,000 | 7141 | pyzx_opt | unavailable | - | - | - | - |
| 4 | chain_cp | mixed_signed | 50,000 | 7141 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | ring_cp | nonresonant_seeded | 4,000 | 499 | qiskit_opt3 | ok | 7,996 | 7,987 | 3,992 | 1.413 s |
| 4 | ring_cp | nonresonant_seeded | 4,000 | 499 | baseline_ucc | ok | 32 | 23 | 8 | 5.518 s |
| 4 | ring_cp | nonresonant_seeded | 4,000 | 499 | semantic_ucc | ok | 32 | 23 | 8 | 5.395 s |
| 4 | ring_cp | nonresonant_seeded | 4,000 | 499 | pyzx_opt | unavailable | - | - | - | - |
| 4 | ring_cp | nonresonant_seeded | 4,000 | 499 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | ring_cp | nonresonant_seeded | 10,000 | 1249 | qiskit_opt3 | ok | 19,996 | 19,987 | 9,992 | 8.243 s |
| 4 | ring_cp | nonresonant_seeded | 10,000 | 1249 | baseline_ucc | ok | 32 | 23 | 8 | 23.192 s |
| 4 | ring_cp | nonresonant_seeded | 10,000 | 1249 | semantic_ucc | ok | 32 | 23 | 8 | 22.89 s |
| 4 | ring_cp | nonresonant_seeded | 10,000 | 1249 | pyzx_opt | unavailable | - | - | - | - |
| 4 | ring_cp | nonresonant_seeded | 10,000 | 1249 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | ring_cp | nonresonant_seeded | 20,000 | 2499 | qiskit_opt3 | ok | 39,995 | 39,987 | 19,992 | 33.597 s |
| 4 | ring_cp | nonresonant_seeded | 20,000 | - | baseline_ucc | timeout | - | - | - | > 60 s |
| 4 | ring_cp | nonresonant_seeded | 20,000 | 2499 | semantic_ucc | ok | 32 | 23 | 8 | 64.984 s |
| 4 | ring_cp | nonresonant_seeded | 20,000 | 2499 | pyzx_opt | unavailable | - | - | - | - |
| 4 | ring_cp | nonresonant_seeded | 20,000 | 2499 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | ring_cp | nonresonant_seeded | 50,000 | - | qiskit_opt3 | timeout | - | - | - | > 90 s |
| 4 | ring_cp | nonresonant_seeded | 50,000 | 6249 | baseline_ucc | ok | 32 | 23 | 8 | 72.196 s |
| 4 | ring_cp | nonresonant_seeded | 50,000 | 6249 | semantic_ucc | ok | 32 | 23 | 8 | 72.46 s |
| 4 | ring_cp | nonresonant_seeded | 50,000 | 6249 | pyzx_opt | unavailable | - | - | - | - |
| 4 | ring_cp | nonresonant_seeded | 50,000 | 6249 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | ring_cp | qft_dyadic | 4,000 | 499 | qiskit_opt3 | ok | 7,996 | 7,987 | 3,992 | 1.397 s |
| 4 | ring_cp | qft_dyadic | 4,000 | 499 | baseline_ucc | ok | 32 | 23 | 8 | 5.448 s |
| 4 | ring_cp | qft_dyadic | 4,000 | 499 | semantic_ucc | ok | 32 | 23 | 8 | 5.449 s |
| 4 | ring_cp | qft_dyadic | 4,000 | 499 | pyzx_opt | unavailable | - | - | - | - |
| 4 | ring_cp | qft_dyadic | 4,000 | 499 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | ring_cp | qft_dyadic | 10,000 | 1249 | qiskit_opt3 | ok | 19,996 | 19,987 | 9,992 | 7.936 s |
| 4 | ring_cp | qft_dyadic | 10,000 | 1249 | baseline_ucc | ok | 32 | 23 | 8 | 24.617 s |
| 4 | ring_cp | qft_dyadic | 10,000 | 1249 | semantic_ucc | ok | 32 | 23 | 8 | 22.74 s |
| 4 | ring_cp | qft_dyadic | 10,000 | 1249 | pyzx_opt | unavailable | - | - | - | - |
| 4 | ring_cp | qft_dyadic | 10,000 | 1249 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | ring_cp | qft_dyadic | 20,000 | 2499 | qiskit_opt3 | ok | 39,996 | 39,987 | 19,992 | 30.837 s |
| 4 | ring_cp | qft_dyadic | 20,000 | - | baseline_ucc | timeout | - | - | - | > 60 s |
| 4 | ring_cp | qft_dyadic | 20,000 | 2499 | semantic_ucc | ok | 32 | 23 | 8 | 60.741 s |
| 4 | ring_cp | qft_dyadic | 20,000 | 2499 | pyzx_opt | unavailable | - | - | - | - |
| 4 | ring_cp | qft_dyadic | 20,000 | 2499 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | ring_cp | qft_dyadic | 50,000 | - | qiskit_opt3 | timeout | - | - | - | > 90 s |
| 4 | ring_cp | qft_dyadic | 50,000 | 6249 | baseline_ucc | ok | 32 | 23 | 8 | 75.615 s |
| 4 | ring_cp | qft_dyadic | 50,000 | 6249 | semantic_ucc | ok | 32 | 23 | 8 | 72.645 s |
| 4 | ring_cp | qft_dyadic | 50,000 | 6249 | pyzx_opt | unavailable | - | - | - | - |
| 4 | ring_cp | qft_dyadic | 50,000 | 6249 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | ring_cp | mixed_signed | 4,000 | 499 | qiskit_opt3 | ok | 7,996 | 7,987 | 3,992 | 1.377 s |
| 4 | ring_cp | mixed_signed | 4,000 | 499 | baseline_ucc | ok | 32 | 23 | 8 | 7.133 s |
| 4 | ring_cp | mixed_signed | 4,000 | 499 | semantic_ucc | ok | 32 | 23 | 8 | 5.229 s |
| 4 | ring_cp | mixed_signed | 4,000 | 499 | pyzx_opt | unavailable | - | - | - | - |
| 4 | ring_cp | mixed_signed | 4,000 | 499 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | ring_cp | mixed_signed | 10,000 | 1249 | qiskit_opt3 | ok | 19,996 | 19,987 | 9,992 | 7.795 s |
| 4 | ring_cp | mixed_signed | 10,000 | 1249 | baseline_ucc | ok | 32 | 23 | 8 | 22.419 s |
| 4 | ring_cp | mixed_signed | 10,000 | 1249 | semantic_ucc | ok | 32 | 23 | 8 | 22.89 s |
| 4 | ring_cp | mixed_signed | 10,000 | 1249 | pyzx_opt | unavailable | - | - | - | - |
| 4 | ring_cp | mixed_signed | 10,000 | 1249 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | ring_cp | mixed_signed | 20,000 | 2499 | qiskit_opt3 | ok | 39,996 | 39,987 | 19,992 | 31.684 s |
| 4 | ring_cp | mixed_signed | 20,000 | - | baseline_ucc | timeout | - | - | - | > 60 s |
| 4 | ring_cp | mixed_signed | 20,000 | 2499 | semantic_ucc | ok | 32 | 23 | 8 | 61.278 s |
| 4 | ring_cp | mixed_signed | 20,000 | 2499 | pyzx_opt | unavailable | - | - | - | - |
| 4 | ring_cp | mixed_signed | 20,000 | 2499 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | ring_cp | mixed_signed | 50,000 | - | qiskit_opt3 | timeout | - | - | - | > 90 s |
| 4 | ring_cp | mixed_signed | 50,000 | 6249 | baseline_ucc | ok | 32 | 23 | 8 | 72.235 s |
| 4 | ring_cp | mixed_signed | 50,000 | 6249 | semantic_ucc | ok | 32 | 23 | 8 | 71.942 s |
| 4 | ring_cp | mixed_signed | 50,000 | 6249 | pyzx_opt | unavailable | - | - | - | - |
| 4 | ring_cp | mixed_signed | 50,000 | 6249 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | sparse_cp_0.5 | nonresonant_seeded | 4,000 | 570 | qiskit_opt3 | ok | 6,851 | 4,563 | 3,420 | 3.512 s |
| 4 | sparse_cp_0.5 | nonresonant_seeded | 4,000 | 570 | baseline_ucc | ok | 27 | 12 | 6 | 7.224 s |
| 4 | sparse_cp_0.5 | nonresonant_seeded | 4,000 | 570 | semantic_ucc | ok | 27 | 12 | 6 | 7.181 s |
| 4 | sparse_cp_0.5 | nonresonant_seeded | 4,000 | 570 | pyzx_opt | unavailable | - | - | - | - |
| 4 | sparse_cp_0.5 | nonresonant_seeded | 4,000 | 570 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | sparse_cp_0.5 | nonresonant_seeded | 10,000 | 1427 | qiskit_opt3 | ok | 17,136 | 11,419 | 8,562 | 23.163 s |
| 4 | sparse_cp_0.5 | nonresonant_seeded | 10,000 | 1427 | baseline_ucc | ok | 27 | 12 | 6 | 31.465 s |
| 4 | sparse_cp_0.5 | nonresonant_seeded | 10,000 | 1427 | semantic_ucc | ok | 27 | 12 | 6 | 33.512 s |
| 4 | sparse_cp_0.5 | nonresonant_seeded | 10,000 | 1427 | pyzx_opt | unavailable | - | - | - | - |
| 4 | sparse_cp_0.5 | nonresonant_seeded | 10,000 | 1427 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | sparse_cp_0.5 | nonresonant_seeded | 20,000 | - | qiskit_opt3 | timeout | - | - | - | > 60 s |
| 4 | sparse_cp_0.5 | nonresonant_seeded | 20,000 | - | baseline_ucc | timeout | - | - | - | > 60 s |
| 4 | sparse_cp_0.5 | nonresonant_seeded | 20,000 | 2856 | semantic_ucc | ok | 27 | 12 | 6 | 118.587 s |
| 4 | sparse_cp_0.5 | nonresonant_seeded | 20,000 | 2856 | pyzx_opt | unavailable | - | - | - | - |
| 4 | sparse_cp_0.5 | nonresonant_seeded | 20,000 | 2856 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | sparse_cp_0.5 | nonresonant_seeded | 50,000 | - | qiskit_opt3 | timeout | - | - | - | > 90 s |
| 4 | sparse_cp_0.5 | nonresonant_seeded | 50,000 | 7141 | baseline_ucc | ok | 27 | 12 | 6 | 69.585 s |
| 4 | sparse_cp_0.5 | nonresonant_seeded | 50,000 | 7141 | semantic_ucc | ok | 27 | 12 | 6 | 68.348 s |
| 4 | sparse_cp_0.5 | nonresonant_seeded | 50,000 | 7141 | pyzx_opt | unavailable | - | - | - | - |
| 4 | sparse_cp_0.5 | nonresonant_seeded | 50,000 | 7141 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | sparse_cp_0.5 | qft_dyadic | 4,000 | 570 | qiskit_opt3 | ok | 6,852 | 4,563 | 3,420 | 3.43 s |
| 4 | sparse_cp_0.5 | qft_dyadic | 4,000 | 570 | baseline_ucc | ok | 27 | 12 | 6 | 7.127 s |
| 4 | sparse_cp_0.5 | qft_dyadic | 4,000 | 570 | semantic_ucc | ok | 27 | 12 | 6 | 7.122 s |
| 4 | sparse_cp_0.5 | qft_dyadic | 4,000 | 570 | pyzx_opt | unavailable | - | - | - | - |
| 4 | sparse_cp_0.5 | qft_dyadic | 4,000 | 570 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | sparse_cp_0.5 | qft_dyadic | 10,000 | 1427 | qiskit_opt3 | ok | 17,136 | 11,419 | 8,562 | 21.715 s |
| 4 | sparse_cp_0.5 | qft_dyadic | 10,000 | 1427 | baseline_ucc | ok | 27 | 12 | 6 | 31.246 s |
| 4 | sparse_cp_0.5 | qft_dyadic | 10,000 | 1427 | semantic_ucc | ok | 27 | 12 | 6 | 33.213 s |
| 4 | sparse_cp_0.5 | qft_dyadic | 10,000 | 1427 | pyzx_opt | unavailable | - | - | - | - |
| 4 | sparse_cp_0.5 | qft_dyadic | 10,000 | 1427 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | sparse_cp_0.5 | qft_dyadic | 20,000 | - | qiskit_opt3 | timeout | - | - | - | > 60 s |
| 4 | sparse_cp_0.5 | qft_dyadic | 20,000 | - | baseline_ucc | timeout | - | - | - | > 60 s |
| 4 | sparse_cp_0.5 | qft_dyadic | 20,000 | 2856 | semantic_ucc | ok | 25 | 12 | 6 | 124.237 s |
| 4 | sparse_cp_0.5 | qft_dyadic | 20,000 | 2856 | pyzx_opt | unavailable | - | - | - | - |
| 4 | sparse_cp_0.5 | qft_dyadic | 20,000 | 2856 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | sparse_cp_0.5 | qft_dyadic | 50,000 | - | qiskit_opt3 | timeout | - | - | - | > 90 s |
| 4 | sparse_cp_0.5 | qft_dyadic | 50,000 | 7141 | baseline_ucc | ok | 27 | 12 | 6 | 69.127 s |
| 4 | sparse_cp_0.5 | qft_dyadic | 50,000 | 7141 | semantic_ucc | ok | 27 | 12 | 6 | 70.95 s |
| 4 | sparse_cp_0.5 | qft_dyadic | 50,000 | 7141 | pyzx_opt | unavailable | - | - | - | - |
| 4 | sparse_cp_0.5 | qft_dyadic | 50,000 | 7141 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | sparse_cp_0.5 | mixed_signed | 4,000 | 570 | qiskit_opt3 | ok | 6,851 | 4,563 | 3,420 | 3.515 s |
| 4 | sparse_cp_0.5 | mixed_signed | 4,000 | 570 | baseline_ucc | ok | 27 | 12 | 6 | 7.28 s |
| 4 | sparse_cp_0.5 | mixed_signed | 4,000 | 570 | semantic_ucc | ok | 27 | 12 | 6 | 7.38 s |
| 4 | sparse_cp_0.5 | mixed_signed | 4,000 | 570 | pyzx_opt | unavailable | - | - | - | - |
| 4 | sparse_cp_0.5 | mixed_signed | 4,000 | 570 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | sparse_cp_0.5 | mixed_signed | 10,000 | 1427 | qiskit_opt3 | ok | 17,136 | 11,419 | 8,562 | 21.2 s |
| 4 | sparse_cp_0.5 | mixed_signed | 10,000 | 1427 | baseline_ucc | ok | 27 | 12 | 6 | 31.434 s |
| 4 | sparse_cp_0.5 | mixed_signed | 10,000 | 1427 | semantic_ucc | ok | 27 | 12 | 6 | 32.855 s |
| 4 | sparse_cp_0.5 | mixed_signed | 10,000 | 1427 | pyzx_opt | unavailable | - | - | - | - |
| 4 | sparse_cp_0.5 | mixed_signed | 10,000 | 1427 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | sparse_cp_0.5 | mixed_signed | 20,000 | - | qiskit_opt3 | timeout | - | - | - | > 60 s |
| 4 | sparse_cp_0.5 | mixed_signed | 20,000 | - | baseline_ucc | timeout | - | - | - | > 60 s |
| 4 | sparse_cp_0.5 | mixed_signed | 20,000 | 2856 | semantic_ucc | ok | 25 | 11 | 6 | 117.816 s |
| 4 | sparse_cp_0.5 | mixed_signed | 20,000 | 2856 | pyzx_opt | unavailable | - | - | - | - |
| 4 | sparse_cp_0.5 | mixed_signed | 20,000 | 2856 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | sparse_cp_0.5 | mixed_signed | 50,000 | - | qiskit_opt3 | timeout | - | - | - | > 90 s |
| 4 | sparse_cp_0.5 | mixed_signed | 50,000 | 7141 | baseline_ucc | ok | 27 | 12 | 6 | 69.147 s |
| 4 | sparse_cp_0.5 | mixed_signed | 50,000 | 7141 | semantic_ucc | ok | 27 | 12 | 6 | 71.594 s |
| 4 | sparse_cp_0.5 | mixed_signed | 50,000 | 7141 | pyzx_opt | unavailable | - | - | - | - |
| 4 | sparse_cp_0.5 | mixed_signed | 50,000 | 7141 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | full_pair_cp | nonresonant_seeded | 4,000 | 399 | qiskit_opt3 | ok | 10,783 | 5,593 | 4,389 | 3.792 s |
| 4 | full_pair_cp | nonresonant_seeded | 4,000 | 399 | baseline_ucc | ok | 42 | 24 | 12 | 7.873 s |
| 4 | full_pair_cp | nonresonant_seeded | 4,000 | 399 | semantic_ucc | ok | 42 | 24 | 12 | 7.967 s |
| 4 | full_pair_cp | nonresonant_seeded | 4,000 | 399 | pyzx_opt | unavailable | - | - | - | - |
| 4 | full_pair_cp | nonresonant_seeded | 4,000 | 399 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | full_pair_cp | nonresonant_seeded | 10,000 | 999 | qiskit_opt3 | ok | 26,983 | 13,993 | 10,989 | 22.803 s |
| 4 | full_pair_cp | nonresonant_seeded | 10,000 | 999 | baseline_ucc | ok | 42 | 24 | 12 | 34.435 s |
| 4 | full_pair_cp | nonresonant_seeded | 10,000 | 999 | semantic_ucc | ok | 42 | 24 | 12 | 33.841 s |
| 4 | full_pair_cp | nonresonant_seeded | 10,000 | 999 | pyzx_opt | unavailable | - | - | - | - |
| 4 | full_pair_cp | nonresonant_seeded | 10,000 | 999 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | full_pair_cp | nonresonant_seeded | 20,000 | - | qiskit_opt3 | timeout | - | - | - | > 60 s |
| 4 | full_pair_cp | nonresonant_seeded | 20,000 | - | baseline_ucc | timeout | - | - | - | > 60 s |
| 4 | full_pair_cp | nonresonant_seeded | 20,000 | 1999 | semantic_ucc | ok | 42 | 24 | 12 | 136.39 s |
| 4 | full_pair_cp | nonresonant_seeded | 20,000 | 1999 | pyzx_opt | unavailable | - | - | - | - |
| 4 | full_pair_cp | nonresonant_seeded | 20,000 | 1999 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | full_pair_cp | nonresonant_seeded | 50,000 | - | qiskit_opt3 | timeout | - | - | - | > 90 s |
| 4 | full_pair_cp | nonresonant_seeded | 50,000 | 4999 | baseline_ucc | ok | 42 | 24 | 12 | 77.669 s |
| 4 | full_pair_cp | nonresonant_seeded | 50,000 | 4999 | semantic_ucc | ok | 42 | 24 | 12 | 76.598 s |
| 4 | full_pair_cp | nonresonant_seeded | 50,000 | 4999 | pyzx_opt | unavailable | - | - | - | - |
| 4 | full_pair_cp | nonresonant_seeded | 50,000 | 4999 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | full_pair_cp | qft_dyadic | 4,000 | 399 | qiskit_opt3 | ok | 9,588 | 5,593 | 4,788 | 3.584 s |
| 4 | full_pair_cp | qft_dyadic | 4,000 | 399 | baseline_ucc | ok | 42 | 24 | 12 | 7.729 s |
| 4 | full_pair_cp | qft_dyadic | 4,000 | 399 | semantic_ucc | ok | 42 | 24 | 12 | 7.91 s |
| 4 | full_pair_cp | qft_dyadic | 4,000 | 399 | pyzx_opt | unavailable | - | - | - | - |
| 4 | full_pair_cp | qft_dyadic | 4,000 | 399 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | full_pair_cp | qft_dyadic | 10,000 | 999 | qiskit_opt3 | ok | 23,988 | 13,993 | 11,988 | 21.573 s |
| 4 | full_pair_cp | qft_dyadic | 10,000 | 999 | baseline_ucc | ok | 42 | 24 | 12 | 32.423 s |
| 4 | full_pair_cp | qft_dyadic | 10,000 | 999 | semantic_ucc | ok | 42 | 24 | 12 | 32.091 s |
| 4 | full_pair_cp | qft_dyadic | 10,000 | 999 | pyzx_opt | unavailable | - | - | - | - |
| 4 | full_pair_cp | qft_dyadic | 10,000 | 999 | tket_full_peephole | unavailable | - | - | - | - |
| 4 | full_pair_cp | qft_dyadic | 20,000 | - | qiskit_opt3 | timeout | - | - | - | > 60 s |
| 4 | full_pair_cp | qft_dyadic | 20,000 | - | baseline_ucc | timeout | - | - | - | > 60 s |
| 5 | chain_cp | nonresonant_seeded | 4,000 | 443 | semantic_ucc | ok | 35 | 23 | 8 | 5.753 s |
| 5 | chain_cp | nonresonant_seeded | 4,000 | 443 | qiskit_opt3 | ok | 7,097 | 3,553 | 3,101 | 1.371 s |
| 5 | chain_cp | nonresonant_seeded | 4,000 | 443 | baseline_ucc | ok | 35 | 23 | 8 | 5.104 s |
| 5 | chain_cp | nonresonant_seeded | 10,000 | 1110 | semantic_ucc | ok | 35 | 23 | 8 | 21.53 s |
| 5 | chain_cp | nonresonant_seeded | 10,000 | 1110 | qiskit_opt3 | ok | 17,774 | 8,890 | 7,770 | 8.114 s |
| 5 | chain_cp | nonresonant_seeded | 10,000 | 1110 | baseline_ucc | ok | 35 | 23 | 8 | 20.736 s |
| 5 | chain_cp | nonresonant_seeded | 20,000 | 2221 | semantic_ucc | ok | 35 | 23 | 8 | 60.685 s |
| 5 | chain_cp | nonresonant_seeded | 20,000 | 2221 | qiskit_opt3 | ok | 35,545 | 17,777 | 15,547 | 32.172 s |
| 5 | chain_cp | nonresonant_seeded | 20,000 | - | baseline_ucc | timeout | - | - | - | > 60 s |
| 5 | chain_cp | qft_dyadic | 4,000 | 443 | semantic_ucc | ok | 35 | 23 | 8 | 4.573 s |
| 5 | chain_cp | qft_dyadic | 4,000 | 443 | qiskit_opt3 | ok | 7,103 | 3,113 | 3,544 | 1.196 s |
| 5 | chain_cp | qft_dyadic | 4,000 | 443 | baseline_ucc | ok | 35 | 23 | 8 | 4.584 s |
| 5 | chain_cp | qft_dyadic | 10,000 | 1110 | semantic_ucc | ok | 35 | 23 | 8 | 20.615 s |
| 5 | chain_cp | qft_dyadic | 10,000 | 1110 | qiskit_opt3 | ok | 17,775 | 7,782 | 8,880 | 6.942 s |
| 5 | chain_cp | qft_dyadic | 10,000 | 1110 | baseline_ucc | ok | 35 | 23 | 8 | 21.391 s |
| 5 | chain_cp | qft_dyadic | 20,000 | 2221 | semantic_ucc | ok | 35 | 23 | 8 | 58.234 s |
| 5 | chain_cp | qft_dyadic | 20,000 | 2221 | qiskit_opt3 | ok | 35,551 | 15,559 | 17,768 | 27.399 s |
| 5 | chain_cp | qft_dyadic | 20,000 | - | baseline_ucc | timeout | - | - | - | > 60 s |
| 5 | full_pair_cp | nonresonant_seeded | 4,000 | 266 | semantic_ucc | ok | 65 | 32 | 20 | 5.528 s |
| 5 | full_pair_cp | nonresonant_seeded | 4,000 | 266 | qiskit_opt3 | ok | 11,711 | 4,798 | 5,054 | 1.488 s |
| 5 | full_pair_cp | nonresonant_seeded | 4,000 | 266 | baseline_ucc | ok | 65 | 32 | 20 | 5.298 s |
| 5 | full_pair_cp | nonresonant_seeded | 10,000 | 666 | semantic_ucc | ok | 65 | 32 | 20 | 22.449 s |
| 5 | full_pair_cp | nonresonant_seeded | 10,000 | 666 | qiskit_opt3 | ok | 29,315 | 11,998 | 12,654 | 8.166 s |
| 5 | full_pair_cp | nonresonant_seeded | 10,000 | 666 | baseline_ucc | ok | 65 | 32 | 20 | 22.339 s |
| 5 | full_pair_cp | nonresonant_seeded | 20,000 | 1332 | semantic_ucc | ok | 65 | 32 | 20 | 62.52 s |
| 5 | full_pair_cp | nonresonant_seeded | 20,000 | 1332 | qiskit_opt3 | ok | 58,614 | 23,986 | 25,308 | 30.573 s |
| 5 | full_pair_cp | nonresonant_seeded | 20,000 | - | baseline_ucc | timeout | - | - | - | > 60 s |
| 5 | full_pair_cp | qft_dyadic | 4,000 | 266 | semantic_ucc | ok | 65 | 32 | 20 | 7.466 s |
| 5 | full_pair_cp | qft_dyadic | 4,000 | 266 | qiskit_opt3 | ok | 10,655 | 4,798 | 5,320 | 3.049 s |
| 5 | full_pair_cp | qft_dyadic | 4,000 | 266 | baseline_ucc | ok | 65 | 32 | 20 | 7.51 s |
| 5 | full_pair_cp | qft_dyadic | 10,000 | 666 | semantic_ucc | ok | 65 | 32 | 20 | 38.328 s |
| 5 | full_pair_cp | qft_dyadic | 10,000 | 666 | qiskit_opt3 | ok | 26,655 | 11,998 | 13,320 | 18.699 s |
| 5 | full_pair_cp | qft_dyadic | 10,000 | 666 | baseline_ucc | ok | 65 | 32 | 20 | 33.791 s |
| 5 | full_pair_cp | qft_dyadic | 20,000 | 1332 | semantic_ucc | ok | 65 | 32 | 20 | 102.736 s |
| 5 | full_pair_cp | qft_dyadic | 20,000 | - | qiskit_opt3 | timeout | - | - | - | > 60 s |
| 5 | full_pair_cp | qft_dyadic | 20,000 | - | baseline_ucc | timeout | - | - | - | > 60 s |
| 6 | chain_cp | nonresonant_seeded | 4,000 | 362 | semantic_ucc | ok | 68 | 21 | 8 | 2.171 s |
| 6 | chain_cp | nonresonant_seeded | 4,000 | 362 | qiskit_opt3 | ok | 8,338 | 2,910 | 3,258 | 1.159 s |
| 6 | chain_cp | nonresonant_seeded | 4,000 | 362 | baseline_ucc | ok | 68 | 21 | 8 | 2.287 s |
| 6 | chain_cp | nonresonant_seeded | 10,000 | 908 | semantic_ucc | ok | 43 | 28 | 10 | 21.758 s |
| 6 | chain_cp | nonresonant_seeded | 10,000 | 908 | qiskit_opt3 | ok | 20,900 | 7,279 | 8,172 | 6.537 s |
| 6 | chain_cp | nonresonant_seeded | 10,000 | 908 | baseline_ucc | ok | 43 | 28 | 10 | 21.623 s |
| 6 | chain_cp | nonresonant_seeded | 20,000 | 1817 | semantic_ucc | ok | 43 | 28 | 10 | 56.422 s |
| 6 | chain_cp | nonresonant_seeded | 20,000 | 1817 | qiskit_opt3 | ok | 41,807 | 14,551 | 16,353 | 27.107 s |
| 6 | chain_cp | nonresonant_seeded | 20,000 | - | baseline_ucc | timeout | - | - | - | > 60 s |
| 6 | chain_cp | qft_dyadic | 4,000 | 362 | semantic_ucc | ok | 43 | 28 | 10 | 5.253 s |
| 6 | chain_cp | qft_dyadic | 4,000 | 362 | qiskit_opt3 | ok | 7,257 | 2,550 | 3,620 | 1.064 s |
| 6 | chain_cp | qft_dyadic | 4,000 | 362 | baseline_ucc | ok | 43 | 28 | 10 | 5.202 s |
| 6 | chain_cp | qft_dyadic | 10,000 | 908 | semantic_ucc | ok | 41 | 27 | 10 | 22.927 s |
| 6 | chain_cp | qft_dyadic | 10,000 | 908 | qiskit_opt3 | ok | 18,176 | 6,372 | 9,080 | 8.047 s |
| 6 | chain_cp | qft_dyadic | 10,000 | 908 | baseline_ucc | ok | 41 | 27 | 10 | 20.967 s |
| 6 | chain_cp | qft_dyadic | 20,000 | 1817 | semantic_ucc | ok | 43 | 28 | 10 | 55.183 s |
| 6 | chain_cp | qft_dyadic | 20,000 | 1817 | qiskit_opt3 | ok | 36,358 | 12,735 | 18,170 | 25.611 s |
| 6 | chain_cp | qft_dyadic | 20,000 | - | baseline_ucc | timeout | - | - | - | > 60 s |
| 6 | full_pair_cp | nonresonant_seeded | 4,000 | 189 | semantic_ucc | ok | 93 | 40 | 30 | 7.06 s |
| 6 | full_pair_cp | nonresonant_seeded | 4,000 | 189 | qiskit_opt3 | ok | 12,108 | 4,359 | 5,481 | 1.524 s |
| 6 | full_pair_cp | nonresonant_seeded | 4,000 | 189 | baseline_ucc | ok | 93 | 40 | 30 | 5.696 s |
| 6 | full_pair_cp | nonresonant_seeded | 10,000 | 475 | semantic_ucc | ok | 93 | 40 | 30 | 20.438 s |
| 6 | full_pair_cp | nonresonant_seeded | 10,000 | 475 | qiskit_opt3 | ok | 30,417 | 10,939 | 13,775 | 7.851 s |
| 6 | full_pair_cp | nonresonant_seeded | 10,000 | 475 | baseline_ucc | ok | 93 | 40 | 30 | 19.313 s |
| 6 | full_pair_cp | nonresonant_seeded | 20,000 | 951 | semantic_ucc | ok | 93 | 40 | 30 | 68.375 s |
| 6 | full_pair_cp | nonresonant_seeded | 20,000 | 951 | qiskit_opt3 | ok | 60,876 | 21,885 | 27,579 | 31.051 s |
| 6 | full_pair_cp | nonresonant_seeded | 20,000 | - | baseline_ucc | timeout | - | - | - | > 60 s |
| 6 | full_pair_cp | qft_dyadic | 4,000 | 189 | semantic_ucc | ok | 93 | 40 | 30 | 6.714 s |
| 6 | full_pair_cp | qft_dyadic | 4,000 | 189 | qiskit_opt3 | ok | 11,358 | 4,171 | 5,670 | 2.482 s |
| 6 | full_pair_cp | qft_dyadic | 4,000 | 189 | baseline_ucc | ok | 93 | 40 | 30 | 6.795 s |
| 6 | full_pair_cp | qft_dyadic | 10,000 | 475 | semantic_ucc | ok | 93 | 40 | 30 | 26.98 s |
| 6 | full_pair_cp | qft_dyadic | 10,000 | 475 | qiskit_opt3 | ok | 28,518 | 10,463 | 14,250 | 14.995 s |
| 6 | full_pair_cp | qft_dyadic | 10,000 | 475 | baseline_ucc | ok | 93 | 40 | 30 | 27.362 s |
| 6 | full_pair_cp | qft_dyadic | 20,000 | 951 | semantic_ucc | ok | 93 | 40 | 30 | 94.51 s |
| 6 | full_pair_cp | qft_dyadic | 20,000 | - | qiskit_opt3 | timeout | - | - | - | > 60 s |
| 6 | full_pair_cp | qft_dyadic | 20,000 | - | baseline_ucc | timeout | - | - | - | > 60 s |

# Generalized Fourier Witness Suite Summary

## Overall Conclusion
Semantic Fourier-layer aggregation remains repetition-independent across topology, angle-family, and requested-size axes at fixed width `n=4`.

## Analysis by Setup
Each setup is `(n_qubits, topology, angle_family)`.

- ⚠️ Setup `(4, 'chain_cp', 'mixed_signed')` is NOT repetition-independent: `{4000: 27, 10000: 27, 20000: 23, 50000: 27}`
- ✅ Setup `(4, 'chain_cp', 'nonresonant_seeded')` is repetition-independent (constant size `27`).
- ✅ Setup `(4, 'chain_cp', 'qft_dyadic')` is repetition-independent (constant size `27`).
- ✅ Setup `(4, 'full_pair_cp', 'nonresonant_seeded')` is repetition-independent (constant size `42`).
- ✅ Setup `(4, 'full_pair_cp', 'qft_dyadic')` is repetition-independent (constant size `42`).
- ✅ Setup `(4, 'ring_cp', 'mixed_signed')` is repetition-independent (constant size `32`).
- ✅ Setup `(4, 'ring_cp', 'nonresonant_seeded')` is repetition-independent (constant size `32`).
- ✅ Setup `(4, 'ring_cp', 'qft_dyadic')` is repetition-independent (constant size `32`).
- ⚠️ Setup `(4, 'sparse_cp_0.5', 'mixed_signed')` is NOT repetition-independent: `{4000: 27, 10000: 27, 20000: 25, 50000: 27}`
- ✅ Setup `(4, 'sparse_cp_0.5', 'nonresonant_seeded')` is repetition-independent (constant size `27`).
- ⚠️ Setup `(4, 'sparse_cp_0.5', 'qft_dyadic')` is NOT repetition-independent: `{4000: 27, 10000: 27, 20000: 25, 50000: 27}`
- ✅ Setup `(5, 'chain_cp', 'nonresonant_seeded')` is repetition-independent (constant size `35`).
- ✅ Setup `(5, 'chain_cp', 'qft_dyadic')` is repetition-independent (constant size `35`).
- ✅ Setup `(5, 'full_pair_cp', 'nonresonant_seeded')` is repetition-independent (constant size `65`).
- ✅ Setup `(5, 'full_pair_cp', 'qft_dyadic')` is repetition-independent (constant size `65`).
- ⚠️ Setup `(6, 'chain_cp', 'nonresonant_seeded')` is NOT repetition-independent: `{4000: 68, 10000: 43, 20000: 43}`
- ⚠️ Setup `(6, 'chain_cp', 'qft_dyadic')` is NOT repetition-independent: `{4000: 43, 10000: 41, 20000: 43}`
- ✅ Setup `(6, 'full_pair_cp', 'nonresonant_seeded')` is repetition-independent (constant size `93`).
- ✅ Setup `(6, 'full_pair_cp', 'qft_dyadic')` is repetition-independent (constant size `93`).
- **Strict structural-quality wins**: `66/66`
- **No-worse quality points**: `66/66`
- **Runtime/scalability wins**: `16/66`
- **Total timeouts across all tools/runs**: `36`

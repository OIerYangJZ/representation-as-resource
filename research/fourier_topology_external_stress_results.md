# Fourier Topology External Stress Results

| Topology | Size | Method | Status | Gates | Depth | CX | Runtime (s) |
|---|------|--------|--------|-------|-------|----|-------------|
| chain_cp | 4000 | semantic_ucc | ok | 27 | 18 | 6 | 1.393 |
| chain_cp | 4000 | qiskit_opt3 | ok | 6851 | 3998 | 3420 | 0.619 |
| chain_cp | 4000 | pyzx_opt | ok | 10838 | 5139 | 3420 | 1.396 |
| chain_cp | 4000 | tket_full_peephole | ok | 20555 | 10852 | 3420 | 40.807 |
| chain_cp | 10000 | semantic_ucc | ok | 27 | 18 | 6 | 5.149 |
| chain_cp | 10000 | qiskit_opt3 | ok | 17136 | 9997 | 8562 | 2.968 |
| chain_cp | 10000 | pyzx_opt | ok | 27121 | 12852 | 8562 | 7.421 |
| chain_cp | 10000 | tket_full_peephole | timeout | - | - | - | - |
| ring_cp | 4000 | semantic_ucc | ok | 32 | 23 | 8 | 1.364 |
| ring_cp | 4000 | qiskit_opt3 | ok | 7996 | 7987 | 3992 | 0.528 |
| ring_cp | 4000 | pyzx_opt | ok | 11984 | 10481 | 3992 | 1.454 |
| ring_cp | 4000 | tket_full_peephole | ok | 23987 | 23957 | 3992 | 14.155 |
| ring_cp | 10000 | semantic_ucc | ok | 32 | 23 | 8 | 5.448 |
| ring_cp | 10000 | qiskit_opt3 | ok | 19996 | 19987 | 9992 | 2.265 |
| ring_cp | 10000 | pyzx_opt | ok | 29984 | 26231 | 9992 | 7.303 |
| ring_cp | 10000 | tket_full_peephole | ok | 59987 | 59957 | 9992 | 37.467 |
| sparse_cp_0.5 | 4000 | semantic_ucc | ok | 27 | 12 | 6 | 1.962 |
| sparse_cp_0.5 | 4000 | qiskit_opt3 | ok | 6851 | 4563 | 3420 | 1.171 |
| sparse_cp_0.5 | 4000 | pyzx_opt | ok | 10838 | 5133 | 3420 | 1.69 |
| sparse_cp_0.5 | 4000 | tket_full_peephole | timeout | - | - | - | - |
| sparse_cp_0.5 | 10000 | semantic_ucc | ok | 27 | 12 | 6 | 8.471 |
| sparse_cp_0.5 | 10000 | qiskit_opt3 | ok | 17136 | 11419 | 8562 | 6.323 |
| sparse_cp_0.5 | 10000 | pyzx_opt | ok | 27121 | 12846 | 8562 | 8.709 |
| sparse_cp_0.5 | 10000 | tket_full_peephole | timeout | - | - | - | - |
| full_pair_cp | 4000 | semantic_ucc | ok | 42 | 24 | 12 | 2.108 |
| full_pair_cp | 4000 | qiskit_opt3 | ok | 10783 | 5593 | 4389 | 1.231 |
| full_pair_cp | 4000 | pyzx_opt | ok | 13574 | 6392 | 4788 | 1.673 |
| full_pair_cp | 4000 | tket_full_peephole | timeout | - | - | - | - |
| full_pair_cp | 10000 | semantic_ucc | ok | 42 | 24 | 12 | 8.603 |
| full_pair_cp | 10000 | qiskit_opt3 | ok | 26983 | 13993 | 10989 | 6.454 |
| full_pair_cp | 10000 | pyzx_opt | ok | 33974 | 15992 | 11988 | 8.565 |
| full_pair_cp | 10000 | tket_full_peephole | timeout | - | - | - | - |
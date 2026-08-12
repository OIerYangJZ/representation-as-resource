# Unbounded Witness and Public-Baseline Summary

Generated: `2026-07-12T06:32:58+00:00`
Uniform per-cell timeout: `600` seconds.

The unbounded theorem certificate is symbolic (exact support rank plus Proposition 1). Operator checks below are implementation checks only. Timeout/error cells are statuses, never structural wins.

| Family | Requested | Actual | r | Method | Status | Gates | Depth | CX | Runtime | Equiv |
|---|---:|---:|---:|---|---|---:|---:|---:|---:|---|
| rational_cp | 4000 | 3998 | 399 | PyZX full_reduce | completed | 107 | 59 | 31 | 97.233 | True |
| rational_cp | 4000 | 3998 | 399 | qiskit opt3 | completed | 9588 | 5593 | 4788 | 1.370 | True |
| rational_cp | 4000 | 3998 | 399 | semantic UCC (Fourier-layer IR enabled) | completed | 42 | 24 | 12 | 3.116 | True |
| rational_cp | 4000 | 3998 | 399 | staq rotation folding | completed | 9188 | 4996 | 4788 | 0.688 | True |
| rational_cp | 4000 | 3998 | 399 | TKET GuidedPauliSimp | completed | 13574 | 6392 | 4788 | 1.528 | True |
| rational_cp | 4000 | 3998 | 399 | TKET PauliSimp (rebased) | completed | 52 | 29 | 19 | 1.197 | True |
| rational_cp | 4000 | 3998 | 399 | TKET PauliSimp (unrebased configuration) | predicate_error | - | - | - | 0.815 | - |
| rational_cp | 10000 | 9998 | 999 | PyZX full_reduce | timeout | - | - | - | 600.105 | - |
| rational_cp | 10000 | 9998 | 999 | qiskit opt3 | completed | 23988 | 13993 | 11988 | 5.919 | True |
| rational_cp | 10000 | 9998 | 999 | semantic UCC (Fourier-layer IR enabled) | completed | 42 | 24 | 12 | 9.122 | True |
| rational_cp | 10000 | 9998 | 999 | staq rotation folding | completed | 22988 | 12496 | 11988 | 1.419 | True |
| rational_cp | 10000 | 9998 | 999 | TKET GuidedPauliSimp | completed | 33974 | 15992 | 11988 | 2.779 | True |
| rational_cp | 10000 | 9998 | 999 | TKET PauliSimp (rebased) | completed | 62 | 36 | 28 | 2.010 | True |
| rational_cp | 10000 | 9998 | 999 | TKET PauliSimp (unrebased configuration) | predicate_error | - | - | - | 1.009 | - |
| rational_cp | 20000 | 19998 | 1999 | PyZX full_reduce | timeout | - | - | - | 600.105 | - |
| rational_cp | 20000 | 19998 | 1999 | qiskit opt3 | completed | 47988 | 27993 | 23988 | 21.496 | True |
| rational_cp | 20000 | 19998 | 1999 | semantic UCC (Fourier-layer IR enabled) | completed | 42 | 24 | 12 | 30.363 | True |
| rational_cp | 20000 | 19998 | 1999 | staq rotation folding | completed | 45988 | 24996 | 23988 | 2.659 | True |
| rational_cp | 20000 | 19998 | 1999 | TKET GuidedPauliSimp | completed | 67974 | 31992 | 23988 | 4.891 | True |
| rational_cp | 20000 | 19998 | 1999 | TKET PauliSimp (rebased) | completed | 59 | 27 | 20 | 3.555 | True |
| rational_cp | 20000 | 19998 | 1999 | TKET PauliSimp (unrebased configuration) | predicate_error | - | - | - | 1.368 | - |
| rational_cp | 50000 | 49998 | 4999 | PyZX full_reduce | timeout | - | - | - | 600.109 | - |
| rational_cp | 50000 | 49998 | 4999 | qiskit opt3 | completed | 119988 | 69993 | 59988 | 125.290 | True |
| rational_cp | 50000 | 49998 | 4999 | semantic UCC (Fourier-layer IR enabled) | completed | 42 | 24 | 12 | 22.666 | True |
| rational_cp | 50000 | 49998 | 4999 | staq rotation folding | completed | 114988 | 62496 | 59988 | 6.363 | True |
| rational_cp | 50000 | 49998 | 4999 | TKET GuidedPauliSimp | completed | 169974 | 79992 | 59988 | 11.391 | True |
| rational_cp | 50000 | 49998 | 4999 | TKET PauliSimp (rebased) | completed | 73 | 44 | 35 | 8.349 | True |
| rational_cp | 50000 | 49998 | 4999 | TKET PauliSimp (unrebased configuration) | predicate_error | - | - | - | 2.408 | - |
| rational_cp | 100000 | 99998 | 9999 | PyZX full_reduce | timeout | - | - | - | 600.112 | - |
| rational_cp | 100000 | 99998 | 9999 | qiskit opt3 | completed | 239988 | 139993 | 119988 | 494.296 | True |
| rational_cp | 100000 | 99998 | 9999 | semantic UCC (Fourier-layer IR enabled) | completed | 42 | 24 | 12 | 32.084 | True |
| rational_cp | 100000 | 99998 | 9999 | staq rotation folding | completed | 229988 | 124996 | 119988 | 12.568 | True |
| rational_cp | 100000 | 99998 | 9999 | TKET GuidedPauliSimp | completed | 339974 | 159992 | 119988 | 22.258 | True |
| rational_cp | 100000 | 99998 | 9999 | TKET PauliSimp (rebased) | completed | 66 | 37 | 28 | 16.238 | True |
| rational_cp | 100000 | 99998 | 9999 | TKET PauliSimp (unrebased configuration) | predicate_error | - | - | - | 4.058 | - |
| unbounded_independent_pauli | 4000 | 3998 | 399 | PyZX full_reduce | completed | 38 | 19 | 8 | 6.217 | True |
| unbounded_independent_pauli | 4000 | 3998 | 399 | qiskit opt3 | completed | 4799 | 2801 | 2394 | 0.650 | True |
| unbounded_independent_pauli | 4000 | 3998 | 399 | semantic UCC (Fourier-layer IR enabled) | completed | 27 | 18 | 6 | 2.327 | True |
| unbounded_independent_pauli | 4000 | 3998 | 399 | staq rotation folding | completed | 3402 | 2201 | 2394 | 0.475 | True |
| unbounded_independent_pauli | 4000 | 3998 | 399 | TKET GuidedPauliSimp | completed | 8786 | 4000 | 2394 | 1.348 | True |
| unbounded_independent_pauli | 4000 | 3998 | 399 | TKET PauliSimp (rebased) | completed | 36 | 14 | 6 | 1.043 | True |
| unbounded_independent_pauli | 4000 | 3998 | 399 | TKET PauliSimp (unrebased configuration) | predicate_error | - | - | - | 0.800 | - |
| unbounded_independent_pauli | 10000 | 9998 | 999 | PyZX full_reduce | completed | 48 | 33 | 12 | 32.438 | True |
| unbounded_independent_pauli | 10000 | 9998 | 999 | qiskit opt3 | completed | 12000 | 7001 | 5994 | 1.966 | True |
| unbounded_independent_pauli | 10000 | 9998 | 999 | semantic UCC (Fourier-layer IR enabled) | completed | 27 | 18 | 6 | 5.008 | True |
| unbounded_independent_pauli | 10000 | 9998 | 999 | staq rotation folding | completed | 8502 | 5501 | 5994 | 0.882 | True |
| unbounded_independent_pauli | 10000 | 9998 | 999 | TKET GuidedPauliSimp | completed | 21986 | 10000 | 5994 | 2.327 | True |
| unbounded_independent_pauli | 10000 | 9998 | 999 | TKET PauliSimp (rebased) | completed | 35 | 15 | 8 | 1.617 | True |
| unbounded_independent_pauli | 10000 | 9998 | 999 | TKET PauliSimp (unrebased configuration) | predicate_error | - | - | - | 0.990 | - |
| unbounded_independent_pauli | 20000 | 19998 | 1999 | PyZX full_reduce | correctness_failure | 48 | 33 | 12 | 129.160 | False |
| unbounded_independent_pauli | 20000 | 19998 | 1999 | qiskit opt3 | completed | 24000 | 14001 | 11994 | 5.876 | True |
| unbounded_independent_pauli | 20000 | 19998 | 1999 | semantic UCC (Fourier-layer IR enabled) | completed | 27 | 18 | 6 | 13.869 | True |
| unbounded_independent_pauli | 20000 | 19998 | 1999 | staq rotation folding | completed | 17002 | 11001 | 11994 | 1.600 | True |
| unbounded_independent_pauli | 20000 | 19998 | 1999 | TKET GuidedPauliSimp | completed | 43986 | 20000 | 11994 | 4.042 | True |
| unbounded_independent_pauli | 20000 | 19998 | 1999 | TKET PauliSimp (rebased) | completed | 38 | 16 | 8 | 2.690 | True |
| unbounded_independent_pauli | 20000 | 19998 | 1999 | TKET PauliSimp (unrebased configuration) | predicate_error | - | - | - | 1.316 | - |
| unbounded_independent_pauli | 50000 | 49998 | 4999 | PyZX full_reduce | timeout | - | - | - | 600.110 | - |
| unbounded_independent_pauli | 50000 | 49998 | 4999 | qiskit opt3 | completed | 60000 | 35001 | 29994 | 31.367 | True |
| unbounded_independent_pauli | 50000 | 49998 | 4999 | semantic UCC (Fourier-layer IR enabled) | completed | 27 | 18 | 6 | 21.486 | True |
| unbounded_independent_pauli | 50000 | 49998 | 4999 | staq rotation folding | completed | 42502 | 27501 | 29994 | 3.723 | True |
| unbounded_independent_pauli | 50000 | 49998 | 4999 | TKET GuidedPauliSimp | completed | 109986 | 50000 | 29994 | 9.133 | True |
| unbounded_independent_pauli | 50000 | 49998 | 4999 | TKET PauliSimp (rebased) | completed | 36 | 15 | 8 | 5.988 | True |
| unbounded_independent_pauli | 50000 | 49998 | 4999 | TKET PauliSimp (unrebased configuration) | predicate_error | - | - | - | 2.253 | - |
| unbounded_independent_pauli | 100000 | 99998 | 9999 | PyZX full_reduce | timeout | - | - | - | 600.110 | - |
| unbounded_independent_pauli | 100000 | 99998 | 9999 | qiskit opt3 | completed | 120000 | 70001 | 59994 | 119.004 | True |
| unbounded_independent_pauli | 100000 | 99998 | 9999 | semantic UCC (Fourier-layer IR enabled) | completed | 27 | 18 | 6 | 29.712 | True |
| unbounded_independent_pauli | 100000 | 99998 | 9999 | staq rotation folding | completed | 85002 | 55001 | 59994 | 7.253 | True |
| unbounded_independent_pauli | 100000 | 99998 | 9999 | TKET GuidedPauliSimp | completed | 219986 | 100000 | 59994 | 17.934 | True |
| unbounded_independent_pauli | 100000 | 99998 | 9999 | TKET PauliSimp (rebased) | completed | 37 | 16 | 8 | 11.673 | True |
| unbounded_independent_pauli | 100000 | 99998 | 9999 | TKET PauliSimp (unrebased configuration) | predicate_error | - | - | - | 3.838 | - |

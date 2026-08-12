# Unbounded Witness and Public-Baseline Summary

Generated: `2026-07-12T05:06:01+00:00`
Uniform per-cell timeout: `30` seconds.

The unbounded theorem certificate is symbolic (exact support rank plus Proposition 1). Operator checks below are implementation checks only. Timeout/error cells are statuses, never structural wins.

| Family | Requested | Actual | r | Method | Status | Gates | Depth | CX | Runtime | Equiv |
|---|---:|---:|---:|---|---|---:|---:|---:|---:|---|
| rational_cp | 48 | 48 | 4 | PyZX full_reduce | completed | 84 | 48 | 22 | 0.142 | True |
| rational_cp | 48 | 48 | 4 | qiskit opt3 | completed | 108 | 63 | 48 | 0.014 | True |
| rational_cp | 48 | 48 | 4 | semantic UCC (Fourier-layer IR enabled) | completed | 42 | 24 | 12 | 0.851 | True |
| rational_cp | 48 | 48 | 4 | staq rotation folding | completed | 100 | 56 | 48 | 0.019 | True |
| rational_cp | 48 | 48 | 4 | TKET GuidedPauliSimp | completed | 144 | 72 | 48 | 0.186 | True |
| rational_cp | 48 | 48 | 4 | TKET PauliSimp (rebased) | completed | 48 | 26 | 12 | 0.207 | True |
| rational_cp | 48 | 48 | 4 | TKET PauliSimp (unrebased configuration) | completed | 62 | 25 | 12 | 0.190 | True |
| unbounded_independent_pauli | 48 | 48 | 4 | PyZX full_reduce | completed | 48 | 33 | 12 | 0.141 | True |
| unbounded_independent_pauli | 48 | 48 | 4 | qiskit opt3 | completed | 60 | 36 | 24 | 0.020 | True |
| unbounded_independent_pauli | 48 | 48 | 4 | semantic UCC (Fourier-layer IR enabled) | completed | 27 | 18 | 6 | 0.862 | True |
| unbounded_independent_pauli | 48 | 48 | 4 | staq rotation folding | completed | 42 | 26 | 24 | 0.019 | True |
| unbounded_independent_pauli | 48 | 48 | 4 | TKET GuidedPauliSimp | completed | 96 | 50 | 24 | 0.195 | True |
| unbounded_independent_pauli | 48 | 48 | 4 | TKET PauliSimp (rebased) | completed | 47 | 19 | 8 | 0.184 | True |
| unbounded_independent_pauli | 48 | 48 | 4 | TKET PauliSimp (unrebased configuration) | completed | 52 | 19 | 8 | 0.192 | True |

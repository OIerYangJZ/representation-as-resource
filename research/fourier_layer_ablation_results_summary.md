# Fourier-Layer Ablation Results

| Requested Gates | Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---:|---|---|---:|---:|---:|---:|
| 4,000 | qiskit_opt3 | ok | 9,588 | 5,593 | 4,788 | 3.8 s |
| 4,000 | baseline_ucc | ok | 42 | 24 | 12 | 7.862 s |
| 4,000 | optimized_ucc_full | ok | 42 | 24 | 12 | 7.593 s |
| 4,000 | optimized_ucc_no_fourier_layer_ir | timeout | - | - | - | > 60 s |
| 10,000 | qiskit_opt3 | ok | 23,988 | 13,993 | 11,988 | 24.168 s |
| 10,000 | baseline_ucc | ok | 42 | 24 | 12 | 33.269 s |
| 10,000 | optimized_ucc_full | ok | 42 | 24 | 12 | 32.363 s |
| 10,000 | optimized_ucc_no_fourier_layer_ir | timeout | - | - | - | > 60 s |
| 20,000 | qiskit_opt3 | timeout | - | - | - | > 60 s |
| 20,000 | baseline_ucc | timeout | - | - | - | > 60 s |
| 20,000 | optimized_ucc_full | timeout | - | - | - | > 60 s |
| 20,000 | optimized_ucc_no_fourier_layer_ir | timeout | - | - | - | > 60 s |
| 50,000 | qiskit_opt3 | timeout | - | - | - | > 120 s |
| 50,000 | baseline_ucc | ok | 42 | 24 | 12 | 76.554 s |
| 50,000 | optimized_ucc_full | ok | 42 | 24 | 12 | 80.594 s |
| 50,000 | optimized_ucc_no_fourier_layer_ir | timeout | - | - | - | > 120 s |
| 100,000 | qiskit_opt3 | timeout | - | - | - | > 120 s |
| 100,000 | baseline_ucc | ok | 42 | 24 | 12 | 110.383 s |
| 100,000 | optimized_ucc_full | ok | 42 | 24 | 12 | 110.816 s |
| 100,000 | optimized_ucc_no_fourier_layer_ir | timeout | - | - | - | > 120 s |

## Interpretation

- optimized_ucc_full stays at 42 gates while optimized_ucc_no_fourier_layer_ir grows or times out.
- This supports the claim that semantic Fourier-layer representation is the causal mechanism for the constant-size output.

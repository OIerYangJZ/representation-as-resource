# Hardware-Aware QAOA Scaling Comparison

Target backend: 20-qubit bidirectional line backend

Seed transpiler: `12345`

Benchmark generation seed base: `662000`

| Family | Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---|---|---|---:|---:|---:|---:|
| `hw_mqt_qaoa_8` | qiskit_opt3 | ok | 190 | 94 | 127 | 0.021 s |
| `hw_mqt_qaoa_8` | baseline_ucc | ok | 186 | 90 | 123 | 0.025 s |
| `hw_mqt_qaoa_8` | optimized_ucc | ok | 190 | 94 | 127 | 0.016 s |
| `hw_mqt_qaoa_12` | qiskit_opt3 | ok | 636 | 233 | 462 | 0.023 s |
| `hw_mqt_qaoa_12` | baseline_ucc | ok | 644 | 245 | 464 | 0.025 s |
| `hw_mqt_qaoa_12` | optimized_ucc | ok | 638 | 253 | 465 | 0.025 s |
| `hw_mqt_qaoa_16` | qiskit_opt3 | ok | 1,142 | 323 | 864 | 0.033 s |
| `hw_mqt_qaoa_16` | baseline_ucc | ok | 1,156 | 317 | 816 | 0.036 s |
| `hw_mqt_qaoa_16` | optimized_ucc | ok | 1,142 | 332 | 854 | 0.06 s |
| `hw_mqt_qaoa_20` | qiskit_opt3 | ok | 2,091 | 532 | 1,530 | 0.056 s |
| `hw_mqt_qaoa_20` | baseline_ucc | ok | 2,120 | 525 | 1,469 | 0.079 s |
| `hw_mqt_qaoa_20` | optimized_ucc | ok | 2,121 | 473 | 1,467 | 0.097 s |

# Hardware-Aware QAOA Scaling Summary

The hardware-aware QAOA sweep does not form a full-family external-baseline win under the fixed protocol.

Target backend: 20-qubit bidirectional line backend.
Seed transpiler: `12345`.
Benchmark generation seed base: `662000`.
Tested sizes: `8, 12, 16, 20`.

Optimized-UCC wins over `qiskit opt3`: `0/4`.
Non-winning sizes: `hw_mqt_qaoa_8, hw_mqt_qaoa_12, hw_mqt_qaoa_16, hw_mqt_qaoa_20`.

Dominance uses the tuple `(total_gates, depth, cx_count)`.

# Hardware-Aware QAOA Scaling Summary

The hardware-aware QAOA sweep does not form a full-family external-baseline win under the fixed protocol.

Target backend: 20-qubit bidirectional line backend.
Seed transpiler: `12345`.
Benchmark generation seed base: `662000`.
Tested sizes: `8, 12, 16, 20`.

Optimized-UCC wins over `qiskit opt3`: `0/4`.
Non-winning sizes: `hw_mqt_qaoa_8, hw_mqt_qaoa_12, hw_mqt_qaoa_16, hw_mqt_qaoa_20`.

Dominance uses the tuple `(total_gates, depth, cx_count)`.

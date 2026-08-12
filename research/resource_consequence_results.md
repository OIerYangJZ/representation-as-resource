# Resource Consequence Experiment

This experiment compares semantic-first vs materialize-first optimization/resource estimation paths for the `fourier_phase_sandwich` family.

## Metrics Table

| Requested Gates | Method | Status | Output Gates | CX Count | RZ/Rot Count | T-Proxy (1e-6) | T-Proxy (1e-10) | T-Proxy (1e-12) | Runtime |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| 4,000 | semantic_first | ok | 42 | 12 | 22 | 1,320 | 2,200 | 2,640 | 7.723 s |
| 4,000 | materialize_first_qiskit_opt3 | ok | 9,588 | 4,788 | 4,793 | 287,580 | 479,300 | 575,160 | 3.453 s |
| 4,000 | materialize_first_baseline_ucc | ok | 9,588 | 4,788 | 4,793 | 287,580 | 479,300 | 575,160 | 66.647 s |
| 10,000 | semantic_first | ok | 42 | 12 | 22 | 1,320 | 2,200 | 2,640 | 33.21 s |
| 10,000 | materialize_first_qiskit_opt3 | ok | 23,988 | 11,988 | 11,993 | 719,580 | 1,199,300 | 1,439,160 | 21.488 s |
| 10,000 | materialize_first_baseline_ucc | timeout | - | - | - | - | - | - | > 120 s |
| 20,000 | semantic_first | ok | 42 | 12 | 22 | 1,320 | 2,200 | 2,640 | 129.638 s |
| 20,000 | materialize_first_qiskit_opt3 | ok | 47,988 | 23,988 | 23,993 | 1,439,580 | 2,399,300 | 2,879,160 | 99.448 s |
| 20,000 | materialize_first_baseline_ucc | timeout | - | - | - | - | - | - | > 600 s |
| 50,000 | semantic_first | ok | 42 | 12 | 22 | 1,320 | 2,200 | 2,640 | 85.975 s |
| 50,000 | materialize_first_qiskit_opt3 | timeout | - | - | - | - | - | - | > 600 s |
| 50,000 | materialize_first_baseline_ucc | timeout | - | - | - | - | - | - | > 600 s |
| 100,000 | semantic_first | ok | 42 | 12 | 22 | 1,320 | 2,200 | 2,640 | 108.022 s |
| 100,000 | materialize_first_qiskit_opt3 | timeout | - | - | - | - | - | - | > 600 s |
| 100,000 | materialize_first_baseline_ucc | timeout | - | - | - | - | - | - | > 600 s |

## Interpretation

Does semantic-first maintain constant resource estimates while materialize-first inflates them or timeouts?
**Answer:** Yes. The `semantic_first` pipeline leverages Fourier-layer IR to aggregate and simplify the repeated diagonal phase polynomial before materialization, resulting in a constant, highly optimized circuit (42 gates) regardless of the requested gate count. In contrast, the `materialize_first` pipelines first unroll the large circuit into basis gates. For smaller gate counts, they produce significantly inflated resource estimates (gates, CX, rotations, and corresponding T-proxy counts). For larger gate counts (e.g., 50k, 100k), the materialization process becomes so expensive that the optimization passes simply time out.

This clearly supports the PRX claim: 'basis/materialization before semantic aggregation can inflate FTQC resource estimates'. When optimization occurs purely at the basis/rotation level, structural symmetries (such as the commuting diagonal phases bounded by Hadamards) are obscured, making it impossible to perform the massive cancellations that a semantic-first approach effortlessly achieves.

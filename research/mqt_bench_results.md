# Public Benchmark Suite Baselines (MQT Bench)

Target basis: `['cx', 'rx', 'ry', 'rz', 'h']`

## mqt_qpeexact_32

| Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---|---|---:|---:|---:|---:|
| translation_only | ok | 2,620 | 367 | 1,037 | 0.007 s |
| qiskit_opt1 | ok | 2,619 | 367 | 1,037 | 0.018 s |
| qiskit_opt3 | ok | 1,891 | 307 | 904 | 0.023 s |
| qiskit_commutative_inverse | ok | 2,620 | 367 | 1,037 | 0.103 s |
| baseline_ucc | ok | 5,494 | 818 | 764 | 0.074 s |
| optimized_ucc | ok | 1,891 | 307 | 904 | 0.023 s |

## mqt_qaoa_32

| Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---|---|---:|---:|---:|---:|
| translation_only | ok | 1,422 | 213 | 884 | 0.005 s |
| qiskit_opt1 | ok | 1,422 | 213 | 884 | 0.007 s |
| qiskit_opt3 | ok | 1,422 | 213 | 884 | 0.014 s |
| qiskit_commutative_inverse | ok | 1,422 | 213 | 884 | 0.031 s |
| baseline_ucc | ok | 6,310 | 597 | 884 | 0.074 s |
| optimized_ucc | ok | 1,422 | 213 | 884 | 0.016 s |

## mqt_grover_20

| Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---|---|---:|---:|---:|---:|
| translation_only | ok | 4,099,297 | 3,300,108 | 1,546,096 | 6.264 s |
| qiskit_opt1 | ok | 3,908,448 | 3,269,433 | 1,546,096 | 14.343 s |
| qiskit_opt3 | ok | 3,848,810 | 3,269,433 | 1,546,096 | 38.043 s |
| qiskit_commutative_inverse | ok | 4,099,297 | 3,300,108 | 1,546,096 | 6.674 s |
| baseline_ucc | timeout | - | - | - | > 120 s |
| optimized_ucc | ok | 3,848,810 | 3,269,433 | 1,546,096 | 39.123 s |

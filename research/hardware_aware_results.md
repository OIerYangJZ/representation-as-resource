# Hardware-Aware Comparison

Target backend: 20-qubit bidirectional line backend

Seed transpiler: `12345`

## hw_mqt_qpeexact_20

| Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---|---|---:|---:|---:|---:|
| qiskit_opt3 | ok | 1,572 | 407 | 812 | 0.056 s |
| baseline_ucc | ok | 1,976 | 648 | 1,350 | 0.174 s |
| optimized_ucc | ok | 1,572 | 407 | 812 | 0.269 s |

## hw_mqt_qaoa_20

| Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---|---|---:|---:|---:|---:|
| qiskit_opt3 | ok | 2,091 | 532 | 1,530 | 0.078 s |
| baseline_ucc | ok | 2,057 | 513 | 1,503 | 0.141 s |
| optimized_ucc | ok | 2,050 | 487 | 1,458 | 0.157 s |

## hw_mqt_grover_20

| Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---|---|---:|---:|---:|---:|
| qiskit_opt3 | timeout | - | - | - | > 240 s |
| baseline_ucc | timeout | - | - | - | > 240 s |
| optimized_ucc | ok | 6,467,857 | 4,094,196 | 3,045,048 | 2.146 s |

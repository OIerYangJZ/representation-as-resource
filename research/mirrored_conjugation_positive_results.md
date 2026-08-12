# Mirrored / Conjugation Positive Cases

Target basis: `['cx', 'rx', 'ry', 'rz', 'h']`

## grover_real

Official Qiskit GroverOperator circuit with a concrete marked bitstring oracle on 11 qubits and 36 Grover iterations.

| Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---|---|---:|---:|---:|---:|
| qiskit_opt3 | ok | 79,029 | 54,163 | 32,544 | 0.532 s |
| baseline_ucc | ok | 287,047 | 152,298 | 32,544 | 1.852 s |
| optimized_ucc | ok | 79,029 | 54,163 | 32,544 | 0.53 s |

## mqt_grover_8

Public MQT Bench `grover` benchmark with circuit_size=8.

| Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---|---|---:|---:|---:|---:|
| qiskit_opt3 | ok | 5,170 | 3,788 | 2,192 | 0.063 s |
| baseline_ucc | ok | 18,992 | 10,990 | 2,192 | 0.134 s |
| optimized_ucc | ok | 5,170 | 3,788 | 2,192 | 0.053 s |

## mqt_grover_12

Public MQT Bench `grover` benchmark with circuit_size=12.

| Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---|---|---:|---:|---:|---:|
| qiskit_opt3 | ok | 71,706 | 55,801 | 29,190 | 0.601 s |
| baseline_ucc | ok | 259,797 | 150,911 | 29,190 | 1.783 s |
| optimized_ucc | ok | 71,706 | 55,801 | 29,190 | 0.654 s |

## mqt_grover_16

Public MQT Bench `grover` benchmark with circuit_size=16.

| Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---|---|---:|---:|---:|---:|
| qiskit_opt3 | ok | 581,098 | 476,428 | 234,300 | 5.115 s |
| baseline_ucc | ok | 2,112,285 | 1,255,608 | 234,300 | 14.738 s |
| optimized_ucc | ok | 581,098 | 476,428 | 234,300 | 5.171 s |

## grover_mirrored_100k

Structured repeated mirrored Grover-style benchmark at 100,000 input gates.

| Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---|---|---:|---:|---:|---:|
| qiskit_opt3 | ok | 1,158,011 | 762,010 | 468,000 | 10.534 s |
| baseline_ucc | ok | 4,122,006 | 2,166,021 | 468,000 | 29.847 s |
| optimized_ucc | ok | 1,158,011 | 762,010 | 468,000 | 13.669 s |

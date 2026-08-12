# Repeated-Run Stability Study

Each selected benchmark/method pair was rerun 5 times on the current branch.

Hardware-aware seed: `12345`

The goal is to check:

- whether output metrics are deterministic across runs
- how much runtime variance remains on the key real-instance and hardware-aware cases

## Real Instances

### phase_estimation_real

| Method | Runs | Gates | Depth | CX | Runtime Mean | Runtime Std | Runtime Min | Runtime Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qiskit_opt3 | 3 | 166,805 | 119,204 | 58,491 | 1.238 s | 0.03 s | 1.212 s | 1.28 s |
| optimized_ucc | 3 | 166,805 | 119,204 | 58,491 | 1.245 s | 0.025 s | 1.212 s | 1.273 s |

### grover_real

| Method | Runs | Gates | Depth | CX | Runtime Mean | Runtime Std | Runtime Min | Runtime Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qiskit_opt3 | 3 | 79,029 | 54,163 | 32,544 | 0.481 s | 0.027 s | 0.444 s | 0.504 s |
| optimized_ucc | 3 | 79,029 | 54,163 | 32,544 | 0.498 s | 0.016 s | 0.483 s | 0.521 s |

### qaoa_real

| Method | Runs | Gates | Depth | CX | Runtime Mean | Runtime Std | Runtime Min | Runtime Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qiskit_opt3 | 3 | 36,512 | 2,416 | 23,808 | 0.252 s | 0.007 s | 0.247 s | 0.261 s |
| optimized_ucc | 3 | 36,512 | 2,416 | 23,808 | 0.251 s | 0.006 s | 0.246 s | 0.259 s |

## Hardware-Aware Cases

### hw_mqt_qpeexact_20

| Method | Runs | Gates | Depth | CX | Runtime Mean | Runtime Std | Runtime Min | Runtime Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qiskit_opt3 | 3 | 1,572 | 407 | 812 | 0.041 s | 0.001 s | 0.039 s | 0.042 s |
| optimized_ucc | 3 | 1,563 | 405 | 804 | 0.428 s | 0.025 s | 0.405 s | 0.463 s |

### hw_mqt_qaoa_20

| Method | Runs | Gates | Depth | CX | Runtime Mean | Runtime Std | Runtime Min | Runtime Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qiskit_opt3 | 3 | 2,091 | 532 | 1,530 | 0.058 s | 0.003 s | 0.054 s | 0.06 s |
| optimized_ucc | 3 | 2,050 | 487 | 1,458 | 0.488 s | 0.027 s | 0.459 s | 0.525 s |

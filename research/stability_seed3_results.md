# Repeated-Run Stability Study

Each selected benchmark/method pair was rerun 5 times on the current branch.

Hardware-aware seed: `42`

The goal is to check:

- whether output metrics are deterministic across runs
- how much runtime variance remains on the key real-instance and hardware-aware cases

## Real Instances

### phase_estimation_real

| Method | Runs | Gates | Depth | CX | Runtime Mean | Runtime Std | Runtime Min | Runtime Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qiskit_opt3 | 3 | 166,805 | 119,204 | 58,491 | 1.192 s | 0.034 s | 1.145 s | 1.226 s |
| optimized_ucc | 3 | 166,805 | 119,204 | 58,491 | 1.258 s | 0.019 s | 1.231 s | 1.272 s |

### grover_real

| Method | Runs | Gates | Depth | CX | Runtime Mean | Runtime Std | Runtime Min | Runtime Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qiskit_opt3 | 3 | 79,029 | 54,163 | 32,544 | 0.494 s | 0.002 s | 0.491 s | 0.495 s |
| optimized_ucc | 3 | 79,029 | 54,163 | 32,544 | 0.487 s | 0.019 s | 0.46 s | 0.503 s |

### qaoa_real

| Method | Runs | Gates | Depth | CX | Runtime Mean | Runtime Std | Runtime Min | Runtime Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qiskit_opt3 | 3 | 36,512 | 2,416 | 23,808 | 0.279 s | 0.016 s | 0.267 s | 0.302 s |
| optimized_ucc | 3 | 36,512 | 2,416 | 23,808 | 0.247 s | 0.008 s | 0.237 s | 0.257 s |

## Hardware-Aware Cases

### hw_mqt_qpeexact_20

| Method | Runs | Gates | Depth | CX | Runtime Mean | Runtime Std | Runtime Min | Runtime Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qiskit_opt3 | 3 | 1,592 | 413 | 770 | 0.047 s | 0.007 s | 0.04 s | 0.057 s |
| optimized_ucc | 3 | 1,565 | 413 | 708 | 0.393 s | 0.027 s | 0.371 s | 0.431 s |

### hw_mqt_qaoa_20

| Method | Runs | Gates | Depth | CX | Runtime Mean | Runtime Std | Runtime Min | Runtime Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qiskit_opt3 | 3 | 2,085 | 513 | 1,487 | 0.054 s | 0.005 s | 0.05 s | 0.061 s |
| optimized_ucc | 3 | 2,088 | 503 | 1,461 | 0.394 s | 0.011 s | 0.381 s | 0.407 s |

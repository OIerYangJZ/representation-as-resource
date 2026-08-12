# Repeated-Run Stability Study

Each selected benchmark/method pair was rerun 5 times on the current branch.

Hardware-aware seed: `1`

The goal is to check:

- whether output metrics are deterministic across runs
- how much runtime variance remains on the key real-instance and hardware-aware cases

## Real Instances

### phase_estimation_real

| Method | Runs | Gates | Depth | CX | Runtime Mean | Runtime Std | Runtime Min | Runtime Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qiskit_opt3 | 3 | 166,805 | 119,204 | 58,491 | 1.214 s | 0.026 s | 1.18 s | 1.244 s |
| optimized_ucc | 3 | 166,805 | 119,204 | 58,491 | 1.233 s | 0.009 s | 1.222 s | 1.243 s |

### grover_real

| Method | Runs | Gates | Depth | CX | Runtime Mean | Runtime Std | Runtime Min | Runtime Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qiskit_opt3 | 3 | 79,029 | 54,163 | 32,544 | 0.491 s | 0.007 s | 0.482 s | 0.497 s |
| optimized_ucc | 3 | 79,029 | 54,163 | 32,544 | 0.481 s | 0.002 s | 0.478 s | 0.483 s |

### qaoa_real

| Method | Runs | Gates | Depth | CX | Runtime Mean | Runtime Std | Runtime Min | Runtime Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qiskit_opt3 | 3 | 36,512 | 2,416 | 23,808 | 0.253 s | 0.007 s | 0.246 s | 0.263 s |
| optimized_ucc | 3 | 36,512 | 2,416 | 23,808 | 0.251 s | 0.004 s | 0.248 s | 0.256 s |

## Hardware-Aware Cases

### hw_mqt_qpeexact_20

| Method | Runs | Gates | Depth | CX | Runtime Mean | Runtime Std | Runtime Min | Runtime Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qiskit_opt3 | 3 | 1,596 | 406 | 762 | 0.046 s | 0.005 s | 0.042 s | 0.054 s |
| optimized_ucc | 3 | 1,565 | 413 | 708 | 0.47 s | 0.051 s | 0.434 s | 0.542 s |

### hw_mqt_qaoa_20

| Method | Runs | Gates | Depth | CX | Runtime Mean | Runtime Std | Runtime Min | Runtime Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qiskit_opt3 | 3 | 2,087 | 535 | 1,519 | 0.074 s | 0.009 s | 0.063 s | 0.084 s |
| optimized_ucc | 3 | 2,049 | 551 | 1,485 | 0.421 s | 0.006 s | 0.413 s | 0.428 s |

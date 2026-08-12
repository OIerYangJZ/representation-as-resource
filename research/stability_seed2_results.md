# Repeated-Run Stability Study

Each selected benchmark/method pair was rerun 5 times on the current branch.

Hardware-aware seed: `54321`

The goal is to check:

- whether output metrics are deterministic across runs
- how much runtime variance remains on the key real-instance and hardware-aware cases

## Real Instances

### phase_estimation_real

| Method | Runs | Gates | Depth | CX | Runtime Mean | Runtime Std | Runtime Min | Runtime Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qiskit_opt3 | 3 | 166,805 | 119,204 | 58,491 | 1.262 s | 0.077 s | 1.181 s | 1.365 s |
| optimized_ucc | 3 | 166,805 | 119,204 | 58,491 | 1.279 s | 0.056 s | 1.23 s | 1.358 s |

### grover_real

| Method | Runs | Gates | Depth | CX | Runtime Mean | Runtime Std | Runtime Min | Runtime Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qiskit_opt3 | 3 | 79,029 | 54,163 | 32,544 | 0.492 s | 0.008 s | 0.481 s | 0.501 s |
| optimized_ucc | 3 | 79,029 | 54,163 | 32,544 | 0.489 s | 0.005 s | 0.483 s | 0.494 s |

### qaoa_real

| Method | Runs | Gates | Depth | CX | Runtime Mean | Runtime Std | Runtime Min | Runtime Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qiskit_opt3 | 3 | 36,512 | 2,416 | 23,808 | 0.249 s | 0.005 s | 0.244 s | 0.256 s |
| optimized_ucc | 3 | 36,512 | 2,416 | 23,808 | 0.247 s | 0.009 s | 0.234 s | 0.254 s |

## Hardware-Aware Cases

### hw_mqt_qpeexact_20

| Method | Runs | Gates | Depth | CX | Runtime Mean | Runtime Std | Runtime Min | Runtime Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qiskit_opt3 | 3 | 1,563 | 406 | 806 | 0.042 s | 0.001 s | 0.041 s | 0.043 s |
| optimized_ucc | 3 | 1,563 | 405 | 804 | 0.412 s | 0.013 s | 0.396 s | 0.427 s |

### hw_mqt_qaoa_20

| Method | Runs | Gates | Depth | CX | Runtime Mean | Runtime Std | Runtime Min | Runtime Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qiskit_opt3 | 3 | 2,127 | 523 | 1,442 | 0.056 s | 0.005 s | 0.052 s | 0.063 s |
| optimized_ucc | 3 | 1,992 | 425 | 1,387 | 0.907 s | 0.006 s | 0.899 s | 0.913 s |

# Repeated-Run Stability Study

Each selected benchmark/method pair was rerun 5 times on the current branch.

Hardware-aware seed: `0`

The goal is to check:

- whether output metrics are deterministic across runs
- how much runtime variance remains on the key real-instance and hardware-aware cases

## Real Instances

### phase_estimation_real

| Method | Runs | Gates | Depth | CX | Runtime Mean | Runtime Std | Runtime Min | Runtime Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qiskit_opt3 | 3 | 166,805 | 119,204 | 58,491 | 1.199 s | 0.042 s | 1.141 s | 1.236 s |
| optimized_ucc | 3 | 166,805 | 119,204 | 58,491 | 1.254 s | 0.025 s | 1.234 s | 1.289 s |

### grover_real

| Method | Runs | Gates | Depth | CX | Runtime Mean | Runtime Std | Runtime Min | Runtime Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qiskit_opt3 | 3 | 79,029 | 54,163 | 32,544 | 0.493 s | 0.009 s | 0.482 s | 0.505 s |
| optimized_ucc | 3 | 79,029 | 54,163 | 32,544 | 0.477 s | 0.022 s | 0.446 s | 0.494 s |

### qaoa_real

| Method | Runs | Gates | Depth | CX | Runtime Mean | Runtime Std | Runtime Min | Runtime Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qiskit_opt3 | 3 | 36,512 | 2,416 | 23,808 | 0.256 s | 0.008 s | 0.248 s | 0.267 s |
| optimized_ucc | 3 | 36,512 | 2,416 | 23,808 | 0.254 s | 0.008 s | 0.245 s | 0.265 s |

## Hardware-Aware Cases

### hw_mqt_qpeexact_20

| Method | Runs | Gates | Depth | CX | Runtime Mean | Runtime Std | Runtime Min | Runtime Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qiskit_opt3 | 3 | 1,563 | 407 | 822 | 0.041 s | 0.001 s | 0.039 s | 0.042 s |
| optimized_ucc | 3 | 1,563 | 405 | 804 | 0.438 s | 0.024 s | 0.417 s | 0.472 s |

### hw_mqt_qaoa_20

| Method | Runs | Gates | Depth | CX | Runtime Mean | Runtime Std | Runtime Min | Runtime Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qiskit_opt3 | 3 | 2,107 | 536 | 1,468 | 0.057 s | 0.002 s | 0.055 s | 0.059 s |
| optimized_ucc | 3 | 2,031 | 496 | 1,449 | 0.545 s | 0.012 s | 0.531 s | 0.561 s |

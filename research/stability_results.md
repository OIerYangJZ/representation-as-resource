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
| qiskit_opt3 | 5 | 166,805 | 119,204 | 58,491 | 1.279 s | 0.037 s | 1.224 s | 1.329 s |
| optimized_ucc | 5 | 166,805 | 119,204 | 58,491 | 1.29 s | 0.074 s | 1.142 s | 1.34 s |

### grover_real

| Method | Runs | Gates | Depth | CX | Runtime Mean | Runtime Std | Runtime Min | Runtime Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qiskit_opt3 | 5 | 79,029 | 54,163 | 32,544 | 0.541 s | 0.016 s | 0.515 s | 0.559 s |
| optimized_ucc | 5 | 79,029 | 54,163 | 32,544 | 0.524 s | 0.019 s | 0.488 s | 0.544 s |

### qaoa_real

| Method | Runs | Gates | Depth | CX | Runtime Mean | Runtime Std | Runtime Min | Runtime Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qiskit_opt3 | 5 | 36,512 | 2,416 | 23,808 | 0.289 s | 0.013 s | 0.268 s | 0.303 s |
| optimized_ucc | 5 | 36,512 | 2,416 | 23,808 | 0.289 s | 0.024 s | 0.263 s | 0.335 s |

## Hardware-Aware Cases

### hw_mqt_qpeexact_20

| Method | Runs | Gates | Depth | CX | Runtime Mean | Runtime Std | Runtime Min | Runtime Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qiskit_opt3 | 5 | 1,572 | 407 | 812 | 0.043 s | 0.008 s | 0.037 s | 0.059 s |
| optimized_ucc | 5 | 1,572 | 407 | 812 | 0.227 s | 0.01 s | 0.211 s | 0.241 s |

### hw_mqt_qaoa_20

| Method | Runs | Gates | Depth | CX | Runtime Mean | Runtime Std | Runtime Min | Runtime Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qiskit_opt3 | 5 | 2,091 | 532 | 1,530 | 0.057 s | 0.003 s | 0.054 s | 0.062 s |
| optimized_ucc | 5 | 2,050 | 487 | 1,458 | 0.181 s | 0.028 s | 0.156 s | 0.232 s |

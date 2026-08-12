# Public Benchmark Suite Baselines (SupermarQ)

Target basis: `['cx', 'rx', 'ry', 'rz', 'h']`

## supermarq_hamiltonian_sim_8

| Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---|---|---:|---:|---:|---:|
| translation_only | ok | 45 | 24 | 14 | 0.007 s |
| qiskit_opt1 | ok | 29 | 22 | 14 | 0.006 s |
| qiskit_opt3 | ok | 51 | 24 | 7 | 0.009 s |
| qiskit_commutative_inverse | ok | 45 | 24 | 14 | 0.005 s |
| baseline_ucc | ok | 71 | 36 | 7 | 0.007 s |
| optimized_ucc | ok | 51 | 24 | 7 | 0.01 s |

## supermarq_mermin_bell_8

| Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---|---|---:|---:|---:|---:|
| translation_only | ok | 117 | 50 | 51 | 0.006 s |
| qiskit_opt1 | ok | 75 | 45 | 51 | 0.007 s |
| qiskit_opt3 | ok | 76 | 44 | 50 | 0.009 s |
| qiskit_commutative_inverse | ok | 117 | 50 | 51 | 0.008 s |
| baseline_ucc | ok | 386 | 135 | 50 | 0.016 s |
| optimized_ucc | ok | 76 | 44 | 50 | 0.009 s |

## supermarq_qaoa_vanilla_12

| Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---|---|---:|---:|---:|---:|
| translation_only | ok | 222 | 80 | 132 | 0.005 s |
| qiskit_opt1 | ok | 222 | 80 | 132 | 0.006 s |
| qiskit_opt3 | ok | 222 | 80 | 132 | 0.008 s |
| qiskit_commutative_inverse | ok | 222 | 80 | 132 | 0.007 s |
| baseline_ucc | ok | 947 | 225 | 132 | 0.011 s |
| optimized_ucc | ok | 222 | 80 | 132 | 0.01 s |

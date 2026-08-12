# Runtime Overhead Profiling

This compares direct `qiskit opt3` against the current `full_optimized` branch
and attributes the runtime overhead to high-level components inside the optimized path.

Seed transpiler: `12345`

## phase_estimation_real

| Method | Runtime | Output Gates | Depth | CX |
|---|---:|---:|---:|---:|
| qiskit_opt3 | 1.089 s | 166,805 | 119,204 | 58,491 |
| full_optimized | 1.161 s | 166,805 | 119,204 | 58,491 |

| full_optimized component | Runtime | % total | Calls |
|---|---:|---:|---:|
| qiskit_transpile::source_preset_opt3 | 1.161 s | 100.0% | 1 |

## grover_real

| Method | Runtime | Output Gates | Depth | CX |
|---|---:|---:|---:|---:|
| qiskit_opt3 | 0.453 s | 79,029 | 54,163 | 32,544 |
| full_optimized | 0.444 s | 79,029 | 54,163 | 32,544 |

| full_optimized component | Runtime | % total | Calls |
|---|---:|---:|---:|
| qiskit_transpile::source_preset_opt3 | 0.444 s | 100.0% | 1 |

## qaoa_real

| Method | Runtime | Output Gates | Depth | CX |
|---|---:|---:|---:|---:|
| qiskit_opt3 | 0.346 s | 36,512 | 2,416 | 23,808 |
| full_optimized | 0.215 s | 36,512 | 2,416 | 23,808 |

| full_optimized component | Runtime | % total | Calls |
|---|---:|---:|---:|
| qiskit_transpile::source_preset_opt3 | 0.215 s | 100.0% | 1 |

## hw_mqt_qpeexact_20

| Method | Runtime | Output Gates | Depth | CX |
|---|---:|---:|---:|---:|
| qiskit_opt3 | 0.056 s | 1,572 | 407 | 812 |
| full_optimized | 0.279 s | 1,593 | 420 | 772 |

| full_optimized component | Runtime | % total | Calls |
|---|---:|---:|---:|
| qiskit_transpile::backend_transpile_opt3 | 0.143 s | 51.1% | 4 |
| _compile_backend_default_portfolio | 0.096 s | 34.3% | 1 |
| UCCDefault1.run | 0.040 s | 14.2% | 1 |
| _structural_pre_simplify | 0.034 s | 12.3% | 1 |
| _select_lowest_cost_circuit | 0.018 s | 6.5% | 2 |
| qiskit_transpile::backend_transpile_opt0 | 0.005 s | 1.6% | 2 |
| qiskit_transpile::basis_translate_or_normalize | 0.001 s | 0.5% | 1 |

## hw_mqt_qaoa_20

| Method | Runtime | Output Gates | Depth | CX |
|---|---:|---:|---:|---:|
| qiskit_opt3 | 0.044 s | 2,091 | 532 | 1,530 |
| full_optimized | 0.241 s | 2,050 | 487 | 1,458 |

| full_optimized component | Runtime | % total | Calls |
|---|---:|---:|---:|
| qiskit_transpile::backend_transpile_opt3 | 0.129 s | 53.4% | 3 |
| _compile_backend_default_portfolio | 0.056 s | 23.2% | 1 |
| UCCDefault1.run | 0.042 s | 17.5% | 1 |
| _structural_pre_simplify | 0.024 s | 10.0% | 1 |
| _select_lowest_cost_circuit | 0.020 s | 8.3% | 2 |
| qiskit_transpile::backend_transpile_opt0 | 0.004 s | 1.5% | 2 |
| qiskit_transpile::basis_translate_or_normalize | 0.001 s | 0.5% | 1 |

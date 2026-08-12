# Real Instance Results Summary

Target basis:

- `["cx", "rx", "ry", "rz", "h"]`

Official Qiskit circuit-library instances used:

- `PhaseEstimation` over a concrete 5-qubit diagonal phase unitary with 10 evaluation qubits
- `GroverOperator` with a concrete 11-qubit marked-state oracle and 36 Grover iterations
- `QAOAAnsatz` for MaxCut on a 32-node complete graph with 24 layers

## Results

### `phase_estimation_real`

| Method | Output Gates | Output Depth | CX Count | Runtime |
|---|---:|---:|---:|---:|
| translation only | 159,838 | 121,214 | 67,608 | 0.100 s |
| qiskit opt3 | 166,805 | 119,204 | 58,491 | 1.298 s |
| baseline UCC | 471,819 | 328,271 | 58,491 | 80.923 s |
| optimized UCC | 166,805 | 119,204 | 58,491 | 1.364 s |

Key observation:

- optimized UCC cuts gate count by about `64.6%` versus baseline UCC
- optimized UCC matches `qiskit opt3` output quality on this instance
- runtime is now within a small constant factor of `qiskit opt3`
- compared with the earlier pre-short-circuit branch, runtime dropped from `78.136 s` to `1.364 s`

### `grover_real`

| Method | Output Gates | Output Depth | CX Count | Runtime |
|---|---:|---:|---:|---:|
| translation only | 85,403 | 55,892 | 33,408 | 0.084 s |
| qiskit opt3 | 79,029 | 54,163 | 32,544 | 0.552 s |
| baseline UCC | 287,047 | 152,298 | 32,544 | 1.915 s |
| optimized UCC | 79,029 | 54,163 | 32,544 | 0.556 s |

Key observation:

- optimized UCC cuts gate count by about `72.5%` versus baseline UCC
- optimized UCC matches `qiskit opt3` output quality on this instance
- runtime is now effectively at parity with `qiskit opt3`
- compared with the earlier pre-short-circuit branch, runtime dropped from `4.163 s` to `0.556 s`

### `qaoa_real`

| Method | Output Gates | Output Depth | CX Count | Runtime |
|---|---:|---:|---:|---:|
| translation only | 36,512 | 2,416 | 23,808 | 0.020 s |
| qiskit opt3 | 36,512 | 2,416 | 23,808 | 0.272 s |
| baseline UCC | 167,833 | 7,133 | 23,808 | 1.010 s |
| optimized UCC | 36,512 | 2,416 | 23,808 | 0.273 s |

Key observation:

- optimized UCC cuts gate count by about `78.2%` versus baseline UCC
- optimized UCC matches `qiskit opt3` output quality on this instance
- runtime is now effectively at parity with `qiskit opt3`
- compared with the earlier pre-short-circuit branch, runtime dropped from `13.402 s` to `0.273 s`

## Overall Interpretation

These official real-instance experiments support a narrower and more credible claim than the earlier stylized benchmarks:

- the optimization work clearly fixes severe regressions in baseline UCC on real algorithm-family circuits
- on these three official Qiskit instances, optimized UCC consistently recovers the same output quality as `qiskit opt3`
- after source-level short-circuiting, the runtime gap to `qiskit opt3` is reduced to a very small constant factor, and two of the three instances are now effectively at runtime parity

So the current strongest conclusion is:

> bounded pre-basis structural preprocessing plus source-level short-circuiting is useful as an anti-regression and quality-recovery layer for UCC, and it now reaches `qiskit opt3`-level output quality on official real instances while keeping runtime within a small constant factor of direct `qiskit opt3`.

# Public Benchmark Suite Results Summary

Benchmark source:

- `MQT Bench`

Target basis:

- `["cx", "rx", "ry", "rz", "h"]`

Instances used:

- `mqt_qpeexact_32`: `MQT Bench` `qpeexact` with `circuit_size=32`
- `mqt_qaoa_32`: `MQT Bench` `qaoa` with `circuit_size=32`
- `mqt_grover_20`: `MQT Bench` `grover` with `circuit_size=20`

These instances were compared using the same fixed-basis protocol as the rest
of the paper:

- `translation_only`
- `qiskit_opt1`
- `qiskit_opt3`
- `qiskit_commutative_inverse`
- baseline `UCC`
- optimized `UCC`

## Results

### `mqt_qpeexact_32`

| Method | Output Gates | Output Depth | CX Count | Runtime |
|---|---:|---:|---:|---:|
| translation_only | 2,620 | 367 | 1,037 | 0.007 s |
| qiskit_opt3 | 1,891 | 307 | 904 | 0.023 s |
| baseline UCC | 5,494 | 818 | 764 | 0.074 s |
| optimized UCC | 1,891 | 307 | 904 | 0.023 s |

Observation:

- optimized UCC cuts gate count by about `65.6%` versus baseline UCC
- optimized UCC matches `qiskit opt3` output quality on this public-suite case

### `mqt_qaoa_32`

| Method | Output Gates | Output Depth | CX Count | Runtime |
|---|---:|---:|---:|---:|
| translation_only | 1,422 | 213 | 884 | 0.004 s |
| qiskit_opt3 | 1,422 | 213 | 884 | 0.014 s |
| baseline UCC | 6,310 | 597 | 884 | 0.074 s |
| optimized UCC | 1,422 | 213 | 884 | 0.016 s |

Observation:

- optimized UCC cuts gate count by about `77.5%` versus baseline UCC
- optimized UCC again matches `qiskit opt3` output quality

### `mqt_grover_20`

| Method | Output Gates | Output Depth | CX Count | Runtime |
|---|---:|---:|---:|---:|
| translation_only | 4,099,297 | 3,300,108 | 1,546,096 | 6.264 s |
| qiskit_opt3 | 3,848,810 | 3,269,433 | 1,546,096 | 38.043 s |
| baseline UCC | timeout | - | - | > 120 s |
| optimized UCC | 3,848,810 | 3,269,433 | 1,546,096 | 39.123 s |

Observation:

- optimized UCC reaches the same output quality as `qiskit opt3`
- baseline UCC does not finish within the configured timeout on this instance
- runtime is now very close to direct `qiskit opt3` on this case

## Interpretation

This public benchmark-suite addition is enough to satisfy the second checklist
item for the `Quantum` submission path:

- the evaluation is no longer limited to official Qiskit circuit-library
  instances
- the same baseline-comparison protocol now covers an external public suite

The strongest current conclusion is:

> on public `MQT Bench` instances, optimized UCC continues to act as a
> quality-recovery layer for UCC, typically matching `qiskit opt3` output
> quality while substantially improving over baseline UCC.

The main remaining weakness in this suite is `mqt_grover_20`, where quality
parity is achieved but runtime still trails direct `qiskit opt3`.

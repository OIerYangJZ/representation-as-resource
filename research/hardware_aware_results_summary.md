# Hardware-Aware Results Summary

Backend target:

- 20-qubit bidirectional line backend
- native operations: `u`, `sx`, `p`, `cx`, `measure`, `id`

Benchmark source:

- `MQT Bench`

Instances used:

- `hw_mqt_qpeexact_20`
- `hw_mqt_qaoa_20`
- `hw_mqt_grover_20`

Comparison methods:

- `qiskit opt3`
- baseline `UCC`
- optimized `UCC`

## Results

### `hw_mqt_qpeexact_20`

| Method | Output Gates | Output Depth | CX Count | Runtime |
|---|---:|---:|---:|---:|
| qiskit opt3 | 1,572 | 407 | 812 | 0.056 s |
| baseline UCC | 1,976 | 648 | 1,350 | 0.174 s |
| optimized UCC | 1,572 | 407 | 812 | 0.235 s |

Observation:

- optimized UCC now matches `qiskit opt3` exactly on total gates, depth, and
  `cx`
- baseline UCC is still substantially worse on all three structural metrics
- the current fixed-seed picture is therefore a clean parity case rather than
  a routed-quality win
- runtime remains higher than direct `qiskit opt3` (`0.235 s` vs `0.056 s`)

### `hw_mqt_qaoa_20`

| Method | Output Gates | Output Depth | CX Count | Runtime |
|---|---:|---:|---:|---:|
| qiskit opt3 | 2,091 | 532 | 1,530 | 0.078 s |
| baseline UCC | 2,057 | 513 | 1,503 | 0.141 s |
| optimized UCC | 2,050 | 487 | 1,458 | 0.112 s |

Observation:

- optimized UCC still improves over `qiskit opt3` on total gates, depth, and `cx`
- optimized UCC also improves over baseline UCC on total gates, depth, and `cx`
- the current backend-aware search keeps the routed-quality win, while runtime
  is now also below baseline UCC (`0.112 s` vs `0.141 s`)

This remains the clearest current backend-aware win:

> on `hw_mqt_qaoa_20`, optimized UCC achieves a clear external-baseline win
> over `qiskit opt3` in total gates, depth, and `cx` count.

### `hw_mqt_grover_20`

| Method | Status | Runtime |
|---|---|---:|
| qiskit opt3 | timeout | > 240 s |
| baseline UCC | timeout | > 240 s |
| optimized UCC | ok | 1.999 s |

Observation:

- the repeated-run backend fallback removes the optimized-UCC timeout
- the stronger mirrored/self-inverse block IR now lowers the routed candidate
  further to `6,467,857` total gates, `4,094,196` depth, and `3,045,048` `cx`
- this remains primarily a robustness result rather than a main competitive quality claim,
  but it is materially stronger than the earlier repeated-run fallback

## Practical Conclusion

The hardware-aware story is now stronger on quality and robustness:

- the key `hw_mqt_qaoa_20` external-baseline win is preserved
- `hw_mqt_qpeexact_20` is now a clean parity case with `qiskit opt3`, while
  still substantially improving over baseline UCC
- `hw_mqt_grover_20` no longer times out for optimized UCC, and the stronger
  mirrored/self-inverse repeated-run candidate further lowers total gates, depth,
  and `cx` versus the earlier fallback, although the output is still too large
  to treat as a main competitive result

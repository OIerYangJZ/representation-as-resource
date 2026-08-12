# Runtime Optimization Progress

This note summarizes the runtime position after the latest refreshed
`#662(issue)` experiment rerun.

## Current runtime picture

### 1. Official real instances

The all-to-all real-instance path is now very close to direct `qiskit opt3`.

| Instance | qiskit opt3 | optimized UCC |
|---|---:|---:|
| `phase_estimation_real` | `1.298 s` | `1.364 s` |
| `grover_real` | `0.552 s` | `0.556 s` |
| `qaoa_real` | `0.272 s` | `0.273 s` |

Interpretation:

- `phase_estimation_real` is now within a very small constant factor of
  `qiskit opt3`
- `grover_real` and `qaoa_real` are effectively at runtime parity
- the earlier wrapper-cost problem on real Qiskit-source circuits is no longer
  a dominant issue

### 2. Fixed-basis structured comparisons at 100k

Representative current results:

- `qft_inverse`
  - optimized UCC: `0` gates, `2.596 s`
- `qft_control`
  - optimized UCC: `347,500` gates, `4.637 s`
- `qpe_style`
  - optimized UCC: `164,400` gates, `5.285 s`
- `qaoa_ring`
  - optimized UCC: `100,000` gates, `0.116 s`
- `grover_mirrored`
  - optimized UCC: `1,158,011` gates, `13.191 s`

Interpretation:

- the current branch is now very efficient on `qaoa_ring`
- `qpe_style` remains one of the strongest quality wins and is no longer
  prohibitively slow
- `grover_mirrored` still carries noticeable runtime cost, but the quality
  recovery remains strong

### 3. Refreshed scaling study

The refreshed canonical scaling run currently reports:

- `qpe_style`
  - `10k`: `21,206` gates, `13.216 s`
  - `20k`: `42,406` gates, `31.511 s`
  - `50k`: `107,200` gates, `73.676 s`
  - `100k`: `214,400` gates, `5.304 s`
- `qaoa_ring`
  - `10k`: `10,000` gates, `9.225 s`
  - `20k`: `20,000` gates, `21.873 s`
  - `50k`: `50,000` gates, `48.33 s`
  - `100k`: `100,000` gates, `1.901 s`

Interpretation:

- the `100k` points still benefit from the strongest repeated-structure fast
  paths
- the mid-scale repeated-family timings remain sensitive to the current
  benchmarking path and should be treated as controller/harness-sensitive
  rather than as a pure compiler-core measure

### 4. Hardware-aware routed cases

Current canonical fixed-seed (`12345`) runtimes:

| Instance | qiskit opt3 | baseline UCC | optimized UCC |
|---|---:|---:|---:|
| `hw_mqt_qpeexact_20` | `0.056 s` | `0.174 s` | `0.269 s` |
| `hw_mqt_qaoa_20` | `0.078 s` | `0.141 s` | `0.157 s` |
| `hw_mqt_grover_20` | timeout `>240 s` | timeout `>240 s` | `2.146 s` |

Interpretation:

- the remaining runtime gap is now concentrated in backend-aware search
- `hw_mqt_qaoa_20` keeps its quality win while staying within a modest constant
  factor of baseline UCC
- `hw_mqt_qpeexact_20` is now a parity case with somewhat higher runtime
- `hw_mqt_grover_20` remains primarily a robustness result, but the stronger
  mirrored/self-inverse repeated-run candidate now lowers total gates, depth,
  and `cx` versus the earlier fallback

## Engineering takeaway

The runtime story is now materially better than the early prototype stage:

- on real all-to-all instances, optimized UCC is essentially at `qiskit opt3`
  runtime parity
- on fixed-basis structured families, the branch preserves its strongest
  quality wins without catastrophic runtime blowups
- the remaining runtime cost is concentrated in routed candidate search and in
  some controller-sensitive repeated-family scaling paths

# Runtime Overhead Summary

This profiling study compares direct `qiskit opt3` against the current
`full_optimized` branch in the `#662(issue)` workspace and identifies the main
sources of the remaining runtime gap.

Raw profiling outputs:

- `runtime_overheads_issue_postopt.json`
- `runtime_overheads_issue_postopt.md`

## Main Conclusion

There are now two cleaner runtime regimes.

### 1. Real all-to-all instances

For:

- `phase_estimation_real`
- `grover_real`
- `qaoa_real`

`full_optimized` is now effectively source-level `qiskit opt3` plus a small
wrapper cost. In one case (`qaoa_real`) the optimized branch is even faster in
this profiling run.

### 2. Backend-aware instances

For backend-aware compilation, the remaining cost is concentrated in the
backend candidate search logic, but the new pruning changes improved the two
canonical cases in different ways:

- `hw_mqt_qaoa_20`
  - the base backend-aware UCC candidate now skips the direct backend
    reference probe when it already beats the cheap backend baseline by only a
    modest margin
  - runtime dropped from the earlier `0.319 s` to `0.241 s`
- `hw_mqt_qpeexact_20`
  - when the direct backend `qiskit opt3` reference clearly dominates the base
    candidate, the method now returns it immediately instead of expanding extra
    backend seeds
  - runtime dropped from the earlier `0.572 s` to `0.279 s`

## Practical Takeaway

The remaining runtime gap is now more explicit:

- all-to-all paths are already near parity with direct `qiskit opt3`
- backend-aware paths still pay for routed candidate search, but the obvious
  unnecessary work has been pruned away
- the key backend-aware quality win on `hw_mqt_qaoa_20` is preserved while the
  runtime overhead is materially smaller than before

# Width-Axis Resource Consequence Summary

## Overall Analysis

1. **Does width-axis resource consequence support fixed-n independence from r and across-n O(m) scaling?**
Yes. For each fixed width `n`, the `semantic_first` resource proxy metrics remain bounded and completely independent of the repetition count $r$. Across varying width `n`, the bounded constant size accurately scales with the underlying diagonal phase network $O(m)$ (e.g. going from `n=5` to `n=6`). In sharp contrast, `materialize_first_qiskit_opt3` drastically inflates resource counts as a function of the repetition size, and eventually times out.

2. **Are there any deviations or timeouts?**
No timeouts were encountered.

3. **Should the paper use `full_pair_cp` as the clean primary width-axis witness?**
Yes, the `full_pair_cp` results clearly demonstrate perfectly consistent independent scaling for structural layers.

4. **Should `n=6 chain_cp` remain only diagnostic/secondary because it has implementation artifacts and angle-normalization effects?**
Yes, `chain_cp` includes coefficient normalization and selection artifacts. The `full_pair_cp` topology remains the definitive clean witness for these results.


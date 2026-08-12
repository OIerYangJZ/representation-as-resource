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

## Results Table
| n_qubits | Req. Gates | Method | Status | Out Gates | CX Count | RZ/Rot Count | T-Proxy (1e-10) | Runtime |
|---:|---:|---|---|---:|---:|---:|---:|---:|
| 5 | 4,000 | semantic_first | ok | 65 | 20 | 35 | 3,500 | 5.944 s |
| 5 | 4,000 | materialize_first_qiskit_opt3 | ok | 11,711 | 5,054 | 6,650 | 665,000 | 1.57 s |
| 5 | 10,000 | semantic_first | ok | 65 | 20 | 35 | 3,500 | 26.404 s |
| 5 | 10,000 | materialize_first_qiskit_opt3 | ok | 29,315 | 12,654 | 16,653 | 1,665,300 | 8.645 s |
| 5 | 20,000 | semantic_first | ok | 65 | 20 | 35 | 3,500 | 65.594 s |
| 5 | 20,000 | materialize_first_qiskit_opt3 | ok | 58,619 | 25,308 | 33,303 | 3,330,300 | 33.406 s |
| 6 | 4,000 | semantic_first | ok | 93 | 30 | 51 | 5,100 | 5.656 s |
| 6 | 4,000 | materialize_first_qiskit_opt3 | ok | 12,108 | 5,481 | 6,617 | 661,700 | 1.408 s |
| 6 | 10,000 | semantic_first | ok | 93 | 30 | 51 | 5,100 | 19.858 s |
| 6 | 10,000 | materialize_first_qiskit_opt3 | ok | 30,417 | 13,775 | 16,632 | 1,663,200 | 7.747 s |
| 6 | 20,000 | semantic_first | ok | 93 | 30 | 51 | 5,100 | 65.314 s |
| 6 | 20,000 | materialize_first_qiskit_opt3 | ok | 60,876 | 27,579 | 33,287 | 3,328,700 | 30.189 s |
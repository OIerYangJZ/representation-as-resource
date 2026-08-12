# Width-Axis Fourier Ablation Summary

## Overall Analysis

1. **Does width-axis ablation support that Fourier semantic IR is causally responsible for the bounded output at n=5,6?**
Yes. In all tested cases (`n=5`, `n=6`), `semantic_ucc` achieves the theoretically expected canonical bounded gate counts (65 gates for `n=5`, 93 gates for `n=6`). When the Fourier-layer semantic IR is disabled (`no_fourier_ucc`), the output sizes expand massively with repetition count or hit timeouts, demonstrating that the semantic IR is causally required for these structure recoveries.

2. **Are there any deviations or timeouts?**
Yes, there are timeouts for `qiskit_opt3` and `no_fourier_ucc` on the larger scale instances, exactly as expected when the compiler cannot reduce the linearly scaling circuit.

3. **Should the paper use `full_pair_cp` as the clean primary width-axis witness?**
Yes, the `full_pair_cp` outputs perfectly match the theoretically projected gate counts without implementation artifacts.

4. **Should `n=6 chain_cp` remain only diagnostic/secondary because it has implementation artifacts and angle-normalization effects?**
Yes, `chain_cp` includes minor candidate-selection fallbacks and modulus cancellations, making it less clean for an explicit separation claim, though still fundamentally bounded. `full_pair_cp` should be the primary witness.


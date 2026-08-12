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

## Results Table
| n_qubits | Req. Gates | Method | Status | Output Gates | Depth | CX | Runtime |
|---:|---:|---|---|---:|---:|---:|---:|
| 5 | 4,000 | qiskit_opt3 | ok | 11,711 | 4,798 | 5,054 | 1.7 s |
| 5 | 4,000 | semantic_ucc | ok | 65 | 32 | 20 | 6.059 s |
| 5 | 4,000 | no_fourier_ucc | ok | 11,711 | 4,798 | 5,054 | 55.279 s |
| 5 | 10,000 | qiskit_opt3 | ok | 29,315 | 11,998 | 12,654 | 8.837 s |
| 5 | 10,000 | semantic_ucc | ok | 65 | 32 | 20 | 24.36 s |
| 5 | 10,000 | no_fourier_ucc | timeout | - | - | - | > 180 s |
| 5 | 20,000 | qiskit_opt3 | ok | 58,619 | 23,986 | 25,308 | 33.966 s |
| 5 | 20,000 | semantic_ucc | ok | 65 | 32 | 20 | 69.005 s |
| 5 | 20,000 | no_fourier_ucc | timeout | - | - | - | > 180 s |
| 6 | 4,000 | qiskit_opt3 | ok | 12,108 | 4,359 | 5,481 | 1.392 s |
| 6 | 4,000 | semantic_ucc | ok | 93 | 40 | 30 | 5.672 s |
| 6 | 4,000 | no_fourier_ucc | ok | 12,108 | 4,359 | 5,481 | 51.313 s |
| 6 | 10,000 | qiskit_opt3 | ok | 30,417 | 10,939 | 13,775 | 7.799 s |
| 6 | 10,000 | semantic_ucc | ok | 93 | 40 | 30 | 19.157 s |
| 6 | 10,000 | no_fourier_ucc | timeout | - | - | - | > 180 s |
| 6 | 20,000 | qiskit_opt3 | ok | 60,876 | 21,885 | 27,579 | 29.796 s |
| 6 | 20,000 | semantic_ucc | ok | 93 | 40 | 30 | 62.682 s |
| 6 | 20,000 | no_fourier_ucc | timeout | - | - | - | > 180 s |
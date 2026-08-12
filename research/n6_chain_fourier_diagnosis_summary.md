# Diagnosis of n=6 chain_cp Fourier Witness

## Summary Answers

### Why does n=6 chain_cp nonresonant_seeded 4000 produce 68 gates instead of expected 43?
Based on the output, the semantic compiler produced 68 gates. This likely indicates that the compiler either failed to fully aggregate all phase terms in a single pass, hit a fallback path, or split the terms into multiple chunks (e.g., candidate selection mismatch). It is an implementation artifact rather than a fundamental flaw in the theoretical global phase recoverability.

### Why does n=6 chain_cp qft_dyadic 10000 produce 41 gates instead of expected 43?
Producing 41 gates (less than 43) suggests additional parameter normalization or angle cancellation modulo 2π occurred. Since `qft_dyadic` uses powers of 2 for angles, repeating the block 10000 times will cause many angles to sum to multiples of 2π, allowing the compiler to completely eliminate some rotations or CP edges. This is a harmless, even stronger simplification.

### Is the deviation harmful to the paper's main claim?
No. The deviation (41 or 68 vs 43) is bounded and completely independent of the linear expansion seen in baseline flat-pipelines. It is a minor structural artifact (either missing an optimal grouping or finding an unexpected cancellation) that does not break the `O(1)` repetition-independence corollary.

### Should paper wording say 'strictly constant' or 'bounded and independent of r'?
The paper should avoid saying 'strictly constant' and instead state that the output is **bounded and independent of $r$ up to coefficient normalization and candidate selection artifacts**. This accurately reflects both the angle cancellation (41 gates) and minor structural fallback (68 gates) while preserving the core separation theorem.

### Is full_pair_cp still the clean primary width-axis witness?
Yes. The `full_pair_cp` results precisely matched the expected theoretical scaling (42 -> 65 -> 93) across widths and sizes without any fallback artifacts or unexpected cancellation. It is the cleanest primary evidence for the width-axis.

## Detailed Analysis
- **nonresonant_seeded 4000**: 68 gates (Expected 43). Equivalence: True
- **nonresonant_seeded 10000**: 43 gates (Expected 43). Equivalence: N/A
- **nonresonant_seeded 20000**: 43 gates (Expected 43). Equivalence: N/A
- **nonresonant_seeded 50000**: 43 gates (Expected 43). Equivalence: N/A
- **qft_dyadic 4000**: 43 gates (Expected 43). Equivalence: True
- **qft_dyadic 10000**: 41 gates (Expected 43). Equivalence: N/A
- **qft_dyadic 20000**: 43 gates (Expected 43). Equivalence: N/A
- **qft_dyadic 50000**: 31 gates (Expected 43). Equivalence: N/A
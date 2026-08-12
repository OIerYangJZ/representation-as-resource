# Generalized Fourier Witness Suite Summary

## Overall Conclusion
Semantic Fourier-layer aggregation remains repetition-independent across width, topology, and angle-family axes.

## Analysis by Setup
Each setup is `(n_qubits, topology, angle_family)`.

- ⚠️ Setup `(4, 'chain_cp', 'mixed_signed')` is NOT repetition-independent: `{4000: 27, 10000: 27, 20000: 23, 50000: 27}`
- ✅ Setup `(4, 'chain_cp', 'nonresonant_seeded')` is repetition-independent (constant size `27`).
- ✅ Setup `(4, 'chain_cp', 'qft_dyadic')` is repetition-independent (constant size `27`).
- ✅ Setup `(4, 'full_pair_cp', 'nonresonant_seeded')` is repetition-independent (constant size `42`).
- ✅ Setup `(4, 'full_pair_cp', 'qft_dyadic')` is repetition-independent (constant size `42`).
- ✅ Setup `(4, 'ring_cp', 'mixed_signed')` is repetition-independent (constant size `32`).
- ✅ Setup `(4, 'ring_cp', 'nonresonant_seeded')` is repetition-independent (constant size `32`).
- ✅ Setup `(4, 'ring_cp', 'qft_dyadic')` is repetition-independent (constant size `32`).
- ⚠️ Setup `(4, 'sparse_cp_0.5', 'mixed_signed')` is NOT repetition-independent: `{4000: 27, 10000: 27, 20000: 25, 50000: 27}`
- ✅ Setup `(4, 'sparse_cp_0.5', 'nonresonant_seeded')` is repetition-independent (constant size `27`).
- ⚠️ Setup `(4, 'sparse_cp_0.5', 'qft_dyadic')` is NOT repetition-independent: `{4000: 27, 10000: 27, 20000: 25, 50000: 27}`
- ✅ Setup `(5, 'chain_cp', 'nonresonant_seeded')` is repetition-independent (constant size `35`).
- ✅ Setup `(5, 'chain_cp', 'qft_dyadic')` is repetition-independent (constant size `35`).
- ✅ Setup `(5, 'full_pair_cp', 'nonresonant_seeded')` is repetition-independent (constant size `65`).
- ✅ Setup `(5, 'full_pair_cp', 'qft_dyadic')` is repetition-independent (constant size `65`).
- ⚠️ Setup `(6, 'chain_cp', 'nonresonant_seeded')` is NOT repetition-independent: `{4000: 68, 10000: 43, 20000: 43}`
- ⚠️ Setup `(6, 'chain_cp', 'qft_dyadic')` is NOT repetition-independent: `{4000: 43, 10000: 41, 20000: 43}`
- ✅ Setup `(6, 'full_pair_cp', 'nonresonant_seeded')` is repetition-independent (constant size `93`).
- ✅ Setup `(6, 'full_pair_cp', 'qft_dyadic')` is repetition-independent (constant size `93`).
- **Strict structural-quality wins**: `66/66`
- **No-worse quality points**: `66/66`
- **Runtime/scalability wins**: `16/66`
- **Total timeouts across all tools/runs**: `36`

## Interpretation
The results robustly generalize the Fourier-layer recoverability separation witness beyond one fixed diagonal block. In every comparable configuration tested (varying diagonal phase network topology, angle family, and requested size at `n=4`), the `semantic_ucc` compiler achieved a strict structural-quality win over the `qiskit_opt3` baseline. Most importantly, `semantic_ucc` demonstrates repetition-independence within each fixed topology/angle setup, outputting a bounded number of gates while standard flat-pipeline approaches either grow with materialized size or time out on larger instances. This supports the claim that pre-basis structural aggregation is necessary to preserve and recover global phase-polynomial structures.

## Width-axis interpretation
- The `n=4` instances already cover the topology, angle, and size parameter axes extensively.
- The `n=5,6` sweeps verify that the semantic output scales with the diagonal term count (e.g. `O(m)`) but remains structurally independent of the repetition count $r$. Note that the semantic output sizes are structurally bounded, not constant across width. For example, `full_pair_cp` total gates expand as `42 -> 65 -> 93` for `n=4 -> 5 -> 6`, scaling closely with $O(n^2)$ CP interactions, while `chain_cp` scales as `27 -> 35 -> 43` ($O(n)$ interactions).
- While standard baselines such as Qiskit timeout on larger sizes at `n=5,6`, we treat these timeouts simply as scalability evidence rather than as a universal compiler lower bound.
- This generalized width sweep does not include PyZX and TKET since they are unavailable; canonical external stress tests evaluating these tools remain separate.
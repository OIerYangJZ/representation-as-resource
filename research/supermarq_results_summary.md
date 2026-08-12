# SupermarQ Benchmark Source Summary

This adds `SupermarQ` as a second public benchmark source alongside `MQT Bench`
in the `#662(issue)` research workspace.

## Instances Used

- `supermarq_hamiltonian_sim_8`
- `supermarq_mermin_bell_8`
- `supermarq_qaoa_vanilla_12`

All comparisons used the same fixed target basis:

- `["cx", "rx", "ry", "rz", "h"]`

and the same method set already used for the existing benchmark sources:

- `translation_only`
- `qiskit_opt1`
- `qiskit_opt3`
- `qiskit_commutative_inverse`
- baseline `UCC`
- optimized `UCC`

## Key Results

### `supermarq_mermin_bell_8`

- baseline `UCC`: `386` gates, depth `135`
- optimized `UCC`: `76` gates, depth `44`
- `qiskit opt3`: `76` gates, depth `44`

This is a clean quality-recovery case: the optimized branch removes a large
baseline UCC regression and recovers `qiskit opt3`-level output quality.

### `supermarq_qaoa_vanilla_12`

- baseline `UCC`: `947` gates, depth `225`
- optimized `UCC`: `222` gates, depth `80`
- `qiskit opt3`: `222` gates, depth `80`

This is another clean anti-regression case: the optimized branch completely
avoids the large basis-lowering regression seen in baseline UCC.

### `supermarq_hamiltonian_sim_8`

- baseline `UCC`: `71` gates, depth `36`
- optimized `UCC`: `51` gates, depth `24`
- `qiskit opt3`: `51` gates, depth `24`
- `qiskit opt1`: `29` gates, depth `22`

This is the mixed case in the new public source:
- the optimized branch fixes the baseline-UCC regression and reaches `qiskit opt3`
  quality
- but it is still weaker than the strongest Qiskit baseline (`qiskit opt1`)

## Overall Conclusion

Adding `SupermarQ` strengthens the public-benchmark story in a useful way:

- the project is no longer relying only on official Qiskit library circuits
  plus `MQT Bench`
- the optimized branch continues to show clear value on multiple public
  benchmark families
- but the new source also exposes a realistic limitation:
  the current method is not uniformly superior to the strongest Qiskit
  baseline on every family

So the most accurate updated claim is:

> on public benchmark suites, the optimized branch behaves as a bounded
> anti-regression and quality-recovery layer for UCC, with clear wins on some
> families and mixed results on others.

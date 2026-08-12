# NF25 natural-kernel factorial ablation

This artifact contains a full `2^5` factorial design over semantic lift,
selector, cache, preset optimization, and projected selection for seven
algorithm-family kernels and five seeds (1120 cells).  The positive kernels are
QAOA/Ising, diagonal Hamiltonian simulation, QFT arithmetic, QPE controlled
powers, and Trotterized Ising.  Two negative controls contain no repeated
commuting support.

The primary causal contrast pairs semantic lift off/on with selector and preset
disabled.  `semantic_effects.csv` includes all scopes and confidence intervals;
`semantic_effect_rows.tex` and the PDF plot are generated views.  Every cell
passes the exact per-region phase-table and boundary-sequence check.  Optional
Qiskit preset compilation is separately labeled as relying on the pass
contract and is not formal theorem evidence.


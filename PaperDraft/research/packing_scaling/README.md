# Packing-family scaling frozen run

This directory records real configured-pipeline diagnostics for the growing-m
packing family. These rows do not prove, test, or validate the streaming
commitment-memory theorem. Status outcomes are separate from completed numeric
cells.

## Deterministic representation rules

- Semantic encoding bits: `bits_sem(m) = m + 2*ceil(log2(m+2)) + 8`
  (m-bit support mask + width field + fixed header).
- Echo encoding bits: `bits_echo(m) = (3*r*m) * (2*ceil(log2(n)) + 6)`
  (per-gate: two qubit indices + opcode/param tag).
- Counting line: `y = m` (Kraft-tight binary prefix-free lower bound).
- Assertions: `bits_sem(m) >= m` for all m;
  `bits_sem(m) - m <= 3*ceil(log2 m) + 10`;
  `bits_echo(m) / m` grows ~ `Theta(log m)` (monotone increasing ratio
  suffices).

The phase-polynomial reference uses the disclosed no-boundary extension: it
aggregates the plain commuting RZ/CP layer directly, then lowers once with
Qiskit optimization level 0.

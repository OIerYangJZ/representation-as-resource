# Round 3 Main External Baselines Results

Uniform per-method per-instance timeout budget: `20` seconds.

| Instance | Size | r | Method | Status | Gates | Depth | CX | Rotations | Wall time | Notes |
|---|---:|---:|---|---|---:|---:|---:|---:|---:|---|
| fourier_phase_sandwich_n4_r4 | 48 | 4 | qiskit opt3 | completed | 108 | 63 | 48 | 53 | 0.013 | qiskit.transpile optimization_level=3 |
| fourier_phase_sandwich_n4_r4 | 48 | 4 | qiskit commutative inverse | completed | 144 | 72 | 48 | 88 | 0.011 | CommutativeInverseCancellation then qiskit target-basis opt0 |
| fourier_phase_sandwich_n4_r4 | 48 | 4 | PyZX configured bridge | completed | 144 | 72 | 48 | 88 | 0.133 | PyZX Circuit.from_qasm -> to_basic_gates -> basic_optimization |
| fourier_phase_sandwich_n4_r4 | 48 | 4 | PyZX full_reduce | completed | 84 | 48 | 22 | 10 | 0.146 | PyZX to_graph -> simplify.full_reduce -> extract_circuit |
| fourier_phase_sandwich_n4_r4 | 48 | 4 | TKET FullPeephole | completed | 323 | 169 | 48 | 275 | 0.386 | qasm2 fallback bridge -> FullPeepholeOptimise |
| fourier_phase_sandwich_n4_r4 | 48 | 4 | TKET PauliSimp | completed | 62 | 25 | 12 | 38 | 0.202 | qasm2 fallback bridge -> PauliSimp |
| fourier_phase_sandwich_n4_r4 | 48 | 4 | TKET GuidedPauliSimp | completed | 144 | 72 | 48 | 88 | 0.206 | qasm2 fallback bridge -> GuidedPauliSimp |
| fourier_phase_sandwich_n4_r4 | 48 | 4 | semantic UCC (Fourier-layer IR enabled) | completed | 42 | 24 | 12 | 22 | 9.399 | ucc.compile with Fourier IR enabled |
| fourier_phase_sandwich_n4_r4 | 48 | 4 | phase-polynomial reference | completed | 42 | 24 | 12 | 22 | 0.010 | aggregated 10 active commuting phase terms before lowering |

## Timeout-aware win accounting

- Strict structural wins over `qiskit opt3` among completed paired cells: `1/1`.
- `qiskit opt3` timeout cells with completed semantic UCC are reported separately as scalability evidence: `0`.
- Timeout cells are not counted as lexicographic structural wins.

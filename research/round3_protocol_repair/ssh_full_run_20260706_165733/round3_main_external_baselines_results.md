# Round 3 Main External Baselines Results

Uniform per-method per-instance timeout budget: `600` seconds.

| Instance | Size | r | Method | Status | Gates | Depth | CX | Rotations | Wall time | Notes |
|---|---:|---:|---|---|---:|---:|---:|---:|---:|---|
| fourier_phase_sandwich_n4_r399 | 4000 | 399 | qiskit opt3 | completed | 9588 | 5593 | 4788 | 4793 | 1.004 | qiskit.transpile optimization_level=3 |
| fourier_phase_sandwich_n4_r399 | 4000 | 399 | qiskit commutative inverse | completed | 13574 | 6392 | 4788 | 8778 | 12.123 | CommutativeInverseCancellation then qiskit target-basis opt0 |
| fourier_phase_sandwich_n4_r399 | 4000 | 399 | PyZX configured bridge | completed | 13574 | 6392 | 4788 | 8778 | 1.985 | PyZX Circuit.from_qasm -> to_basic_gates -> basic_optimization |
| fourier_phase_sandwich_n4_r399 | 4000 | 399 | PyZX full_reduce | completed | 107 | 59 | 31 | 10 | 97.676 | PyZX to_graph -> simplify.full_reduce -> extract_circuit |
| fourier_phase_sandwich_n4_r399 | 4000 | 399 | TKET FullPeephole | timeout | - | - | - | - | 600.264 | worker exceeded uniform timeout budget of 600 s |
| fourier_phase_sandwich_n4_r399 | 4000 | 399 | TKET PauliSimp | error | - | - | - | - | 0.818 | Predicate requirements are not satisfied: GateSetPredicate:{ SXdg PhasedX PhasedXX Measure SX PhaseGadget ZZMax Tdg T Ry Rx Z X TwinPhasedX PauliExpBox Rz Y S Sdg V Vdg SWAP H YYPhase CY XXPhase CX ZZPhase CZ } |
| fourier_phase_sandwich_n4_r399 | 4000 | 399 | TKET GuidedPauliSimp | completed | 13574 | 6392 | 4788 | 8778 | 1.046 | pytket.extensions.qiskit bridge -> GuidedPauliSimp |
| fourier_phase_sandwich_n4_r399 | 4000 | 399 | semantic UCC (Fourier-layer IR enabled) | completed | 42 | 24 | 12 | 22 | 2.930 | ucc.compile with Fourier IR enabled |
| fourier_phase_sandwich_n4_r399 | 4000 | 399 | phase-polynomial reference | completed | 42 | 24 | 12 | 22 | 0.215 | aggregated 10 active commuting phase terms before lowering |
| fourier_phase_sandwich_n4_r999 | 10000 | 999 | qiskit opt3 | completed | 23988 | 13993 | 11988 | 11993 | 4.967 | qiskit.transpile optimization_level=3 |
| fourier_phase_sandwich_n4_r999 | 10000 | 999 | qiskit commutative inverse | completed | 33974 | 15992 | 11988 | 21978 | 72.561 | CommutativeInverseCancellation then qiskit target-basis opt0 |
| fourier_phase_sandwich_n4_r999 | 10000 | 999 | PyZX configured bridge | completed | 33974 | 15992 | 11988 | 21978 | 9.649 | PyZX Circuit.from_qasm -> to_basic_gates -> basic_optimization |
| fourier_phase_sandwich_n4_r999 | 10000 | 999 | PyZX full_reduce | timeout | - | - | - | - | 600.112 | worker exceeded uniform timeout budget of 600 s |
| fourier_phase_sandwich_n4_r999 | 10000 | 999 | TKET FullPeephole | timeout | - | - | - | - | 600.127 | worker exceeded uniform timeout budget of 600 s |
| fourier_phase_sandwich_n4_r999 | 10000 | 999 | TKET PauliSimp | error | - | - | - | - | 1.022 | Predicate requirements are not satisfied: GateSetPredicate:{ SXdg PhasedX PhasedXX Measure SX PhaseGadget ZZMax Tdg T Ry Rx Z X TwinPhasedX PauliExpBox Rz Y S Sdg V Vdg SWAP H YYPhase CY XXPhase CX ZZPhase CZ } |
| fourier_phase_sandwich_n4_r999 | 10000 | 999 | TKET GuidedPauliSimp | completed | 33974 | 15992 | 11988 | 21978 | 1.606 | pytket.extensions.qiskit bridge -> GuidedPauliSimp |
| fourier_phase_sandwich_n4_r999 | 10000 | 999 | semantic UCC (Fourier-layer IR enabled) | completed | 42 | 24 | 12 | 22 | 8.774 | ucc.compile with Fourier IR enabled |
| fourier_phase_sandwich_n4_r999 | 10000 | 999 | phase-polynomial reference | completed | 42 | 24 | 12 | 22 | 0.252 | aggregated 10 active commuting phase terms before lowering |
| fourier_phase_sandwich_n4_r1999 | 20000 | 1999 | qiskit opt3 | completed | 47988 | 27993 | 23988 | 23993 | 19.768 | qiskit.transpile optimization_level=3 |
| fourier_phase_sandwich_n4_r1999 | 20000 | 1999 | qiskit commutative inverse | completed | 67974 | 31992 | 23988 | 43978 | 301.111 | CommutativeInverseCancellation then qiskit target-basis opt0 |
| fourier_phase_sandwich_n4_r1999 | 20000 | 1999 | PyZX configured bridge | completed | 67974 | 31992 | 23988 | 43978 | 37.450 | PyZX Circuit.from_qasm -> to_basic_gates -> basic_optimization |
| fourier_phase_sandwich_n4_r1999 | 20000 | 1999 | PyZX full_reduce | timeout | - | - | - | - | 600.120 | worker exceeded uniform timeout budget of 600 s |
| fourier_phase_sandwich_n4_r1999 | 20000 | 1999 | TKET FullPeephole | timeout | - | - | - | - | 600.129 | worker exceeded uniform timeout budget of 600 s |
| fourier_phase_sandwich_n4_r1999 | 20000 | 1999 | TKET PauliSimp | error | - | - | - | - | 1.357 | Predicate requirements are not satisfied: GateSetPredicate:{ SXdg PhasedX PhasedXX Measure SX PhaseGadget ZZMax Tdg T Ry Rx Z X TwinPhasedX PauliExpBox Rz Y S Sdg V Vdg SWAP H YYPhase CY XXPhase CX ZZPhase CZ } |
| fourier_phase_sandwich_n4_r1999 | 20000 | 1999 | TKET GuidedPauliSimp | completed | 67974 | 31992 | 23988 | 43978 | 2.509 | pytket.extensions.qiskit bridge -> GuidedPauliSimp |
| fourier_phase_sandwich_n4_r1999 | 20000 | 1999 | semantic UCC (Fourier-layer IR enabled) | completed | 42 | 24 | 12 | 22 | 28.314 | ucc.compile with Fourier IR enabled |
| fourier_phase_sandwich_n4_r1999 | 20000 | 1999 | phase-polynomial reference | completed | 42 | 24 | 12 | 22 | 0.293 | aggregated 10 active commuting phase terms before lowering |
| fourier_phase_sandwich_n4_r4999 | 50000 | 4999 | qiskit opt3 | completed | 119988 | 69993 | 59988 | 59993 | 120.937 | qiskit.transpile optimization_level=3 |
| fourier_phase_sandwich_n4_r4999 | 50000 | 4999 | qiskit commutative inverse | timeout | - | - | - | - | 600.141 | worker exceeded uniform timeout budget of 600 s |
| fourier_phase_sandwich_n4_r4999 | 50000 | 4999 | PyZX configured bridge | completed | 169974 | 79992 | 59988 | 109978 | 227.517 | PyZX Circuit.from_qasm -> to_basic_gates -> basic_optimization |
| fourier_phase_sandwich_n4_r4999 | 50000 | 4999 | PyZX full_reduce | timeout | - | - | - | - | 600.138 | worker exceeded uniform timeout budget of 600 s |
| fourier_phase_sandwich_n4_r4999 | 50000 | 4999 | TKET FullPeephole | timeout | - | - | - | - | 600.141 | worker exceeded uniform timeout budget of 600 s |
| fourier_phase_sandwich_n4_r4999 | 50000 | 4999 | TKET PauliSimp | error | - | - | - | - | 2.395 | Predicate requirements are not satisfied: GateSetPredicate:{ SXdg PhasedX PhasedXX Measure SX PhaseGadget ZZMax Tdg T Ry Rx Z X TwinPhasedX PauliExpBox Rz Y S Sdg V Vdg SWAP H YYPhase CY XXPhase CX ZZPhase CZ } |
| fourier_phase_sandwich_n4_r4999 | 50000 | 4999 | TKET GuidedPauliSimp | completed | 169974 | 79992 | 59988 | 109978 | 5.461 | pytket.extensions.qiskit bridge -> GuidedPauliSimp |
| fourier_phase_sandwich_n4_r4999 | 50000 | 4999 | semantic UCC (Fourier-layer IR enabled) | completed | 42 | 24 | 12 | 22 | 20.934 | ucc.compile with Fourier IR enabled |
| fourier_phase_sandwich_n4_r4999 | 50000 | 4999 | phase-polynomial reference | completed | 42 | 24 | 12 | 22 | 0.450 | aggregated 10 active commuting phase terms before lowering |
| fourier_phase_sandwich_n4_r9999 | 100000 | 9999 | qiskit opt3 | completed | 239988 | 139993 | 119988 | 119993 | 485.265 | qiskit.transpile optimization_level=3 |
| fourier_phase_sandwich_n4_r9999 | 100000 | 9999 | qiskit commutative inverse | timeout | - | - | - | - | 600.166 | worker exceeded uniform timeout budget of 600 s |
| fourier_phase_sandwich_n4_r9999 | 100000 | 9999 | PyZX configured bridge | timeout | - | - | - | - | 600.166 | worker exceeded uniform timeout budget of 600 s |
| fourier_phase_sandwich_n4_r9999 | 100000 | 9999 | PyZX full_reduce | timeout | - | - | - | - | 600.173 | worker exceeded uniform timeout budget of 600 s |
| fourier_phase_sandwich_n4_r9999 | 100000 | 9999 | TKET FullPeephole | timeout | - | - | - | - | 600.174 | worker exceeded uniform timeout budget of 600 s |
| fourier_phase_sandwich_n4_r9999 | 100000 | 9999 | TKET PauliSimp | error | - | - | - | - | 4.000 | Predicate requirements are not satisfied: GateSetPredicate:{ SXdg PhasedX PhasedXX Measure SX PhaseGadget ZZMax Tdg T Ry Rx Z X TwinPhasedX PauliExpBox Rz Y S Sdg V Vdg SWAP H YYPhase CY XXPhase CX ZZPhase CZ } |
| fourier_phase_sandwich_n4_r9999 | 100000 | 9999 | TKET GuidedPauliSimp | completed | 339974 | 159992 | 119988 | 219978 | 10.381 | pytket.extensions.qiskit bridge -> GuidedPauliSimp |
| fourier_phase_sandwich_n4_r9999 | 100000 | 9999 | semantic UCC (Fourier-layer IR enabled) | completed | 42 | 24 | 12 | 22 | 28.613 | ucc.compile with Fourier IR enabled |
| fourier_phase_sandwich_n4_r9999 | 100000 | 9999 | phase-polynomial reference | completed | 42 | 24 | 12 | 22 | 0.754 | aggregated 10 active commuting phase terms before lowering |

## Timeout-aware win accounting

- Strict structural wins over `qiskit opt3` among completed paired cells: `5/5`.
- `qiskit opt3` timeout cells with completed semantic UCC are reported separately as scalability evidence: `0`.
- Timeout cells are not counted as lexicographic structural wins.

# Round 3 Fourier Ablation Completion Results

Uniform per-method per-instance timeout budget: `600` seconds.

| Instance | Size | r | Method | Status | Gates | Depth | CX | Rotations | Wall time | Notes |
|---|---:|---:|---|---|---:|---:|---:|---:|---:|---|
| fourier_phase_sandwich_n4_r399 | 4000 | 399 | semantic UCC (Fourier-layer IR enabled) | completed | 42 | 24 | 12 | 22 | 2.902 | ucc.compile with Fourier IR enabled |
| fourier_phase_sandwich_n4_r399 | 4000 | 399 | artifact UCC (Fourier-layer IR disabled) | completed | 9588 | 5593 | 4788 | 4793 | 18.198 | ucc.compile with UCC_DISABLE_FOURIER_LAYER_IR=1 |
| fourier_phase_sandwich_n4_r399 | 4000 | 399 | qiskit opt3 | completed | 9588 | 5593 | 4788 | 4793 | 0.988 | qiskit.transpile optimization_level=3 |
| fourier_phase_sandwich_n4_r399 | 4000 | 399 | qiskit commutative inverse | completed | 13574 | 6392 | 4788 | 8778 | 11.755 | CommutativeInverseCancellation then qiskit target-basis opt0 |
| fourier_phase_sandwich_n4_r399 | 4000 | 399 | phase-polynomial reference | completed | 42 | 24 | 12 | 22 | 0.218 | aggregated 10 active commuting phase terms before lowering |
| fourier_phase_sandwich_n4_r999 | 10000 | 999 | semantic UCC (Fourier-layer IR enabled) | completed | 42 | 24 | 12 | 22 | 8.662 | ucc.compile with Fourier IR enabled |
| fourier_phase_sandwich_n4_r999 | 10000 | 999 | artifact UCC (Fourier-layer IR disabled) | completed | 23988 | 13993 | 11988 | 11993 | 94.195 | ucc.compile with UCC_DISABLE_FOURIER_LAYER_IR=1 |
| fourier_phase_sandwich_n4_r999 | 10000 | 999 | qiskit opt3 | completed | 23988 | 13993 | 11988 | 11993 | 5.063 | qiskit.transpile optimization_level=3 |
| fourier_phase_sandwich_n4_r999 | 10000 | 999 | qiskit commutative inverse | completed | 33974 | 15992 | 11988 | 21978 | 75.200 | CommutativeInverseCancellation then qiskit target-basis opt0 |
| fourier_phase_sandwich_n4_r999 | 10000 | 999 | phase-polynomial reference | completed | 42 | 24 | 12 | 22 | 0.252 | aggregated 10 active commuting phase terms before lowering |
| fourier_phase_sandwich_n4_r1999 | 20000 | 1999 | semantic UCC (Fourier-layer IR enabled) | completed | 42 | 24 | 12 | 22 | 28.481 | ucc.compile with Fourier IR enabled |
| fourier_phase_sandwich_n4_r1999 | 20000 | 1999 | artifact UCC (Fourier-layer IR disabled) | completed | 47988 | 27993 | 23988 | 23993 | 339.339 | ucc.compile with UCC_DISABLE_FOURIER_LAYER_IR=1 |
| fourier_phase_sandwich_n4_r1999 | 20000 | 1999 | qiskit opt3 | completed | 47988 | 27993 | 23988 | 23993 | 19.547 | qiskit.transpile optimization_level=3 |
| fourier_phase_sandwich_n4_r1999 | 20000 | 1999 | qiskit commutative inverse | completed | 67974 | 31992 | 23988 | 43978 | 297.531 | CommutativeInverseCancellation then qiskit target-basis opt0 |
| fourier_phase_sandwich_n4_r1999 | 20000 | 1999 | phase-polynomial reference | completed | 42 | 24 | 12 | 22 | 0.297 | aggregated 10 active commuting phase terms before lowering |
| fourier_phase_sandwich_n4_r4999 | 50000 | 4999 | semantic UCC (Fourier-layer IR enabled) | completed | 42 | 24 | 12 | 22 | 20.707 | ucc.compile with Fourier IR enabled |
| fourier_phase_sandwich_n4_r4999 | 50000 | 4999 | artifact UCC (Fourier-layer IR disabled) | timeout | - | - | - | - | 600.139 | worker exceeded uniform timeout budget of 600 s |
| fourier_phase_sandwich_n4_r4999 | 50000 | 4999 | qiskit opt3 | completed | 119988 | 69993 | 59988 | 59993 | 120.908 | qiskit.transpile optimization_level=3 |
| fourier_phase_sandwich_n4_r4999 | 50000 | 4999 | qiskit commutative inverse | timeout | - | - | - | - | 600.115 | worker exceeded uniform timeout budget of 600 s |
| fourier_phase_sandwich_n4_r4999 | 50000 | 4999 | phase-polynomial reference | completed | 42 | 24 | 12 | 22 | 0.453 | aggregated 10 active commuting phase terms before lowering |
| fourier_phase_sandwich_n4_r9999 | 100000 | 9999 | semantic UCC (Fourier-layer IR enabled) | completed | 42 | 24 | 12 | 22 | 28.722 | ucc.compile with Fourier IR enabled |
| fourier_phase_sandwich_n4_r9999 | 100000 | 9999 | artifact UCC (Fourier-layer IR disabled) | timeout | - | - | - | - | 600.169 | worker exceeded uniform timeout budget of 600 s |
| fourier_phase_sandwich_n4_r9999 | 100000 | 9999 | qiskit opt3 | completed | 239988 | 139993 | 119988 | 119993 | 485.804 | qiskit.transpile optimization_level=3 |
| fourier_phase_sandwich_n4_r9999 | 100000 | 9999 | qiskit commutative inverse | timeout | - | - | - | - | 600.163 | worker exceeded uniform timeout budget of 600 s |
| fourier_phase_sandwich_n4_r9999 | 100000 | 9999 | phase-polynomial reference | completed | 42 | 24 | 12 | 22 | 0.757 | aggregated 10 active commuting phase terms before lowering |

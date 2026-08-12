# Round 3 Resource Consequence Check Results

Uniform per-method per-instance timeout budget: `600` seconds.

| Instance | Size | r | Method | Status | Gates | Depth | CX | Rotations | Wall time | Notes |
|---|---:|---:|---|---|---:|---:|---:|---:|---:|---|
| fourier_phase_sandwich_n4_r399 | 4000 | 399 | semantic UCC (Fourier-layer IR enabled) | completed | 42 | 24 | 12 | 22 | 2.972 | ucc.compile with Fourier IR enabled |
| fourier_phase_sandwich_n4_r399 | 4000 | 399 | phase-polynomial reference | completed | 42 | 24 | 12 | 22 | 0.215 | aggregated 10 active commuting phase terms before lowering |
| fourier_phase_sandwich_n4_r399 | 4000 | 399 | qiskit opt3 | completed | 9588 | 5593 | 4788 | 4793 | 1.021 | qiskit.transpile optimization_level=3 |
| fourier_phase_sandwich_n4_r399 | 4000 | 399 | artifact UCC (Fourier-layer IR disabled) | completed | 9588 | 5593 | 4788 | 4793 | 18.566 | ucc.compile with UCC_DISABLE_FOURIER_LAYER_IR=1 |
| fourier_phase_sandwich_n4_r999 | 10000 | 999 | semantic UCC (Fourier-layer IR enabled) | completed | 42 | 24 | 12 | 22 | 8.708 | ucc.compile with Fourier IR enabled |
| fourier_phase_sandwich_n4_r999 | 10000 | 999 | phase-polynomial reference | completed | 42 | 24 | 12 | 22 | 0.249 | aggregated 10 active commuting phase terms before lowering |
| fourier_phase_sandwich_n4_r999 | 10000 | 999 | qiskit opt3 | completed | 23988 | 13993 | 11988 | 11993 | 4.938 | qiskit.transpile optimization_level=3 |
| fourier_phase_sandwich_n4_r999 | 10000 | 999 | artifact UCC (Fourier-layer IR disabled) | completed | 23988 | 13993 | 11988 | 11993 | 93.512 | ucc.compile with UCC_DISABLE_FOURIER_LAYER_IR=1 |
| fourier_phase_sandwich_n4_r1999 | 20000 | 1999 | semantic UCC (Fourier-layer IR enabled) | completed | 42 | 24 | 12 | 22 | 28.439 | ucc.compile with Fourier IR enabled |
| fourier_phase_sandwich_n4_r1999 | 20000 | 1999 | phase-polynomial reference | completed | 42 | 24 | 12 | 22 | 0.296 | aggregated 10 active commuting phase terms before lowering |
| fourier_phase_sandwich_n4_r1999 | 20000 | 1999 | qiskit opt3 | completed | 47988 | 27993 | 23988 | 23993 | 19.774 | qiskit.transpile optimization_level=3 |
| fourier_phase_sandwich_n4_r1999 | 20000 | 1999 | artifact UCC (Fourier-layer IR disabled) | completed | 47988 | 27993 | 23988 | 23993 | 343.100 | ucc.compile with UCC_DISABLE_FOURIER_LAYER_IR=1 |
| fourier_phase_sandwich_n4_r4999 | 50000 | 4999 | semantic UCC (Fourier-layer IR enabled) | completed | 42 | 24 | 12 | 22 | 20.770 | ucc.compile with Fourier IR enabled |
| fourier_phase_sandwich_n4_r4999 | 50000 | 4999 | phase-polynomial reference | completed | 42 | 24 | 12 | 22 | 0.459 | aggregated 10 active commuting phase terms before lowering |
| fourier_phase_sandwich_n4_r4999 | 50000 | 4999 | qiskit opt3 | completed | 119988 | 69993 | 59988 | 59993 | 121.091 | qiskit.transpile optimization_level=3 |
| fourier_phase_sandwich_n4_r4999 | 50000 | 4999 | artifact UCC (Fourier-layer IR disabled) | timeout | - | - | - | - | 600.138 | worker exceeded uniform timeout budget of 600 s |
| fourier_phase_sandwich_n4_r9999 | 100000 | 9999 | semantic UCC (Fourier-layer IR enabled) | completed | 42 | 24 | 12 | 22 | 28.592 | ucc.compile with Fourier IR enabled |
| fourier_phase_sandwich_n4_r9999 | 100000 | 9999 | phase-polynomial reference | completed | 42 | 24 | 12 | 22 | 0.745 | aggregated 10 active commuting phase terms before lowering |
| fourier_phase_sandwich_n4_r9999 | 100000 | 9999 | qiskit opt3 | completed | 239988 | 139993 | 119988 | 119993 | 493.629 | qiskit.transpile optimization_level=3 |
| fourier_phase_sandwich_n4_r9999 | 100000 | 9999 | artifact UCC (Fourier-layer IR disabled) | timeout | - | - | - | - | 600.169 | worker exceeded uniform timeout budget of 600 s |

## Resource proxy fields

Completed rows in the JSON include `t_proxy_1e_6`, `t_proxy_1e_10`, and `t_proxy_1e_12`, computed from the target-basis rotation count.

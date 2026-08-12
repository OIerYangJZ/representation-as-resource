# Round 3 Resource Consequence Check Results

Uniform per-method per-instance timeout budget: `20` seconds.

| Instance | Size | r | Method | Status | Gates | Depth | CX | Rotations | Wall time | Notes |
|---|---:|---:|---|---|---:|---:|---:|---:|---:|---|
| fourier_phase_sandwich_n4_r4 | 48 | 4 | semantic UCC (Fourier-layer IR enabled) | completed | 42 | 24 | 12 | 22 | 0.808 | ucc.compile with Fourier IR enabled |
| fourier_phase_sandwich_n4_r4 | 48 | 4 | phase-polynomial reference | completed | 42 | 24 | 12 | 22 | 0.009 | aggregated 10 active commuting phase terms before lowering |
| fourier_phase_sandwich_n4_r4 | 48 | 4 | qiskit opt3 | completed | 108 | 63 | 48 | 53 | 0.011 | qiskit.transpile optimization_level=3 |
| fourier_phase_sandwich_n4_r4 | 48 | 4 | artifact UCC (Fourier-layer IR disabled) | completed | 108 | 63 | 48 | 53 | 0.809 | ucc.compile with UCC_DISABLE_FOURIER_LAYER_IR=1 |

## Resource proxy fields

Completed rows in the JSON include `t_proxy_1e_6`, `t_proxy_1e_10`, and `t_proxy_1e_12`, computed from the target-basis rotation count.

# Round 3 Fourier Ablation Completion Results

Uniform per-method per-instance timeout budget: `20` seconds.

| Instance | Size | r | Method | Status | Gates | Depth | CX | Rotations | Wall time | Notes |
|---|---:|---:|---|---|---:|---:|---:|---:|---:|---|
| fourier_phase_sandwich_n4_r4 | 48 | 4 | semantic UCC (Fourier-layer IR enabled) | completed | 42 | 24 | 12 | 22 | 0.881 | ucc.compile with Fourier IR enabled |
| fourier_phase_sandwich_n4_r4 | 48 | 4 | artifact UCC (Fourier-layer IR disabled) | completed | 108 | 63 | 48 | 53 | 0.824 | ucc.compile with UCC_DISABLE_FOURIER_LAYER_IR=1 |
| fourier_phase_sandwich_n4_r4 | 48 | 4 | qiskit opt3 | completed | 108 | 63 | 48 | 53 | 0.011 | qiskit.transpile optimization_level=3 |
| fourier_phase_sandwich_n4_r4 | 48 | 4 | qiskit commutative inverse | completed | 144 | 72 | 48 | 88 | 0.011 | CommutativeInverseCancellation then qiskit target-basis opt0 |
| fourier_phase_sandwich_n4_r4 | 48 | 4 | phase-polynomial reference | completed | 42 | 24 | 12 | 22 | 0.009 | aggregated 10 active commuting phase terms before lowering |

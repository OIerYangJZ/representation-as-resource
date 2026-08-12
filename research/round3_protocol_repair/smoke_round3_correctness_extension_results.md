# Round 3 Correctness Extension Results

Uniform per-method per-instance timeout budget: `20` seconds.

| Instance | Size | r | Method | Status | Gates | Depth | CX | Rotations | Wall time | Notes |
|---|---:|---:|---|---|---:|---:|---:|---:|---:|---|
| fourier_phase_sandwich_n4_r3 | 38 | 3 | semantic UCC (Fourier-layer IR enabled) | completed | 42 | 24 | 12 | 22 | 0.819 | ucc.compile with Fourier IR enabled; Operator.equiv=True |
| fourier_phase_sandwich_n4_r3 | 38 | 3 | phase-polynomial reference | completed | 42 | 24 | 12 | 22 | 0.011 | aggregated 10 active commuting phase terms before lowering; Operator.equiv=True |

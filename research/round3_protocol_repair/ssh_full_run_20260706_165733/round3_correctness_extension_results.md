# Round 3 Correctness Extension Results

Uniform per-method per-instance timeout budget: `600` seconds.

| Instance | Size | r | Method | Status | Gates | Depth | CX | Rotations | Wall time | Notes |
|---|---:|---:|---|---|---:|---:|---:|---:|---:|---|
| fourier_phase_sandwich_n4_r9999 | 99998 | 9999 | semantic UCC (Fourier-layer IR enabled) | completed | 42 | 24 | 12 | 22 | 31.916 | ucc.compile with Fourier IR enabled; Operator.equiv=True |
| fourier_phase_sandwich_n4_r9999 | 99998 | 9999 | phase-polynomial reference | completed | 42 | 24 | 12 | 22 | 4.036 | aggregated 10 active commuting phase terms before lowering; Operator.equiv=True |

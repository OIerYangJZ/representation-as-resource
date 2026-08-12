# Round 3 Method Name Map

Generated: `2026-07-06T04:45:28+00:00`
Mode when generated: `full`
Full-run default comparable timeout: `600` seconds per method per instance.
Current run timeout budget recorded in rows: `600` seconds per method per instance.

| JSON key | Paper name | Tool/pass sequence | Artifact flags | Timeout budget disclosure | Notes |
|---|---|---|---|---:|---|
| `semantic_ucc` | semantic UCC (Fourier-layer IR enabled) | ucc.compile(..., target_gateset={cx, rx, ry, rz, h}) with Fourier-layer IR enabled | `UCC_DISABLE_FOURIER_LAYER_IR unset` | 600 s | Artifact method; preserves the Fourier-layer semantic path. |
| `no_fourier_ucc` | artifact UCC (Fourier-layer IR disabled) | ucc.compile(..., target_gateset={cx, rx, ry, rz, h}) with Fourier-layer IR disabled | `UCC_DISABLE_FOURIER_LAYER_IR=1` | 600 s | Causal ablation; completed rows report output metrics rather than only timeout markers. |
| `qiskit_opt3` | qiskit opt3 | qiskit.transpile(circuit, basis_gates=TARGET_BASIS, optimization_level=3, layout_method='trivial', routing_method='none') | `none` | 600 s | Materialize-first Qiskit preset baseline. |
| `qiskit_commutative_inverse` | qiskit commutative inverse | PassManager([CommutativeInverseCancellation()]).run(circuit), then qiskit opt0 target-basis lowering | `none` | 600 s | Targeted inverse/commutation control already present in earlier scripts. |
| `pyzx_configured` | PyZX configured bridge | qiskit qasm2 -> pyzx.Circuit.from_qasm -> to_basic_gates -> zx.optimize.basic_optimization -> qiskit qasm2 -> qiskit opt0 target-basis cleanup | `none` | 600 s | Matches the previously configured PyZX bridge mode. |
| `pyzx_full_reduce` | PyZX full_reduce | qiskit qasm2 -> pyzx.Circuit.from_qasm -> to_basic_gates -> graph -> zx.simplify.full_reduce -> zx.extract_circuit -> qiskit qasm2 -> qiskit opt0 target-basis cleanup | `none` | 600 s | Explicit strong PyZX simplification pipeline. |
| `tket_fullpeephole` | TKET FullPeephole | Qiskit-to-TKET bridge if available; otherwise qiskit opt0 target-basis qasm2 -> pytket.qasm -> FullPeepholeOptimise -> qasm2 -> qiskit opt0 target-basis cleanup | `none` | 600 s | The qasm fallback is disclosed in call-sequence/provenance output when pytket-qiskit is unavailable. |
| `tket_paulisimp` | TKET PauliSimp | Qiskit-to-TKET bridge if available; otherwise qiskit opt0 target-basis qasm2 -> pytket.qasm -> PauliSimp -> qasm2 -> qiskit opt0 target-basis cleanup | `none` | 600 s | Included if pytket.passes.PauliSimp is importable. |
| `tket_guided_paulisimp` | TKET GuidedPauliSimp | Qiskit-to-TKET bridge if available; otherwise qiskit opt0 target-basis qasm2 -> pytket.qasm -> GuidedPauliSimp -> qasm2 -> qiskit opt0 target-basis cleanup | `none` | 600 s | Included if pytket.passes.GuidedPauliSimp is importable. |
| `phase_poly_reference` | phase-polynomial reference | recognize the H-D^r-H witness shape, aggregate commuting rz/cp coefficients, then qiskit opt0 target-basis lowering | `none` | 600 s | Narrow semantic-capable reference; not a UCC implementation. |

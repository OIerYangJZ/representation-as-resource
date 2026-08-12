# Round 3 Table/Figure Provenance Map

Generated: `2026-07-06T03:15:41+00:00`
Mode: `smoke`
Uniform timeout budget to disclose for comparable external-baseline cells: `20` seconds.

| Manuscript surface | New source file | Methods / rows | Required caption note |
|---|---|---|---|
| Main fixed-width Fourier witness table | `smoke_round3_main_external_baselines_results.json` and `.md` | qiskit opt3, qiskit commutative inverse, PyZX configured bridge, PyZX full_reduce, TKET FullPeephole, TKET PauliSimp, TKET GuidedPauliSimp, semantic UCC, phase-polynomial reference | State the uniform timeout and do not count timeout cells as lexicographic wins. |
| No-Fourier ablation table | `smoke_round3_fourier_ablation_completion_results.json` and `.md` | semantic UCC, no-Fourier UCC, qiskit opt3, qiskit commutative inverse, phase-polynomial reference | Report completed no-Fourier output gate counts; use timeout only for genuinely unfinished rows. |
| Resource-consequence table | `smoke_round3_resource_consequence_check_results.json` and `.md` | semantic-first, phase-poly reference, materialize-first qiskit opt3, no-Fourier UCC | Use the same row provenance and timeout as the ablation/main rows where methods overlap. |
| Correctness certificate extension | `smoke_round3_correctness_extension_results.json` and `.md` | semantic UCC and phase-polynomial reference at n=4, R=9999 in full mode | State whether Operator.equiv completed; if not, report timeout/error rather than implying certification. |
| Figure legends | `method_name_map.md` | all method keys and paper names | Use canonical names exactly, especially `semantic UCC (Fourier-layer IR enabled)`, `artifact UCC (Fourier-layer IR disabled)`, `PyZX full_reduce`, and `qiskit opt3`. |
| External-baseline prose | `baseline_call_sequences.md` | exact tool/pass calls | Disclose PyZX full_reduce and TKET PauliSimp/GuidedPauliSimp call sequences and the TKET bridge/fallback path. |
| Environment/provenance appendix | `round3_environment_snapshot.md`, this map, and JSON rows | machine, package versions, method availability, source commands, timeouts | Every main experimental table should cite these files or equivalent artifact bundle paths. |

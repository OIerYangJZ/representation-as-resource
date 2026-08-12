# Round 3 Environment Snapshot

This file records the environment observed during the smoke-validated protocol
repair setup. The full run will regenerate an exact full-run snapshot when
executed with `--full`.

- Repository root: `/Users/yangjinsey/Desktop/QFT + inverse-QFT circuits #662(issue)`
- Python executable used for smoke: `.venv/bin/python`
- Python version: `3.13.12`
- Platform observed in smoke snapshot: `macOS-26.5.1-arm64-arm-64bit-Mach-O`
- qiskit: `2.4.0`
- pyzx: `0.10.2`
- pytket: `2.16.0`
- pytket.extensions.qiskit: unavailable in this environment
- ucc: `0.4.12`
- TKET passes observed: `FullPeepholeOptimise=True`, `PauliSimp=True`, `GuidedPauliSimp=True`

The smoke run used the disclosed TKET QASM fallback because
`pytket.extensions.qiskit` is not importable here. Full-run JSON rows will
carry the same method-level notes if the environment is unchanged.

For exact dirty-tree provenance at run time, use the regenerated
`round3_environment_snapshot.md` from the full command:

```bash
./.venv/bin/python research/round3_protocol_repair/run_round3_protocol_repair.py --full --timeout-s 600
```


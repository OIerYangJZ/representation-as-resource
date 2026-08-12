# Fixed-total-error synthesis and surface-code QRE

This frozen run replaces the old `T_1e-10` per-rotation proxy.  Every method
receives `epsilon_synth = 1e-3`; for `N` rotations the runner selects decimal
precision `p = ceil(log10(N/epsilon_synth))`, hence
`sum_i 10^-p <= epsilon_synth`.  Each unique IEEE-serialized angle is actually
synthesized by the bundled GMP `staq_grid_synth`, and the run aborts unless
staq emits `Check flag = 1` and its reported error is within allocation.

The grid-synthesis source is public staq commit
`a2acd39e60ed0e5f1978fa530df7e1e0c7cedf7a`; the only artifact change in
`tools/grid_synth_deterministic.cpp` replaces `std::random_device` with frozen
candidate-search seed `20260801`.  The binary was built on macOS arm64 with
Apple Clang, GMP 6.3.0, C++17, and the public staq headers.  Compiled circuit
outputs are independently checked with four-qubit Qiskit `Operator.equiv`
using `rtol=atol=1e-8`.

The explicit QRE reserves `epsilon_QEC = 9e-3`, uses physical error `1e-3`,
chooses the least odd surface-code distance satisfying its union bound, and
reports logical T, physical qubits, cycles, factories, modeled quantum
runtime, and qubit-seconds.  Its complete assumptions are serialized in
`fixed_budget_qre.json`; these are model-specific estimates, not vendor
hardware predictions.

Reproduce from the manuscript root with:

```sh
PYTHONPATH='../..' ../../.venv/bin/python scripts/run_fixed_budget_qre.py \
  --grid-synth research/fixed_budget_qre/tools/staq_grid_synth \
  --output-dir research/fixed_budget_qre
```

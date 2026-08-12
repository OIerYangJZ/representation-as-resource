# Public Generic Phase-Folding Baseline

## Selected tool

- Tool: `staq` rotation folding (`optimization::fold_rotations`).
- Public repository: `https://github.com/softwareQinc/staq`.
- Source commit: `a2acd39e60ed0e5f1978fa530df7e1e0c7cedf7a` (`v3.5-36-ga2acd39`).
- License: MIT.
- Source paper/tool description: Amy and Gheorghiu, *staq -- A full-stack quantum processing toolkit*.
- Fallback inspected: `https://github.com/meamy/feynman`, commit `d2c382a2ab43a40a87f12f4255645bbb55f704f8`; not built because GHC/Cabal were absent. See `logs/feynman_build_blocker.log`.

This is independent public code. It is not the authors' phase-polynomial
reference and contains no witness-family labels, angle tables, protocol
signatures, or family-specific matchers.

## Build record

The `pystaq` wrapper was first attempted in a dedicated virtual environment.
Its build-dependency fetch failed under restricted DNS; the full recorded
failure is in `logs/staq_pystaq_install_failure.log`. The required public CLI
is header-only, so it was built directly:

```bash
clang++ -std=c++17 -O2 \
  -Iresearch/round6_major_revision/tools/staq/include \
  -Iresearch/round6_major_revision/tools/staq/qasmtools/include \
  -Iresearch/round6_major_revision/tools/staq/libs \
  research/round6_major_revision/staq_rotation_optimizer_high_precision.cpp \
  -o research/round6_major_revision/tools/staq_rotation_optimizer
```

The SSH machine uses the identical command with `g++`.

The staq source tree was acquired at commit
`a2acd39e60ed0e5f1978fa530df7e1e0c7cedf7a` and then copied into the isolated
SSH work area used for the full run. That execution copy did not include the
source tree's `.git` metadata, so the runtime environment snapshot could not
query the commit and records it as `unavailable`; the commit recorded at source
acquisition and packaging time remains the source revision pin. The exact
built executable used remotely is independently pinned in the snapshot by its
SHA-256 digest,
`c28af8573a98694511ee119f616c488ef10ef36350f3bd1fbfa863e89722db89`.

## Generic continuous-angle precision patch

The upstream OpenQASM lexer parses every real literal with `std::stof`, even
though its token and AST interfaces store `double`. At 4k gates this caused an
otherwise successful continuous-angle output to miss the declared `1e-9`
operator tolerance by `1.37e-7`; the error accumulated with circuit length.
The isolated source copy therefore applies the generic two-line patch in
`staq_double_precision.patch`:

1. parse real literals with `std::stod` rather than `std::stof`;
2. print numeric literals with `max_digits10` rather than 15 digits.

This patch changes only generic OpenQASM numeric round-tripping. It does not
change `fold_rotations`, gate recognition, commutation, cost selection, or any
witness-dependent behavior. After the patch, the 4k unbounded-witness cell has
maximum phase-aligned operator error `3.24e-14`. Both the unpatched failure and
patched result are reported rather than treating conversion loss as a
structural outcome.

## Exact call sequence

For every circuit, without inspecting its family name or angle values:

```text
Qiskit circuit
  -> qiskit transpile opt0 to {cx,rx,ry,rz,h}
  -> OpenQASM 2 serialization
  -> staq rotation optimizer on stdin
  -> OpenQASM 2 parse
  -> qiskit opt0 cleanup to {cx,rx,ry,rz,h}
  -> gates/depth/cx metrics
  -> 4-qubit operator equivalence up to global phase
```

The public optimizer is invoked with no witness-specific option. Completed
cells must satisfy the same phase-aligned matrix check as every other method,
with `atol=rtol=1e-9`.

## Protocol

- Families: the canonical rational CP family and the new independent-Pauli
  irrational-angle family.
- Requested sizes: 4k, 10k, 20k, 50k, 100k.
- Actual sizes: 3998, 9998, 19998, 49998, 99998.
- Hardware: the same SSH machine as every other headline method.
- Budget: 600 s per method per instance.
- Result source: `public_phase_folding_results.json` plus per-cell logs under
  `logs/`.

## Results and interpretation

All ten full-run cells completed and passed the declared equivalence check:

| Family | Requested | Gates/depth/CX | Runtime (s) | Max operator error |
|---|---:|---:|---:|---:|
| rational CP | 4k | 9188/4996/4788 | 0.688 | 2.00e-14 |
| rational CP | 10k | 22988/12496/11988 | 1.419 | 4.70e-14 |
| rational CP | 20k | 45988/24996/23988 | 2.659 | 9.76e-14 |
| rational CP | 50k | 114988/62496/59988 | 6.363 | 2.10e-13 |
| rational CP | 100k | 229988/124996/119988 | 12.568 | 4.21e-13 |
| irrational independent-Pauli | 4k | 3402/2201/2394 | 0.475 | 2.64e-14 |
| irrational independent-Pauli | 10k | 8502/5501/5994 | 0.882 | 6.01e-14 |
| irrational independent-Pauli | 20k | 17002/11001/11994 | 1.600 | 1.78e-13 |
| irrational independent-Pauli | 50k | 42502/27501/29994 | 3.723 | 3.65e-13 |
| irrational independent-Pauli | 100k | 85002/55001/59994 | 7.253 | 7.61e-13 |

The public folding pass reduces the lowered input but does not recover a
bounded form on either family. This is a completed configured-pipeline result,
not an impossibility theorem and not evidence that staq belongs to the formal
transducer class. The separate rebased PauliSimp result demonstrates the
classification's positive alternative: a generic pipeline can cross the
boundary when it reconstructs a compact aggregate representation.

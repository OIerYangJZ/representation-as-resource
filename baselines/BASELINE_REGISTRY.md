# W5 external baseline registry

This registry freezes the classification used by the W5 campaign.  A tool is
classified by the semantics of the configured pass sequence, not by whether a
particular output happens to be small.

| family | class | semantic scope | installed version | configurations |
|---|---|---|---|---|
| Qiskit preset level 3 | `local` | standard preset/local and block optimisations; no claimed global Pauli recovery | resolved at runtime (`qiskit`) | recommended native; unified `{cx,rz,h}` |
| TKET `PauliSimp` | `semantic-capable` | constructs a Pauli-gadget graph, accounts for commutation and phase folding, and resynthesises commuting sets | resolved at runtime (`pytket`) | recommended native; unified `{cx,rz,h}` |
| PyZX `full_reduce` | `semantic-capable` | global ZX-graph simplification followed by circuit extraction | resolved at runtime (`pyzx`) | recommended native; unified `{cx,rz,h}` |
| exact parity/phase table | `authors-reference` | exact CNOT-Rz parity extraction, coefficient folding modulo `2 pi`, and minimal constructive two-body lowering | repository Git revision | recommended semantic IR; unified `{cx,rz,h}` |

## Discovered but not used as a semantic baseline

- BQSKit 1.2.1 is installed.  It is a general synthesis framework, but the
  installed default workflows do not by themselves define a Pauli-network,
  phase-polynomial, or ZX/global-IR recovery path comparable to this family.
- Qiskit exposes `CommutationAnalysis`, `CommutativeCancellation`,
  `CollectLinearFunctions`, and block/unitary synthesis passes.  They remain
  part of the local/standard family here; the campaign does not relabel them
  as a global Pauli-network baseline.
- TKET also exposes `OptimisePhaseGadgets`, `ComposePhasePolyBoxes`,
  `GreedyPauliSimp`, and `GuidedPauliSimp`.  The frozen baseline uses the
  documented deterministic default `PauliSimp(Sets, Snake)` path so that one
  pass sequence, rather than a post-hoc best-of menu, is compared.

## Status and comparison policy

- `completed` requires the common
  `pyzx_rewrite_identity_up_to_global_phase_v1` certificate.
- A bridge or output that cannot be translated is `unsupported`.
- A certificate that cannot establish equality is `predicate_error`.
- `correctness_failure` is reserved for an explicit exact CNOT-Rz phase-table
  inequality; it is never inferred from an inconclusive rewrite certificate.
- Native and unified modes are reported separately.  Native semantic objects
  are not silently counted as target-basis gates.
- Conclusions are made within `local`, `semantic-capable`, and
  `authors-reference` classes.  The campaign does not select a single winner
  by mixing unlike native IR objects.

Runtime manifests record exact versions, available VCS commit metadata, pass
sequence, bridge, seed, basis, timeout, memory cap, input and output
certificates, and hashes of this registry and every YAML configuration.


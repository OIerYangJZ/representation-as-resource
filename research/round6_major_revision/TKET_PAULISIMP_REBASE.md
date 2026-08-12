# TKET PauliSimp Rebase Diagnosis

## Predicate failure

On the SSH environment (`pytket 2.18.0`, direct
`pytket.extensions.qiskit` bridge), the old pipeline is:

```python
tk_circuit = qiskit_to_tk(circuit)
pytket.passes.PauliSimp().apply(tk_circuit)
```

It fails before optimization with `Predicate requirements are not satisfied`.
The pass reports a `GateSetPredicate` containing, among others, `CX`, `Rz`,
`Rx`, `Ry`, `H`, `PauliExpBox`, and phase-gadget/Pauli-rotation gates, together
with `NoClassicalControlPredicate` and `NoMidMeasurePredicate`. The direct
bridge can retain operations outside that gate set. This is a configuration
predicate error, not a timeout, structural loss, or correctness result.

## Generic repaired preamble

The installed API was inspected before choosing names. The available passes
include `DecomposeBoxes`, `AutoRebase`, `RebaseTket`,
`RemoveRedundancies`, and `PauliSimp`. `RebaseTket` produces `TK1`, which is
not in the observed PauliSimp gate-set predicate in this version, so the
version-correct minimal generic pipeline is:

```python
DecomposeBoxes().apply(tk_circuit)
AutoRebase({OpType.CX, OpType.Rz, OpType.Rx}).apply(tk_circuit)
RemoveRedundancies().apply(tk_circuit)
PauliSimp().apply(tk_circuit)
RemoveRedundancies().apply(tk_circuit)
```

The target `{CX,Rz,Rx}` is a subset of PauliSimp's reported allowed gate set.
The sequence is identical for every family and size and contains no witness
matcher or angle special case. Output is converted back through the same
bridge and Qiskit target-basis cleanup as the other TKET rows.

## Naming and table disposition

- `TKET PauliSimp (unrebased configuration)`: provenance/status only;
  predicate-error cells are excluded from numerical quality comparisons.
- `TKET PauliSimp (rebased)`: eligible for headline completed comparisons;
  every completed cell must pass operator equivalence.

The full SSH suite shows the same separation on both witness families. The
unrebased direct-bridge configuration reports `predicate_error` in all ten
cells. The rebased pipeline completes and passes equivalence in all ten:

| Family | Requested | Gates/depth/CX | Runtime (s) |
|---|---:|---:|---:|
| rational CP | 4k | 52/29/19 | 1.197 |
| rational CP | 10k | 62/36/28 | 2.010 |
| rational CP | 20k | 59/27/20 | 3.555 |
| rational CP | 50k | 73/44/35 | 8.349 |
| rational CP | 100k | 66/37/28 | 16.238 |
| irrational independent-Pauli | 4k | 36/14/6 | 1.043 |
| irrational independent-Pauli | 10k | 35/15/8 | 1.617 |
| irrational independent-Pauli | 20k | 38/16/8 | 2.690 |
| irrational independent-Pauli | 50k | 36/15/8 | 5.988 |
| irrational independent-Pauli | 100k | 37/16/8 | 11.673 |

These values come from `tket_paulisimp_results.json`. The repaired row belongs
in the headline numerical comparison; the raw row remains only in the
predicate-error status/provenance record.

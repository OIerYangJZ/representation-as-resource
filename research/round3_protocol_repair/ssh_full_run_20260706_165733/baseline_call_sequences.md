# Round 3 Baseline Call Sequences

Generated: `2026-07-06T04:45:28+00:00`
Mode when generated: `full`
Full-run default uniform timeout: `600` seconds.
Uniform timeout disclosed in current output rows: `600` seconds.

All pipelines emit target-basis Qiskit circuits over `{cx, rx, ry, rz, h}` before metrics are recorded.

## qiskit opt3

```python
compiled = qiskit.transpile(
    circuit,
    basis_gates=TARGET_BASIS,
    optimization_level=3,
    layout_method="trivial",
    routing_method="none",
)
```

## PyZX configured bridge

```python
qasm_str = qiskit.qasm2.dumps(circuit)
zxc = pyzx.Circuit.from_qasm(qasm_str)
zxc = zxc.to_basic_gates()
pyzx.optimize.basic_optimization(zxc)
compiled = qiskit.transpile(qiskit.qasm2.loads(zxc.to_qasm()), basis_gates=TARGET_BASIS, optimization_level=0)
```

## PyZX full_reduce

```python
qasm_str = qiskit.qasm2.dumps(circuit)
zxc = pyzx.Circuit.from_qasm(qasm_str).to_basic_gates()
graph = zxc.to_graph()
pyzx.simplify.full_reduce(graph)
extracted = pyzx.extract_circuit(graph.copy()).to_basic_gates()
compiled = qiskit.transpile(qiskit.qasm2.loads(extracted.to_qasm()), basis_gates=TARGET_BASIS, optimization_level=0)
```

## TKET FullPeephole

```python
tk_circuit = qiskit_to_tk(circuit)  # if pytket.extensions.qiskit is importable
pytket.passes.FullPeepholeOptimise().apply(tk_circuit)
compiled = qiskit.transpile(tk_to_qiskit(tk_circuit), basis_gates=TARGET_BASIS, optimization_level=0)
```

When the qiskit extension is not importable, the runner uses the disclosed fallback:

```python
lowered = qiskit.transpile(circuit, basis_gates=TARGET_BASIS, optimization_level=0)
tk_circuit = pytket.qasm.circuit_from_qasm_str(qiskit.qasm2.dumps(lowered))
pytket.passes.FullPeepholeOptimise().apply(tk_circuit)
compiled = qiskit.transpile(qiskit.qasm2.loads(pytket.qasm.circuit_to_qasm_str(tk_circuit)), basis_gates=TARGET_BASIS, optimization_level=0)
```

## TKET PauliSimp

Same bridge/fallback as TKET FullPeephole, with:

```python
pytket.passes.PauliSimp().apply(tk_circuit)
```

## TKET GuidedPauliSimp

Same bridge/fallback as TKET FullPeephole, with:

```python
pytket.passes.GuidedPauliSimp().apply(tk_circuit)
```

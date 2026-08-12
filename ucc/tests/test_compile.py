import pytest
import math
import importlib
import cirq
from cirq import Circuit as CirqCircuit
from cirq import CNOT, H, X, LineQubit, NamedQubit
from cirq.testing import assert_same_circuits
from pytket import Circuit as TketCircuit
from qiskit import QuantumCircuit as QiskitCircuit
from qiskit import transpile as qiskit_transpile
from qiskit.converters import circuit_to_dag
from qiskit.quantum_info import Statevector
from qiskit.transpiler.passes import GatesInBasis, CountOps
from qiskit.transpiler.passes.utils import CheckMap
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.circuit.library import HGate, XGate
from qiskit.circuit.library import QAOAAnsatz
from qiskit.quantum_info import SparsePauliOp
from ucc.tests.mock_backends import Mybackend
from ucc import compile
from ucc.compile import (
    _CompileDispatchPlan,
    _ConjugationSpanNode,
    _InstructionSpanNode,
    _MirroredSelfInverseBlockNode,
    _RepeatedSpanNode,
    _SemanticCircuitLeafTerm,
    _SemanticConjugationTerm,
    _SemanticFourierLayerTerm,
    _SemanticMirroredSelfInverseTerm,
    _SemanticRepeatTerm,
    _SemanticSequenceTerm,
    _build_compile_dispatch_plan,
    _build_hierarchical_nodes,
    _build_repeated_run_term,
    _build_semantic_term,
    _compile_conjugation_reference,
    _compile_mirrored_self_inverse_reference,
    _compile_semantic_reference_with_local_opt,
    _compile_repeated_structure_dispatch,
    _compile_repeated_composite_prefix_reference,
    _compile_hierarchical_reference,
    _compile_backend_default_portfolio,
    _select_backend_repeated_run_candidates,
    _build_semantic_ir,
    _find_conjugation_span,
    _find_mirrored_self_inverse_block,
    _lower_semantic_ir_to_target_basis,
    _lower_semantic_term_to_circuit,
    _project_repeated_run_metrics,
    _semantic_compiled_term_metrics,
    _semantic_ir_to_term,
    _semantic_local_simplify,
    _merge_adjacent_parameterized_gates,
    _should_use_backend_repeated_run_shortcut,
    _should_direct_short_circuit_qiskit_source_preset,
    _should_direct_short_circuit_repeated_basis_source,
    _should_direct_short_circuit_small_basis_source_preset,
    _should_short_circuit_to_source_preset,
    _should_compare_against_direct_full_preset,
    _should_compare_against_presimplified_preset,
    _structural_pre_simplify,
)
from ucc.transpilers.ucc_defaults import UCCDefault1
from ucc.transpilers.aqc.mps_pass import MPSPass
import numpy as np


def repeated_block(block, repeats):
    circuit = QiskitCircuit(block.num_qubits)
    for _ in range(repeats):
        circuit.compose(block, inplace=True)
    return circuit


def qft_forward_block(num_qubits):
    qc = QiskitCircuit(num_qubits)
    for target in range(num_qubits):
        qc.h(target)
        for control in range(target + 1, num_qubits):
            qc.cp(math.pi / (2 ** (control - target)), control, target)
    for i in range(num_qubits // 2):
        qc.swap(i, num_qubits - 1 - i)
    return qc


def qft_inverse_block(num_qubits):
    qc = QiskitCircuit(num_qubits)
    for i in range(num_qubits // 2):
        qc.swap(i, num_qubits - 1 - i)
    for target in reversed(range(num_qubits)):
        for control in reversed(range(target + 1, num_qubits)):
            qc.cp(-math.pi / (2 ** (control - target)), control, target)
        qc.h(target)
    return qc


def qaoa_ring_circuit(num_qubits, layers, gamma=0.125, beta=0.25):
    qc = QiskitCircuit(num_qubits)
    for _ in range(layers):
        for qubit in range(num_qubits):
            qc.h(qubit)
        for qubit in range(num_qubits):
            neighbour = (qubit + 1) % num_qubits
            qc.cx(qubit, neighbour)
            qc.rz(gamma, neighbour)
            qc.cx(qubit, neighbour)
        for qubit in range(num_qubits):
            qc.rx(beta, qubit)
    return qc


def qpe_roundtrip_block(eval_qubits):
    total_qubits = eval_qubits + 1
    phase_qubit = eval_qubits
    qc = QiskitCircuit(total_qubits)

    for qubit in range(eval_qubits):
        qc.h(qubit)

    for qubit in range(eval_qubits):
        for _ in range(2**qubit):
            qc.cp(math.pi / 8, qubit, phase_qubit)

    for qubit in reversed(range(eval_qubits)):
        for control in reversed(range(qubit + 1, eval_qubits)):
            qc.cp(-math.pi / (2 ** (control - qubit)), control, qubit)
        qc.h(qubit)

    for qubit in range(eval_qubits // 2):
        qc.swap(qubit, eval_qubits - 1 - qubit)

    for qubit in range(eval_qubits):
        qc.h(qubit)

    for qubit in reversed(range(eval_qubits)):
        for _ in range(2**qubit):
            qc.cp(-math.pi / 8, qubit, phase_qubit)

    return qc


def conjugation_block():
    qc = QiskitCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.rz(0.25, 1)
    qc.cx(0, 1)
    qc.h(0)
    return qc


def mirrored_self_inverse_block():
    qc = QiskitCircuit(2)
    qc.cz(0, 1)
    qc.h(0)
    qc.x(1)
    qc.cx(0, 1)
    qc.x(1)
    qc.h(0)
    return qc


def grover_mirrored_block(num_qubits):
    qc = QiskitCircuit(num_qubits)
    oracle_qubits = list(range(num_qubits - 1))
    ancilla = num_qubits - 1

    for qubit in oracle_qubits:
        qc.h(qubit)
    qc.x(ancilla)
    qc.h(ancilla)
    qc.mcx(oracle_qubits, ancilla)

    for qubit in oracle_qubits:
        qc.h(qubit)
        qc.x(qubit)
    qc.h(oracle_qubits[-1])
    qc.mcx(oracle_qubits[:-1], oracle_qubits[-1])
    qc.h(oracle_qubits[-1])
    for qubit in oracle_qubits:
        qc.x(qubit)
        qc.h(qubit)

    for qubit in reversed(oracle_qubits):
        qc.h(qubit)
    qc.h(ancilla)
    qc.x(ancilla)

    return qc


def complete_graph_maxcut_operator(num_qubits):
    terms = []
    for i in range(num_qubits):
        for j in range(i + 1, num_qubits):
            label = ["I"] * num_qubits
            label[num_qubits - 1 - i] = "Z"
            label[num_qubits - 1 - j] = "Z"
            terms.append(("".join(label), 1.0))
    return SparsePauliOp.from_list(terms)


def random_area_law_circuit(N, seed=12345):
    """A circuit to generate a random area-law statevector.

    Parameters:
        N (int): Number of qubits

    Returns:
        QiskitCircuit: Output circuit
    """
    np.random.seed(seed)

    state = np.random.rand(2**N) + 1j * np.random.rand(2**N)
    state /= np.linalg.norm(state)

    circuit = QiskitCircuit(N)
    circuit.initialize(state, range(N))

    return circuit


def qcnn_circuit(N, seed=12345):
    """A circuit to generate a Quantum Convolutional Neural Network

    Parameters:
        N (int): Number of qubits

    Returns:
        QiskitCircuit: Output circuit
    """
    rng = np.random.default_rng(seed=seed)

    qc = QiskitCircuit(N)
    num_layers = int(np.ceil(np.log2(N)))
    i_conv = 0
    for i_layer in range(num_layers):
        for i_sub_layer in [0, 2**i_layer]:
            for i_q1 in range(i_sub_layer, N, 2 ** (i_layer + 1)):
                i_q2 = 2**i_layer + i_q1
                if i_q2 < N:
                    qc.rxx(rng.random(), i_q1, i_q2)
                    qc.ry(rng.random(), i_q1)
                    qc.ry(rng.random(), i_q2)
                    i_conv += 1

    return qc


def random_clifford_circuit(num_qubits, seed=12345):
    """Generate a random clifford circuit
    Parameters:
        num_qubits (int): Number of qubits
        seed (int): Optional. Seed the random number generator, default=12345

    Returns:
        QuantumCircuit: Clifford circuit
    """
    # This code is used to generate the QASM file
    from qiskit.circuit.random import random_clifford_circuit

    gates = ["cx", "cz", "cy", "swap", "x", "y", "z", "s", "sdg", "h"]
    qc = random_clifford_circuit(
        num_qubits,
        gates=gates,
        num_gates=10 * num_qubits * num_qubits,
        seed=seed,
    )
    return qc


def test_build_hierarchical_nodes_detects_dominant_repeated_run():
    repeated_gate_body = QiskitCircuit(2)
    repeated_gate_body.cx(0, 1)
    repeated_gate_body.h(0)
    repeated_gate = repeated_gate_body.to_gate(label="R")

    circuit = QiskitCircuit(2)
    circuit.x(0)
    for _ in range(10):
        circuit.append(repeated_gate, [0, 1])
    circuit.z(1)

    nodes = _build_hierarchical_nodes(circuit)

    assert nodes[0] == _InstructionSpanNode(0, 1)
    assert nodes[1] == _RepeatedSpanNode(1, 1, 10)
    assert nodes[2] == _InstructionSpanNode(11, 12)


def test_compile_hierarchical_reference_locally_compiles_repeated_composite_run(
    monkeypatch,
):
    compile_module = importlib.import_module("ucc.compile")

    repeated_gate_body = QiskitCircuit(2)
    repeated_gate_body.cx(0, 1)
    repeated_gate_body.h(0)
    repeated_gate = repeated_gate_body.to_gate(label="R")

    circuit = QiskitCircuit(2)
    for _ in range(10):
        circuit.append(repeated_gate, [0, 1])

    class FakeCompiler:
        target_backend = None
        target_gateset = {"u", "cx", "p"}

    transpile_call_sizes = []

    def wrapped_qiskit_transpile(subcircuit, **kwargs):
        transpile_call_sizes.append(len(subcircuit.data))
        compiled = QiskitCircuit(2)
        compiled.cx(0, 1)
        return compiled

    monkeypatch.setattr(compile_module, "qiskit_transpile", wrapped_qiskit_transpile)

    rebuilt_circuit = _compile_hierarchical_reference(circuit, FakeCompiler())

    assert rebuilt_circuit is not None
    assert len(rebuilt_circuit.data) == 10
    assert max(transpile_call_sizes) == 1


def test_qiskit_compile():
    circuit = QiskitCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    result_circuit = compile(circuit, return_format="original")
    assert isinstance(result_circuit, QiskitCircuit)


def test_cirq_compile():
    qubits = LineQubit.range(2)
    circuit = CirqCircuit(H(qubits[0]), CNOT(qubits[0], qubits[1]))
    result_circuit = compile(circuit, return_format="original")
    assert isinstance(result_circuit, CirqCircuit)


def test_tket_compile():
    circuit = TketCircuit(2)
    circuit.H(0)
    circuit.CX(0, 1)
    result_circuit = compile(circuit, return_format="original")
    assert isinstance(result_circuit, TketCircuit)


def test_callback():
    was_called = False

    def my_callback(**kwargs):
        nonlocal was_called
        was_called = True

    circuit = QiskitCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    _ = compile(circuit, callback=my_callback)
    assert was_called


def test_custom_pass():
    """Verify that a custom pass works with a non-qiskit input circuit"""

    class HtoX(TransformationPass):
        """Toy transformation that converts all H gates to X gates"""

        def run(self, dag):
            for node in dag.op_nodes():
                if isinstance(node.op, HGate):
                    dag.substitute_node(node, XGate())
            return dag

    # Example usage with a cirq circuit, stil showcasing the cross-frontend compatibility

    qubit = NamedQubit("q_0")
    cirq_circuit = CirqCircuit(H(qubit))

    post_compiler_circuit = compile(cirq_circuit, custom_passes=[HtoX()])
    assert cirq.equal_up_to_global_phase(
        cirq.unitary(post_compiler_circuit), cirq.unitary(CirqCircuit(X(qubit)))
    )


def test_qiskit_roundtrip_bypasses_qbraid_translate(monkeypatch):
    compile_module = importlib.import_module("ucc.compile")
    circuit = QiskitCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)

    monkeypatch.setattr(
        compile_module,
        "translate",
        lambda *args, **kwargs: pytest.fail(
            "qBraid translate should not run for qiskit->qiskit compile"
        ),
    )

    result_circuit = compile(circuit, return_format="qiskit")

    assert isinstance(result_circuit, QiskitCircuit)


def test_compile_target_backend_opset():
    circuit = QiskitCircuit(3)
    circuit.cz(0, 1)
    circuit.cz(0, 2)

    # Create a simple backend that does not have direct CX between 0 and 2
    t = Mybackend()
    # Check that the gates in the original circuit are not support by the target
    # to ensure this isn't a trival check
    assert set(op.name for op in circuit).issubset(t.operation_names) is False

    result_circuit = compile(
        circuit, return_format="original", target_backend=t
    )
    # Check that the gates in the final circuit are all supported on the target device
    assert set(op.name for op in result_circuit).issubset(t.operation_names)


def test_compile_target_backend_coupling_map():
    circuit = QiskitCircuit(3)
    circuit.cx(0, 1)
    circuit.cx(0, 2)

    # Create a simple target that does not have direct CX between 0 and 2
    t = Mybackend()
    result_circuit = compile(
        circuit, return_format="original", target_backend=t
    )
    # Check that the compiled circuit respects the coupling map of the target device
    analysis_pass = CheckMap(
        t.target.build_coupling_map(), property_set_field="check_map"
    )

    dag = circuit_to_dag(result_circuit)
    analysis_pass.run(dag)
    assert analysis_pass.property_set["check_map"]


def test_compile_with_no_target_gateset_or_device():
    """Test that the final circuit is in the default gateset if no `target_gateset` or `target_backend` is provided."""

    # Circuit not in the default target_gateset {"cx", "rz", "rx", "ry", "h"}
    circuit = QiskitCircuit(2)
    circuit.cz(0, 1)
    circuit.h(0)

    result_circuit = compile(
        circuit,
    )

    assert set(op.name for op in result_circuit).issubset(
        {"cx", "rz", "rx", "ry", "h"}
    )

    # Circuit already in the default target_gateset {"cx", "rz", "rx", "ry", "h"}
    circuit = QiskitCircuit(2)
    circuit.cx(0, 1)
    circuit.h(0)

    result_circuit = compile(
        circuit,
    )

    assert set(op.name for op in result_circuit).issubset(
        {"cx", "rz", "rx", "ry", "h"}
    )


def test_raise_error_on_bad_backend():
    circuit = QiskitCircuit(2)
    circuit.cx(0, 1)
    circuit.h(0)

    class BadBackend:
        pass

    with pytest.raises(ValueError):
        _ = compile(circuit, target_backend=BadBackend())


def test_bqskit_compile():
    from ucc.transpilers.ucc_bqskit import BQSKitTransformationPass

    bqskit_pass = BQSKitTransformationPass()
    qasm = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[3];
        h q[0];
        cp(1.5707963267948966) q[1], q[0];
        h q[1];
        cp(0.7853981633974483) q[2], q[0];
        cp(1.5707963267948966) q[2], q[1];
        h q[2];
        swap q[0], q[2];
        h q[0];
        cp(-1.5707963267948966) q[1], q[0];
        h q[1];
        cp(-0.7853981633974483) q[2], q[0];
        cp(-1.5707963267948966) q[2], q[1];
        h q[2];
        swap q[0], q[2];
        """
    # This qasm describes a 3-qubit QFT followed by a 3-qubit inverse QFT.
    # This circuit resolves to the identity, but that's not obvious to
    # most synthesis tools.
    # BQSKit using LEAP will usually remove all 2-qubit gates
    # from the circuit, leaving 3 u3 gates that don't do anything
    # because it just focuses on the 2-qubit gates. A further
    # post processing step would remove these 1-qubit gates, but in
    # more realistic use cases, its often not worth the extra processing.

    def get_post_cx_count(circuit, custom_passes=[]):
        post_compiler_circuit = compile(qasm, custom_passes=custom_passes)
        analysis_pass = CountOps()
        dag = circuit_to_dag(
            QiskitCircuit.from_qasm_str(post_compiler_circuit)
        )
        analysis_pass.run(dag)
        if "cx" in analysis_pass.property_set["count_ops"]:
            return analysis_pass.property_set["count_ops"]["cx"]
        else:
            return 0

    assert get_post_cx_count(qasm, [bqskit_pass]) < get_post_cx_count(qasm)


@pytest.mark.parametrize("N", [5, 8, 10, 11])
def test_compile_with_mps_pass(N):
    """Test that the circuit compiled by `MPSPass` works as expected."""
    circuit = random_area_law_circuit(N)
    circuit = qiskit_transpile(circuit, basis_gates=["u3", "cx"])

    compiled_circuit = compile(
        circuit, target_gateset=["u3", "cx"], custom_passes=[MPSPass()]
    )

    fidelity = np.abs(
        np.vdot(Statevector(circuit).data, Statevector(compiled_circuit).data)
    )

    assert np.abs(fidelity) > 0.9

    assert circuit.depth() > compiled_circuit.depth()
    assert circuit.count_ops().get("cx", 0) > compiled_circuit.count_ops().get(
        "cx", 0
    )


def test_compile_trivial_state_with_mps_pass():
    """Test that `MPSPass` does not use CX gates when state has no entanglement."""
    qasm = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[10];
        ry(pi/2) q[9];
        rx(pi) q[9];
        rz(pi/4) q[9];
        cx q[9],q[8];
        rz(-pi/4) q[8];
        cx q[9],q[8];
        rz(pi/4) q[8];
        ry(pi/2) q[8];
        rx(pi) q[8];
        rz(pi/4) q[8];
        rz(pi/8) q[9];
        cx q[9],q[7];
        rz(-pi/8) q[7];
        cx q[9],q[7];
        rz(pi/8) q[7];
        cx q[8],q[7];
        rz(-pi/4) q[7];
        cx q[8],q[7];
        rz(pi/4) q[7];
        ry(pi/2) q[7];
        rx(pi) q[7];
        rz(pi/4) q[7];
        rz(pi/8) q[8];
        rz(pi/16) q[9];
        cx q[9],q[6];
        rz(-pi/16) q[6];
        cx q[9],q[6];
        rz(pi/16) q[6];
        cx q[8],q[6];
        rz(-pi/8) q[6];
        cx q[8],q[6];
        rz(pi/8) q[6];
        cx q[7],q[6];
        rz(-pi/4) q[6];
        cx q[7],q[6];
        rz(pi/4) q[6];
        ry(pi/2) q[6];
        rx(pi) q[6];
        rz(pi/4) q[6];
        rz(pi/8) q[7];
        rz(pi/16) q[8];
        rz(pi/32) q[9];
        cx q[9],q[5];
        rz(-pi/32) q[5];
        cx q[9],q[5];
        rz(pi/32) q[5];
        cx q[8],q[5];
        rz(-pi/16) q[5];
        cx q[8],q[5];
        rz(pi/16) q[5];
        cx q[7],q[5];
        rz(-pi/8) q[5];
        cx q[7],q[5];
        rz(pi/8) q[5];
        cx q[6],q[5];
        rz(-pi/4) q[5];
        cx q[6],q[5];
        rz(pi/4) q[5];
        ry(pi/2) q[5];
        rx(pi) q[5];
        rz(pi/4) q[5];
        rz(pi/8) q[6];
        rz(pi/16) q[7];
        rz(pi/32) q[8];
        rz(pi/64) q[9];
        cx q[9],q[4];
        rz(-pi/64) q[4];
        cx q[9],q[4];
        rz(pi/64) q[4];
        cx q[8],q[4];
        rz(-pi/32) q[4];
        cx q[8],q[4];
        rz(pi/32) q[4];
        cx q[7],q[4];
        rz(-pi/16) q[4];
        cx q[7],q[4];
        rz(pi/16) q[4];
        cx q[6],q[4];
        rz(-pi/8) q[4];
        cx q[6],q[4];
        rz(pi/8) q[4];
        cx q[5],q[4];
        rz(-pi/4) q[4];
        cx q[5],q[4];
        rz(pi/4) q[4];
        ry(pi/2) q[4];
        rx(pi) q[4];
        rz(pi/4) q[4];
        rz(pi/8) q[5];
        rz(pi/16) q[6];
        rz(pi/32) q[7];
        rz(pi/64) q[8];
        rz(pi/128) q[9];
        cx q[9],q[3];
        rz(-pi/128) q[3];
        cx q[9],q[3];
        rz(pi/128) q[3];
        cx q[8],q[3];
        rz(-pi/64) q[3];
        cx q[8],q[3];
        rz(pi/64) q[3];
        cx q[7],q[3];
        rz(-pi/32) q[3];
        cx q[7],q[3];
        rz(pi/32) q[3];
        cx q[6],q[3];
        rz(-pi/16) q[3];
        cx q[6],q[3];
        rz(pi/16) q[3];
        cx q[5],q[3];
        rz(-pi/8) q[3];
        cx q[5],q[3];
        rz(pi/8) q[3];
        cx q[4],q[3];
        rz(-pi/4) q[3];
        cx q[4],q[3];
        rz(pi/4) q[3];
        ry(pi/2) q[3];
        rx(pi) q[3];
        rz(pi/4) q[3];
        rz(pi/8) q[4];
        rz(pi/16) q[5];
        rz(pi/32) q[6];
        rz(pi/64) q[7];
        rz(pi/128) q[8];
        rz(pi/256) q[9];
        cx q[9],q[2];
        rz(-pi/256) q[2];
        cx q[9],q[2];
        rz(pi/256) q[2];
        cx q[8],q[2];
        rz(-pi/128) q[2];
        cx q[8],q[2];
        rz(pi/128) q[2];
        cx q[7],q[2];
        rz(-pi/64) q[2];
        cx q[7],q[2];
        rz(pi/64) q[2];
        cx q[6],q[2];
        rz(-pi/32) q[2];
        cx q[6],q[2];
        rz(pi/32) q[2];
        cx q[5],q[2];
        rz(-pi/16) q[2];
        cx q[5],q[2];
        rz(pi/16) q[2];
        cx q[4],q[2];
        rz(-pi/8) q[2];
        cx q[4],q[2];
        rz(pi/8) q[2];
        cx q[3],q[2];
        rz(-pi/4) q[2];
        cx q[3],q[2];
        rz(pi/4) q[2];
        ry(pi/2) q[2];
        rx(pi) q[2];
        rz(pi/4) q[2];
        rz(pi/8) q[3];
        rz(pi/16) q[4];
        rz(pi/32) q[5];
        rz(pi/64) q[6];
        rz(pi/128) q[7];
        rz(pi/256) q[8];
        rz(pi/512) q[9];
        cx q[9],q[1];
        rz(-pi/512) q[1];
        cx q[9],q[1];
        rz(pi/512) q[1];
        cx q[8],q[1];
        rz(-pi/256) q[1];
        cx q[8],q[1];
        rz(pi/256) q[1];
        cx q[7],q[1];
        rz(-pi/128) q[1];
        cx q[7],q[1];
        rz(pi/128) q[1];
        cx q[6],q[1];
        rz(-pi/64) q[1];
        cx q[6],q[1];
        rz(pi/64) q[1];
        cx q[5],q[1];
        rz(-pi/32) q[1];
        cx q[5],q[1];
        rz(pi/32) q[1];
        cx q[4],q[1];
        rz(-pi/16) q[1];
        cx q[4],q[1];
        rz(pi/16) q[1];
        cx q[3],q[1];
        rz(-pi/8) q[1];
        cx q[3],q[1];
        rz(pi/8) q[1];
        cx q[2],q[1];
        rz(-pi/4) q[1];
        cx q[2],q[1];
        rz(pi/4) q[1];
        ry(pi/2) q[1];
        rx(pi) q[1];
        rz(pi/4) q[1];
        rz(pi/8) q[2];
        rz(pi/16) q[3];
        rz(pi/32) q[4];
        rz(pi/64) q[5];
        rz(pi/128) q[6];
        rz(pi/256) q[7];
        rz(pi/512) q[8];
        rz(pi/1024) q[9];
        cx q[9],q[0];
        rz(-pi/1024) q[0];
        cx q[9],q[0];
        rz(pi/1024) q[0];
        cx q[8],q[0];
        rz(-pi/512) q[0];
        cx q[8],q[0];
        rz(pi/512) q[0];
        cx q[7],q[0];
        rz(-pi/256) q[0];
        cx q[7],q[0];
        rz(pi/256) q[0];
        cx q[6],q[0];
        rz(-pi/128) q[0];
        cx q[6],q[0];
        rz(pi/128) q[0];
        cx q[5],q[0];
        rz(-pi/64) q[0];
        cx q[5],q[0];
        rz(pi/64) q[0];
        cx q[4],q[0];
        rz(-pi/32) q[0];
        cx q[4],q[0];
        rz(pi/32) q[0];
        cx q[3],q[0];
        rz(-pi/16) q[0];
        cx q[3],q[0];
        rz(pi/16) q[0];
        cx q[2],q[0];
        rz(-pi/8) q[0];
        cx q[2],q[0];
        rz(pi/8) q[0];
        cx q[1],q[0];
        rz(-pi/4) q[0];
        cx q[1],q[0];
        rz(pi/4) q[0];
        ry(pi/2) q[0];
        rx(pi) q[0];
        cx q[0],q[9];
        cx q[1],q[8];
        cx q[2],q[7];
        cx q[3],q[6];
        cx q[4],q[5];
        cx q[5],q[4];
        cx q[4],q[5];
        cx q[6],q[3];
        cx q[3],q[6];
        cx q[7],q[2];
        cx q[2],q[7];
        cx q[8],q[1];
        cx q[1],q[8];
        cx q[9],q[0];
        cx q[0],q[9];
    """
    circuit = QiskitCircuit.from_qasm_str(qasm)

    compiled_circuit = compile(
        circuit, target_gateset=["u3", "cx"], custom_passes=[MPSPass()]
    )

    fidelity = np.abs(
        np.vdot(Statevector(circuit).data, Statevector(compiled_circuit).data)
    )

    assert compiled_circuit.count_ops().get("cx", 0) == 0


def repeated_qft_inverse_block(repeats=4):
    circuit = QiskitCircuit(8)
    base_block = QiskitCircuit(8)

    for target in range(8):
        base_block.h(target)
        for control in range(target + 1, 8):
            base_block.cp(np.pi / (2 ** (control - target)), control, target)

    for i in range(4):
        base_block.swap(i, 7 - i)

    for i in range(4):
        base_block.swap(i, 7 - i)

    for target in reversed(range(8)):
        for control in reversed(range(target + 1, 8)):
            base_block.cp(
                -np.pi / (2 ** (control - target)), control, target
            )
        base_block.h(target)

    for _ in range(repeats):
        circuit.compose(base_block, inplace=True)
    return circuit


def test_compile_cancels_repeated_qft_inverse_pairs():
    circuit = repeated_qft_inverse_block()

    compiled_circuit = compile(circuit, return_format="qiskit")

    assert len(circuit.data) > 0
    assert len(compiled_circuit.data) == 0


def test_compile_prefers_preset_reference_for_repeated_qft_structure():
    circuit = repeated_block(qft_forward_block(8), repeats=8)

    basis_translated_circuit = qiskit_transpile(
        circuit,
        basis_gates=UCCDefault1.DEFAULT_GATESET,
        optimization_level=0,
    )
    preset_reference = qiskit_transpile(
        circuit,
        basis_gates=list(UCCDefault1.DEFAULT_GATESET),
        optimization_level=3,
        layout_method="trivial",
        routing_method="none",
    )
    result_circuit = compile(circuit, return_format="qiskit")

    assert len(preset_reference.data) < len(basis_translated_circuit.data)
    assert result_circuit.count_ops() == preset_reference.count_ops()
    assert result_circuit.depth() == preset_reference.depth()


def test_compile_reuses_optimized_prefix_block_for_large_repeated_structure(
    monkeypatch,
):
    circuit = repeated_block(qft_forward_block(8), repeats=8)

    compile_module = importlib.import_module("ucc.compile")
    monkeypatch.setattr(compile_module, "_MAX_FULL_PRESET_REFERENCE_SIZE", 1)
    monkeypatch.setattr(
        UCCDefault1,
        "run",
        lambda self, *args, **kwargs: pytest.fail(
            "large exact repeats should bypass the default UCC pipeline"
        ),
    )

    optimized_block = qiskit_transpile(
        qft_forward_block(8),
        basis_gates=list(UCCDefault1.DEFAULT_GATESET),
        optimization_level=3,
        layout_method="trivial",
        routing_method="none",
    )
    expected_circuit = repeated_block(optimized_block, repeats=8)

    result_circuit = compile(circuit, return_format="qiskit")

    assert result_circuit.count_ops() == expected_circuit.count_ops()
    assert result_circuit.depth() == expected_circuit.depth()


def test_compile_bypasses_default_ucc_for_large_dominant_prefix_with_tail(
    monkeypatch,
):
    circuit = repeated_block(qft_forward_block(8), repeats=8)
    circuit.h(0)

    compile_module = importlib.import_module("ucc.compile")
    monkeypatch.setattr(compile_module, "_MAX_FULL_PRESET_REFERENCE_SIZE", 1)
    monkeypatch.setattr(compile_module, "_FAST_PREFIX_SCAN_SIZE", 1)
    monkeypatch.setattr(
        UCCDefault1,
        "run",
        lambda self, *args, **kwargs: pytest.fail(
            "dominant repeated prefixes should bypass the default UCC pipeline"
        ),
    )

    optimized_block = qiskit_transpile(
        qft_forward_block(8),
        basis_gates=list(UCCDefault1.DEFAULT_GATESET),
        optimization_level=3,
        layout_method="trivial",
        routing_method="none",
    )
    expected_circuit = repeated_block(optimized_block, repeats=8)
    expected_circuit.h(0)
    basis_translated_circuit = qiskit_transpile(
        circuit,
        basis_gates=list(UCCDefault1.DEFAULT_GATESET),
        optimization_level=0,
    )

    result_circuit = compile(circuit, return_format="qiskit")

    assert len(result_circuit.data) < len(basis_translated_circuit.data)
    assert result_circuit.depth() < basis_translated_circuit.depth()


def test_compile_keeps_qaoa_ring_at_basis_translation_scale():
    circuit = qaoa_ring_circuit(8, layers=6)

    basis_translated_circuit = qiskit_transpile(
        circuit,
        basis_gates=UCCDefault1.DEFAULT_GATESET,
        optimization_level=0,
    )
    result_circuit = compile(circuit, return_format="qiskit")

    assert result_circuit.count_ops() == basis_translated_circuit.count_ops()
    assert result_circuit.depth() == basis_translated_circuit.depth()


def test_compile_qpe_style_prefers_non_regressing_candidate():
    circuit = repeated_block(qpe_roundtrip_block(3), repeats=6)

    basis_translated_circuit = qiskit_transpile(
        circuit,
        basis_gates=UCCDefault1.DEFAULT_GATESET,
        optimization_level=0,
    )
    result_circuit = compile(circuit, return_format="qiskit")

    assert len(result_circuit.data) < len(basis_translated_circuit.data)
    assert result_circuit.depth() < basis_translated_circuit.depth()


def test_structural_pre_simplify_reduces_grover_mirrored_prefix():
    circuit = repeated_block(grover_mirrored_block(6), repeats=4)

    simplified_circuit = _structural_pre_simplify(circuit)

    assert len(simplified_circuit.data) < len(circuit.data)
    assert simplified_circuit.depth() < circuit.depth()


def test_merge_adjacent_parameterized_gates_collapses_repeated_cp():
    circuit = QiskitCircuit(2)
    for _ in range(4):
        circuit.cp(math.pi / 8, 0, 1)

    merged_circuit = _merge_adjacent_parameterized_gates(circuit)

    assert len(merged_circuit.data) == 1
    assert merged_circuit.data[0].operation.name == "cp"
    assert merged_circuit.data[0].operation.params[0] == pytest.approx(
        math.pi / 2
    )


def test_semantic_local_simplify_canonicalizes_commuting_diagonal_phase_span():
    circuit = QiskitCircuit(2)
    circuit.cp(0.1, 0, 1)
    circuit.rz(0.2, 0)
    circuit.cp(0.3, 0, 1)
    circuit.p(0.4, 1)

    simplified_circuit = _semantic_local_simplify(circuit)

    assert len(simplified_circuit.data) == 3
    assert simplified_circuit.data[0].operation.name == "cp"
    assert simplified_circuit.data[0].operation.params[0] == pytest.approx(0.4)


def test_compile_presimplifies_fourier_phase_sandwich_before_direct_shortcut():
    circuit = QiskitCircuit(4)
    for qubit in range(4):
        circuit.h(qubit)
    for _ in range(8):
        for qubit in range(4):
            circuit.rz(math.pi / (7 + qubit), qubit)
        for control in range(4):
            for target in range(control + 1, 4):
                circuit.cp(math.pi / (11 + control + target), control, target)
    for qubit in range(4):
        circuit.h(qubit)

    target_gateset = {"cx", "rx", "ry", "rz", "h"}
    assert not _should_direct_short_circuit_qiskit_source_preset(
        circuit, target_gateset, None, False
    )

    presimplified = _structural_pre_simplify(circuit)
    assert len(presimplified.data) == 18

    compiled = compile(
        circuit, return_format="qiskit", target_gateset=target_gateset
    )

    assert sum(compiled.count_ops().values()) <= 50
    assert Statevector(circuit).equiv(Statevector(compiled))


def test_semantic_ir_lowering_preserves_qpe_roundtrip_unitary():
    circuit = qpe_roundtrip_block(3)

    semantic_ir = _build_semantic_ir(_semantic_local_simplify(circuit))

    assert semantic_ir is not None
    assert len(semantic_ir) == 1
    assert type(semantic_ir[0]).__name__ == "_SemanticPhaseLadderNode"
    lowered_circuit = _lower_semantic_ir_to_target_basis(circuit, semantic_ir)
    assert lowered_circuit is not None
    assert Statevector(circuit).equiv(Statevector(lowered_circuit))


def test_semantic_term_lowering_preserves_qpe_roundtrip_unitary():
    circuit = qpe_roundtrip_block(3)

    semantic_ir = _build_semantic_ir(_semantic_local_simplify(circuit))

    assert semantic_ir is not None
    semantic_term = _semantic_ir_to_term(semantic_ir)
    lowered_circuit = _lower_semantic_term_to_circuit(circuit, semantic_term)

    assert lowered_circuit is not None
    assert Statevector(circuit).equiv(Statevector(lowered_circuit))


def test_build_semantic_term_promotes_qpe_roundtrip_to_fourier_term():
    template_circuit, semantic_term = _build_semantic_term(
        _semantic_local_simplify(qpe_roundtrip_block(3))
    )

    assert template_circuit is not None
    assert isinstance(semantic_term, _SemanticFourierLayerTerm)
    assert len(semantic_term.stages) >= 2


def test_backend_semantic_reference_path_is_available_for_qpe_roundtrip():
    circuit = _semantic_local_simplify(qpe_roundtrip_block(3))
    compiler = UCCDefault1(target_backend=Mybackend())

    semantic_reference = _compile_semantic_reference_with_local_opt(
        circuit, compiler
    )

    assert semantic_reference is not None


def test_semantic_compiled_term_metrics_match_repeated_run_projection():
    prefix_circuit = QiskitCircuit(2)
    prefix_circuit.h(0)
    block_circuit = QiskitCircuit(2)
    block_circuit.cx(0, 1)
    block_circuit.rz(0.25, 1)
    suffix_circuit = QiskitCircuit(2)
    suffix_circuit.rx(0.5, 0)

    repeated_term = _build_repeated_run_term(
        prefix_circuit, block_circuit, suffix_circuit, 3
    )
    projected_metrics = _project_repeated_run_metrics(
        prefix_circuit, block_circuit, suffix_circuit, 3
    )

    assert projected_metrics == _semantic_compiled_term_metrics(repeated_term)


def test_semantic_conjugation_term_lowering_preserves_unitary():
    prefix_circuit = QiskitCircuit(2)
    prefix_circuit.h(0)
    prefix_circuit.cx(0, 1)
    center_circuit = QiskitCircuit(2)
    center_circuit.rz(0.25, 1)

    conjugation_term = _SemanticConjugationTerm(
        _SemanticCircuitLeafTerm(prefix_circuit),
        _SemanticCircuitLeafTerm(center_circuit),
    )
    lowered_circuit = _lower_semantic_term_to_circuit(
        conjugation_block(), conjugation_term
    )

    assert lowered_circuit is not None
    assert Statevector(conjugation_block()).equiv(Statevector(lowered_circuit))


def test_build_semantic_term_detects_mirrored_self_inverse_structure():
    template_circuit, semantic_term = _build_semantic_term(
        mirrored_self_inverse_block()
    )

    assert template_circuit is not None
    assert isinstance(semantic_term, _SemanticMirroredSelfInverseTerm)


def test_semantic_mirrored_self_inverse_term_lowering_preserves_unitary():
    template_circuit, semantic_term = _build_semantic_term(
        mirrored_self_inverse_block()
    )

    assert isinstance(semantic_term, _SemanticMirroredSelfInverseTerm)
    lowered_circuit = _lower_semantic_term_to_circuit(
        template_circuit, semantic_term
    )

    assert lowered_circuit is not None
    assert Statevector(mirrored_self_inverse_block()).equiv(
        Statevector(lowered_circuit)
    )


def test_find_conjugation_span_detects_prefix_center_inverse_prefix():
    circuit = conjugation_block()

    conjugation_span = _find_conjugation_span(circuit)

    assert conjugation_span == _ConjugationSpanNode(
        prefix_size=2,
        center_start=2,
        center_end=3,
    )


def test_compile_conjugation_reference_preserves_unitary():
    circuit = conjugation_block()
    compiler = UCCDefault1(target_gateset={"cx", "rx", "ry", "rz", "h"})

    reference_circuit = _compile_conjugation_reference(circuit, compiler)

    assert reference_circuit is not None
    assert Statevector(circuit).equiv(Statevector(reference_circuit))


def test_find_mirrored_self_inverse_block_detects_diagonal_prefix_shell():
    circuit = mirrored_self_inverse_block()

    mirrored_block = _find_mirrored_self_inverse_block(circuit)

    assert mirrored_block == _MirroredSelfInverseBlockNode(
        diagonal_prefix_size=1,
        shell_prefix_size=2,
    )


def test_compile_mirrored_self_inverse_reference_preserves_unitary():
    circuit = mirrored_self_inverse_block()
    compiler = UCCDefault1(target_gateset={"cx", "rx", "ry", "rz", "h"})

    reference_circuit = _compile_mirrored_self_inverse_reference(
        circuit, compiler
    )

    assert reference_circuit is not None
    assert Statevector(circuit).equiv(Statevector(reference_circuit))


def test_presimplified_preset_heuristic_targets_low_entanglement_mirrored_case():
    grover_circuit = repeated_block(grover_mirrored_block(6), repeats=8)
    simplified_grover = _structural_pre_simplify(grover_circuit)
    qpe_circuit = repeated_block(qpe_roundtrip_block(3), repeats=8)
    simplified_qpe = _structural_pre_simplify(qpe_circuit)

    assert _should_compare_against_presimplified_preset(
        grover_circuit, simplified_grover
    )
    assert not _should_compare_against_presimplified_preset(
        qpe_circuit, simplified_qpe
    )


def test_compile_short_circuits_to_presimplified_preset(monkeypatch):
    compile_module = importlib.import_module("ucc.compile")
    expected_circuit = QiskitCircuit(2)
    expected_circuit.rx(math.pi, 0)

    monkeypatch.setattr(
        compile_module, "_structural_pre_simplify", lambda circuit: circuit
    )
    monkeypatch.setattr(
        compile_module,
        "_should_compare_against_presimplified_preset",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(
        compile_module,
        "_compile_presimplified_full_preset_reference",
        lambda *args, **kwargs: expected_circuit,
    )
    monkeypatch.setattr(
        compile_module,
        "_find_repeated_prefix",
        lambda *args, **kwargs: pytest.fail(
            "presimplified preset early return should bypass repeated-prefix detection"
        ),
    )

    result_circuit = compile(QiskitCircuit(2), return_format="qiskit")

    assert result_circuit.count_ops() == expected_circuit.count_ops()


def test_direct_full_preset_heuristic_targets_unsimplified_dominant_repeat():
    qft_control_circuit = repeated_block(qft_forward_block(8), repeats=8)
    qft_control_simplified = _structural_pre_simplify(qft_control_circuit)

    assert _should_compare_against_direct_full_preset(
        qft_control_circuit, qft_control_simplified, (40, 8)
    )
    assert not _should_compare_against_direct_full_preset(
        repeated_block(qpe_roundtrip_block(3), repeats=8),
        _structural_pre_simplify(repeated_block(qpe_roundtrip_block(3), repeats=8)),
        (50, 8),
    )


def test_source_preset_short_circuit_heuristic_detects_medium_composite_ansatz():
    ansatz = QAOAAnsatz(
        complete_graph_maxcut_operator(32), reps=24, flatten=True
    )
    ansatz = ansatz.assign_parameters([0.1] * len(ansatz.parameters))
    translated = qiskit_transpile(
        ansatz,
        basis_gates=["cx", "rx", "ry", "rz", "h"],
        optimization_level=0,
    )
    compiler = UCCDefault1()

    assert _should_short_circuit_to_source_preset(
        ansatz, translated, compiler
    )


def test_direct_qiskit_source_fast_path_detects_composite_ansatz():
    ansatz = QAOAAnsatz(
        complete_graph_maxcut_operator(32), reps=24, flatten=True
    )
    ansatz = ansatz.assign_parameters([0.1] * len(ansatz.parameters))

    assert _should_direct_short_circuit_qiskit_source_preset(
        ansatz,
        {"cx", "rx", "ry", "rz", "h"},
        None,
        False,
    )


def test_direct_small_basis_source_fast_path_detects_small_in_basis_circuit():
    circuit = QiskitCircuit(3)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.rz(0.2, 1)
    circuit.rx(0.1, 2)

    assert _should_direct_short_circuit_small_basis_source_preset(
        circuit,
        {"cx", "rx", "ry", "rz", "h"},
        None,
        False,
    )


def test_direct_repeated_basis_source_fast_path_detects_large_repeated_basis_circuit():
    block = QiskitCircuit(3)
    block.cx(0, 1)
    block.rz(0.2, 1)
    block.rx(0.1, 2)
    circuit = repeated_block(block, 1500)

    assert _should_direct_short_circuit_repeated_basis_source(
        circuit,
        {"cx", "rx", "ry", "rz", "h"},
        None,
        False,
    )


def test_compile_direct_qiskit_source_fast_path_bypasses_ucc_default(monkeypatch):
    compile_module = importlib.import_module("ucc.compile")

    ansatz = QAOAAnsatz(
        complete_graph_maxcut_operator(32), reps=24, flatten=True
    )
    ansatz = ansatz.assign_parameters([0.1] * len(ansatz.parameters))
    expected_circuit = qiskit_transpile(
        ansatz,
        basis_gates=["cx", "rx", "ry", "rz", "h"],
        optimization_level=3,
        layout_method="trivial",
        routing_method="none",
    )

    original_qiskit_transpile = compile_module.qiskit_transpile

    def wrapped_qiskit_transpile(*args, **kwargs):
        if kwargs.get("optimization_level") == 3:
            return expected_circuit
        return original_qiskit_transpile(*args, **kwargs)

    monkeypatch.setattr(compile_module, "qiskit_transpile", wrapped_qiskit_transpile)
    monkeypatch.setattr(
        UCCDefault1,
        "__init__",
        lambda *args, **kwargs: pytest.fail(
            "direct qiskit-source fast path should bypass UCCDefault1 construction"
        ),
    )

    result_circuit = compile(ansatz, return_format="qiskit")

    assert result_circuit.count_ops() == expected_circuit.count_ops()


def test_compile_short_circuits_to_source_preset(monkeypatch):
    compile_module = importlib.import_module("ucc.compile")

    ansatz = QAOAAnsatz(
        complete_graph_maxcut_operator(32), reps=24, flatten=True
    )
    ansatz = ansatz.assign_parameters([0.1] * len(ansatz.parameters))
    expected_circuit = qiskit_transpile(
        ansatz,
        basis_gates=["cx", "rx", "ry", "rz", "h"],
        optimization_level=0,
    )

    monkeypatch.setattr(
        compile_module,
        "_should_direct_short_circuit_qiskit_source_preset",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setattr(
        compile_module,
        "_compile_presimplified_full_preset_reference",
        lambda *args, **kwargs: expected_circuit,
    )
    monkeypatch.setattr(
        compile_module,
        "_structural_pre_simplify",
        lambda *args, **kwargs: pytest.fail(
            "source preset short-circuit should bypass structural preprocessing"
        ),
    )
    monkeypatch.setattr(
        UCCDefault1,
        "run",
        lambda *args, **kwargs: pytest.fail(
            "source preset short-circuit should bypass default UCC"
        ),
    )

    result_circuit = compile(ansatz, return_format="qiskit")

    assert result_circuit.count_ops() == expected_circuit.count_ops()


def test_compile_direct_small_basis_source_fast_path_bypasses_ucc_default(
    monkeypatch,
):
    compile_module = importlib.import_module("ucc.compile")

    circuit = QiskitCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.rz(0.2, 1)

    expected_circuit = qiskit_transpile(
        circuit,
        basis_gates=["cx", "rx", "ry", "rz", "h"],
        optimization_level=3,
        layout_method="trivial",
        routing_method="none",
    )

    monkeypatch.setattr(
        compile_module,
        "_should_direct_short_circuit_qiskit_source_preset",
        lambda *args, **kwargs: False,
    )

    original_qiskit_transpile = compile_module.qiskit_transpile

    def wrapped_qiskit_transpile(*args, **kwargs):
        if kwargs.get("optimization_level") == 3:
            return expected_circuit
        return original_qiskit_transpile(*args, **kwargs)

    monkeypatch.setattr(compile_module, "qiskit_transpile", wrapped_qiskit_transpile)
    monkeypatch.setattr(
        UCCDefault1,
        "__init__",
        lambda *args, **kwargs: pytest.fail(
            "direct small-basis source fast path should bypass UCCDefault1 construction"
        ),
    )

    result_circuit = compile(circuit, return_format="qiskit")

    assert result_circuit.count_ops() == expected_circuit.count_ops()


def test_compile_direct_repeated_basis_source_fast_path_bypasses_ucc_default(
    monkeypatch,
):
    compile_module = importlib.import_module("ucc.compile")

    block = QiskitCircuit(3)
    block.cx(0, 1)
    block.rz(0.2, 1)
    block.rx(0.1, 2)
    circuit = repeated_block(block, 1500)

    monkeypatch.setattr(
        compile_module,
        "_should_direct_short_circuit_qiskit_source_preset",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setattr(
        compile_module,
        "_should_direct_short_circuit_small_basis_source_preset",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setattr(
        UCCDefault1,
        "__init__",
        lambda *args, **kwargs: pytest.fail(
            "direct repeated-basis source fast path should bypass UCCDefault1 construction"
        ),
    )

    result_circuit = compile(circuit, return_format="qiskit")

    assert result_circuit.count_ops() == circuit.count_ops()


def test_compile_dispatches_repeated_structure_fast_path(monkeypatch):
    compile_module = importlib.import_module("ucc.compile")

    source_circuit = QiskitCircuit(2)
    source_circuit.cx(0, 1)
    expected_circuit = QiskitCircuit(2)
    expected_circuit.rz(0.1, 0)

    class FakeCompiler:
        DEFAULT_GATESET = {"cx", "rx", "ry", "rz", "h"}

        def __init__(self, *args, **kwargs):
            self.target_backend = None
            self.target_gateset = {"cx", "rx", "ry", "rz", "h"}
            self.seed_transpiler = kwargs.get("seed_transpiler")

    monkeypatch.setattr(
        compile_module, "_translate_to_qiskit", lambda circuit: source_circuit
    )
    monkeypatch.setattr(
        compile_module,
        "_should_direct_short_circuit_qiskit_source_preset",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setattr(
        compile_module,
        "_should_direct_short_circuit_small_basis_source_preset",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setattr(
        compile_module,
        "_should_short_circuit_to_source_preset",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setattr(
        compile_module, "_structural_pre_simplify", lambda circuit: circuit
    )
    monkeypatch.setattr(compile_module, "UCCDefault1", FakeCompiler)
    monkeypatch.setattr(
        compile_module,
        "_build_compile_dispatch_plan",
        lambda *args, **kwargs: _CompileDispatchPlan(
            mode="repeated_structure_dispatch",
            compiler=FakeCompiler(),
            source_circuit=source_circuit,
            presimplified_circuit=source_circuit,
            basis_translated_circuit=source_circuit,
            baseline_circuit=source_circuit,
        ),
    )
    monkeypatch.setattr(
        compile_module,
        "_compile_repeated_structure_dispatch",
        lambda *args, **kwargs: expected_circuit,
    )
    monkeypatch.setattr(
        compile_module,
        "_translate_from_qiskit",
        lambda circuit, return_format: circuit,
    )

    result_circuit = compile(source_circuit, return_format="qiskit")

    assert result_circuit is expected_circuit


def test_repeated_structure_dispatch_large_repeated_prefix_prefers_block_reference(
    monkeypatch,
):
    compile_module = importlib.import_module("ucc.compile")

    source_circuit = QiskitCircuit(2)
    block = QiskitCircuit(2)
    block.h(0)
    block.cp(0.3, 0, 1)
    block.h(1)
    for _ in range(8000):
        source_circuit.compose(block, inplace=True)

    compiler = UCCDefault1(target_gateset={"cx", "rx", "ry", "rz", "h"})
    baseline_circuit = qiskit_transpile(
        source_circuit, basis_gates=["cx", "rx", "ry", "rz", "h"], optimization_level=0
    )
    repeated_prefix_reference = baseline_circuit.copy()

    monkeypatch.setattr(
        compile_module,
        "_compile_repeated_prefix_reference",
        lambda *args, **kwargs: repeated_prefix_reference,
    )
    monkeypatch.setattr(
        compile_module,
        "_compile_hierarchical_reference",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        compile_module,
        "_compile_preset_reference",
        lambda *args, **kwargs: pytest.fail(
            "large repeated-prefix dispatch should use block reference instead of direct preset"
        ),
    )

    result = _compile_repeated_structure_dispatch(
        _CompileDispatchPlan(
            mode="repeated_structure_dispatch",
                compiler=compiler,
                source_circuit=source_circuit,
                presimplified_circuit=source_circuit,
                basis_translated_circuit=baseline_circuit,
                baseline_circuit=baseline_circuit,
                repeated_prefix=(len(block.data), 8000),
            )
        )

    assert result.count_ops() == repeated_prefix_reference.count_ops()


def test_repeated_structure_dispatch_semantic_repeated_prefix_skips_expensive_candidates(
    monkeypatch,
):
    compile_module = importlib.import_module("ucc.compile")

    source_circuit = repeated_block(qpe_roundtrip_block(3), repeats=8)
    compiler = UCCDefault1(target_gateset={"cx", "rx", "ry", "rz", "h"})
    baseline_circuit = qiskit_transpile(
        source_circuit,
        basis_gates=["cx", "rx", "ry", "rz", "h"],
        optimization_level=0,
    )

    composite_reference = baseline_circuit.copy_empty_like()
    for _ in range(10):
        composite_reference.h(0)

    repeated_prefix_reference = baseline_circuit.copy_empty_like()
    for _ in range(5):
        repeated_prefix_reference.h(0)

    monkeypatch.setattr(
        compile_module,
        "_compile_repeated_composite_prefix_reference",
        lambda *args, **kwargs: pytest.fail(
            "semantic repeated-prefix fast path should skip repeated composite reference"
        ),
    )
    monkeypatch.setattr(
        compile_module,
        "_compile_repeated_prefix_reference",
        lambda *args, **kwargs: repeated_prefix_reference,
    )
    monkeypatch.setattr(
        compile_module,
        "_compile_hierarchical_reference",
        lambda *args, **kwargs: pytest.fail(
            "semantic repeated-prefix fast path should skip hierarchical reference"
        ),
    )
    monkeypatch.setattr(
        compile_module,
        "_compile_presimplified_full_preset_reference",
        lambda *args, **kwargs: pytest.fail(
            "semantic repeated-prefix fast path should skip presimplified full preset"
        ),
    )

    result = _compile_repeated_structure_dispatch(
        _CompileDispatchPlan(
            mode="repeated_structure_dispatch",
            compiler=compiler,
            source_circuit=source_circuit,
            presimplified_circuit=source_circuit,
            basis_translated_circuit=baseline_circuit,
            baseline_circuit=baseline_circuit,
            repeated_prefix=(len(qpe_roundtrip_block(3).data), 8),
        )
    )

    assert result.count_ops() == repeated_prefix_reference.count_ops()


def test_repeated_structure_dispatch_prefers_presimplified_repeated_candidates(
    monkeypatch,
):
    compile_module = importlib.import_module("ucc.compile")

    source_circuit = repeated_block(grover_mirrored_block(6), repeats=8)
    presimplified_circuit = source_circuit.copy()
    compiler = UCCDefault1(target_gateset={"cx", "rx", "ry", "rz", "h"})
    baseline_circuit = qiskit_transpile(
        source_circuit,
        basis_gates=["cx", "rx", "ry", "rz", "h"],
        optimization_level=0,
    )

    source_reference = baseline_circuit.copy_empty_like()
    for _ in range(12):
        source_reference.h(0)

    presimplified_reference = baseline_circuit.copy_empty_like()
    for _ in range(6):
        presimplified_reference.h(0)

    presimplified_full = baseline_circuit.copy_empty_like()
    for _ in range(4):
        presimplified_full.h(0)

    monkeypatch.setattr(
        compile_module,
        "_should_compare_against_presimplified_repeated_dispatch",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(
        compile_module,
        "_supports_semantic_repeated_prefix_fast_path",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setattr(
        compile_module,
        "_dominant_repeated_prefix",
        lambda circuit: (2, 4) if circuit is presimplified_circuit else None,
    )
    monkeypatch.setattr(
        compile_module,
        "_compile_repeated_composite_prefix_reference",
        lambda circuit, *args, **kwargs: (
            source_reference
            if circuit is source_circuit
            else presimplified_reference
        ),
    )
    monkeypatch.setattr(
        compile_module,
        "_compile_repeated_prefix_reference",
        lambda circuit, *args, **kwargs: (
            source_reference
            if circuit is source_circuit
            else presimplified_reference
        ),
    )
    monkeypatch.setattr(
        compile_module,
        "_compile_presimplified_full_preset_reference",
        lambda *args, **kwargs: presimplified_full,
    )
    monkeypatch.setattr(
        compile_module,
        "_compile_hierarchical_reference",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        compile_module,
        "_compile_preset_reference",
        lambda *args, **kwargs: None,
    )

    result = _compile_repeated_structure_dispatch(
        _CompileDispatchPlan(
            mode="repeated_structure_dispatch",
            compiler=compiler,
            source_circuit=source_circuit,
            presimplified_circuit=presimplified_circuit,
            basis_translated_circuit=baseline_circuit,
            baseline_circuit=baseline_circuit,
            repeated_prefix=(len(grover_mirrored_block(6).data), 8),
        )
    )

    assert result.count_ops() == presimplified_full.count_ops()

def test_build_compile_dispatch_plan_skips_global_repeat_scan_for_dominant_prefix(
    monkeypatch,
):
    compile_module = importlib.import_module("ucc.compile")

    source_circuit = repeated_block(qpe_roundtrip_block(3), repeats=512)
    presimplified_circuit = _structural_pre_simplify(source_circuit)
    compiler = UCCDefault1(target_gateset={"cx", "rx", "ry", "rz", "h"})

    monkeypatch.setattr(
        compile_module,
        "_dominant_hierarchical_repeat",
        lambda *args, **kwargs: pytest.fail(
            "dominant repeated-prefix cases should not need a global repeated-run scan"
        ),
    )

    plan = _build_compile_dispatch_plan(
        source_circuit, presimplified_circuit, compiler, False
    )

    assert plan.mode == "repeated_structure_dispatch"
    assert plan.repeated_prefix is not None
    assert plan.repeated_prefix[0] * plan.repeated_prefix[1] == len(
        source_circuit.data
    )


def test_repeated_composite_prefix_reference_avoids_original_block_opt3_when_semantic_ir_handles_it(
    monkeypatch,
):
    compile_module = importlib.import_module("ucc.compile")
    compile_module._REPEATED_REFERENCE_CACHE.clear()

    source_circuit = repeated_block(qpe_roundtrip_block(3), repeats=6)
    compiler = UCCDefault1(target_gateset={"cx", "rx", "ry", "rz", "h"})
    original_qiskit_transpile = compile_module.qiskit_transpile

    def wrapped_qiskit_transpile(subcircuit, **kwargs):
        if kwargs.get("optimization_level") == 3 and any(
            compile_module._instruction_has_nontrivial_composite_definition(
                instruction
            )
            for instruction in subcircuit.data
        ):
            return pytest.fail(
                "semantic repeated-composite lowering should avoid opt3 on the original composite block"
            )
        return original_qiskit_transpile(subcircuit, **kwargs)

    monkeypatch.setattr(compile_module, "qiskit_transpile", wrapped_qiskit_transpile)

    repeated_reference = _compile_repeated_composite_prefix_reference(
        source_circuit,
        compiler,
        (len(qpe_roundtrip_block(3).data), 6),
    )

    assert repeated_reference is not None


def test_repeated_composite_prefix_reference_full_coverage_skips_global_relowering(
    monkeypatch,
):
    compile_module = importlib.import_module("ucc.compile")
    compile_module._REPEATED_REFERENCE_CACHE.clear()

    source_circuit = repeated_block(qpe_roundtrip_block(3), repeats=6)
    compiler = UCCDefault1(target_gateset={"cx", "rx", "ry", "rz", "h"})
    original_qiskit_transpile = compile_module.qiskit_transpile

    def wrapped_qiskit_transpile(subcircuit, **kwargs):
        if (
            kwargs.get("optimization_level") == 0
            and len(subcircuit.data) > len(qpe_roundtrip_block(3).data)
        ):
            return pytest.fail(
                "full-coverage repeated composite references should not relower the rebuilt full circuit"
            )
        return original_qiskit_transpile(subcircuit, **kwargs)

    monkeypatch.setattr(compile_module, "qiskit_transpile", wrapped_qiskit_transpile)

    repeated_reference = _compile_repeated_composite_prefix_reference(
        source_circuit,
        compiler,
        (len(qpe_roundtrip_block(3).data), 6),
    )

    assert repeated_reference is not None


def test_hierarchical_reference_cache_reuses_previous_result(monkeypatch):
    compile_module = importlib.import_module("ucc.compile")
    compile_module._REPEATED_REFERENCE_CACHE.clear()
    compile_module._NODE_REFERENCE_CACHE.clear()

    repeated_gate_body = QiskitCircuit(2)
    repeated_gate_body.cx(0, 1)
    repeated_gate_body.h(0)
    repeated_gate = repeated_gate_body.to_gate(label="R")

    circuit = QiskitCircuit(2)
    for _ in range(10):
        circuit.append(repeated_gate, [0, 1])

    class FakeCompiler:
        target_backend = None
        target_gateset = {"u", "cx", "p"}

    transpile_call_count = 0

    def wrapped_qiskit_transpile(subcircuit, **kwargs):
        nonlocal transpile_call_count
        transpile_call_count += 1
        compiled = QiskitCircuit(2)
        compiled.cx(0, 1)
        return compiled

    monkeypatch.setattr(compile_module, "qiskit_transpile", wrapped_qiskit_transpile)

    first_reference = _compile_hierarchical_reference(circuit, FakeCompiler())
    second_reference = _compile_hierarchical_reference(circuit, FakeCompiler())

    assert first_reference is second_reference
    assert transpile_call_count == 1


def test_backend_default_portfolio_skips_direct_reference_probe_on_modest_base_win(monkeypatch):
    compile_module = importlib.import_module("ucc.compile")

    class FakeCompiler:
        def __init__(self):
            self.target_backend = object()
            self.target_gateset = {"u", "cx", "p"}
            self.seed_transpiler = 12345

        def run(self, circuit, callback=None):
            candidate = QiskitCircuit(2)
            candidate.cx(0, 1)
            candidate.rz(0.2, 1)
            return candidate

    source_circuit = QiskitCircuit(2)
    source_circuit.cx(0, 1)
    source_circuit.rz(0.2, 1)

    baseline_circuit = QiskitCircuit(2)
    baseline_circuit.cx(0, 1)
    baseline_circuit.rz(0.2, 1)
    baseline_circuit.p(0.1, 0)

    monkeypatch.setattr(
        compile_module,
        "_enforce_target_constraints",
        lambda circuit, compiler: circuit,
    )
    monkeypatch.setattr(
        compile_module,
        "_should_skip_backend_reference_probe",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(
        compile_module,
        "qiskit_transpile",
        lambda *args, **kwargs: pytest.fail(
            "modest backend base win should skip direct backend reference"
        ),
    )

    result_circuit = _compile_backend_default_portfolio(
        source_circuit,
        FakeCompiler(),
        source_circuit=source_circuit,
        baseline_circuit=baseline_circuit,
    )

    assert result_circuit.count_ops().get("cx", 0) == 1


def test_backend_default_portfolio_returns_direct_reference_on_clear_reference_win(monkeypatch):
    compile_module = importlib.import_module("ucc.compile")

    class FakeCompiler:
        def __init__(self):
            self.target_backend = object()
            self.target_gateset = {"u", "cx", "p"}
            self.seed_transpiler = 12345

        def run(self, circuit, callback=None):
            candidate = QiskitCircuit(2)
            candidate.cx(0, 1)
            candidate.cx(0, 1)
            candidate.rz(0.2, 1)
            return candidate

    source_circuit = QiskitCircuit(2)
    source_circuit.cx(0, 1)
    source_circuit.rz(0.2, 1)

    direct_reference = QiskitCircuit(2)
    direct_reference.cx(0, 1)
    direct_reference.rz(0.2, 1)

    baseline_circuit = QiskitCircuit(2)
    baseline_circuit.cx(0, 1)
    baseline_circuit.cx(0, 1)
    baseline_circuit.cx(0, 1)
    baseline_circuit.rz(0.2, 1)

    monkeypatch.setattr(
        compile_module,
        "_enforce_target_constraints",
        lambda circuit, compiler: circuit,
    )

    original_qiskit_transpile = compile_module.qiskit_transpile

    def wrapped_qiskit_transpile(*args, **kwargs):
        if kwargs.get("backend") is not None and kwargs.get("optimization_level") == 3:
            return direct_reference
        return original_qiskit_transpile(*args, **kwargs)

    monkeypatch.setattr(compile_module, "qiskit_transpile", wrapped_qiskit_transpile)
    monkeypatch.setattr(
        compile_module,
        "UCCDefault1",
        lambda *args, **kwargs: pytest.fail(
            "clear backend reference win should bypass additional portfolio compilers"
        ),
    )

    result_circuit = _compile_backend_default_portfolio(
        source_circuit,
        FakeCompiler(),
        source_circuit=source_circuit,
        baseline_circuit=baseline_circuit,
    )

    assert result_circuit.count_ops().get("cx", 0) == 1


def test_backend_default_portfolio_short_circuits_on_clear_base_win(monkeypatch):
    compile_module = importlib.import_module("ucc.compile")

    class FakeCompiler:
        def __init__(self):
            self.target_backend = object()
            self.target_gateset = {"u", "cx", "p"}
            self.seed_transpiler = 12345

        def run(self, circuit, callback=None):
            candidate = QiskitCircuit(2)
            candidate.cx(0, 1)
            return candidate

    source_circuit = QiskitCircuit(2)
    source_circuit.cx(0, 1)
    source_circuit.rz(0.2, 1)

    baseline_reference = QiskitCircuit(2)
    baseline_reference.cx(0, 1)
    baseline_reference.cx(0, 1)
    baseline_reference.rz(0.2, 1)

    monkeypatch.setattr(
        compile_module,
        "_enforce_target_constraints",
        lambda circuit, compiler: circuit,
    )

    original_qiskit_transpile = compile_module.qiskit_transpile

    def wrapped_qiskit_transpile(*args, **kwargs):
        if kwargs.get("backend") is not None and kwargs.get("optimization_level") == 3:
            return baseline_reference
        return original_qiskit_transpile(*args, **kwargs)

    monkeypatch.setattr(compile_module, "qiskit_transpile", wrapped_qiskit_transpile)
    monkeypatch.setattr(
        compile_module,
        "UCCDefault1",
        lambda *args, **kwargs: pytest.fail(
            "clear backend win should bypass additional portfolio compilers"
        ),
    )

    result_circuit = _compile_backend_default_portfolio(
        source_circuit,
        FakeCompiler(),
        source_circuit=source_circuit,
    )

    assert result_circuit.count_ops().get("cx", 0) == 1


def test_backend_default_portfolio_prefers_anchor_dominator(monkeypatch):
    compile_module = importlib.import_module("ucc.compile")

    class FakeCompiler:
        def __init__(self):
            self.target_backend = object()
            self.target_gateset = {"u", "cx", "p"}
            self.seed_transpiler = 12345

        def run(self, circuit, callback=None):
            candidate = QiskitCircuit(2)
            candidate.cx(0, 1)
            candidate.rz(0.2, 1)
            return candidate

    source_circuit = QiskitCircuit(2)
    source_circuit.cx(0, 1)
    source_circuit.rz(0.2, 1)

    anchor_reference = QiskitCircuit(2)
    anchor_reference.cx(0, 1)
    anchor_reference.cx(0, 1)
    anchor_reference.rz(0.2, 1)

    dominating_reference = QiskitCircuit(2)
    dominating_reference.cx(0, 1)
    dominating_reference.rz(0.2, 1)

    lower_cost_tradeoff = QiskitCircuit(2)
    for _ in range(5):
        lower_cost_tradeoff.rz(0.2, 0)

    monkeypatch.setattr(
        compile_module,
        "_enforce_target_constraints",
        lambda circuit, compiler: circuit,
    )

    def wrapped_qiskit_transpile(*args, **kwargs):
        if kwargs.get("backend") is not None and kwargs.get("optimization_level") == 3:
            seed = kwargs.get("seed_transpiler")
            if seed == 12345:
                return anchor_reference
            if seed == 17:
                return dominating_reference
            if seed == 29:
                return lower_cost_tradeoff
            return anchor_reference
        return args[0]

    monkeypatch.setattr(compile_module, "qiskit_transpile", wrapped_qiskit_transpile)
    monkeypatch.setattr(
        compile_module,
        "UCCDefault1",
        lambda *args, **kwargs: FakeCompiler(),
    )

    result_circuit = _compile_backend_default_portfolio(
        source_circuit,
        FakeCompiler(),
        source_circuit=source_circuit,
        baseline_circuit=anchor_reference,
    )

    assert result_circuit.count_ops().get("cx", 0) == 1
    assert result_circuit.depth() == dominating_reference.depth()


def test_backend_default_portfolio_reuses_cached_backend_references(monkeypatch):
    compile_module = importlib.import_module("ucc.compile")
    compile_module._BACKEND_PRESET_CACHE.clear()
    compile_module._BACKEND_DEFAULT_RUN_CACHE.clear()

    class FakeCompiler:
        def __init__(self):
            self.target_backend = object()
            self.target_gateset = {"u", "cx", "p"}
            self.seed_transpiler = 12345

        def run(self, circuit, callback=None):
            candidate = QiskitCircuit(2)
            candidate.cx(0, 1)
            for _ in range(8):
                candidate.rz(0.2, 0)
            return candidate

    source_circuit = QiskitCircuit(2)
    source_circuit.cx(0, 1)
    source_circuit.rz(0.2, 1)

    anchor_reference = QiskitCircuit(2)
    anchor_reference.cx(0, 1)
    anchor_reference.cx(0, 1)

    exploratory_reference = QiskitCircuit(2)
    exploratory_reference.cx(0, 1)

    backend_opt3_calls = 0

    monkeypatch.setattr(
        compile_module,
        "_enforce_target_constraints",
        lambda circuit, compiler: circuit,
    )

    def wrapped_qiskit_transpile(*args, **kwargs):
        if kwargs.get("backend") is not None and kwargs.get("optimization_level") == 3:
            nonlocal backend_opt3_calls
            backend_opt3_calls += 1
            seed = kwargs.get("seed_transpiler")
            if seed == 12345:
                return anchor_reference
            return exploratory_reference
        return args[0]

    monkeypatch.setattr(compile_module, "qiskit_transpile", wrapped_qiskit_transpile)

    first_result = _compile_backend_default_portfolio(
        source_circuit,
        FakeCompiler(),
        source_circuit=source_circuit,
    )
    second_result = _compile_backend_default_portfolio(
        source_circuit,
        FakeCompiler(),
        source_circuit=source_circuit,
    )

    assert first_result.count_ops().get("cx", 0) == 1
    assert second_result.count_ops().get("cx", 0) == 1
    assert backend_opt3_calls == len(
        compile_module._backend_reference_seeds(FakeCompiler(), source_circuit)
    )


def test_should_use_backend_repeated_run_shortcut_detects_large_composite_run():
    repeated_gate_body = QiskitCircuit(2)
    repeated_gate_body.cx(0, 1)
    repeated_gate_body.h(0)
    repeated_gate = repeated_gate_body.to_gate(label="R")

    circuit = QiskitCircuit(2)
    for _ in range(20):
        circuit.h(0)
    for _ in range(568):
        circuit.append(repeated_gate, [0, 1])

    assert _should_use_backend_repeated_run_shortcut(circuit)


def test_select_backend_repeated_run_candidates_prefers_depth_and_multi_tradeoff(monkeypatch):
    reference_circuit = object()
    tradeoff_circuit = object()

    metrics_by_circuit = {
        id(reference_circuit): {
            "total_gates": 100,
            "depth": 100,
            "multi_qubit_gates": 100,
        },
        id(tradeoff_circuit): {
            "total_gates": 108,
            "depth": 85,
            "multi_qubit_gates": 75,
        },
    }

    monkeypatch.setattr(
        importlib.import_module("ucc.compile"),
        "_circuit_metrics",
        lambda circuit: metrics_by_circuit[id(circuit)],
    )

    selected_circuit = _select_backend_repeated_run_candidates(
        [reference_circuit, tradeoff_circuit]
    )

    assert selected_circuit is tradeoff_circuit


def test_compile_uses_backend_repeated_run_shortcut(monkeypatch):
    compile_module = importlib.import_module("ucc.compile")

    class FakeCompiler:
        DEFAULT_GATESET = {"u", "cx", "p"}

        def __init__(self, *args, **kwargs):
            self.target_backend = object()
            self.target_gateset = {"u", "cx", "p"}
            self.seed_transpiler = kwargs.get("seed_transpiler")

    source_circuit = QiskitCircuit(2)
    source_circuit.cx(0, 1)

    shortcut_circuit = QiskitCircuit(2)
    shortcut_circuit.rz(0.1, 0)

    monkeypatch.setattr(
        compile_module,
        "_translate_to_qiskit",
        lambda circuit: source_circuit,
    )
    monkeypatch.setattr(
        compile_module,
        "_should_direct_short_circuit_qiskit_source_preset",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setattr(
        compile_module,
        "_should_use_backend_repeated_run_shortcut",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(
        compile_module,
        "_compile_backend_repeated_run_reference",
        lambda *args, **kwargs: shortcut_circuit,
    )
    monkeypatch.setattr(
        compile_module,
        "_translate_from_qiskit",
        lambda circuit, return_format: circuit,
    )
    monkeypatch.setattr(compile_module, "UCCDefault1", FakeCompiler)

    result_circuit = compile(
        source_circuit,
        return_format="qiskit",
        target_backend=object(),
    )

    assert result_circuit is shortcut_circuit


def test_compile_with_target_gateset():
    """Test that the final circuit respects the user-defined gateset, no target device"""
    circuit = QiskitCircuit(2)
    circuit.cx(0, 1)
    circuit.h(0)

    target_gateset = {
        "ry",
        "rx",
        "cz",
    }
    result_circuit = compile(
        circuit,
        target_gateset=target_gateset,
    )

    assert set(op.name for op in result_circuit).issubset(target_gateset)


@pytest.mark.parametrize(
    "circuit_function", [qcnn_circuit, random_clifford_circuit]
)
@pytest.mark.parametrize("num_qubits", [6, 7, 8, 9, 10])
@pytest.mark.parametrize("seed", [1, 326, 5678, 12345])
def test_compilation_retains_gateset(circuit_function, num_qubits, seed):
    circuit = circuit_function(num_qubits, seed)
    transpiler = UCCDefault1()
    target_basis = transpiler.target_gateset
    transpiled_circuit = transpiler.run(circuit)
    dag = circuit_to_dag(transpiled_circuit)
    analysis_pass = GatesInBasis(basis_gates=target_basis)
    analysis_pass.run(dag)
    assert analysis_pass.property_set["all_gates_in_basis"]


# Test compilation accepts QASM circuits containing IF-ELSE
def test_compile_if_else():
    qasm = """
    OPENQASM 3;
    include "stdgates.inc";
    bit[3] data;
    bit[2] syndrome;
    qubit[3] q0;
    qubit[2] q1;

    syndrome[0] = measure q0[0];
    syndrome[1] = measure q1[1];
    if (syndrome[0]) {
        x q1[0];
    }
    if (syndrome[1]) {
        x q1[0];
    }
    """
    transpiled = compile(qasm, return_format="qiskit")
    assert isinstance(transpiled, QiskitCircuit)


@pytest.mark.parametrize(
    "circuit_function", [qcnn_circuit, random_clifford_circuit]
)
@pytest.mark.parametrize("num_qubits", [6, 7, 8, 9, 10, 15])
@pytest.mark.parametrize("seed", [1, 326, 5678, 12345])
def test_compiled_circuits_equivalent(circuit_function, num_qubits, seed):
    circuit = circuit_function(num_qubits, seed)
    transpiled = compile(circuit, return_format="qiskit")
    sv1 = Statevector(circuit)
    sv2 = Statevector(transpiled)
    assert sv1.equiv(sv2)

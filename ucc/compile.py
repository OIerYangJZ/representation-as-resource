import os
from qbraid.programs.alias_manager import get_program_type_alias
from qbraid.transpiler import ConversionGraph
from qbraid.transpiler import transpile as translate
from qiskit import transpile as qiskit_transpile
from qiskit.circuit import CircuitInstruction
from qiskit.circuit import QuantumCircuit as QiskitCircuit
from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import CommutativeInverseCancellation
from .transpilers.ucc_defaults import UCCDefault1

from dataclasses import dataclass
import math
import sys
import warnings

# Specify the supported Python version range
REQUIRED_MAJOR = 3
MINOR_VERSION_MIN = 12
MINOR_VERSION_MAX = 13

current_major = sys.version_info.major
current_minor = sys.version_info.minor

if current_major != REQUIRED_MAJOR or not (
    MINOR_VERSION_MIN <= current_minor <= MINOR_VERSION_MAX
):
    warnings.warn(
        f"Warning: This package is designed for Python {REQUIRED_MAJOR}.{MINOR_VERSION_MIN}-{REQUIRED_MAJOR}.{MINOR_VERSION_MAX}. "
        f"You are using Python {current_major}.{current_minor}."
    )
supported_circuit_formats = ConversionGraph().nodes()
_MAX_STRUCTURAL_BLOCK_SIZE = 256
_MIN_REPEATED_BLOCK_REPEATS = 4
_MAX_GLOBAL_STRUCTURAL_SCAN_SIZE = 50000
_MAX_FULL_PRESET_REFERENCE_SIZE = 20000
_MAX_PRESIMPLIFIED_FULL_PRESET_SIZE = 70000
_MAX_FULL_DIRECT_PRESET_SIZE = 120000
_MAX_DIRECT_SOURCE_PRESET_SIZE = 20000
_MIN_DIRECT_SOURCE_PRESET_SIZE = 2048
_FAST_PREFIX_SCAN_SIZE = 4096
_MIN_DOMINANT_REPEAT_FRACTION = 0.8
_MAX_REPEAT_MACRO_BLOCK_SIZE = 2048
_REPEAT_MACRO_FACTORS = (4, 2, 1)
_PARAMETER_MERGE_TOLERANCE = 1e-12
_MERGEABLE_PARAMETERIZED_GATES = {"rx", "ry", "rz", "p", "cp"}
_DIAGONAL_PHASE_GATES = {"rz", "p", "cp", "cz"}
_MIRRORED_SELF_INVERSE_DIAGONAL_PREFIX_GATES = _DIAGONAL_PHASE_GATES | {
    "mcphase"
}
_LOW_MULTI_QUBIT_FRACTION = 0.2
_DIRECT_SOURCE_DECOMPOSITION_RATIO = 20
_MEDIUM_DIRECT_SOURCE_DECOMPOSITION_RATIO = 2.5
_BACKEND_SEED_PORTFOLIO_OFFSETS = (0, 1, 2)
_BACKEND_REFERENCE_GLOBAL_SEEDS = (17, 29, 42)
_MAX_BACKEND_SEED_PORTFOLIO_SIZE = 10000
_MAX_BACKEND_DEFAULT_PORTFOLIO_SIZE = 5000
_MIN_BACKEND_REPEATED_RUN_REPEATS = 8
_MAX_BACKEND_REPEATED_RUN_BLOCK_SIZE = 4
_MIN_BACKEND_REPEATED_RUN_FRACTION = 0.8
_MIN_BACKEND_REPEATED_RUN_SIZE = 512
_BACKEND_REPEATED_RUN_TOTAL_GATE_MARGIN = 0.10
_BACKEND_REPEATED_RUN_DEPTH_IMPROVEMENT = 0.10
_BACKEND_REPEATED_RUN_MULTI_IMPROVEMENT = 0.20
_MAX_HIERARCHICAL_LOCAL_BLOCK_SIZE = 256
_MIN_REPEAT_DISPATCH_SIZE = 10000
_MAX_REPEAT_DISPATCH_HIERARCHICAL_SIZE = 50000
_MAX_SMALL_BASIS_SOURCE_PRESET_SIZE = 2048
_MIN_REPEATED_BASIS_SOURCE_FAST_PATH_SIZE = 4000
_MIN_BLOCKWISE_REPEAT_PRESIMPLIFY_SIZE = 10000
_MAX_REPEAT_DISPATCH_EXPENSIVE_SEARCH_SIZE = 10000
_MAX_SEMANTIC_LOCAL_OPT_BLOCK_SIZE = 1024
_MAX_REFERENCE_CACHE_SIZE = 4096

_CACHE_MISS = object()
_BACKEND_PRESET_CACHE = {}
_NODE_REFERENCE_CACHE = {}
_REPEATED_REFERENCE_CACHE = {}
_BACKEND_DEFAULT_RUN_CACHE = {}
_SEMANTIC_TERM_CACHE = {}
_SEMANTIC_REFERENCE_CACHE = {}
_SEMANTIC_TERM_COMPILED_CACHE = {}
_REPEATED_RUN_BLOCK_REFERENCE_CACHE = {}


@dataclass(frozen=True)
class _InstructionSpanNode:
    """Leaf node representing a contiguous instruction span."""

    start_index: int
    end_index: int


@dataclass(frozen=True)
class _RepeatedSpanNode:
    """Macro node representing a repeated contiguous block."""

    start_index: int
    block_size: int
    repeat_count: int


@dataclass(frozen=True)
class _DiagonalPhaseSpanNode:
    """Semantic IR node for a contiguous commuting diagonal-phase span."""

    start_index: int
    end_index: int


@dataclass(frozen=True)
class _SemanticHadamardNode:
    """Semantic IR node for a Hadamard gate."""

    qubit_index: int


@dataclass(frozen=True)
class _SemanticSwapNode:
    """Semantic IR node for a swap gate."""

    left_index: int
    right_index: int


@dataclass(frozen=True)
class _SemanticDiagonalPhaseOpNode:
    """Semantic IR node for a diagonal phase operation."""

    gate_name: str
    qubit_indices: tuple[int, ...]
    parameter: float


@dataclass(frozen=True)
class _SemanticPhaseLadderNode:
    """Semantic IR node for a QFT/QPE-style phase ladder."""

    operations: tuple[object, ...]


@dataclass(frozen=True)
class _ConjugationSpanNode:
    """Block-level IR node for a prefix-center-inverse(prefix) structure."""

    prefix_size: int
    center_start: int
    center_end: int


@dataclass(frozen=True)
class _MirroredSelfInverseBlockNode:
    """Block-level IR node for diagonal-prefix + mirrored self-inverse shell."""

    diagonal_prefix_size: int
    shell_prefix_size: int


@dataclass(frozen=True)
class _SemanticCircuitLeafTerm:
    """Term-algebra leaf storing a compiled circuit fragment."""

    circuit: QiskitCircuit


@dataclass(frozen=True)
class _SemanticNodeLeafTerm:
    """Term-algebra leaf storing one semantic IR node."""

    node: object


@dataclass(frozen=True)
class _SemanticSequenceTerm:
    """Sequential composition in the semantic term algebra."""

    parts: tuple[object, ...]


@dataclass(frozen=True)
class _SemanticRepeatTerm:
    """Repeated composition of one semantic term."""

    body: object
    repeat_count: int


@dataclass(frozen=True)
class _SemanticConjugationTerm:
    """Conjugation term representing U · M · U^{-1}."""

    prefix: object
    center: object


@dataclass(frozen=True)
class _SemanticFourierLayerTerm:
    """Hierarchical term representing a phase-ladder/Fourier layer."""

    stages: tuple[object, ...]


@dataclass(frozen=True)
class _SemanticMirroredSelfInverseTerm:
    """Diagonal-prefix plus mirrored/self-inverse shell term."""

    diagonal_prefix: object
    shell: object
    shell_prefix_size: int


@dataclass(frozen=True)
class _CompileDispatchPlan:
    """Execution plan for the top-level compile controller."""

    mode: str
    compiler: object
    source_circuit: QiskitCircuit
    presimplified_circuit: QiskitCircuit
    basis_translated_circuit: QiskitCircuit | None = None
    baseline_circuit: QiskitCircuit | None = None
    repeated_prefix: tuple[int, int] | None = None


def _dominant_repeated_prefix(circuit):
    """Return a repeated prefix only when it covers a dominant fraction."""

    repeated_prefix = _find_repeated_prefix(circuit)
    if repeated_prefix is None:
        return None

    block_size, repeat_count = repeated_prefix
    coverage = block_size * repeat_count
    if coverage < _MIN_DOMINANT_REPEAT_FRACTION * len(circuit.data):
        return None
    return repeated_prefix


def _should_compare_against_presimplified_repeated_dispatch(
    source_circuit, presimplified_circuit
):
    """Return True when repeated dispatch should also probe the simplified view."""

    source_gate_count = len(source_circuit.data)
    simplified_gate_count = len(presimplified_circuit.data)
    if (
        source_gate_count == 0
        or simplified_gate_count >= source_gate_count
        or simplified_gate_count > _MAX_PRESIMPLIFIED_FULL_PRESET_SIZE
    ):
        return False

    repeated_prefix = _dominant_repeated_prefix(presimplified_circuit)
    if repeated_prefix is None:
        return False

    reduction_fraction = 1 - (simplified_gate_count / source_gate_count)
    return reduction_fraction >= 0.20


def _translate_to_qiskit(circuit):
    """Translate to Qiskit, but skip qBraid when already in Qiskit format."""

    if isinstance(circuit, QiskitCircuit):
        return circuit
    return translate(circuit, "qiskit")


def _translate_from_qiskit(circuit, return_format):
    """Translate from Qiskit only when the caller asked for another format."""

    if return_format == "qiskit":
        return circuit
    return translate(circuit, return_format)


def _effective_target_gateset(target_gateset):
    """Resolve the all-to-all target gateset without constructing a compiler."""

    if target_gateset is not None:
        return set(target_gateset)
    return set(UCCDefault1.DEFAULT_GATESET)


def _build_circuit_from_instructions(template_circuit, instructions):
    """Build a new circuit with the same registers from a list of instructions."""

    rebuilt_circuit = template_circuit.copy_empty_like()
    rebuilt_circuit.global_phase = template_circuit.global_phase
    for instruction in instructions:
        rebuilt_circuit.append(
            instruction.operation,
            instruction.qubits,
            instruction.clbits,
        )
    return rebuilt_circuit


def _expand_single_composite_reference_source(circuit):
    """Expand a single composite instruction into its definition when useful."""

    if len(circuit.data) != 1:
        return circuit

    definition = getattr(circuit.data[0].operation, "definition", None)
    if definition is None or len(definition.data) <= 1:
        return circuit

    expanded_circuit = definition.copy()
    expanded_circuit.global_phase = definition.global_phase
    return expanded_circuit


def _normalize_param(param):
    """Return a hashable representation for instruction parameters."""

    if isinstance(param, (int, float)):
        return round(float(param), 12)
    return str(param)


def _normalize_global_phase(phase):
    """Return a hashable representation for circuit global phase."""

    if isinstance(phase, (int, float)):
        return round(float(phase), 12)
    return str(phase)


def _instruction_signature(circuit, instruction):
    """Compute a stable signature for repeated-block detection."""

    return (
        instruction.operation.name,
        tuple(
            _normalize_param(param) for param in instruction.operation.params
        ),
        tuple(circuit.find_bit(qubit).index for qubit in instruction.qubits),
        tuple(circuit.find_bit(clbit).index for clbit in instruction.clbits),
    )


def _cacheable_circuit_key(circuit, max_size=_MAX_REFERENCE_CACHE_SIZE):
    """Return a stable cache key for a small/medium circuit."""

    if len(circuit.data) > max_size:
        return None

    return (
        circuit.num_qubits,
        circuit.num_clbits,
        _normalize_global_phase(circuit.global_phase),
        tuple(
            _instruction_signature(circuit, instruction)
            for instruction in circuit.data
        ),
    )


def _backend_cache_marker(compiler):
    """Return a stable backend marker for cache keys."""

    if compiler.target_backend is None:
        return None
    return id(compiler.target_backend)


def _target_basis_cache_key(compiler):
    """Return a stable target-basis marker for cache keys."""

    return tuple(sorted(compiler.target_gateset))


def _semantic_cache_key(circuit, compiler, tag, max_size=_MAX_REFERENCE_CACHE_SIZE):
    """Return a stable cache key for semantic builder/reference results."""

    circuit_key = _cacheable_circuit_key(circuit, max_size=max_size)
    if circuit_key is None:
        return None
    return (
        circuit_key,
        _target_basis_cache_key(compiler),
        _backend_cache_marker(compiler),
        getattr(compiler, "seed_transpiler", None),
        tag,
    )


def _semantic_node_signature(node):
    """Return a stable cache signature for a semantic IR node."""

    if isinstance(node, _SemanticHadamardNode):
        return ("h", node.qubit_index)
    if isinstance(node, _SemanticSwapNode):
        return ("swap", node.left_index, node.right_index)
    if isinstance(node, _SemanticDiagonalPhaseOpNode):
        return (
            node.gate_name,
            node.qubit_indices,
            _normalize_param(node.parameter),
        )
    if isinstance(node, _SemanticPhaseLadderNode):
        return (
            "phase_ladder",
            tuple(_semantic_node_signature(op) for op in node.operations),
        )
    return None


def _semantic_term_signature(term):
    """Return a stable cache signature for a semantic term."""

    if isinstance(term, _SemanticCircuitLeafTerm):
        circuit_key = _cacheable_circuit_key(term.circuit)
        if circuit_key is None:
            return None
        return ("circuit", circuit_key)

    if isinstance(term, _SemanticNodeLeafTerm):
        node_signature = _semantic_node_signature(term.node)
        if node_signature is None:
            return None
        return ("node", node_signature)

    if isinstance(term, _SemanticSequenceTerm):
        part_signatures = tuple(
            _semantic_term_signature(part) for part in term.parts
        )
        if any(signature is None for signature in part_signatures):
            return None
        return ("sequence", part_signatures)

    if isinstance(term, _SemanticRepeatTerm):
        body_signature = _semantic_term_signature(term.body)
        if body_signature is None:
            return None
        return ("repeat", body_signature, term.repeat_count)

    if isinstance(term, _SemanticConjugationTerm):
        prefix_signature = _semantic_term_signature(term.prefix)
        center_signature = _semantic_term_signature(term.center)
        if prefix_signature is None or center_signature is None:
            return None
        return ("conjugation", prefix_signature, center_signature)

    if isinstance(term, _SemanticFourierLayerTerm):
        stage_signatures = tuple(
            _semantic_term_signature(stage) for stage in term.stages
        )
        if any(signature is None for signature in stage_signatures):
            return None
        return ("fourier", stage_signatures)

    if isinstance(term, _SemanticMirroredSelfInverseTerm):
        diagonal_signature = _semantic_term_signature(term.diagonal_prefix)
        shell_signature = _semantic_term_signature(term.shell)
        if diagonal_signature is None or shell_signature is None:
            return None
        return (
            "mirrored_self_inverse",
            diagonal_signature,
            shell_signature,
            term.shell_prefix_size,
        )

    return None


def _semantic_term_cache_key(term, compiler):
    """Return a stable cache key for a compiled semantic term."""

    term_signature = _semantic_term_signature(term)
    if term_signature is None:
        return None
    return (
        term_signature,
        _target_basis_cache_key(compiler),
        _backend_cache_marker(compiler),
        getattr(compiler, "seed_transpiler", None),
    )


def _inverse_instruction_signature(circuit, instruction):
    """Compute the signature of an instruction's inverse when available."""

    try:
        inverse_operation = instruction.operation.inverse()
    except Exception:
        return None

    return (
        inverse_operation.name,
        tuple(_normalize_param(param) for param in inverse_operation.params),
        tuple(circuit.find_bit(qubit).index for qubit in instruction.qubits),
        tuple(circuit.find_bit(clbit).index for clbit in instruction.clbits),
    )


def _copy_operation_with_parameter(operation, parameter):
    """Return a mutable copy of a single-parameter operation."""

    try:
        copied_operation = type(operation)(parameter)
    except Exception:
        copied_operation = (
            operation.to_mutable()
            if hasattr(operation, "to_mutable")
            else operation.copy()
        )
        copied_operation.params = [parameter]
    return copied_operation


def _can_merge_adjacent_parameterized_gates(left_instruction, right_instruction):
    """Return True when two adjacent single-parameter gates can be merged."""

    left_operation = left_instruction.operation
    right_operation = right_instruction.operation
    return (
        left_operation.name == right_operation.name
        and left_operation.name in _MERGEABLE_PARAMETERIZED_GATES
        and len(left_operation.params) == 1
        and len(right_operation.params) == 1
        and isinstance(left_operation.params[0], (int, float))
        and isinstance(right_operation.params[0], (int, float))
        and left_instruction.qubits == right_instruction.qubits
        and left_instruction.clbits == right_instruction.clbits
    )


def _is_diagonal_phase_instruction(instruction):
    """Return True when an instruction is a commuting diagonal phase gate."""

    operation = instruction.operation
    if operation.name not in _DIAGONAL_PHASE_GATES:
        return False
    return not getattr(operation, "condition", None)


def _diagonal_phase_signature(circuit, instruction):
    """Return a stable signature for commuting diagonal phase aggregation."""

    return (
        instruction.operation.name,
        tuple(circuit.find_bit(qubit).index for qubit in instruction.qubits),
        tuple(circuit.find_bit(clbit).index for clbit in instruction.clbits),
    )


def _diagonal_phase_parameter(operation):
    """Return the additive phase parameter for a diagonal gate when supported."""

    if operation.name == "cz":
        return math.pi
    if len(operation.params) == 1 and isinstance(operation.params[0], (int, float)):
        return float(operation.params[0])
    return None


def _instruction_is_self_inverse(circuit, instruction):
    """Return True when an instruction is its own inverse on the same wires."""

    inverse_signature = _inverse_instruction_signature(circuit, instruction)
    if inverse_signature is None:
        return False
    return inverse_signature == _instruction_signature(circuit, instruction)


def _contiguous_operation_groups(circuit, start_index=0):
    """Group contiguous operations with the same operation kind."""

    groups = []
    index = start_index
    while index < len(circuit.data):
        instruction = circuit.data[index]
        group_name = instruction.operation.name
        group_qubit_count = instruction.operation.num_qubits
        next_index = index + 1
        while next_index < len(circuit.data):
            next_instruction = circuit.data[next_index]
            if (
                next_instruction.operation.name != group_name
                or next_instruction.operation.num_qubits != group_qubit_count
                or next_instruction.clbits
            ):
                break
            next_index += 1
        groups.append((index, next_index))
        index = next_index
    return groups


def _group_signature(circuit, start_index, end_index):
    """Return an order-insensitive signature for a contiguous instruction group."""

    return tuple(
        sorted(
            _instruction_signature(circuit, instruction)
            for instruction in circuit.data[start_index:end_index]
        )
    )


def _build_diagonal_phase_span_nodes(circuit):
    """Build contiguous semantic nodes for commuting diagonal-phase spans."""

    nodes = []
    start_index = None
    for index, instruction in enumerate(circuit.data):
        if _is_diagonal_phase_instruction(instruction):
            if start_index is None:
                start_index = index
            continue
        if start_index is not None and index > start_index:
            nodes.append(_DiagonalPhaseSpanNode(start_index, index))
            start_index = None
    if start_index is not None and len(circuit.data) > start_index:
        nodes.append(_DiagonalPhaseSpanNode(start_index, len(circuit.data)))
    return nodes


def _canonicalize_diagonal_phase_span(circuit, node):
    """Canonicalize a commuting diagonal-phase span by aggregating equal terms."""

    phase_terms = {}
    ordered_keys = []
    for instruction in circuit.data[node.start_index : node.end_index]:
        parameter = _diagonal_phase_parameter(instruction.operation)
        if parameter is None:
            return _build_circuit_from_instructions(
                circuit, list(circuit.data[node.start_index : node.end_index])
            )
        signature = _diagonal_phase_signature(circuit, instruction)
        if signature not in phase_terms:
            phase_terms[signature] = 0.0
            ordered_keys.append(signature)
        phase_terms[signature] += parameter

    rebuilt_span = circuit.copy_empty_like()
    rebuilt_span.global_phase = 0
    for gate_name, qubit_indices, clbit_indices in ordered_keys:
        parameter = phase_terms[(gate_name, qubit_indices, clbit_indices)]
        if abs(parameter) <= _PARAMETER_MERGE_TOLERANCE:
            continue
        if gate_name == "rz":
            rebuilt_span.rz(parameter, qubit_indices[0])
        elif gate_name == "p":
            rebuilt_span.p(parameter, qubit_indices[0])
        elif gate_name == "cp":
            rebuilt_span.cp(parameter, qubit_indices[0], qubit_indices[1])
        elif gate_name == "cz":
            rebuilt_span.cz(qubit_indices[0], qubit_indices[1])
        else:
            return _build_circuit_from_instructions(
                circuit, list(circuit.data[node.start_index : node.end_index])
            )
    return rebuilt_span


def _canonicalize_diagonal_phase_spans(circuit):
    """Aggregate every contiguous commuting diagonal-phase span once."""

    if os.environ.get("UCC_DISABLE_FOURIER_LAYER_IR") == "1":
        return circuit

    diagonal_nodes = _build_diagonal_phase_span_nodes(circuit)
    if not diagonal_nodes:
        return circuit

    rebuilt_circuit = circuit.copy_empty_like()
    rebuilt_circuit.global_phase = circuit.global_phase
    next_index = 0
    used_semantic_node = False

    for node in diagonal_nodes:
        _append_instruction_sequence(
            rebuilt_circuit, circuit.data[next_index : node.start_index]
        )
        simplified_span = _canonicalize_diagonal_phase_span(circuit, node)
        for instruction in simplified_span.data:
            _append_mapped_instruction(rebuilt_circuit, simplified_span, instruction)
        used_semantic_node = True
        next_index = node.end_index

    _append_instruction_sequence(rebuilt_circuit, circuit.data[next_index:])

    if not used_semantic_node:
        return circuit

    return rebuilt_circuit


def _has_reducible_diagonal_phase_span(circuit, reduction_ratio=0.8):
    """Return True when a diagonal phase span has a clear semantic reduction."""

    for node in _build_diagonal_phase_span_nodes(circuit):
        span_size = node.end_index - node.start_index
        if span_size <= 1:
            continue
        simplified_span = _canonicalize_diagonal_phase_span(circuit, node)
        if len(simplified_span.data) < reduction_ratio * span_size:
            return True
    return False


def _semantic_local_simplify(circuit):
    """Apply a small semantic IR pass before structural peephole simplification."""

    return _structural_pre_simplify(_canonicalize_diagonal_phase_spans(circuit))


def _build_phase_ladder_semantic_node(semantic_nodes):
    """Return a higher-level phase-ladder node when a semantic block fits."""

    if not semantic_nodes:
        return None

    if not any(
        isinstance(node, _SemanticHadamardNode) for node in semantic_nodes
    ):
        return None
    if not any(
        isinstance(node, _SemanticDiagonalPhaseOpNode)
        for node in semantic_nodes
    ):
        return None
    if any(
        not isinstance(
            node,
            (
                _SemanticHadamardNode,
                _SemanticSwapNode,
                _SemanticDiagonalPhaseOpNode,
            ),
        )
        for node in semantic_nodes
    ):
        return None

    return _SemanticPhaseLadderNode(tuple(semantic_nodes))


def _build_fourier_stage_terms(circuit, phase_ladder_node):
    """Split a phase ladder into smaller Fourier stages for term compilation."""

    if os.environ.get("UCC_DISABLE_FOURIER_LAYER_IR") == "1":
        return None

    stage_nodes = []
    current_stage = []
    for node in phase_ladder_node.operations:
        if (
            current_stage
            and isinstance(node, (_SemanticHadamardNode, _SemanticSwapNode))
        ):
            stage_nodes.append(tuple(current_stage))
            current_stage = [node]
            continue
        current_stage.append(node)

    if current_stage:
        stage_nodes.append(tuple(current_stage))

    stage_terms = []
    for stage in stage_nodes:
        lowered_stage = _lower_semantic_ir_to_target_basis(circuit, list(stage))
        if lowered_stage is None:
            return None
        stage_terms.append(_SemanticCircuitLeafTerm(lowered_stage))

    if len(stage_terms) == 1:
        return stage_terms[0]
    return _SemanticFourierLayerTerm(tuple(stage_terms))


def _semantic_node_to_term(circuit, node):
    """Convert one semantic IR node into a compositional term."""

    if isinstance(node, _SemanticPhaseLadderNode):
        fourier_term = _build_fourier_stage_terms(circuit, node)
        if fourier_term is not None:
            return fourier_term
    return _SemanticNodeLeafTerm(node)


def _semantic_ir_to_term(semantic_ir, template_circuit=None):
    """Convert a flat semantic IR list into a compositional term."""

    if not semantic_ir:
        return _SemanticSequenceTerm(tuple())

    if template_circuit is None:
        parts = tuple(_SemanticNodeLeafTerm(node) for node in semantic_ir)
    else:
        parts = tuple(
            _semantic_node_to_term(template_circuit, node)
            for node in semantic_ir
        )
    if len(parts) == 1:
        return parts[0]
    return _SemanticSequenceTerm(parts)


def _build_conjugation_term(circuit):
    """Build a semantic term for a full-span U · M · U^{-1} pattern."""

    conjugation_span = _find_conjugation_span(circuit)
    if conjugation_span is None:
        return None

    prefix_circuit = _build_circuit_from_instructions(
        circuit, list(circuit.data[: conjugation_span.prefix_size])
    )
    center_circuit = _build_circuit_from_instructions(
        circuit,
        list(
            circuit.data[
                conjugation_span.center_start : conjugation_span.center_end
            ]
        ),
    )
    return (
        circuit,
        _SemanticConjugationTerm(
            _SemanticCircuitLeafTerm(prefix_circuit),
            _SemanticCircuitLeafTerm(center_circuit),
        ),
    )


def _build_mirrored_self_inverse_term(circuit):
    """Build a semantic term for a diagonal-prefix mirrored/self-inverse shell."""

    expanded_circuit = _expand_single_composite_reference_source(circuit)
    mirrored_block = _find_mirrored_self_inverse_block(expanded_circuit)
    if mirrored_block is None:
        return None

    diagonal_prefix_circuit = _build_circuit_from_instructions(
        expanded_circuit,
        list(expanded_circuit.data[: mirrored_block.diagonal_prefix_size]),
    )
    shell_circuit = _build_circuit_from_instructions(
        expanded_circuit,
        list(expanded_circuit.data[mirrored_block.diagonal_prefix_size :]),
    )
    return (
        expanded_circuit,
        _SemanticMirroredSelfInverseTerm(
            _SemanticCircuitLeafTerm(diagonal_prefix_circuit),
            _SemanticCircuitLeafTerm(shell_circuit),
            mirrored_block.shell_prefix_size,
        ),
    )


def _build_semantic_term(circuit):
    """Build the strongest available semantic term for a circuit."""

    cache_key = _cacheable_circuit_key(circuit)
    if cache_key is not None:
        cached_term = _SEMANTIC_TERM_CACHE.get(cache_key)
        if cached_term is _CACHE_MISS:
            return None
        if cached_term is not None:
            return cached_term

    semantic_ir = _build_semantic_ir(circuit)
    if semantic_ir is not None:
        built_term = (circuit, _semantic_ir_to_term(semantic_ir, circuit))
        if cache_key is not None:
            _SEMANTIC_TERM_CACHE[cache_key] = built_term
        return built_term

    conjugation_term = _build_conjugation_term(circuit)
    if conjugation_term is not None:
        if cache_key is not None:
            _SEMANTIC_TERM_CACHE[cache_key] = conjugation_term
        return conjugation_term

    mirrored_term = _build_mirrored_self_inverse_term(circuit)
    if cache_key is not None:
        _SEMANTIC_TERM_CACHE[cache_key] = (
            mirrored_term if mirrored_term is not None else _CACHE_MISS
        )
    return mirrored_term


def _build_semantic_ir(circuit):
    """Build a direct-lowering semantic IR for H/swap/diagonal-phase circuits."""

    nodes = []
    diagonal_nodes = iter(_build_diagonal_phase_span_nodes(circuit))
    current_diagonal_node = next(diagonal_nodes, None)
    index = 0
    while index < len(circuit.data):
        if (
            current_diagonal_node is not None
            and index == current_diagonal_node.start_index
        ):
            simplified_span = _canonicalize_diagonal_phase_span(
                circuit, current_diagonal_node
            )
            for instruction in simplified_span.data:
                parameter = _diagonal_phase_parameter(instruction.operation)
                if parameter is None:
                    return None
                nodes.append(
                    _SemanticDiagonalPhaseOpNode(
                        instruction.operation.name,
                        tuple(
                            simplified_span.find_bit(qubit).index
                            for qubit in instruction.qubits
                        ),
                        float(parameter),
                    )
                )
            index = current_diagonal_node.end_index
            current_diagonal_node = next(diagonal_nodes, None)
            continue

        instruction = circuit.data[index]
        if instruction.operation.name == "h" and not instruction.clbits:
            nodes.append(
                _SemanticHadamardNode(
                    circuit.find_bit(instruction.qubits[0]).index
                )
            )
            index += 1
            continue

        if instruction.operation.name == "swap" and not instruction.clbits:
            nodes.append(
                _SemanticSwapNode(
                    circuit.find_bit(instruction.qubits[0]).index,
                    circuit.find_bit(instruction.qubits[1]).index,
                )
            )
            index += 1
            continue

        return None

    phase_ladder_node = _build_phase_ladder_semantic_node(nodes)
    if phase_ladder_node is not None:
        return [phase_ladder_node]

    return nodes


def _lower_semantic_leaf_node(circuit, node):
    """Lower a single semantic IR node into the target basis."""

    if isinstance(node, _SemanticHadamardNode):
        circuit.h(node.qubit_index)
        return True

    if isinstance(node, _SemanticSwapNode):
        _append_swap_in_target_basis(
            circuit, node.left_index, node.right_index
        )
        return True

    if isinstance(node, _SemanticDiagonalPhaseOpNode):
        if node.gate_name in {"rz", "p"}:
            circuit.rz(node.parameter, node.qubit_indices[0])
            return True
        if node.gate_name == "cp":
            _append_cp_in_target_basis(
                circuit,
                node.qubit_indices[0],
                node.qubit_indices[1],
                node.parameter,
            )
            return True
        if node.gate_name == "cz":
            _append_cp_in_target_basis(
                circuit,
                node.qubit_indices[0],
                node.qubit_indices[1],
                math.pi,
            )
            return True

    return False


def _append_cp_in_target_basis(
    circuit, control_index, target_index, parameter
):
    """Append a controlled-phase gate using only CX/RZ, up to global phase."""

    if abs(parameter) <= _PARAMETER_MERGE_TOLERANCE:
        return
    control = circuit.qubits[control_index]
    target = circuit.qubits[target_index]
    half_parameter = parameter / 2
    circuit.rz(half_parameter, control)
    circuit.cx(control, target)
    circuit.rz(-half_parameter, target)
    circuit.cx(control, target)
    circuit.rz(half_parameter, target)


def _append_swap_in_target_basis(circuit, left_index, right_index):
    """Append a swap using only CX gates."""

    left = circuit.qubits[left_index]
    right = circuit.qubits[right_index]
    circuit.cx(left, right)
    circuit.cx(right, left)
    circuit.cx(left, right)


def _lower_semantic_ir_to_target_basis(circuit, semantic_nodes):
    """Lower a semantic IR directly into the default all-to-all target basis."""

    rebuilt_circuit = circuit.copy_empty_like()
    rebuilt_circuit.global_phase = circuit.global_phase

    for node in semantic_nodes:
        if isinstance(node, _SemanticPhaseLadderNode):
            for operation_node in node.operations:
                if not _lower_semantic_leaf_node(
                    rebuilt_circuit, operation_node
                ):
                    return None
            continue

        if not _lower_semantic_leaf_node(rebuilt_circuit, node):
            return None

    return rebuilt_circuit


def _copy_compiled_fragment(circuit):
    """Return a detached copy of a compiled circuit fragment."""

    rebuilt_circuit = circuit.copy_empty_like()
    rebuilt_circuit.global_phase = circuit.global_phase
    rebuilt_circuit.compose(circuit, inplace=True)
    return rebuilt_circuit


def _empty_compose_container(reference_circuit, global_phase=0):
    """Return an empty circuit with the same wire shape as a compiled fragment."""

    rebuilt_circuit = reference_circuit.copy_empty_like()
    rebuilt_circuit.global_phase = global_phase
    return rebuilt_circuit


def _semantic_compiled_term_metrics(term):
    """Compute structural metrics recursively on compiled-term fragments."""

    if isinstance(term, _SemanticCircuitLeafTerm):
        return _circuit_metrics(term.circuit)

    if isinstance(term, _SemanticSequenceTerm):
        total_gates = 0
        depth = 0
        multi_qubit_gates = 0
        for part in term.parts:
            part_metrics = _semantic_compiled_term_metrics(part)
            total_gates += part_metrics["total_gates"]
            depth += part_metrics["depth"]
            multi_qubit_gates += part_metrics["multi_qubit_gates"]
        return {
            "total_gates": total_gates,
            "depth": depth,
            "multi_qubit_gates": multi_qubit_gates,
        }

    if isinstance(term, _SemanticRepeatTerm):
        body_metrics = _semantic_compiled_term_metrics(term.body)
        return {
            "total_gates": term.repeat_count * body_metrics["total_gates"],
            "depth": term.repeat_count * body_metrics["depth"],
            "multi_qubit_gates": term.repeat_count
            * body_metrics["multi_qubit_gates"],
        }

    if isinstance(term, _SemanticConjugationTerm):
        prefix_metrics = _semantic_compiled_term_metrics(term.prefix)
        center_metrics = _semantic_compiled_term_metrics(term.center)
        return {
            "total_gates": 2 * prefix_metrics["total_gates"]
            + center_metrics["total_gates"],
            "depth": 2 * prefix_metrics["depth"] + center_metrics["depth"],
            "multi_qubit_gates": 2 * prefix_metrics["multi_qubit_gates"]
            + center_metrics["multi_qubit_gates"],
        }

    if isinstance(term, _SemanticFourierLayerTerm):
        total_gates = 0
        depth = 0
        multi_qubit_gates = 0
        for stage in term.stages:
            stage_metrics = _semantic_compiled_term_metrics(stage)
            total_gates += stage_metrics["total_gates"]
            depth += stage_metrics["depth"]
            multi_qubit_gates += stage_metrics["multi_qubit_gates"]
        return {
            "total_gates": total_gates,
            "depth": depth,
            "multi_qubit_gates": multi_qubit_gates,
        }

    if isinstance(term, _SemanticMirroredSelfInverseTerm):
        diagonal_prefix_metrics = _semantic_compiled_term_metrics(
            term.diagonal_prefix
        )
        shell_metrics = _semantic_compiled_term_metrics(term.shell)
        return {
            "total_gates": diagonal_prefix_metrics["total_gates"]
            + shell_metrics["total_gates"],
            "depth": diagonal_prefix_metrics["depth"] + shell_metrics["depth"],
            "multi_qubit_gates": diagonal_prefix_metrics["multi_qubit_gates"]
            + shell_metrics["multi_qubit_gates"],
        }

    raise TypeError(f"Unsupported compiled semantic term: {type(term)!r}")


def _lower_semantic_term_to_circuit(template_circuit, term):
    """Lower a semantic term recursively into a concrete circuit."""

    if isinstance(term, _SemanticCircuitLeafTerm):
        return _copy_compiled_fragment(term.circuit)

    if isinstance(term, _SemanticNodeLeafTerm):
        return _lower_semantic_ir_to_target_basis(template_circuit, [term.node])

    if isinstance(term, _SemanticSequenceTerm):
        rebuilt_circuit = template_circuit.copy_empty_like()
        rebuilt_circuit.global_phase = template_circuit.global_phase
        for part in term.parts:
            lowered_part = _lower_semantic_term_to_circuit(
                template_circuit, part
            )
            if lowered_part is None:
                return None
            rebuilt_circuit.compose(lowered_part, inplace=True)
        return rebuilt_circuit

    if isinstance(term, _SemanticRepeatTerm):
        body_circuit = _lower_semantic_term_to_circuit(
            template_circuit, term.body
        )
        if body_circuit is None:
            return None
        rebuilt_circuit = template_circuit.copy_empty_like()
        rebuilt_circuit.global_phase = template_circuit.global_phase
        for _ in range(term.repeat_count):
            rebuilt_circuit.compose(body_circuit, inplace=True)
        return rebuilt_circuit

    if isinstance(term, _SemanticConjugationTerm):
        prefix_circuit = _lower_semantic_term_to_circuit(
            template_circuit, term.prefix
        )
        center_circuit = _lower_semantic_term_to_circuit(
            template_circuit, term.center
        )
        if prefix_circuit is None or center_circuit is None:
            return None
        rebuilt_circuit = template_circuit.copy_empty_like()
        rebuilt_circuit.global_phase = template_circuit.global_phase
        rebuilt_circuit.compose(prefix_circuit, inplace=True)
        rebuilt_circuit.compose(center_circuit, inplace=True)
        rebuilt_circuit.compose(prefix_circuit.inverse(), inplace=True)
        return rebuilt_circuit

    if isinstance(term, _SemanticFourierLayerTerm):
        rebuilt_circuit = template_circuit.copy_empty_like()
        rebuilt_circuit.global_phase = template_circuit.global_phase
        for stage in term.stages:
            lowered_stage = _lower_semantic_term_to_circuit(
                template_circuit, stage
            )
            if lowered_stage is None:
                return None
            rebuilt_circuit.compose(lowered_stage, inplace=True)
        return rebuilt_circuit

    if isinstance(term, _SemanticMirroredSelfInverseTerm):
        diagonal_prefix_circuit = _lower_semantic_term_to_circuit(
            template_circuit, term.diagonal_prefix
        )
        shell_circuit = _lower_semantic_term_to_circuit(
            template_circuit, term.shell
        )
        if diagonal_prefix_circuit is None or shell_circuit is None:
            return None
        rebuilt_circuit = template_circuit.copy_empty_like()
        rebuilt_circuit.global_phase = template_circuit.global_phase
        rebuilt_circuit.compose(diagonal_prefix_circuit, inplace=True)
        rebuilt_circuit.compose(shell_circuit, inplace=True)
        return rebuilt_circuit

    raise TypeError(f"Unsupported semantic term: {type(term)!r}")


def _build_repeated_run_term(prefix_circuit, block_circuit, suffix_circuit, repeat_count):
    """Return the term-algebra representation of P · B^r · S."""

    parts = []
    if len(prefix_circuit.data) > 0:
        parts.append(_SemanticCircuitLeafTerm(prefix_circuit))
    parts.append(
        _SemanticRepeatTerm(_SemanticCircuitLeafTerm(block_circuit), repeat_count)
    )
    if len(suffix_circuit.data) > 0:
        parts.append(_SemanticCircuitLeafTerm(suffix_circuit))

    if len(parts) == 1:
        return parts[0]
    return _SemanticSequenceTerm(tuple(parts))


def _compile_semantic_leaf_fragment(circuit, compiler):
    """Compile one semantic-term leaf fragment without recursive term rebuilding."""

    cache_key = _semantic_cache_key(circuit, compiler, "semantic_leaf_fragment")
    if cache_key is not None:
        cached_fragment = _SEMANTIC_REFERENCE_CACHE.get(cache_key)
        if cached_fragment is _CACHE_MISS:
            return None
        if cached_fragment is not None:
            return cached_fragment

    circuit = _semantic_local_simplify(circuit)

    if compiler.target_backend is not None:
        compiled_fragment = _cached_backend_preset_transpile(
            circuit,
            compiler,
            optimization_level=3,
            seed=getattr(compiler, "seed_transpiler", None),
        )
        if cache_key is not None:
            _SEMANTIC_REFERENCE_CACHE[cache_key] = compiled_fragment
        return compiled_fragment

    semantic_ir = _build_semantic_ir(circuit)
    if semantic_ir is not None:
        semantic_reference = _lower_semantic_term_to_circuit(
            circuit, _semantic_ir_to_term(semantic_ir)
        )
        if semantic_reference is not None:
            if len(circuit.data) > _MAX_SEMANTIC_LOCAL_OPT_BLOCK_SIZE:
                if cache_key is not None:
                    _SEMANTIC_REFERENCE_CACHE[cache_key] = semantic_reference
                return semantic_reference
            compiled_fragment = qiskit_transpile(
                semantic_reference,
                basis_gates=list(compiler.target_gateset),
                optimization_level=3,
                layout_method="trivial",
                routing_method="none",
            )
            if cache_key is not None:
                _SEMANTIC_REFERENCE_CACHE[cache_key] = compiled_fragment
            return compiled_fragment

    compiled_fragment = qiskit_transpile(
        circuit,
        basis_gates=list(compiler.target_gateset),
        optimization_level=3,
        layout_method="trivial",
        routing_method="none",
    )
    if cache_key is not None:
        _SEMANTIC_REFERENCE_CACHE[cache_key] = compiled_fragment
    return compiled_fragment


def _compile_semantic_term_to_circuit(template_circuit, term, compiler):
    """Compile a semantic term recursively into a concrete circuit."""

    cache_key = _semantic_term_cache_key(term, compiler)
    if cache_key is not None:
        cached_term = _SEMANTIC_TERM_COMPILED_CACHE.get(cache_key)
        if cached_term is _CACHE_MISS:
            return None
        if cached_term is not None:
            return cached_term

    if isinstance(term, _SemanticCircuitLeafTerm):
        compiled_term = _compile_semantic_leaf_fragment(term.circuit, compiler)
        if cache_key is not None:
            _SEMANTIC_TERM_COMPILED_CACHE[cache_key] = (
                compiled_term if compiled_term is not None else _CACHE_MISS
            )
        return compiled_term

    if isinstance(term, _SemanticNodeLeafTerm):
        lowered_circuit = _lower_semantic_ir_to_target_basis(
            template_circuit, [term.node]
        )
        if lowered_circuit is None:
            if cache_key is not None:
                _SEMANTIC_TERM_COMPILED_CACHE[cache_key] = _CACHE_MISS
            return None
        if compiler.target_backend is None:
            compiled_term = lowered_circuit
        else:
            compiled_term = _cached_backend_preset_transpile(
                lowered_circuit,
                compiler,
                optimization_level=3,
                seed=getattr(compiler, "seed_transpiler", None),
            )
        if cache_key is not None:
            _SEMANTIC_TERM_COMPILED_CACHE[cache_key] = compiled_term
        return compiled_term

    if isinstance(term, _SemanticSequenceTerm):
        compiled_parts = []
        for part in term.parts:
            compiled_part = _compile_semantic_term_to_circuit(
                template_circuit, part, compiler
            )
            if compiled_part is None:
                return None
            compiled_parts.append(compiled_part)
        compiled_term = _empty_compose_container(
            template_circuit, template_circuit.global_phase
        )
        for compiled_part in compiled_parts:
            compiled_term.compose(compiled_part, inplace=True)
        if cache_key is not None:
            _SEMANTIC_TERM_COMPILED_CACHE[cache_key] = compiled_term
        return compiled_term

    if isinstance(term, _SemanticRepeatTerm):
        compiled_body = _compile_semantic_term_to_circuit(
            template_circuit, term.body, compiler
        )
        if compiled_body is None:
            if cache_key is not None:
                _SEMANTIC_TERM_COMPILED_CACHE[cache_key] = _CACHE_MISS
            return None
        compiled_term = _empty_compose_container(
            compiled_body, template_circuit.global_phase
        )
        for _ in range(term.repeat_count):
            compiled_term.compose(compiled_body, inplace=True)
        if cache_key is not None:
            _SEMANTIC_TERM_COMPILED_CACHE[cache_key] = compiled_term
        return compiled_term

    if isinstance(term, _SemanticConjugationTerm):
        compiled_prefix = _compile_semantic_term_to_circuit(
            template_circuit, term.prefix, compiler
        )
        compiled_center = _compile_semantic_term_to_circuit(
            template_circuit, term.center, compiler
        )
        if compiled_prefix is None or compiled_center is None:
            if cache_key is not None:
                _SEMANTIC_TERM_COMPILED_CACHE[cache_key] = _CACHE_MISS
            return None
        compiled_term = _empty_compose_container(
            compiled_prefix, template_circuit.global_phase
        )
        compiled_term.compose(compiled_prefix, inplace=True)
        compiled_term.compose(compiled_center, inplace=True)
        compiled_term.compose(compiled_prefix.inverse(), inplace=True)
        if cache_key is not None:
            _SEMANTIC_TERM_COMPILED_CACHE[cache_key] = compiled_term
        return compiled_term

    if isinstance(term, _SemanticFourierLayerTerm):
        if compiler.target_backend is None:
            compiled_term = _lower_semantic_term_to_circuit(
                template_circuit, term
            )
            if cache_key is not None:
                _SEMANTIC_TERM_COMPILED_CACHE[cache_key] = (
                    compiled_term if compiled_term is not None else _CACHE_MISS
                )
            return compiled_term
        compiled_stages = []
        for stage in term.stages:
            compiled_stage = _compile_semantic_term_to_circuit(
                template_circuit, stage, compiler
            )
            if compiled_stage is None:
                if cache_key is not None:
                    _SEMANTIC_TERM_COMPILED_CACHE[cache_key] = _CACHE_MISS
                return None
            compiled_stages.append(compiled_stage)
        compiled_term = _empty_compose_container(
            compiled_stages[0], template_circuit.global_phase
        )
        for compiled_stage in compiled_stages:
            compiled_term.compose(compiled_stage, inplace=True)
        if cache_key is not None:
            _SEMANTIC_TERM_COMPILED_CACHE[cache_key] = compiled_term
        return compiled_term

    if isinstance(term, _SemanticMirroredSelfInverseTerm):
        compiled_diagonal_prefix = _compile_semantic_term_to_circuit(
            template_circuit, term.diagonal_prefix, compiler
        )
        compiled_shell = _compile_semantic_term_to_circuit(
            template_circuit, term.shell, compiler
        )
        if compiled_diagonal_prefix is None or compiled_shell is None:
            if cache_key is not None:
                _SEMANTIC_TERM_COMPILED_CACHE[cache_key] = _CACHE_MISS
            return None
        compiled_term = _empty_compose_container(
            compiled_diagonal_prefix, template_circuit.global_phase
        )
        compiled_term.compose(compiled_diagonal_prefix, inplace=True)
        compiled_term.compose(compiled_shell, inplace=True)
        if cache_key is not None:
            _SEMANTIC_TERM_COMPILED_CACHE[cache_key] = compiled_term
        return compiled_term

    raise TypeError(f"Unsupported semantic term: {type(term)!r}")


def _compile_semantic_reference(circuit, compiler):
    """Compile a circuit via semantic terms when supported."""

    cache_key = _semantic_cache_key(circuit, compiler, "semantic_reference")
    if cache_key is not None:
        cached_reference = _SEMANTIC_REFERENCE_CACHE.get(cache_key)
        if cached_reference is _CACHE_MISS:
            return None
        if cached_reference is not None:
            return cached_reference

    built_semantic_term = _build_semantic_term(circuit)
    if built_semantic_term is None:
        if cache_key is not None:
            _SEMANTIC_REFERENCE_CACHE[cache_key] = _CACHE_MISS
        return None
    template_circuit, semantic_term = built_semantic_term
    compiled_reference = _compile_semantic_term_to_circuit(
        template_circuit, semantic_term, compiler
    )
    if cache_key is not None:
        _SEMANTIC_REFERENCE_CACHE[cache_key] = (
            compiled_reference if compiled_reference is not None else _CACHE_MISS
        )
    return compiled_reference


def _compile_semantic_reference_with_local_opt(circuit, compiler):
    """Lower semantic IR directly, then locally re-optimize small semantic blocks."""

    cache_key = _semantic_cache_key(
        circuit, compiler, "semantic_reference_local_opt"
    )
    if cache_key is not None:
        cached_reference = _SEMANTIC_REFERENCE_CACHE.get(cache_key)
        if cached_reference is _CACHE_MISS:
            return None
        if cached_reference is not None:
            return cached_reference

    semantic_reference = _compile_semantic_reference(circuit, compiler)
    if semantic_reference is None:
        if cache_key is not None:
            _SEMANTIC_REFERENCE_CACHE[cache_key] = _CACHE_MISS
        return None

    if compiler.target_backend is not None:
        if len(circuit.data) > _MAX_SEMANTIC_LOCAL_OPT_BLOCK_SIZE:
            if cache_key is not None:
                _SEMANTIC_REFERENCE_CACHE[cache_key] = semantic_reference
            return semantic_reference
        semantic_local_opt_reference = qiskit_transpile(
            semantic_reference,
            backend=compiler.target_backend,
            optimization_level=1,
            seed_transpiler=getattr(compiler, "seed_transpiler", None),
        )
        if cache_key is not None:
            _SEMANTIC_REFERENCE_CACHE[cache_key] = semantic_local_opt_reference
        return semantic_local_opt_reference

    if len(circuit.data) > _MAX_SEMANTIC_LOCAL_OPT_BLOCK_SIZE:
        if cache_key is not None:
            _SEMANTIC_REFERENCE_CACHE[cache_key] = semantic_reference
        return semantic_reference

    semantic_local_opt_reference = qiskit_transpile(
        semantic_reference,
        basis_gates=list(compiler.target_gateset),
        optimization_level=3,
        layout_method="trivial",
        routing_method="none",
    )
    if cache_key is not None:
        _SEMANTIC_REFERENCE_CACHE[cache_key] = semantic_local_opt_reference
    return semantic_local_opt_reference


def _merge_adjacent_parameterized_gates(circuit):
    """Merge adjacent additive rotation/phase gates on the same wires."""

    rebuilt_circuit = circuit.copy_empty_like()
    rebuilt_circuit.global_phase = circuit.global_phase
    pending_instruction = None

    def flush_pending_instruction():
        nonlocal pending_instruction
        if pending_instruction is None:
            return
        rebuilt_circuit.append(
            pending_instruction.operation,
            pending_instruction.qubits,
            pending_instruction.clbits,
        )
        pending_instruction = None

    for instruction in circuit.data:
        if pending_instruction is None:
            pending_instruction = instruction
            continue

        if _can_merge_adjacent_parameterized_gates(
            pending_instruction, instruction
        ):
            merged_parameter = float(
                pending_instruction.operation.params[0]
            ) + float(instruction.operation.params[0])
            if abs(merged_parameter) <= _PARAMETER_MERGE_TOLERANCE:
                pending_instruction = None
            else:
                pending_instruction = CircuitInstruction(
                    _copy_operation_with_parameter(
                        pending_instruction.operation, merged_parameter
                    ),
                    pending_instruction.qubits,
                    pending_instruction.clbits,
                )
            continue

        flush_pending_instruction()
        pending_instruction = instruction

    flush_pending_instruction()
    if len(rebuilt_circuit.data) >= len(circuit.data):
        return circuit

    return rebuilt_circuit


def _block_has_mergeable_parameter_repetitions(circuit, block_size):
    """Return True when a repeated block contains adjacent mergeable gates."""

    block_circuit = _build_circuit_from_instructions(
        circuit, list(circuit.data[:block_size])
    )
    return (
        len(_merge_adjacent_parameterized_gates(block_circuit).data)
        < len(block_circuit.data)
    )


def _block_has_self_inverse_boundary_overlap(circuit, block_size):
    """Return True when a block's suffix cancels with the next block's prefix."""

    return _find_self_inverse_prefix_suffix_overlap(circuit, block_size) > 0


def _run_commutative_inverse_cancellation(circuit):
    """Run Qiskit's commutative inverse cancellation when supported."""

    try:
        return PassManager([CommutativeInverseCancellation()]).run(circuit)
    except Exception:
        return circuit


def _has_nontrivial_composite_ops(circuit, target_gateset):
    """Return True when a circuit contains composite non-basis operations."""

    for instruction in circuit.data:
        operation = instruction.operation
        if operation.name in target_gateset or operation.name in {
            "measure",
            "barrier",
        }:
            continue

        definition = getattr(operation, "definition", None)
        if definition is not None and len(definition.data) > 1:
            return True

    return False


def _should_direct_short_circuit_qiskit_source_preset(
    source_circuit, target_gateset, target_backend, has_custom_passes
):
    """Return True when a qiskit-source circuit should go straight to opt3.

    This avoids paying extra wrapper overhead on medium-sized composite-source
    circuits where the optimized branch would ultimately defer to a source-level
    preset transpilation anyway.
    """

    if (
        target_backend is not None
        or has_custom_passes
        or not isinstance(source_circuit, QiskitCircuit)
    ):
        return False

    source_gate_count = len(source_circuit.data)
    if source_gate_count == 0 or source_gate_count > _MAX_DIRECT_SOURCE_PRESET_SIZE:
        return False
    if _has_reducible_diagonal_phase_span(source_circuit):
        return False

    return _has_nontrivial_composite_ops(source_circuit, target_gateset)


def _circuit_is_in_target_basis(circuit, target_gateset):
    """Return True when a circuit already lies in the requested basis."""

    return all(
        instruction.operation.name in target_gateset
        or instruction.operation.name in {"measure", "barrier"}
        for instruction in circuit.data
    )


def _should_direct_short_circuit_small_basis_source_preset(
    source_circuit, target_gateset, target_backend, has_custom_passes
):
    """Return True for tiny qiskit-source circuits already near the target basis.

    These circuits do not benefit from the UCC control layer. A direct opt3
    pass is cheaper and avoids anti-regression cases such as small Hamiltonian
    simulation circuits that are already close to the final basis.
    """

    if (
        target_backend is not None
        or has_custom_passes
        or not isinstance(source_circuit, QiskitCircuit)
    ):
        return False

    source_gate_count = len(source_circuit.data)
    if source_gate_count == 0 or source_gate_count > _MAX_SMALL_BASIS_SOURCE_PRESET_SIZE:
        return False

    return (
        _circuit_is_in_target_basis(source_circuit, target_gateset)
        and not _has_nontrivial_composite_ops(source_circuit, target_gateset)
    )


def _should_direct_short_circuit_repeated_basis_source(
    source_circuit, target_gateset, target_backend, has_custom_passes
):
    """Return True for large primitive sources already in target basis.

    For large all-to-all source circuits that are already expressed in the
    target basis and do not contain composite operations, the UCC control layer
    tends to behave as anti-regression logic rather than as a useful optimizer.
    Short-circuiting these cases avoids paying for repeated-structure scans
    that do not materially improve the output.
    """

    if (
        target_backend is not None
        or has_custom_passes
        or len(source_circuit.data) < _MIN_REPEATED_BASIS_SOURCE_FAST_PATH_SIZE
    ):
        return False
    if not _circuit_is_in_target_basis(source_circuit, target_gateset):
        return False
    return not _has_nontrivial_composite_ops(source_circuit, target_gateset)


def _find_repeated_run(
    circuit,
    max_block_size=_MAX_STRUCTURAL_BLOCK_SIZE,
    min_repeats=_MIN_REPEATED_BLOCK_REPEATS,
):
    """Detect the largest repeated exact block anywhere in a circuit."""

    instruction_count = len(circuit.data)
    max_candidate_size = min(max_block_size, instruction_count // min_repeats)
    if max_candidate_size < 1:
        return None

    signatures = [
        _instruction_signature(circuit, instruction)
        for instruction in circuit.data
    ]
    best_match = None
    best_coverage = 0

    for block_size in range(1, max_candidate_size + 1):
        start_index = 0
        while start_index + min_repeats * block_size <= instruction_count:
            block = signatures[start_index : start_index + block_size]
            repeat_count = 1
            while (
                start_index + (repeat_count + 1) * block_size
                <= instruction_count
            ):
                candidate_start = start_index + repeat_count * block_size
                candidate_end = candidate_start + block_size
                if signatures[candidate_start:candidate_end] != block:
                    break
                repeat_count += 1

            coverage = repeat_count * block_size
            if repeat_count >= min_repeats and coverage > best_coverage:
                best_match = (start_index, block_size, repeat_count)
                best_coverage = coverage

            start_index += coverage if repeat_count > 1 else 1

    return best_match


def _find_repeated_prefix(
    circuit,
    max_block_size=_MAX_STRUCTURAL_BLOCK_SIZE,
    min_repeats=_MIN_REPEATED_BLOCK_REPEATS,
):
    """Detect the largest repeated exact prefix block in a circuit."""

    instruction_count = len(circuit.data)
    max_candidate_size = min(max_block_size, instruction_count // min_repeats)
    if max_candidate_size < 1:
        return None

    signatures = [
        _instruction_signature(circuit, instruction)
        for instruction in circuit.data
    ]

    if instruction_count > _FAST_PREFIX_SCAN_SIZE:
        full_coverage_divisors = [
            block_size
            for block_size in range(max_candidate_size, 0, -1)
            if instruction_count % block_size == 0
        ]
        for block_size in full_coverage_divisors:
            repeat_count = instruction_count // block_size
            if repeat_count < min_repeats:
                continue

            prefix = signatures[:block_size]
            if all(
                signatures[start_index : start_index + block_size] == prefix
                for start_index in range(
                    block_size, instruction_count, block_size
                )
            ):
                return (block_size, repeat_count)

        best_match = None
        best_coverage = 0

        for block_size in range(max_candidate_size, 0, -1):
            max_coverage = block_size * (instruction_count // block_size)
            if max_coverage <= best_coverage:
                continue

            prefix = signatures[:block_size]
            repeat_count = 1
            while (repeat_count + 1) * block_size <= instruction_count:
                start_index = repeat_count * block_size
                end_index = start_index + block_size
                if signatures[start_index:end_index] != prefix:
                    break
                repeat_count += 1

            coverage = repeat_count * block_size
            if repeat_count >= min_repeats and coverage > best_coverage:
                best_match = (block_size, repeat_count)
                best_coverage = coverage
                if coverage == instruction_count:
                    break

        return best_match

    best_match = None
    best_coverage = 0

    for block_size in range(1, max_candidate_size + 1):
        prefix = signatures[:block_size]
        repeat_count = 1
        while (repeat_count + 1) * block_size <= instruction_count:
            start_index = repeat_count * block_size
            end_index = start_index + block_size
            if signatures[start_index:end_index] != prefix:
                break
            repeat_count += 1

        coverage = repeat_count * block_size
        if repeat_count >= min_repeats and coverage > best_coverage:
            best_match = (block_size, repeat_count)
            best_coverage = coverage

    return best_match


def _dominant_hierarchical_repeat(circuit):
    """Return the strongest dominant repeated structure in a circuit."""

    instruction_count = len(circuit.data)
    if instruction_count == 0:
        return None

    best_repeat = None
    best_coverage = 0

    repeated_run = _find_repeated_run(circuit)
    if repeated_run is not None:
        start_index, block_size, repeat_count = repeated_run
        coverage = block_size * repeat_count
        if coverage >= _MIN_DOMINANT_REPEAT_FRACTION * instruction_count:
            best_repeat = _RepeatedSpanNode(
                start_index, block_size, repeat_count
            )
            best_coverage = coverage

    repeated_prefix = _find_repeated_prefix(circuit)
    if repeated_prefix is not None:
        block_size, repeat_count = repeated_prefix
        coverage = block_size * repeat_count
        if coverage >= _MIN_DOMINANT_REPEAT_FRACTION * instruction_count:
            prefix_repeat = _RepeatedSpanNode(0, block_size, repeat_count)
            if coverage > best_coverage:
                best_repeat = prefix_repeat

    return best_repeat


def _build_hierarchical_nodes(circuit):
    """Build a small hierarchical view of the dominant circuit structure."""

    instruction_count = len(circuit.data)
    if instruction_count == 0:
        return []

    dominant_repeat = _dominant_hierarchical_repeat(circuit)
    if dominant_repeat is None:
        return [_InstructionSpanNode(0, instruction_count)]

    nodes = []
    _append_instruction_span_node(nodes, 0, dominant_repeat.start_index)
    nodes.append(dominant_repeat)
    _append_instruction_span_node(
        nodes,
        dominant_repeat.start_index
        + dominant_repeat.block_size * dominant_repeat.repeat_count,
        instruction_count,
    )
    return nodes


def _simplify_repeated_prefix(circuit):
    """Simplify a repeated leading block once and reuse the result."""

    repeated_prefix = _find_repeated_prefix(circuit)
    if repeated_prefix is None:
        return circuit

    block_size, repeat_count = repeated_prefix
    run_end = block_size * repeat_count
    block_instructions = list(circuit.data[:block_size])
    block_circuit = _build_circuit_from_instructions(
        circuit, block_instructions
    )
    simplified_block = _run_commutative_inverse_cancellation(block_circuit)

    if len(simplified_block.data) >= block_size:
        return circuit

    rebuilt_circuit = circuit.copy_empty_like()
    rebuilt_circuit.global_phase = circuit.global_phase
    for _ in range(repeat_count):
        for instruction in simplified_block.data:
            rebuilt_circuit.append(
                instruction.operation,
                instruction.qubits,
                instruction.clbits,
            )

    for instruction in circuit.data[run_end:]:
        rebuilt_circuit.append(
            instruction.operation,
            instruction.qubits,
            instruction.clbits,
        )

    if len(rebuilt_circuit.data) >= len(circuit.data):
        return circuit

    return rebuilt_circuit


def _find_self_inverse_prefix_suffix_overlap(circuit, block_size):
    """Return the overlap size when a block suffix cancels the next prefix."""

    signatures = [
        _instruction_signature(circuit, instruction)
        for instruction in circuit.data[:block_size]
    ]
    inverse_signatures = [
        _inverse_instruction_signature(circuit, instruction)
        for instruction in circuit.data[:block_size]
    ]
    max_overlap = min(block_size // 2, 64)
    for overlap in range(max_overlap, 0, -1):
        suffix = signatures[block_size - overlap : block_size]
        inverse_prefix = list(reversed(inverse_signatures[:overlap]))
        if any(signature is None for signature in inverse_prefix):
            continue
        if suffix == inverse_prefix:
            return overlap
    return 0


def _compress_repeated_prefix_boundary_cancellation(circuit):
    """Compress repeated prefixes when adjacent copies cancel at the boundary."""

    repeated_prefix = _find_repeated_prefix(circuit)
    if repeated_prefix is None:
        return circuit

    block_size, repeat_count = repeated_prefix
    if repeat_count < 2:
        return circuit

    overlap = _find_self_inverse_prefix_suffix_overlap(circuit, block_size)
    if overlap == 0:
        return circuit

    middle_start = overlap
    middle_end = block_size - overlap
    rebuilt_circuit = circuit.copy_empty_like()
    rebuilt_circuit.global_phase = circuit.global_phase

    _append_instruction_sequence(rebuilt_circuit, circuit.data[:overlap])
    middle_instructions = circuit.data[middle_start:middle_end]
    for _ in range(repeat_count):
        _append_instruction_sequence(rebuilt_circuit, middle_instructions)
    _append_instruction_sequence(
        rebuilt_circuit, circuit.data[block_size - overlap : block_size]
    )
    _append_instruction_sequence(
        rebuilt_circuit, circuit.data[block_size * repeat_count :]
    )

    if len(rebuilt_circuit.data) >= len(circuit.data):
        return circuit

    return rebuilt_circuit


def _find_adjacent_inverse_blocks(
    circuit, max_block_size=_MAX_STRUCTURAL_BLOCK_SIZE
):
    """Detect the largest adjacent exact block followed by its inverse."""

    instruction_count = len(circuit.data)
    max_candidate_size = min(max_block_size, instruction_count // 2)
    if max_candidate_size < 1:
        return None

    signatures = [
        _instruction_signature(circuit, instruction)
        for instruction in circuit.data
    ]
    inverse_signatures = [
        _inverse_instruction_signature(circuit, instruction)
        for instruction in circuit.data
    ]
    best_match = None
    best_coverage = 0

    for block_size in range(1, max_candidate_size + 1):
        for start_index in range(0, instruction_count - 2 * block_size + 1):
            block = signatures[start_index : start_index + block_size]
            inverse_block = list(
                reversed(
                    inverse_signatures[
                        start_index + block_size : start_index + 2 * block_size
                    ]
                )
            )
            if any(signature is None for signature in inverse_block):
                continue
            if block != inverse_block:
                continue

            coverage = 2 * block_size
            if coverage > best_coverage:
                best_match = (start_index, block_size)
                best_coverage = coverage

    return best_match


def _simplify_repeated_run(circuit):
    """Simplify a repeated block once and reuse the result."""

    repeated_run = _find_repeated_run(circuit)
    if repeated_run is None:
        return circuit

    start_index, block_size, repeat_count = repeated_run
    run_end = start_index + block_size * repeat_count
    block_instructions = list(
        circuit.data[start_index : start_index + block_size]
    )
    block_circuit = _build_circuit_from_instructions(
        circuit, block_instructions
    )
    simplified_block = _run_commutative_inverse_cancellation(block_circuit)

    if len(simplified_block.data) >= block_size:
        return circuit

    rebuilt_circuit = circuit.copy_empty_like()
    rebuilt_circuit.global_phase = circuit.global_phase
    for instruction in circuit.data[:start_index]:
        rebuilt_circuit.append(
            instruction.operation,
            instruction.qubits,
            instruction.clbits,
        )

    for _ in range(repeat_count):
        for instruction in simplified_block.data:
            rebuilt_circuit.append(
                instruction.operation,
                instruction.qubits,
                instruction.clbits,
            )

    for instruction in circuit.data[run_end:]:
        rebuilt_circuit.append(
            instruction.operation,
            instruction.qubits,
            instruction.clbits,
        )

    if len(rebuilt_circuit.data) >= len(circuit.data):
        return circuit

    return rebuilt_circuit


def _cancel_adjacent_inverse_blocks(circuit):
    """Remove an adjacent block and its exact inverse."""

    inverse_block = _find_adjacent_inverse_blocks(circuit)
    if inverse_block is None:
        return circuit

    start_index, block_size = inverse_block
    rebuilt_circuit = circuit.copy_empty_like()
    rebuilt_circuit.global_phase = circuit.global_phase

    for instruction in circuit.data[:start_index]:
        rebuilt_circuit.append(
            instruction.operation,
            instruction.qubits,
            instruction.clbits,
        )

    for instruction in circuit.data[start_index + 2 * block_size :]:
        rebuilt_circuit.append(
            instruction.operation,
            instruction.qubits,
            instruction.clbits,
        )

    return rebuilt_circuit


def _structural_pre_simplify(circuit):
    """Apply cheap structure-aware simplifications before basis lowering.

    Layer 1 uses commutative inverse cancellation directly on the whole
    circuit. Layer 2 simplifies large repeated exact blocks anywhere in the
    circuit. Layer 3 removes adjacent exact inverse blocks as whole units.
    """

    simplified_circuit = circuit
    for _ in range(3):
        previous_instruction_count = len(simplified_circuit.data)
        simplified_circuit = _canonicalize_diagonal_phase_spans(
            simplified_circuit
        )
        simplified_circuit = _merge_adjacent_parameterized_gates(
            simplified_circuit
        )
        simplified_circuit = _compress_repeated_prefix_boundary_cancellation(
            simplified_circuit
        )
        prefix_simplified_circuit = _simplify_repeated_prefix(
            simplified_circuit
        )
        if len(prefix_simplified_circuit.data) < len(simplified_circuit.data):
            simplified_circuit = prefix_simplified_circuit
        elif len(simplified_circuit.data) <= _MAX_GLOBAL_STRUCTURAL_SCAN_SIZE:
            simplified_circuit = _simplify_repeated_run(simplified_circuit)
            simplified_circuit = _cancel_adjacent_inverse_blocks(
                simplified_circuit
            )
        simplified_circuit = _run_commutative_inverse_cancellation(
            simplified_circuit
        )
        if len(simplified_circuit.data) >= previous_instruction_count:
            break
    return simplified_circuit


def _blockwise_structural_pre_simplify_repeated_prefix(circuit):
    """Pre-simplify a dominant repeated prefix by simplifying one block once."""

    if len(circuit.data) < _MIN_BLOCKWISE_REPEAT_PRESIMPLIFY_SIZE:
        return None

    repeated_prefix = _find_repeated_prefix(circuit)
    if repeated_prefix is None:
        return None

    block_size, repeat_count = repeated_prefix
    coverage = block_size * repeat_count
    if coverage < _MIN_DOMINANT_REPEAT_FRACTION * len(circuit.data):
        return None

    block_circuit = _build_circuit_from_instructions(
        circuit, list(circuit.data[:block_size])
    )
    simplified_block = _structural_pre_simplify(block_circuit)

    rebuilt_circuit = circuit.copy_empty_like()
    rebuilt_circuit.global_phase = circuit.global_phase
    for _ in range(repeat_count):
        for instruction in simplified_block.data:
            _append_mapped_instruction(
                rebuilt_circuit, simplified_block, instruction
            )

    _append_instruction_sequence(rebuilt_circuit, circuit.data[coverage:])
    return rebuilt_circuit


def _circuit_metrics(circuit):
    """Compute coarse structural metrics for anti-regression checks."""

    total_gates = 0
    multi_qubit_gates = 0
    for instruction in circuit.data:
        operation = instruction.operation
        if operation.name == "barrier":
            continue
        total_gates += 1
        if operation.num_qubits > 1 and operation.name != "measure":
            multi_qubit_gates += 1

    return {
        "total_gates": total_gates,
        "depth": circuit.depth(),
        "multi_qubit_gates": multi_qubit_gates,
    }


def _circuit_cost(circuit):
    """Score a circuit for conservative default-pipeline comparisons.

    The default compiler should not significantly inflate total size or depth
    in exchange for tiny multi-qubit improvements. This weighted score keeps
    two-qubit reductions valuable while still rejecting obvious blow-ups.
    """

    metrics = _circuit_metrics(circuit)
    return (
        metrics["total_gates"]
        + metrics["depth"]
        + 10 * metrics["multi_qubit_gates"]
    )


def _should_compare_against_preset(
    original_circuit, baseline_circuit, candidate_circuit
):
    """Return True when the default path shows a clear regression signal.

    Two cases justify the extra preset comparison:
    1. The UCC default flow is already worse than a simple basis translation.
    2. Basis lowering alone inflated the circuit enough that a more global
       optimizer may recover higher-level structure before decomposition.
    """

    baseline_cost = _circuit_cost(baseline_circuit)
    return _circuit_cost(
        candidate_circuit
    ) > baseline_cost or baseline_cost > 1.5 * _circuit_cost(original_circuit)


def _macro_repeat_candidates(circuit, block_size, repeat_count):
    """Yield bounded macro-repeat sizes for blockwise preset references."""

    yield 1

    block_has_parameter_merges = _block_has_mergeable_parameter_repetitions(
        circuit, block_size
    )
    block_has_boundary_overlap = _block_has_self_inverse_boundary_overlap(
        circuit, block_size
    )
    if not (block_has_parameter_merges or block_has_boundary_overlap):
        return

    for macro_repeat in _REPEAT_MACRO_FACTORS:
        if macro_repeat == 1:
            continue
        if macro_repeat > repeat_count:
            continue
        if block_size * macro_repeat > _MAX_REPEAT_MACRO_BLOCK_SIZE:
            continue
        if not block_has_parameter_merges and macro_repeat > 2:
            continue
        yield macro_repeat


def _append_instruction_sequence(circuit, instructions):
    """Append a sequence of instructions to a circuit."""

    for instruction in instructions:
        circuit.append(
            instruction.operation,
            instruction.qubits,
            instruction.clbits,
        )


def _append_mapped_instruction(
    destination_circuit, source_template, instruction
):
    """Append an instruction while remapping qubits/clbits by index."""

    destination_circuit.append(
        instruction.operation,
        [
            destination_circuit.qubits[source_template.find_bit(qubit).index]
            for qubit in instruction.qubits
        ],
        [
            destination_circuit.clbits[source_template.find_bit(clbit).index]
            for clbit in instruction.clbits
        ],
    )


def _append_inverse_mapped_instruction(
    destination_circuit, source_template, instruction
):
    """Append an inverse instruction while remapping qubits/clbits by index."""

    destination_circuit.append(
        instruction.operation.inverse(),
        [
            destination_circuit.qubits[source_template.find_bit(qubit).index]
            for qubit in instruction.qubits
        ],
        [
            destination_circuit.clbits[source_template.find_bit(clbit).index]
            for clbit in instruction.clbits
        ],
    )


def _append_instruction_span_node(nodes, start_index, end_index):
    """Append a non-empty leaf span node."""

    if end_index > start_index:
        nodes.append(_InstructionSpanNode(start_index, end_index))


def _hierarchical_node_coverage(node):
    """Return the instruction coverage of a hierarchical node."""

    if isinstance(node, _InstructionSpanNode):
        return node.end_index - node.start_index
    return node.block_size * node.repeat_count


def _compile_repeated_prefix_reference(circuit, compiler, repeated_prefix):
    """Compile blockwise preset candidates for a dominant repeated prefix."""

    cache_key = (
        _cacheable_circuit_key(circuit),
        repeated_prefix,
        _target_basis_cache_key(compiler),
        _backend_cache_marker(compiler),
        "macro_repeat",
    )
    if cache_key[0] is not None and cache_key in _REPEATED_REFERENCE_CACHE:
        return _REPEATED_REFERENCE_CACHE[cache_key]

    block_size, repeat_count = repeated_prefix
    coverage = block_size * repeat_count
    if coverage < _MIN_DOMINANT_REPEAT_FRACTION * len(circuit.data):
        return None

    candidate_circuits = []
    for macro_repeat in _macro_repeat_candidates(
        circuit, block_size, repeat_count
    ):
        macro_size = block_size * macro_repeat
        macro_circuit = _build_circuit_from_instructions(
            circuit, list(circuit.data[:macro_size])
        )
        macro_circuit = _semantic_local_simplify(macro_circuit)
        optimized_macro = _compile_semantic_reference_with_local_opt(
            macro_circuit, compiler
        )
        if optimized_macro is None:
            optimized_macro = qiskit_transpile(
                macro_circuit,
                basis_gates=list(compiler.target_gateset),
                optimization_level=3,
                layout_method="trivial",
                routing_method="none",
            )

        rebuilt_circuit = circuit.copy_empty_like()
        rebuilt_circuit.global_phase = circuit.global_phase
        full_macros, leftover_repeats = divmod(repeat_count, macro_repeat)
        for _ in range(full_macros):
            rebuilt_circuit.compose(optimized_macro, inplace=True)

        leftover_start = full_macros * macro_size
        leftover_end = leftover_start + leftover_repeats * block_size
        _append_instruction_sequence(
            rebuilt_circuit, circuit.data[leftover_start:leftover_end]
        )
        _append_instruction_sequence(rebuilt_circuit, circuit.data[coverage:])

        if coverage == len(circuit.data) and leftover_repeats == 0:
            candidate_circuits.append(rebuilt_circuit)
        else:
            candidate_circuits.append(
                qiskit_transpile(
                    rebuilt_circuit,
                    basis_gates=list(compiler.target_gateset),
                    optimization_level=0,
                )
            )

    if not candidate_circuits:
        return None

    selected_circuit = _select_lowest_cost_circuit(candidate_circuits)
    if cache_key[0] is not None:
        _REPEATED_REFERENCE_CACHE[cache_key] = selected_circuit
    return selected_circuit


def _repeated_prefix_has_nontrivial_composite_ops(circuit, repeated_prefix):
    """Return True when a repeated prefix block contains composite instructions."""

    block_size, _ = repeated_prefix
    return any(
        _instruction_has_nontrivial_composite_definition(instruction)
        for instruction in circuit.data[:block_size]
    )


def _compile_repeated_composite_prefix_reference(
    circuit, compiler, repeated_prefix
):
    """Compile one repeated composite prefix block and reuse it across the run."""

    cache_key = (
        _cacheable_circuit_key(circuit),
        repeated_prefix,
        _target_basis_cache_key(compiler),
        _backend_cache_marker(compiler),
        "composite_repeat",
    )
    if cache_key[0] is not None and cache_key in _REPEATED_REFERENCE_CACHE:
        return _REPEATED_REFERENCE_CACHE[cache_key]

    block_size, repeat_count = repeated_prefix
    coverage = block_size * repeat_count
    if coverage < _MIN_DOMINANT_REPEAT_FRACTION * len(circuit.data):
        return None
    if not _repeated_prefix_has_nontrivial_composite_ops(circuit, repeated_prefix):
        return None

    block_circuit = _build_circuit_from_instructions(
        circuit, list(circuit.data[:block_size])
    )
    block_circuit = _semantic_local_simplify(block_circuit)

    if compiler.target_backend is not None:
        optimized_block = _compile_backend_preset_portfolio(
            block_circuit,
            compiler,
            optimization_level=1,
        )
    else:
        optimized_block = _compile_semantic_reference_with_local_opt(
            block_circuit, compiler
        )
        if optimized_block is None:
            optimized_block = qiskit_transpile(
                block_circuit,
                basis_gates=list(compiler.target_gateset),
                optimization_level=3,
                layout_method="trivial",
                routing_method="none",
            )

    rebuilt_circuit = circuit.copy_empty_like()
    rebuilt_circuit.global_phase = circuit.global_phase
    for _ in range(repeat_count):
        rebuilt_circuit.compose(optimized_block, inplace=True)
    _append_instruction_sequence(rebuilt_circuit, circuit.data[coverage:])

    if compiler.target_backend is not None:
        selected_circuit = _enforce_target_constraints(rebuilt_circuit, compiler)
    elif coverage == len(circuit.data):
        selected_circuit = rebuilt_circuit
    else:
        selected_circuit = qiskit_transpile(
            rebuilt_circuit,
            basis_gates=list(compiler.target_gateset),
            optimization_level=0,
        )
    if cache_key[0] is not None:
        _REPEATED_REFERENCE_CACHE[cache_key] = selected_circuit
    return selected_circuit


def _supports_semantic_repeated_prefix_fast_path(circuit, repeated_prefix):
    """Return True when a full-coverage repeated composite block is semantically lowerable."""

    if repeated_prefix is None:
        return False

    block_size, repeat_count = repeated_prefix
    coverage = block_size * repeat_count
    if coverage != len(circuit.data):
        return False

    if not _repeated_prefix_has_nontrivial_composite_ops(circuit, repeated_prefix):
        return False

    block_circuit = _build_circuit_from_instructions(
        circuit, list(circuit.data[:block_size])
    )
    block_circuit = _semantic_local_simplify(block_circuit)
    return _build_semantic_term(block_circuit) is not None


def _find_conjugation_span(
    circuit, max_prefix_size=_MAX_STRUCTURAL_BLOCK_SIZE
):
    """Detect a full-span prefix-center-inverse(prefix) structure."""

    instruction_count = len(circuit.data)
    max_candidate_size = min(max_prefix_size, instruction_count // 2)
    if max_candidate_size < 1:
        return None

    signatures = [
        _instruction_signature(circuit, instruction)
        for instruction in circuit.data
    ]

    for prefix_size in range(max_candidate_size, 0, -1):
        center_start = prefix_size
        center_end = instruction_count - prefix_size
        if center_end <= center_start:
            continue

        inverse_prefix = [
            _inverse_instruction_signature(circuit, instruction)
            for instruction in circuit.data[:prefix_size]
        ]
        if any(signature is None for signature in inverse_prefix):
            continue

        if signatures[center_end:] == list(reversed(inverse_prefix)):
            return _ConjugationSpanNode(
                prefix_size=prefix_size,
                center_start=center_start,
                center_end=center_end,
            )

    return None


def _find_mirrored_self_inverse_block(circuit):
    """Detect a diagonal prefix followed by a mirrored self-inverse shell."""

    instruction_count = len(circuit.data)
    if instruction_count < 3:
        return None

    diagonal_prefix_size = 0
    while diagonal_prefix_size < instruction_count and (
        circuit.data[diagonal_prefix_size].operation.name
        in _MIRRORED_SELF_INVERSE_DIAGONAL_PREFIX_GATES
    ):
        diagonal_prefix_size += 1

    shell_size = instruction_count - diagonal_prefix_size
    if diagonal_prefix_size < 1 or shell_size < 3:
        return None

    groups = _contiguous_operation_groups(circuit, diagonal_prefix_size)
    if len(groups) < 3 or len(groups) % 2 == 0:
        return None

    shell_prefix_size = len(groups) // 2
    center_start, center_end = groups[shell_prefix_size]
    if not all(
        _instruction_is_self_inverse(circuit, instruction)
        for instruction in circuit.data[center_start:center_end]
    ):
        return None

    for offset in range(shell_prefix_size):
        left_start, left_end = groups[offset]
        right_start, right_end = groups[-1 - offset]
        if (left_end - left_start) != (right_end - right_start):
            return None

        if not all(
            _instruction_is_self_inverse(circuit, instruction)
            for instruction in circuit.data[left_start:left_end]
        ):
            return None
        if _group_signature(circuit, left_start, left_end) != _group_signature(
            circuit, right_start, right_end
        ):
            return None

    return _MirroredSelfInverseBlockNode(
        diagonal_prefix_size=diagonal_prefix_size,
        shell_prefix_size=shell_prefix_size,
    )


def _compile_mirrored_self_inverse_reference(circuit, compiler):
    """Compile a diagonal-prefix + mirrored self-inverse shell as separate blocks."""

    built_semantic_term = _build_mirrored_self_inverse_term(circuit)
    if built_semantic_term is None:
        return None
    template_circuit, mirrored_term = built_semantic_term
    mirrored_reference = _compile_semantic_term_to_circuit(
        template_circuit, mirrored_term, compiler
    )
    if mirrored_reference is None:
        return None

    if compiler.target_backend is None:
        return mirrored_reference

    return qiskit_transpile(
        mirrored_reference,
        backend=compiler.target_backend,
        optimization_level=1,
        seed_transpiler=getattr(compiler, "seed_transpiler", None),
    )


def _compile_conjugation_reference(circuit, compiler):
    """Compile a U D U^dagger-style block by compiling prefix/center separately."""

    if compiler.target_backend is not None:
        return None

    built_semantic_term = _build_conjugation_term(circuit)
    if built_semantic_term is None:
        return None
    template_circuit, conjugation_term = built_semantic_term
    return _compile_semantic_term_to_circuit(
        template_circuit, conjugation_term, compiler
    )


def _should_compare_against_presimplified_preset(
    original_circuit, presimplified_circuit
):
    """Return True when a full opt3 run on the pre-simplified circuit is warranted."""

    if len(presimplified_circuit.data) > _MAX_PRESIMPLIFIED_FULL_PRESET_SIZE:
        return False

    original_metrics = _circuit_metrics(original_circuit)
    if original_metrics["total_gates"] == 0:
        return False

    reduction_fraction = 1 - (
        len(presimplified_circuit.data) / original_metrics["total_gates"]
    )
    multi_qubit_fraction = (
        original_metrics["multi_qubit_gates"] / original_metrics["total_gates"]
    )
    return (
        reduction_fraction >= 0.25
        and multi_qubit_fraction <= _LOW_MULTI_QUBIT_FRACTION
    )


def _compile_presimplified_full_preset_reference(circuit, compiler):
    """Compile a full opt3 reference on an already pre-simplified circuit."""

    if compiler.target_backend is not None:
        return _compile_backend_preset_portfolio(
            circuit,
            compiler,
            optimization_level=3,
        )

    return qiskit_transpile(
        circuit,
        basis_gates=list(compiler.target_gateset),
        optimization_level=3,
        layout_method="trivial",
        routing_method="none",
    )


def _should_short_circuit_to_source_preset(
    source_circuit, translated_circuit, compiler
):
    """Return True when a source-level opt3 probe should bypass UCC default."""

    source_gate_count = len(source_circuit.data)
    if source_gate_count == 0:
        return False
    if source_gate_count > _MAX_DIRECT_SOURCE_PRESET_SIZE:
        return False
    if _has_reducible_diagonal_phase_span(source_circuit):
        return False

    translated_gate_count = len(translated_circuit.data)
    if (
        translated_gate_count
        >= _DIRECT_SOURCE_DECOMPOSITION_RATIO * source_gate_count
    ):
        return True

    if (
        source_gate_count >= _MIN_DIRECT_SOURCE_PRESET_SIZE
        and translated_gate_count
        >= _MEDIUM_DIRECT_SOURCE_DECOMPOSITION_RATIO * source_gate_count
    ):
        return True

    return (
        source_gate_count >= _MIN_DIRECT_SOURCE_PRESET_SIZE
        and _has_nontrivial_composite_ops(
            source_circuit, compiler.target_gateset
        )
    )


def _should_compare_against_direct_full_preset(
    original_circuit, presimplified_circuit, repeated_prefix
):
    """Return True when direct full opt3 is a cheaper dominant-repeat strategy."""

    if repeated_prefix is None:
        return False
    if len(original_circuit.data) > _MAX_FULL_DIRECT_PRESET_SIZE:
        return False
    if len(presimplified_circuit.data) != len(original_circuit.data):
        return False

    coverage = repeated_prefix[0] * repeated_prefix[1]
    return coverage >= _MIN_DOMINANT_REPEAT_FRACTION * len(original_circuit.data)


def _compile_preset_reference(circuit, compiler):
    """Compile a reference candidate with Qiskit's preset optimizer.

    This is only used as a fallback/reference for the default UCC pipeline, so
    it intentionally does not forward the user callback.
    """

    if compiler.target_backend is not None:
        candidate_circuits = [
            _compile_backend_preset_portfolio(
                circuit,
                compiler,
                optimization_level=3,
            )
        ]
        hierarchical_reference = _compile_hierarchical_reference(
            circuit, compiler
        )
        if hierarchical_reference is not None:
            candidate_circuits.append(hierarchical_reference)
        return _select_backend_candidates(
            candidate_circuits, candidate_circuits[0]
        )

    candidate_circuits = []
    hierarchical_reference = _compile_hierarchical_reference(circuit, compiler)
    if hierarchical_reference is not None:
        candidate_circuits.append(hierarchical_reference)

    repeated_prefix = _find_repeated_prefix(circuit)
    if (
        len(circuit.data) > _MAX_FULL_PRESET_REFERENCE_SIZE
        and repeated_prefix is not None
    ):
        repeated_prefix_reference = _compile_repeated_prefix_reference(
            circuit, compiler, repeated_prefix
        )
        if repeated_prefix_reference is not None:
            candidate_circuits.append(repeated_prefix_reference)

    if len(circuit.data) > _MAX_FULL_PRESET_REFERENCE_SIZE:
        return (
            _select_lowest_cost_circuit(candidate_circuits)
            if candidate_circuits
            else None
        )

    candidate_circuits.append(
        qiskit_transpile(
            circuit,
            basis_gates=list(compiler.target_gateset),
            optimization_level=3,
            layout_method="trivial",
            routing_method="none",
        )
    )
    return _select_lowest_cost_circuit(candidate_circuits)


def _select_lowest_cost_circuit(circuits):
    """Return the circuit with the lowest conservative structural cost."""

    return min(circuits, key=_circuit_cost)


def _circuit_cost_from_metrics(metrics):
    """Return the conservative structural cost from precomputed metrics."""

    return (
        metrics["total_gates"]
        + metrics["depth"]
        + 10 * metrics["multi_qubit_gates"]
    )


def _select_backend_candidates(candidates, anchor_circuit=None):
    """Select backend-aware candidates with anchor-dominance priority."""

    if anchor_circuit is not None:
        dominating_candidates = [
            candidate
            for candidate in candidates
            if _dominates_structural_metrics(candidate, anchor_circuit)
        ]
        if dominating_candidates:
            return _select_lowest_cost_circuit(dominating_candidates)

    return _select_lowest_cost_circuit(candidates)


def _prefer_backend_repeated_run_tradeoff(candidate_circuit, reference_circuit):
    """Return True when a repeated-run candidate wins on routed quality."""

    candidate_metrics = _circuit_metrics(candidate_circuit)
    reference_metrics = _circuit_metrics(reference_circuit)
    return _prefer_backend_repeated_run_tradeoff_metrics(
        candidate_metrics, reference_metrics
    )


def _prefer_backend_repeated_run_tradeoff_metrics(
    candidate_metrics, reference_metrics
):
    """Return True when projected repeated-run metrics win on routed quality."""

    if candidate_metrics["total_gates"] > (
        1.0 + _BACKEND_REPEATED_RUN_TOTAL_GATE_MARGIN
    ) * reference_metrics["total_gates"]:
        return False

    if _backend_improvement_fraction(
        candidate_metrics["depth"], reference_metrics["depth"]
    ) < _BACKEND_REPEATED_RUN_DEPTH_IMPROVEMENT:
        return False

    if _backend_improvement_fraction(
        candidate_metrics["multi_qubit_gates"],
        reference_metrics["multi_qubit_gates"],
    ) < _BACKEND_REPEATED_RUN_MULTI_IMPROVEMENT:
        return False

    return True


def _project_repeated_run_metrics(
    prefix_circuit, block_circuit, suffix_circuit, repeat_count
):
    """Project full repeated-run metrics from prefix/block/suffix components."""
    repeated_term = _build_repeated_run_term(
        prefix_circuit, block_circuit, suffix_circuit, repeat_count
    )
    return _semantic_compiled_term_metrics(repeated_term)


def _select_backend_repeated_run_block_candidate(
    block_candidates, prefix_circuit, suffix_circuit, repeat_count
):
    """Select the best repeated-run block before rebuilding the whole circuit."""

    projected_candidates = [
        (
            block_candidate,
            _project_repeated_run_metrics(
                prefix_circuit,
                block_candidate,
                suffix_circuit,
                repeat_count,
            ),
        )
        for block_candidate in block_candidates
    ]
    reference_candidate, reference_metrics = min(
        projected_candidates,
        key=lambda candidate: _circuit_cost_from_metrics(candidate[1]),
    )
    tradeoff_candidates = [
        (candidate, metrics)
        for candidate, metrics in projected_candidates
        if candidate is not reference_candidate
        and _prefer_backend_repeated_run_tradeoff_metrics(
            metrics, reference_metrics
        )
    ]
    if tradeoff_candidates:
        selected_candidate, _ = min(
            tradeoff_candidates,
            key=lambda candidate: _circuit_cost_from_metrics(candidate[1]),
        )
        return selected_candidate

    return reference_candidate


def _select_backend_repeated_run_candidates(candidates):
    """Select repeated-run candidates, allowing routed-quality tradeoffs."""

    reference_candidate = _select_lowest_cost_circuit(candidates)
    tradeoff_candidates = [
        candidate
        for candidate in candidates
        if candidate is not reference_candidate
        and _prefer_backend_repeated_run_tradeoff(candidate, reference_candidate)
    ]
    if tradeoff_candidates:
        return _select_lowest_cost_circuit(tradeoff_candidates)

    return reference_candidate


def _dominates_structural_metrics(candidate_circuit, reference_circuit):
    """Return True when a candidate is no worse on core structural metrics."""

    candidate_metrics = _circuit_metrics(candidate_circuit)
    reference_metrics = _circuit_metrics(reference_circuit)
    if not (
        candidate_metrics["total_gates"] <= reference_metrics["total_gates"]
        and candidate_metrics["depth"] <= reference_metrics["depth"]
        and candidate_metrics["multi_qubit_gates"]
        <= reference_metrics["multi_qubit_gates"]
    ):
        return False

    return candidate_metrics != reference_metrics


def _backend_improvement_fraction(base_value, baseline_value):
    """Return the fractional reduction from a backend baseline to a candidate."""

    if baseline_value <= 0:
        return 0.0
    return max(0.0, (baseline_value - base_value) / baseline_value)


def _should_skip_backend_reference_probe(base_candidate, baseline_circuit):
    """Return True when the base backend candidate is already good enough.

    On some routed workloads, the default backend-aware UCC candidate already
    beats a cheap backend translation by a modest but consistent margin. In
    these cases, paying for an extra direct backend ``qiskit opt3`` probe tends
    not to change the final answer and only adds latency.
    """

    if baseline_circuit is None:
        return False
    if not _dominates_structural_metrics(base_candidate, baseline_circuit):
        return False

    base_metrics = _circuit_metrics(base_candidate)
    baseline_metrics = _circuit_metrics(baseline_circuit)
    return (
        _backend_improvement_fraction(
            base_metrics['total_gates'], baseline_metrics['total_gates']
        ) <= 0.05
        and _backend_improvement_fraction(
            base_metrics['depth'], baseline_metrics['depth']
        ) <= 0.15
        and _backend_improvement_fraction(
            base_metrics['multi_qubit_gates'],
            baseline_metrics['multi_qubit_gates'],
        ) <= 0.25
    )


def _backend_portfolio_seeds(compiler, circuit):
    """Return a small deterministic seed portfolio for backend-aware opt3."""

    base_seed = getattr(compiler, "seed_transpiler", None)
    if base_seed is None:
        return [None]
    if len(circuit.data) > _MAX_BACKEND_SEED_PORTFOLIO_SIZE:
        return [base_seed]
    return [base_seed + offset for offset in _BACKEND_SEED_PORTFOLIO_OFFSETS]


def _backend_reference_seeds(compiler, circuit):
    """Return backend preset seeds including a small global exploratory set."""

    base_seed = getattr(compiler, "seed_transpiler", None)
    if base_seed is None:
        return [None]

    seeds = [base_seed]
    if len(circuit.data) > _MAX_BACKEND_SEED_PORTFOLIO_SIZE:
        return seeds

    for exploratory_seed in _BACKEND_REFERENCE_GLOBAL_SEEDS:
        if exploratory_seed not in seeds:
            seeds.append(exploratory_seed)
    return seeds


def _cached_backend_preset_transpile(
    circuit, compiler, optimization_level, seed, max_size=_MAX_REFERENCE_CACHE_SIZE
):
    """Run backend preset transpilation with a small in-process cache."""

    circuit_key = _cacheable_circuit_key(circuit, max_size=max_size)
    cache_key = None
    if circuit_key is not None:
        cache_key = (
            circuit_key,
            _backend_cache_marker(compiler),
            optimization_level,
            seed,
        )
        cached_candidate = _BACKEND_PRESET_CACHE.get(cache_key)
        if cached_candidate is not None:
            return cached_candidate

    candidate = qiskit_transpile(
        circuit,
        backend=compiler.target_backend,
        optimization_level=optimization_level,
        seed_transpiler=seed,
    )
    if cache_key is not None:
        _BACKEND_PRESET_CACHE[cache_key] = candidate
    return candidate


def _cached_backend_default_candidate(
    circuit, compiler, callback=None, max_size=_MAX_REFERENCE_CACHE_SIZE
):
    """Run the backend default compiler with a small cache when safe."""

    if callback is not None:
        candidate = compiler.run(circuit, callback=callback)
        return _enforce_target_constraints(candidate, compiler)

    circuit_key = _cacheable_circuit_key(circuit, max_size=max_size)
    cache_key = None
    if circuit_key is not None:
        cache_key = (
            circuit_key,
            _backend_cache_marker(compiler),
            _target_basis_cache_key(compiler),
            getattr(compiler, "seed_transpiler", None),
        )
        cached_candidate = _BACKEND_DEFAULT_RUN_CACHE.get(cache_key)
        if cached_candidate is not None:
            return cached_candidate

    candidate = compiler.run(circuit, callback=callback)
    candidate = _enforce_target_constraints(candidate, compiler)
    if cache_key is not None:
        _BACKEND_DEFAULT_RUN_CACHE[cache_key] = candidate
    return candidate


def _should_expand_backend_reference_search(base_candidate, anchor_candidate):
    """Return True when extra backend reference seeds are worth exploring."""

    base_metrics = _circuit_metrics(base_candidate)
    anchor_metrics = _circuit_metrics(anchor_candidate)
    metric_pairs = (
        ("total_gates", 0.05),
        ("depth", 0.10),
        ("multi_qubit_gates", 0.12),
    )

    for metric_name, margin in metric_pairs:
        base_value = base_metrics[metric_name]
        anchor_value = anchor_metrics[metric_name]
        scale = max(base_value, anchor_value, 1)
        if abs(base_value - anchor_value) / scale > margin:
            return False

    return True


def _compile_backend_preset_portfolio(circuit, compiler, optimization_level):
    """Compile a small backend-aware preset portfolio and keep the best result."""

    candidates = []
    anchor_candidate = None
    for seed in _backend_reference_seeds(compiler, circuit):
        candidate = _cached_backend_preset_transpile(
            circuit,
            compiler,
            optimization_level=optimization_level,
            seed=seed,
        )
        if anchor_candidate is None:
            anchor_candidate = candidate
        candidates.append(candidate)
    return _select_backend_candidates(candidates, anchor_candidate)


def _instruction_has_nontrivial_composite_definition(instruction):
    """Return True when an instruction expands to a nontrivial composite block."""

    definition = getattr(instruction.operation, "definition", None)
    return definition is not None and len(definition.data) > 1


def _node_has_nontrivial_composite_ops(circuit, node):
    """Return True when a node contains at least one composite instruction."""

    if isinstance(node, _InstructionSpanNode):
        instructions = circuit.data[node.start_index : node.end_index]
    else:
        instructions = circuit.data[
            node.start_index : node.start_index + node.block_size
        ]

    return any(
        _instruction_has_nontrivial_composite_definition(instruction)
        for instruction in instructions
    )


def _node_reference_circuit(circuit, node, compiler):
    """Compile a hierarchical node with a local general simplification step."""

    if isinstance(node, _InstructionSpanNode):
        instructions = list(circuit.data[node.start_index : node.end_index])
    else:
        instructions = list(
            circuit.data[node.start_index : node.start_index + node.block_size]
        )

    block_circuit = _build_circuit_from_instructions(circuit, instructions)
    block_circuit = _semantic_local_simplify(block_circuit)

    cache_key = (
        _cacheable_circuit_key(block_circuit),
        _target_basis_cache_key(compiler),
        _backend_cache_marker(compiler),
        "node_reference",
    )
    if cache_key[0] is not None and cache_key in _NODE_REFERENCE_CACHE:
        return _NODE_REFERENCE_CACHE[cache_key]

    if compiler.target_backend is not None:
        node_reference = _compile_mirrored_self_inverse_reference(
            block_circuit, compiler
        )
        if node_reference is None:
            node_reference = _compile_semantic_reference_with_local_opt(
                block_circuit, compiler
            )
        if node_reference is None:
            node_reference = _compile_backend_preset_portfolio(
                block_circuit,
                compiler,
                optimization_level=1,
            )
    else:
        node_reference = _compile_conjugation_reference(
            block_circuit, compiler
        )
        if node_reference is None:
            node_reference = _compile_mirrored_self_inverse_reference(
                block_circuit, compiler
            )
        if node_reference is None:
            node_reference = _compile_semantic_reference_with_local_opt(
                block_circuit, compiler
            )
        if node_reference is None:
            node_reference = qiskit_transpile(
                block_circuit,
                basis_gates=list(compiler.target_gateset),
                optimization_level=3,
                layout_method="trivial",
                routing_method="none",
            )

    if cache_key[0] is not None:
        _NODE_REFERENCE_CACHE[cache_key] = node_reference
    return node_reference


def _compile_hierarchical_reference(circuit, compiler):
    """Compile a circuit through a tiny hierarchical macro-block view."""

    cache_key = (
        _cacheable_circuit_key(circuit),
        _target_basis_cache_key(compiler),
        _backend_cache_marker(compiler),
        "hierarchical_reference",
    )
    if cache_key[0] is not None and cache_key in _REPEATED_REFERENCE_CACHE:
        return _REPEATED_REFERENCE_CACHE[cache_key]

    nodes = _build_hierarchical_nodes(circuit)
    if (
        len(nodes) == 1
        and isinstance(nodes[0], _InstructionSpanNode)
        and nodes[0].start_index == 0
        and nodes[0].end_index == len(circuit.data)
    ):
        return None

    rebuilt_circuit = circuit.copy_empty_like()
    rebuilt_circuit.global_phase = circuit.global_phase
    used_hierarchical_node = False

    for node in nodes:
        if isinstance(node, _InstructionSpanNode):
            span_size = node.end_index - node.start_index
            if (
                span_size <= _MAX_HIERARCHICAL_LOCAL_BLOCK_SIZE
                and _node_has_nontrivial_composite_ops(circuit, node)
            ):
                optimized_span = _node_reference_circuit(circuit, node, compiler)
                rebuilt_circuit.compose(optimized_span, inplace=True)
                used_hierarchical_node = True
                continue

            _append_instruction_sequence(
                rebuilt_circuit, circuit.data[node.start_index : node.end_index]
            )
            continue

        optimized_block = _node_reference_circuit(circuit, node, compiler)
        for _ in range(node.repeat_count):
            rebuilt_circuit.compose(optimized_block, inplace=True)
        used_hierarchical_node = True

    if not used_hierarchical_node:
        return None

    if cache_key[0] is not None:
        _REPEATED_REFERENCE_CACHE[cache_key] = rebuilt_circuit
    return rebuilt_circuit


def _should_use_backend_repeated_run_shortcut(circuit):
    """Return True when a backend repeated-run fallback is worth trying."""

    if len(circuit.data) < _MIN_BACKEND_REPEATED_RUN_SIZE:
        return False

    repeated_run = _find_repeated_run(
        circuit,
        max_block_size=_MAX_BACKEND_REPEATED_RUN_BLOCK_SIZE,
        min_repeats=_MIN_BACKEND_REPEATED_RUN_REPEATS,
    )
    if repeated_run is None:
        return False

    start_index, block_size, repeat_count = repeated_run
    coverage = block_size * repeat_count
    if coverage < _MIN_BACKEND_REPEATED_RUN_FRACTION * len(circuit.data):
        return False

    block_instructions = list(circuit.data[start_index : start_index + block_size])
    return any(
        _instruction_has_nontrivial_composite_definition(instruction)
        for instruction in block_instructions
    )


def _compile_backend_repeated_run_reference(circuit, compiler):
    """Compile a dominant repeated run by routing one block and reusing it."""

    repeated_run = _find_repeated_run(
        circuit,
        max_block_size=_MAX_BACKEND_REPEATED_RUN_BLOCK_SIZE,
        min_repeats=_MIN_BACKEND_REPEATED_RUN_REPEATS,
    )
    if repeated_run is None:
        return None

    start_index, block_size, repeat_count = repeated_run
    run_end = start_index + block_size * repeat_count
    prefix_circuit = _build_circuit_from_instructions(
        circuit, list(circuit.data[:start_index])
    )
    repeated_block = list(circuit.data[start_index : start_index + block_size])
    block_circuit = _build_circuit_from_instructions(circuit, repeated_block)
    suffix_circuit = _build_circuit_from_instructions(
        circuit, list(circuit.data[run_end:])
    )

    prefix_compiled = _cached_backend_preset_transpile(
        prefix_circuit,
        optimization_level=0,
        compiler=compiler,
        seed=getattr(compiler, "seed_transpiler", None),
    )
    suffix_compiled = _cached_backend_preset_transpile(
        suffix_circuit,
        optimization_level=0,
        compiler=compiler,
        seed=getattr(compiler, "seed_transpiler", None),
    )

    def _rebuild_repeated_run(block_compiled):
        rebuilt_circuit = circuit.copy_empty_like()
        rebuilt_circuit.global_phase = circuit.global_phase
        rebuilt_circuit.compose(prefix_compiled, inplace=True)
        for _ in range(repeat_count):
            rebuilt_circuit.compose(block_compiled, inplace=True)
        rebuilt_circuit.compose(suffix_compiled, inplace=True)
        return rebuilt_circuit

    base_seed = getattr(compiler, "seed_transpiler", None)
    selection_cache_key = None
    if (
        _cacheable_circuit_key(prefix_circuit) is not None
        and _cacheable_circuit_key(block_circuit) is not None
        and _cacheable_circuit_key(suffix_circuit) is not None
    ):
        selection_cache_key = (
            _cacheable_circuit_key(prefix_circuit),
            _cacheable_circuit_key(block_circuit),
            _cacheable_circuit_key(suffix_circuit),
            repeat_count,
            _backend_cache_marker(compiler),
            base_seed,
            "backend_repeated_run_block",
        )

    if (
        selection_cache_key is not None
        and selection_cache_key in _REPEATED_RUN_BLOCK_REFERENCE_CACHE
    ):
        selected_block = _REPEATED_RUN_BLOCK_REFERENCE_CACHE[
            selection_cache_key
        ]
    else:
        repeated_run_block_candidates = []
        for optimization_level in (1, 3):
            block_compiled = _cached_backend_preset_transpile(
                block_circuit,
                compiler,
                optimization_level=optimization_level,
                seed=base_seed,
            )
            repeated_run_block_candidates.append(block_compiled)

        semantic_reference = _compile_semantic_reference_with_local_opt(
            block_circuit, compiler
        )
        if semantic_reference is not None:
            repeated_run_block_candidates.append(semantic_reference)

        mirrored_self_inverse_reference = _compile_mirrored_self_inverse_reference(
            block_circuit, compiler
        )
        if mirrored_self_inverse_reference is not None:
            repeated_run_block_candidates.append(
                mirrored_self_inverse_reference
            )

        selected_block = _select_backend_repeated_run_block_candidate(
            repeated_run_block_candidates,
            prefix_compiled,
            suffix_compiled,
            repeat_count,
        )
        if selection_cache_key is not None:
            _REPEATED_RUN_BLOCK_REFERENCE_CACHE[selection_cache_key] = (
                selected_block
            )
    return _rebuild_repeated_run(selected_block)


def _compile_backend_default_portfolio(
    circuit,
    compiler,
    source_circuit=None,
    baseline_circuit=None,
    callback=None,
):
    """Run the backend-aware default pipeline over a small seed portfolio."""

    if (
        getattr(compiler, "seed_transpiler", None) is None
        or len(circuit.data) > _MAX_BACKEND_DEFAULT_PORTFOLIO_SIZE
        or callback is not None
    ):
        compiled_circuit = compiler.run(circuit, callback=callback)
        return _enforce_target_constraints(compiled_circuit, compiler)

    base_candidate = _cached_backend_default_candidate(
        circuit, compiler, callback=callback
    )

    if source_circuit is None:
        return base_candidate

    if _should_skip_backend_reference_probe(base_candidate, baseline_circuit):
        return base_candidate

    semantic_backend_reference = None
    if source_circuit is not None:
        semantic_backend_reference = _compile_semantic_reference_with_local_opt(
            source_circuit, compiler
        )
        if semantic_backend_reference is not None:
            if _dominates_structural_metrics(base_candidate, semantic_backend_reference):
                semantic_backend_reference = None
            elif _dominates_structural_metrics(semantic_backend_reference, base_candidate):
                return semantic_backend_reference

    anchor_backend_reference = _cached_backend_preset_transpile(
        source_circuit,
        compiler,
        optimization_level=3,
        seed=getattr(compiler, "seed_transpiler", None),
    )

    if _dominates_structural_metrics(base_candidate, anchor_backend_reference):
        return base_candidate
    if _dominates_structural_metrics(anchor_backend_reference, base_candidate):
        return anchor_backend_reference

    reference_candidates = [anchor_backend_reference]
    if semantic_backend_reference is not None:
        reference_candidates.append(semantic_backend_reference)
    for seed in _backend_reference_seeds(compiler, source_circuit)[1:]:
        reference_candidates.append(
            _cached_backend_preset_transpile(
                source_circuit,
                compiler,
                optimization_level=3,
                seed=seed,
            )
        )
    direct_backend_reference = _select_backend_candidates(
        reference_candidates, anchor_backend_reference
    )

    if _dominates_structural_metrics(base_candidate, direct_backend_reference):
        return base_candidate
    if _dominates_structural_metrics(direct_backend_reference, base_candidate):
        return direct_backend_reference

    candidates = [direct_backend_reference, base_candidate]
    portfolio_seeds = _backend_portfolio_seeds(compiler, circuit)
    for seed in portfolio_seeds[1:]:
        portfolio_compiler = UCCDefault1(
            target_backend=compiler.target_backend,
            target_gateset=compiler.target_gateset,
            seed_transpiler=seed,
        )
        candidates.append(
            _cached_backend_default_candidate(circuit, portfolio_compiler)
        )

    return _select_backend_candidates(candidates, anchor_backend_reference)


def _enforce_target_constraints(circuit, compiler):
    """Re-translate a circuit into the requested backend or basis.

    Custom passes run after the default pipeline and may introduce operations
    outside the requested target. Run a final, non-optimizing translation so
    the public ``compile()`` contract still holds for the returned circuit.
    """

    if compiler.target_backend is not None:
        return qiskit_transpile(
            circuit,
            backend=compiler.target_backend,
            optimization_level=0,
            seed_transpiler=getattr(compiler, "seed_transpiler", None),
        )

    return qiskit_transpile(
        circuit,
        basis_gates=list(compiler.target_gateset),
        optimization_level=0,
    )


def _should_use_repeated_structure_dispatch(
    source_circuit,
    presimplified_circuit,
    compiler,
    has_custom_passes,
    dominant_repeat,
):
    """Return True when a dominant repeated structure should bypass UCCDefault1.

    This dispatch is intended for all-to-all repeated families where a small
    hierarchical/preset candidate set is cheaper than running the full default
    UCC pipeline and then comparing against additional references.
    """

    if compiler.target_backend is not None or has_custom_passes:
        return False
    if dominant_repeat is None:
        return False
    if len(source_circuit.data) < _MIN_REPEAT_DISPATCH_SIZE:
        return False

    if _should_compare_against_presimplified_preset(
        source_circuit, presimplified_circuit
    ):
        return True

    if _circuit_is_in_target_basis(source_circuit, compiler.target_gateset):
        return True

    return (
        _hierarchical_node_coverage(dominant_repeat)
        >= _MIN_DOMINANT_REPEAT_FRACTION * len(source_circuit.data)
    )


def _build_compile_dispatch_plan(
    source_circuit,
    presimplified_circuit,
    compiler,
    has_custom_passes,
):
    """Build a dispatch plan for the top-level compile controller."""

    if (
        compiler.target_backend is not None
        and not has_custom_passes
        and _should_use_backend_repeated_run_shortcut(source_circuit)
    ):
        return _CompileDispatchPlan(
            mode="backend_repeated_run_shortcut",
            compiler=compiler,
            source_circuit=source_circuit,
            presimplified_circuit=presimplified_circuit,
        )

    if (
        compiler.target_backend is None
        and not has_custom_passes
        and _should_compare_against_presimplified_preset(
            source_circuit, presimplified_circuit
        )
    ):
        basis_translated_circuit = qiskit_transpile(
            presimplified_circuit,
            basis_gates=compiler.target_gateset,
            optimization_level=0,
        )
        return _CompileDispatchPlan(
            mode="presimplified_full_preset",
            compiler=compiler,
            source_circuit=source_circuit,
            presimplified_circuit=presimplified_circuit,
            basis_translated_circuit=basis_translated_circuit,
            baseline_circuit=basis_translated_circuit,
        )

    basis_translated_circuit = qiskit_transpile(
        presimplified_circuit,
        basis_gates=compiler.target_gateset,
        optimization_level=0,
    )

    if compiler.target_backend is None:
        baseline_circuit = basis_translated_circuit
    else:
        baseline_circuit = _enforce_target_constraints(
            presimplified_circuit, compiler
        )

    repeated_prefix = None
    dominant_repeat = None
    if compiler.target_backend is None and not has_custom_passes:
        repeated_prefix = _find_repeated_prefix(source_circuit)
        if repeated_prefix is not None:
            prefix_block_size, prefix_repeat_count = repeated_prefix
            prefix_coverage = prefix_block_size * prefix_repeat_count
            if (
                prefix_coverage
                >= _MIN_DOMINANT_REPEAT_FRACTION * len(source_circuit.data)
            ):
                dominant_repeat = _RepeatedSpanNode(
                    0, prefix_block_size, prefix_repeat_count
                )
        if dominant_repeat is None:
            dominant_repeat = _dominant_hierarchical_repeat(source_circuit)

    if _should_use_repeated_structure_dispatch(
        source_circuit,
        presimplified_circuit,
        compiler,
        has_custom_passes,
        dominant_repeat,
    ):
        return _CompileDispatchPlan(
            mode="repeated_structure_dispatch",
            compiler=compiler,
            source_circuit=source_circuit,
            presimplified_circuit=presimplified_circuit,
            basis_translated_circuit=basis_translated_circuit,
            baseline_circuit=baseline_circuit,
            repeated_prefix=repeated_prefix,
        )

    if compiler.target_backend is not None and not has_custom_passes:
        return _CompileDispatchPlan(
            mode="backend_default",
            compiler=compiler,
            source_circuit=source_circuit,
            presimplified_circuit=presimplified_circuit,
            basis_translated_circuit=basis_translated_circuit,
            baseline_circuit=baseline_circuit,
        )

    return _CompileDispatchPlan(
        mode="default",
        compiler=compiler,
        source_circuit=source_circuit,
        presimplified_circuit=presimplified_circuit,
        basis_translated_circuit=basis_translated_circuit,
        baseline_circuit=baseline_circuit,
        repeated_prefix=repeated_prefix,
    )


def _compile_repeated_structure_dispatch(plan):
    """Compile a dominant repeated structure without running full UCCDefault1."""

    candidate_circuits = [plan.baseline_circuit]
    source_circuit = plan.source_circuit
    presimplified_circuit = plan.presimplified_circuit
    compiler = plan.compiler
    repeated_prefix = plan.repeated_prefix
    blockwise_only = False

    if (
        _circuit_is_in_target_basis(source_circuit, compiler.target_gateset)
        and not _has_nontrivial_composite_ops(
            source_circuit, compiler.target_gateset
        )
    ):
        return plan.baseline_circuit

    semantic_repeated_prefix_fast_path = (
        compiler.target_backend is None
        and _supports_semantic_repeated_prefix_fast_path(
            source_circuit, repeated_prefix
        )
    )

    repeated_prefix_reference = None
    repeated_composite_reference = None
    if repeated_prefix is not None and not semantic_repeated_prefix_fast_path:
        repeated_composite_reference = (
            _compile_repeated_composite_prefix_reference(
                source_circuit, compiler, repeated_prefix
            )
        )
        if repeated_composite_reference is not None:
            candidate_circuits.append(repeated_composite_reference)

    if repeated_prefix is not None and (
        semantic_repeated_prefix_fast_path
        or blockwise_only
        or len(source_circuit.data) > _MAX_FULL_PRESET_REFERENCE_SIZE
    ):
        repeated_prefix_reference = _compile_repeated_prefix_reference(
            source_circuit, compiler, repeated_prefix
        )
        if repeated_prefix_reference is not None:
            candidate_circuits.append(repeated_prefix_reference)

    if semantic_repeated_prefix_fast_path and repeated_prefix_reference is not None:
        return _select_lowest_cost_circuit(candidate_circuits)

    presimplified_repeated_prefix = None
    if _should_compare_against_presimplified_repeated_dispatch(
        source_circuit, presimplified_circuit
    ):
        presimplified_repeated_prefix = _dominant_repeated_prefix(
            presimplified_circuit
        )

    if presimplified_repeated_prefix is not None:
        presimplified_composite_reference = (
            _compile_repeated_composite_prefix_reference(
                presimplified_circuit,
                compiler,
                presimplified_repeated_prefix,
            )
        )
        if presimplified_composite_reference is not None:
            candidate_circuits.append(presimplified_composite_reference)

        presimplified_prefix_reference = _compile_repeated_prefix_reference(
            presimplified_circuit,
            compiler,
            presimplified_repeated_prefix,
        )
        if presimplified_prefix_reference is not None:
            candidate_circuits.append(presimplified_prefix_reference)

        candidate_circuits.append(
            _compile_presimplified_full_preset_reference(
                presimplified_circuit, compiler
            )
        )

    if (
        not blockwise_only
        and len(source_circuit.data) <= _MAX_REPEAT_DISPATCH_HIERARCHICAL_SIZE
    ):
        hierarchical_reference = _compile_hierarchical_reference(
            source_circuit, compiler
        )
        if hierarchical_reference is not None:
            candidate_circuits.append(hierarchical_reference)

    if (
        not blockwise_only
        and _should_compare_against_presimplified_preset(
            source_circuit, plan.presimplified_circuit
        )
    ):
        candidate_circuits.append(
            _compile_presimplified_full_preset_reference(
                plan.presimplified_circuit, compiler
            )
        )
    else:
        if repeated_prefix_reference is None:
            preset_reference = _compile_preset_reference(
                source_circuit, compiler
            )
            if preset_reference is not None:
                candidate_circuits.append(preset_reference)

    return _select_lowest_cost_circuit(candidate_circuits)


def _execute_compile_dispatch_plan(
    plan,
    custom_passes=None,
    callback=None,
):
    """Execute a previously planned compile controller path."""

    compiler = plan.compiler

    if plan.mode == "backend_repeated_run_shortcut":
        repeated_run_reference = _compile_backend_repeated_run_reference(
            plan.source_circuit, compiler
        )
        if repeated_run_reference is not None:
            return repeated_run_reference
        return _compile_backend_default_portfolio(
            plan.basis_translated_circuit,
            compiler,
            source_circuit=plan.presimplified_circuit,
            baseline_circuit=plan.baseline_circuit,
            callback=callback,
        )

    if plan.mode == "repeated_structure_dispatch":
        return _compile_repeated_structure_dispatch(plan)

    if plan.mode == "presimplified_full_preset":
        return _compile_presimplified_full_preset_reference(
            plan.presimplified_circuit, compiler
        )

    if plan.mode == "backend_default":
        return _compile_backend_default_portfolio(
            plan.basis_translated_circuit,
            compiler,
            source_circuit=plan.presimplified_circuit,
            baseline_circuit=plan.baseline_circuit,
            callback=callback,
        )

    compiled_circuit = compiler.run(
        plan.basis_translated_circuit, callback=callback
    )
    compiled_circuit = _enforce_target_constraints(compiled_circuit, compiler)

    if custom_passes:
        custom_pass_manager = PassManager()
        custom_pass_manager.append(custom_passes)
        compiled_circuit = custom_pass_manager.run(
            compiled_circuit, callback=callback
        )
        return _enforce_target_constraints(compiled_circuit, compiler)

    candidate_circuits = [plan.baseline_circuit, compiled_circuit]
    if _should_compare_against_preset(
        plan.source_circuit, plan.baseline_circuit, compiled_circuit
    ):
        preset_reference = _compile_preset_reference(
            plan.source_circuit, compiler
        )
        if preset_reference is not None:
            candidate_circuits.append(preset_reference)
    if _should_compare_against_presimplified_preset(
        plan.source_circuit, plan.presimplified_circuit
    ):
        candidate_circuits.append(
            _compile_presimplified_full_preset_reference(
                plan.presimplified_circuit, compiler
            )
        )
    return _select_lowest_cost_circuit(candidate_circuits)


def compile(
    circuit,
    return_format="original",
    target_gateset=None,
    target_backend=None,
    custom_passes=None,
    callback=None,
    seed_transpiler=None,
):
    """Compiles the provided quantum `circuit` by translating it to a Qiskit
    circuit, transpiling it, and returning the optimized circuit in the
    specified `return_format`.

    Args:
        circuit (object): The quantum circuit to be compiled.
        return_format (str): The format in which your circuit will be returned.
            e.g., "TKET", "OpenQASM2". Check ``ucc.supported_circuit_formats``.
            Defaults to the format of the input circuit.
        target_gateset (set[str]): (optional) The gateset to compile the circuit to.
            e.g. {"cx", "rx",...}. Defaults to the gate set of the target device if available. If no `target_gateset` or ` target_backend` is provided, defaults to {"cx", "rz", "rx", "ry", "h"}.
        target_backend (qiskit.providers.backend): (optional)
            The target device  to compile the circuit for. Can be specified as a Qiskit backend. If None, all-to-all connectivity is assumed. If a `target_backend` is specified, `target_backend.operation_names` supercedes the `target_gateset`.
        custom_passes (list[qiskit.transpiler.TransformationPass]): (optional)
            A list of custom passes to apply after the default set
            of passes. Defaults to None.
        callback: A callback function that will be called after each pass execution. The
                function will be called with 5 keyword arguments::

                    pass_ (Pass): the pass being run
                    dag (DAGCircuit): the dag output of the pass
                    time (float): the time to execute the pass
                    property_set (PropertySet): the property set
                    count (int): the index for the pass execution
        seed_transpiler (int): (optional)
            Fixed seed forwarded to Qiskit's transpiler/preset manager. Useful
            for reproducible backend-aware experiments on the research branch.

    Returns:
        object: The compiled circuit in the specified format.
    """
    if return_format == "original":
        return_format = get_program_type_alias(circuit)

    has_custom_passes = bool(custom_passes)

    # Translate to Qiskit Circuit object
    source_qiskit_circuit = _translate_to_qiskit(circuit)
    effective_target_gateset = _effective_target_gateset(target_gateset)

    if _should_direct_short_circuit_qiskit_source_preset(
        source_qiskit_circuit,
        effective_target_gateset,
        target_backend,
        has_custom_passes,
    ):
        direct_source_preset = qiskit_transpile(
            source_qiskit_circuit,
            basis_gates=list(effective_target_gateset),
            optimization_level=3,
            layout_method="trivial",
            routing_method="none",
        )
        return _translate_from_qiskit(direct_source_preset, return_format)

    if _should_direct_short_circuit_small_basis_source_preset(
        source_qiskit_circuit,
        effective_target_gateset,
        target_backend,
        has_custom_passes,
    ) and callback is None:
        direct_source_preset = qiskit_transpile(
            source_qiskit_circuit,
            basis_gates=list(effective_target_gateset),
            optimization_level=3,
            layout_method="trivial",
            routing_method="none",
        )
        return _translate_from_qiskit(direct_source_preset, return_format)

    if _should_direct_short_circuit_repeated_basis_source(
        source_qiskit_circuit,
        effective_target_gateset,
        target_backend,
        has_custom_passes,
    ):
        return _translate_from_qiskit(source_qiskit_circuit, return_format)

    # Initialize the UCCDefault1 compiler with the target device and gateset
    ucc_default1 = UCCDefault1(
        target_backend=target_backend,
        target_gateset=target_gateset,
        seed_transpiler=seed_transpiler,
    )
    if (
        target_backend is None
        and not has_custom_passes
        and len(source_qiskit_circuit.data) <= _MAX_DIRECT_SOURCE_PRESET_SIZE
    ):
        source_basis_translated_circuit = qiskit_transpile(
            source_qiskit_circuit,
            basis_gates=ucc_default1.target_gateset,
            optimization_level=0,
        )
        if _should_short_circuit_to_source_preset(
            source_qiskit_circuit,
            source_basis_translated_circuit,
            ucc_default1,
        ):
            direct_source_preset = _compile_presimplified_full_preset_reference(
                source_qiskit_circuit, ucc_default1
            )
            if _circuit_cost(direct_source_preset) <= _circuit_cost(
                source_basis_translated_circuit
            ):
                return _translate_from_qiskit(
                    direct_source_preset, return_format
                )

    qiskit_circuit = _blockwise_structural_pre_simplify_repeated_prefix(
        source_qiskit_circuit
    )
    if qiskit_circuit is None:
        qiskit_circuit = _structural_pre_simplify(source_qiskit_circuit)
    dispatch_plan = _build_compile_dispatch_plan(
        source_qiskit_circuit,
        qiskit_circuit,
        ucc_default1,
        has_custom_passes,
    )
    compiled_circuit = _execute_compile_dispatch_plan(
        dispatch_plan,
        custom_passes=custom_passes,
        callback=callback,
    )

    # Translate the compiled circuit to the desired format
    final_result = _translate_from_qiskit(compiled_circuit, return_format)
    return final_result

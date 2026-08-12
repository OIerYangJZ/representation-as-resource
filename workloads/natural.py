"""Executable natural workloads and instrumented W8 reference pipelines."""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import resource
import subprocess
import time
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml


ROOT = Path(__file__).resolve().parents[1]
WIDTH = 6
COMMON_BASIS = ["cx", "rz", "sx", "x"]
EXTERNAL_BRIDGE_BASIS = ["cx", "rz", "h"]
FACTORS = (
    "semantic_lift",
    "aggregation",
    "selector",
    "cache_reuse",
    "preset_recognizer",
    "projected_block_selection",
)
NEGATIVE_FAMILIES = {
    "negative_random_clifford_rz",
    "negative_routing_dominated",
}


def canonical_json(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a mapping")
    return value


def git_revision() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    return result.stdout.strip() or "unavailable"


def process_maxrss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if os.uname().sysname == "Darwin" else value * 1024


@dataclass(frozen=True)
class PauliTerm:
    support: tuple[int, ...]
    angle_over_pi: Fraction

    def record(self) -> dict[str, Any]:
        return {
            "support": list(self.support),
            "angle_over_pi": [self.angle_over_pi.numerator, self.angle_over_pi.denominator],
        }


@dataclass(frozen=True)
class BoundaryGate:
    name: str
    qubits: tuple[int, ...]
    angle_over_pi: Fraction | None = None

    def record(self) -> dict[str, Any]:
        output: dict[str, Any] = {"name": self.name, "qubits": list(self.qubits)}
        if self.angle_over_pi is not None:
            output["angle_over_pi"] = [
                self.angle_over_pi.numerator,
                self.angle_over_pi.denominator,
            ]
        return output


@dataclass(frozen=True)
class Block:
    terms: tuple[PauliTerm, ...]
    boundary: tuple[BoundaryGate, ...] = ()
    label: str = ""

    def record(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "terms": [term.record() for term in self.terms],
            "boundary": [gate.record() for gate in self.boundary],
        }


@dataclass(frozen=True)
class NaturalInstance:
    family: str
    scale: int
    seed: int
    density: float
    topology: str
    blocks: tuple[Block, ...]

    @property
    def workload_class(self) -> str:
        return "negative_control" if self.family in NEGATIVE_FAMILIES else "natural_positive"

    def semantic_record(self) -> dict[str, Any]:
        return {
            "schema": "ucc.natural-instance.v1",
            "family": self.family,
            "scale": self.scale,
            "seed": self.seed,
            "density": self.density,
            "topology": self.topology,
            "width": WIDTH,
            "blocks": [block.record() for block in self.blocks],
        }

    @property
    def instance_id(self) -> str:
        return "nat-" + sha256_bytes(canonical_json(self.semantic_record()))[:20]

    @property
    def representation_id(self) -> str:
        record = {**self.semantic_record(), "topology": "logical_pre_routing"}
        return "repr-" + sha256_bytes(canonical_json(record))[:20]


def _select_edges(edges: list[tuple[int, ...]], density: float, rng: random.Random) -> list[tuple[int, ...]]:
    count = max(1, int(math.ceil(len(edges) * density)))
    shuffled = list(edges)
    rng.shuffle(shuffled)
    return sorted(shuffled[:count])


def generate_instance(
    family: str,
    scale: int,
    seed: int,
    density: float,
    topology: str,
) -> NaturalInstance:
    if scale <= 0 or not 0.0 < density <= 1.0:
        raise ValueError("scale and density must be positive")
    rng = random.Random(seed ^ int(1_000 * density) ^ sum(map(ord, family)))
    chain = [(q, q + 1) for q in range(WIDTH - 1)]
    ring = chain + [(0, WIDTH - 1)]
    all_pairs = [(a, b) for a in range(WIDTH) for b in range(a + 1, WIDTH)]
    blocks: list[Block] = []
    if family == "qaoa_ising":
        edges = _select_edges(ring, density, rng)
        for layer in range(2 * scale):
            base = [PauliTerm(edge, Fraction((seed + layer + edge[0]) % 5 + 1, 256)) for edge in edges]
            terms = tuple(base + list(reversed(base)))
            mixers = tuple(
                BoundaryGate("rx", (q,), Fraction((q + layer) % 5 + 1, 97))
                for q in range(WIDTH)
            )
            blocks.append(Block(terms, mixers, f"qaoa-cost-{layer}"))
    elif family == "diagonal_hamiltonian":
        supports = _select_edges([(q,) for q in range(WIDTH)] + all_pairs, density, rng)
        base = tuple(
            PauliTerm(support, Fraction((sum(support) + seed) % 7 + 1, 384))
            for support in supports
        )
        repeated_terms = tuple(term for _ in range(3) for term in base)
        repeated = Block(repeated_terms, (), "diagonal-segment")
        blocks.extend(repeated for _ in range(2 * scale))
    elif family == "trotter_commuting_blocks":
        edges = _select_edges(chain + [(0, 2), (2, 4), (1, 5)], density, rng)
        for step in range(3 * scale):
            base = [PauliTerm(edge, Fraction((step + edge[0]) % 5 + 1, 512)) for edge in edges]
            terms = tuple(base + base)
            boundary = tuple(
                BoundaryGate("rx", (q,), Fraction((step + q) % 7 + 1, 127))
                for q in range(WIDTH)
            )
            blocks.append(Block(terms, boundary, f"trotter-z-{step}"))
    elif family == "qpe_controlled_powers":
        controls = list(range(WIDTH - 2))
        for power in range(2 * scale):
            control = controls[power % len(controls)]
            base = PauliTerm((control, WIDTH - 1), Fraction(2 ** (power % 4), 1024))
            terms = tuple(base for _ in range(2 + power % 3))
            blocks.append(
                Block(terms, (BoundaryGate("h", (control,)),), f"qpe-power-{power}")
            )
    elif family == "qft_arithmetic":
        for stage in range(1, min(WIDTH, 2 + scale)):
            supports = _select_edges([(q, stage) for q in range(stage)], density, rng)
            base = [PauliTerm(support, Fraction(1, 2 ** (stage + 5))) for support in supports]
            terms = tuple(base + base + list(reversed(base)))
            blocks.append(Block(terms, (BoundaryGate("h", (stage,)),), f"qft-stage-{stage}"))
        blocks *= scale
    elif family == "controlled_power_ladder":
        supports = _select_edges([(q, WIDTH - 1) for q in range(WIDTH - 1)], density, rng)
        for exponent in range(1, 2 * scale + 1):
            base = [
                PauliTerm(support, Fraction(2 ** ((exponent - 1) % 5), 2048))
                for support in supports
            ]
            blocks.append(Block(tuple(base + base), (), f"controlled-power-{exponent}"))
    elif family == "phase_polynomial_blocks":
        nested = [tuple(range(length)) for length in range(1, WIDTH + 1)]
        supports = _select_edges(nested + all_pairs, density, rng)
        for block_index in range(2 * scale):
            base = [
                PauliTerm(support, Fraction((len(support) + block_index) % 7 + 1, 768))
                for support in supports
            ]
            blocks.append(Block(tuple(base + list(reversed(base))), (), f"phase-poly-{block_index}"))
    elif family == "negative_random_clifford_rz":
        for index in range(8 * scale):
            qubit = rng.randrange(WIDTH)
            other = (qubit + rng.randrange(1, WIDTH)) % WIDTH
            term = PauliTerm((qubit,), Fraction(index + 1, 2053))
            name = ("h", "s", "cx")[index % 3]
            qargs = (qubit,) if name != "cx" else (qubit, other)
            blocks.append(Block((term,), (BoundaryGate(name, qargs),), f"random-{index}"))
    elif family == "negative_routing_dominated":
        long_edges = [(0, WIDTH - 1), (1, WIDTH - 2), (0, WIDTH - 2), (1, WIDTH - 1)]
        for index in range(4 * scale):
            edge = long_edges[index % len(long_edges)]
            term = PauliTerm((index % WIDTH,), Fraction(index + 1, 4093))
            boundary = (
                BoundaryGate("cx", edge),
                BoundaryGate("swap", (index % WIDTH, WIDTH - index % WIDTH - 1)),
            )
            blocks.append(Block((term,), boundary, f"routing-{index}"))
    else:
        raise ValueError(f"unknown workload family {family}")
    return NaturalInstance(family, scale, seed, density, topology, tuple(blocks))


def aggregate_terms(terms: Iterable[PauliTerm]) -> tuple[PauliTerm, ...]:
    totals: dict[tuple[int, ...], Fraction] = {}
    for term in terms:
        totals[term.support] = (totals.get(term.support, Fraction()) + term.angle_over_pi) % 2
    return tuple(
        PauliTerm(support, coefficient)
        for support, coefficient in sorted(totals.items())
        if coefficient
    )


def aggregate_adjacent(terms: Iterable[PauliTerm]) -> tuple[PauliTerm, ...]:
    output: list[PauliTerm] = []
    for term in terms:
        if output and output[-1].support == term.support:
            coefficient = (output[-1].angle_over_pi + term.angle_over_pi) % 2
            output[-1] = PauliTerm(term.support, coefficient)
            if not coefficient:
                output.pop()
        else:
            output.append(term)
    return tuple(output)


def semantic_blocks(instance: NaturalInstance, aggregation: bool) -> tuple[Block, ...]:
    return tuple(
        Block(aggregate_terms(block.terms) if aggregation else block.terms, block.boundary, block.label)
        for block in instance.blocks
    )


def local_blocks(instance: NaturalInstance, aggregation: bool) -> tuple[Block, ...]:
    return tuple(
        Block(aggregate_adjacent(block.terms) if aggregation else block.terms, block.boundary, block.label)
        for block in instance.blocks
    )


def preset_blocks(instance: NaturalInstance) -> tuple[Block, ...] | None:
    if instance.family in NEGATIVE_FAMILIES:
        return None
    aggregated = list(semantic_blocks(instance, True))
    merged: list[Block] = []
    pending: list[PauliTerm] = []
    for block in aggregated:
        pending.extend(block.terms)
        if block.boundary:
            merged.append(Block(aggregate_terms(pending), block.boundary, f"preset-{block.label}"))
            pending = []
    if pending:
        merged.append(Block(aggregate_terms(pending), (), "preset-terminal"))
    return tuple(merged)


def append_term(circuit: Any, term: PauliTerm) -> None:
    support = tuple(sorted(term.support))
    target = support[-1]
    for control in support[:-1]:
        circuit.cx(control, target)
    circuit.rz(float(term.angle_over_pi) * math.pi, target)
    for control in reversed(support[:-1]):
        circuit.cx(control, target)


def append_boundary(circuit: Any, gate: BoundaryGate) -> None:
    if gate.name == "h":
        circuit.h(gate.qubits[0])
    elif gate.name == "s":
        circuit.s(gate.qubits[0])
    elif gate.name == "rx" and gate.angle_over_pi is not None:
        circuit.rx(float(gate.angle_over_pi) * math.pi, gate.qubits[0])
    elif gate.name == "cx":
        circuit.cx(*gate.qubits)
    elif gate.name == "swap":
        circuit.swap(*gate.qubits)
    else:
        raise ValueError(f"unsupported boundary {gate}")


def build_circuit(
    blocks: tuple[Block, ...],
    *,
    cache_enabled: bool,
) -> tuple[Any, int, int]:
    from qiskit import QuantumCircuit

    output = QuantumCircuit(WIDTH)
    cache: dict[str, Any] = {}
    hits = 0
    misses = 0
    for block in blocks:
        key = sha256_bytes(canonical_json(block.record()))
        if cache_enabled and key in cache:
            subcircuit = cache[key]
            hits += 1
        else:
            subcircuit = QuantumCircuit(WIDTH)
            for term in block.terms:
                append_term(subcircuit, term)
            for gate in block.boundary:
                append_boundary(subcircuit, gate)
            misses += 1
            if cache_enabled:
                cache[key] = subcircuit
        output.compose(subcircuit, inplace=True)
    return output, hits, misses


def circuit_metrics(circuit: Any) -> dict[str, int]:
    counts = circuit.count_ops()
    return {
        "gates": int(sum(counts.values())),
        "depth": int(circuit.depth() or 0),
        "cx": int(counts.get("cx", 0)),
        "logical_rotations": int(sum(counts.get(name, 0) for name in ("rx", "ry", "rz"))),
    }


def quality_score(circuit: Any) -> tuple[int, int, int]:
    value = circuit_metrics(circuit)
    return value["cx"], value["gates"], value["depth"]


def projected_score(blocks: tuple[Block, ...]) -> tuple[int, int, int]:
    cx = 0
    gates = 0
    depth = 0
    for block in blocks:
        for term in block.terms:
            term_cx = 2 * (len(term.support) - 1)
            cx += term_cx
            gates += term_cx + 1
            depth += term_cx + 1
        for gate in block.boundary:
            gate_cx = 3 if gate.name == "swap" else 1 if gate.name == "cx" else 0
            cx += gate_cx
            gates += 3 if gate.name == "swap" else 1
            depth += 3 if gate.name == "swap" else 1
    return cx, gates, depth


def lower_common(circuit: Any, topology: str, seed: int) -> Any:
    from qiskit import QuantumCircuit, transpile

    del seed  # The exact deterministic router below has no random choice.
    base = transpile(circuit, basis_gates=COMMON_BASIS, optimization_level=0)
    if topology == "all_to_all":
        return base
    if topology == "line":
        routed = QuantumCircuit(WIDTH)
        logical_at_physical = list(range(WIDTH))
        physical_of_logical = list(range(WIDTH))

        def swap_physical(left: int, right: int) -> None:
            if abs(left - right) != 1:
                raise AssertionError("line router attempted a nonadjacent swap")
            routed.cx(left, right)
            routed.cx(right, left)
            routed.cx(left, right)
            logical_left = logical_at_physical[left]
            logical_right = logical_at_physical[right]
            logical_at_physical[left], logical_at_physical[right] = logical_right, logical_left
            physical_of_logical[logical_left], physical_of_logical[logical_right] = right, left

        for instruction in base.data:
            name = instruction.operation.name
            logical_qubits = [base.find_bit(qubit).index for qubit in instruction.qubits]
            if name == "cx":
                control_logical, target_logical = logical_qubits
                control = physical_of_logical[control_logical]
                target = physical_of_logical[target_logical]
                while abs(control - target) > 1:
                    step = 1 if target > control else -1
                    swap_physical(control, control + step)
                    control = physical_of_logical[control_logical]
                    target = physical_of_logical[target_logical]
                routed.cx(control, target)
            elif len(logical_qubits) == 1:
                physical = physical_of_logical[logical_qubits[0]]
                routed.append(instruction.operation, [physical])
            else:
                raise ValueError(f"line router does not support {name}")
        # Restore the identity output layout so the routed circuit implements
        # the same unitary on the same ordered wires, not merely up to a final
        # logical-to-physical permutation.
        for desired_logical in range(WIDTH):
            current = physical_of_logical[desired_logical]
            while current > desired_logical:
                swap_physical(current - 1, current)
                current -= 1
            while current < desired_logical:
                swap_physical(current, current + 1)
                current += 1
        if logical_at_physical != list(range(WIDTH)):
            raise AssertionError("line router failed to restore identity layout")
        return routed
    raise ValueError(topology)


def compile_authors(instance: NaturalInstance, factors: Mapping[str, int]) -> tuple[Any, dict[str, Any]]:
    unknown = set(factors) - set(FACTORS)
    if unknown or set(factors) != set(FACTORS):
        raise ValueError(f"factor assignment mismatch: {sorted(unknown)}")
    started = time.perf_counter()
    flat_blocks = local_blocks(instance, bool(factors["aggregation"]))
    candidates: list[tuple[str, tuple[Block, ...]]] = [("flat", flat_blocks)]
    if factors["semantic_lift"]:
        candidates.append(("semantic", semantic_blocks(instance, bool(factors["aggregation"]))))
    if factors["preset_recognizer"]:
        recognized = preset_blocks(instance)
        if recognized is not None:
            candidates.append(("preset", recognized))
    built: dict[str, tuple[Any, int, int]] = {
        name: build_circuit(blocks, cache_enabled=bool(factors["cache_reuse"]))
        for name, blocks in candidates
    }
    if factors["selector"]:
        if factors["projected_block_selection"]:
            selected_name, selected_blocks = min(
                candidates, key=lambda item: (projected_score(item[1]), item[0])
            )
        else:
            selected_name, selected_blocks = min(
                candidates, key=lambda item: (quality_score(built[item[0]][0]), item[0])
            )
    else:
        selected_name, selected_blocks = candidates[-1]
    selected, hits, misses = built[selected_name]
    lowered = lower_common(selected, instance.topology, instance.seed)
    elapsed = time.perf_counter() - started
    description_record = {
        "factors": {name: int(factors[name]) for name in FACTORS},
        "selected": selected_name,
        "blocks": [block.record() for block in selected_blocks],
    }
    return lowered, {
        "selected_candidate": selected_name,
        "cache_hits": hits,
        "cache_misses": misses,
        "description_bits": 8 * len(canonical_json(description_record)),
        "runtime_s": elapsed,
        "semantic_term_count": sum(len(block.terms) for block in selected_blocks),
    }


def compile_external_tket(instance: NaturalInstance) -> tuple[Any, dict[str, Any]]:
    from qiskit import qasm2, transpile

    import pytket.qasm as tket_qasm
    from pytket import passes
    from pytket.circuit import OpType

    flat, _, _ = build_circuit(local_blocks(instance, False), cache_enabled=False)
    bridge = transpile(flat, basis_gates=EXTERNAL_BRIDGE_BASIS, optimization_level=0)
    input_qasm = qasm2.dumps(bridge)
    started = time.perf_counter()
    native = tket_qasm.circuit_from_qasm_str(input_qasm)
    pass_sequence = [
        passes.DecomposeBoxes(),
        passes.RemoveRedundancies(),
        passes.PauliSimp(),
        passes.RemoveRedundancies(),
        passes.AutoRebase({OpType.CX, OpType.Rz, OpType.H}, allow_swaps=False),
        passes.RemoveRedundancies(),
    ]
    for compiler_pass in pass_sequence:
        compiler_pass.apply(native)
    native_qasm = tket_qasm.circuit_to_qasm_str(native)
    certificate_circuit = qasm2.loads(native_qasm)
    lowered = lower_common(certificate_circuit, instance.topology, instance.seed)
    elapsed = time.perf_counter() - started
    return lowered, {
        "selected_candidate": "tket_paulisimp",
        "cache_hits": 0,
        "cache_misses": len(instance.blocks),
        "description_bits": 8 * len(native_qasm.encode()),
        "runtime_s": elapsed,
        "semantic_term_count": int(native.n_gates),
        "bridge_input_bytes": len(input_qasm.encode()),
        "bridge_output_bytes": len(native_qasm.encode()),
    }


def dense_certificate(reference: Any, candidate: Any) -> dict[str, Any]:
    import numpy as np
    from qiskit import qasm2
    from qiskit.quantum_info import Operator

    if reference.num_qubits > 6 or candidate.num_qubits > 6:
        return {"status": "unsupported", "reason": "dense certificate width exceeds six"}
    left = Operator(reference)
    right = Operator(candidate)
    passed = bool(left.equiv(right, rtol=1e-8, atol=1e-8))
    overlap = np.trace(left.data.conj().T @ right.data)
    dimension = left.data.shape[0]
    distance = math.sqrt(max(0.0, 2 * dimension - 2 * abs(complex(overlap))) / dimension)
    payload = {
        "schema": "ucc.correctness-certificate.v1",
        "kind": "dense_unitary_projective_n_le_6_v1",
        "accepted": passed,
        "width": reference.num_qubits,
        "projective_frobenius_distance": distance,
        "reference_qasm_sha256": sha256_bytes(qasm2.dumps(reference).encode()),
        "candidate_qasm_sha256": sha256_bytes(qasm2.dumps(candidate).encode()),
        "rtol": 1e-8,
        "atol": 1e-8,
    }
    return {
        "status": "completed_valid" if passed else "completed_invalid",
        "certificate_kind": payload["kind"],
        "certificate_sha256": sha256_bytes(canonical_json(payload)),
        "projective_distance": distance,
    }


def raw_reference(instance: NaturalInstance) -> Any:
    circuit, _, _ = build_circuit(local_blocks(instance, False), cache_enabled=False)
    return lower_common(circuit, instance.topology, instance.seed)


def qasm_bytes(circuit: Any) -> bytes:
    from qiskit import qasm2

    return qasm2.dumps(circuit).encode()


class QREContext:
    def __init__(self, epsilon_total: float = 1e-6, factories: int = 16):
        from scripts.allocate_synthesis_error import split_error_budget
        from scripts.run_qre_campaign import GridSynthCache

        self.budget = split_error_budget(
            epsilon_total,
            {"algorithmic": 0.1, "synthesis": 0.45, "logical": 0.45},
        )
        qre_profile_path = ROOT / "qre/configs/surface_code_conservative.yaml"
        self.profile = load_yaml(qre_profile_path)
        self.factory = {"id": f"parallel_{factories}", "requested_factories": factories}
        campaign = load_yaml(ROOT / "qre/configs/campaign.yaml")
        synthesizer = campaign["synthesizer"]
        executable = ROOT / synthesizer["executable"]
        self.grid = GridSynthCache(executable, float(synthesizer["per_angle_timeout_s"]))
        self.output_cache: dict[str, dict[str, Any]] = {}

    def measure(self, circuit: Any) -> dict[str, Any]:
        from scripts.run_qre_campaign import (
            circuit_metrics as qre_circuit_metrics,
            rotation_histogram,
            schedule_qre,
            synthesize_histogram,
        )

        payload = qasm_bytes(circuit)
        digest = sha256_bytes(payload)
        if digest in self.output_cache:
            return dict(self.output_cache[digest])
        started = time.perf_counter()
        synthesis = synthesize_histogram(
            rotation_histogram(circuit),
            self.budget.epsilon_synthesis,
            "equal_decimal",
            self.grid,
        )
        qre = schedule_qre(
            qre_circuit_metrics(circuit),
            int(synthesis["logical_t_states"]),
            self.budget.epsilon_logical,
            self.profile,
            self.factory,
        )
        result = {
            "qre_status": "completed_valid",
            "qre_epsilon_total": self.budget.epsilon_total,
            "logical_t_states": int(synthesis["logical_t_states"]),
            "qre_code_distance": int(qre["code_distance"]),
            "qre_data_physical_qubits": int(qre["data_physical_qubits"]),
            "qre_factory_physical_qubits": int(qre["factory_physical_qubits"]),
            "qre_physical_qubits": int(qre["physical_qubits"]),
            "qre_factories": int(qre["factories"]),
            "qre_cycles": int(qre["cycles"]),
            "qre_runtime_seconds": float(qre["runtime_seconds"]),
            "spacetime_qubit_seconds": float(qre["spacetime_qubit_seconds"]),
            "qre_classical_runtime_s": time.perf_counter() - started,
        }
        self.output_cache[digest] = result
        return dict(result)


def backend_hash(topology: str) -> str:
    record = {
        "topology": topology,
        "width": WIDTH,
        "basis": COMMON_BASIS,
        "router": "qiskit_basic_trivial_layout" if topology == "line" else "none",
    }
    return sha256_bytes(canonical_json(record))


def configuration_hash(method_id: str, factors: Mapping[str, int] | None) -> str:
    record = {
        "method_id": method_id,
        "factors": None if factors is None else {name: int(factors[name]) for name in FACTORS},
    }
    return sha256_bytes(canonical_json(record))


def row_id(instance: NaturalInstance, method_id: str, config_hash: str) -> str:
    record = {
        "experiment_id": "w8-natural-factorial-20260803-local",
        "instance_id": instance.instance_id,
        "representation_id": instance.representation_id,
        "method_id": method_id,
        "seed": instance.seed,
        "backend_hash": backend_hash(instance.topology),
        "config_hash": config_hash,
    }
    return "w8-" + sha256_bytes(canonical_json(record))[:20]


def save_output(circuit: Any, output_root: Path) -> tuple[str, int, str]:
    payload = qasm_bytes(circuit)
    digest = sha256_bytes(payload)
    output_root.mkdir(parents=True, exist_ok=True)
    path = output_root / f"{digest}.qasm"
    if not path.exists():
        path.write_bytes(payload)
    return digest, len(payload), os.path.relpath(path, ROOT)


def build_result_row(
    instance: NaturalInstance,
    method_id: str,
    circuit: Any,
    compiler_record: Mapping[str, Any],
    certificate: Mapping[str, Any],
    qre: Mapping[str, Any],
    config_hash: str,
    output_root: Path,
    factors: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    output_sha, output_bytes, output_path = save_output(circuit, output_root)
    input_bytes = len(canonical_json(instance.semantic_record()))
    row = {
        "experiment_id": "w8-natural-factorial-20260803-local",
        "instance_id": instance.instance_id,
        "representation_id": instance.representation_id,
        "method_id": method_id,
        "seed": instance.seed,
        "backend_hash": backend_hash(instance.topology),
        "tool_version": "repository" if method_id.startswith("authors") else "pytket-runtime",
        "artifact_commit": git_revision(),
        "config_hash": config_hash,
        "row_id": row_id(instance, method_id, config_hash),
        "workload": instance.family,
        "workload_class": instance.workload_class,
        "scale": instance.scale,
        "density": instance.density,
        "hardware_topology": instance.topology,
        "status": certificate["status"],
        "certificate_status": certificate["status"],
        "certificate_kind": certificate.get("certificate_kind"),
        "certificate_sha256": certificate.get("certificate_sha256"),
        "projective_distance": certificate.get("projective_distance"),
        "input_ir_bytes": input_bytes,
        "output_ir_bytes": output_bytes,
        "serialized_ir_bytes": output_bytes,
        "output_artifact_path": output_path,
        "output_artifact_sha256": output_sha,
        "rss_bytes": process_maxrss_bytes(),
        **compiler_record,
        **circuit_metrics(circuit),
        **qre,
    }
    if factors is None:
        row.update({factor: None for factor in FACTORS})
    else:
        row.update({factor: int(factors[factor]) for factor in FACTORS})
    return row

#!/usr/bin/env python3
"""Run the fixed-total-error, angle-synthesis, surface-code QRE campaign.

This campaign measures compiler outputs, certifies the resulting four-qubit
circuits, calls the frozen deterministic staq grid_synth binary for every
unique angle/precision pair, and only then evaluates the versioned QEC and
factory scenarios.  It never reads the historical fixed-1e-10 T proxy.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import re
import subprocess
import sys
import time
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from certificates.canonicalize import ExactCircuit, ExactOperation, PauliAxis  # noqa: E402
from certificates.symbolic_checker import check_equivalence  # noqa: E402
from scripts.allocate_synthesis_error import (  # noqa: E402
    equal_decimal_allocation,
    split_error_budget,
    t_cost_greedy_allocation,
)


SCHEMA = "ucc.qre.campaign-results.v1"
VALID_OUTPUT_STATUSES = {
    "completed_valid",
    "unsupported",
    "predicate_error",
    "correctness_failure",
    "numerical_inconclusive",
    "synthesis_error",
}


class UnsupportedPipeline(RuntimeError):
    pass


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return value


def resolve(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def qubit_index(circuit: Any, qubit: Any) -> int:
    return int(circuit.find_bit(qubit).index)


def build_target(requested_gates: int) -> Any:
    """Construct the same fixed-width H D^r H witness used by the manuscript."""

    from qiskit import QuantumCircuit

    width = 4
    block = QuantumCircuit(width)
    for qubit in range(width):
        block.rz(math.pi / (7 + qubit), qubit)
    for control in range(width):
        for target in range(control + 1, width):
            block.cp(math.pi / (11 + control + target), control, target)
    repeats = max(1, (requested_gates - 2 * width) // len(block.data))
    circuit = QuantumCircuit(width, name=f"hdiag-{requested_gates}")
    for qubit in range(width):
        circuit.h(qubit)
    for _ in range(repeats):
        circuit.compose(block, inplace=True)
    for qubit in range(width):
        circuit.h(qubit)
    return circuit


def compile_pipeline(source: Any, pipeline_id: str, seed: int, config: Mapping[str, Any]) -> tuple[Any, dict[str, Any]]:
    from qiskit import qasm2, transpile

    target_basis = list(config["target_basis"])
    bridge_basis = list(config["external_bridge_basis"])
    if pipeline_id == "semantic_first":
        import ucc

        output = ucc.compile(
            source,
            return_format="qiskit",
            target_gateset=set(target_basis),
        )
        return output, {
            "bridge_format": "native Qiskit semantic circuit",
            "bridge_input_gates": len(source.data),
            "bridge_input_bytes": len(qasm2.dumps(source).encode()),
            "semantic_recovery_before_synthesis": True,
        }
    if pipeline_id == "materialize_first":
        materialized = transpile(source, basis_gates=target_basis, optimization_level=0)
        output = transpile(
            materialized,
            basis_gates=target_basis,
            optimization_level=3,
            layout_method="trivial",
            routing_method="none",
            seed_transpiler=seed,
        )
        return output, {
            "bridge_format": "materialized Qiskit basis circuit",
            "bridge_input_gates": len(materialized.data),
            "bridge_input_bytes": len(qasm2.dumps(materialized).encode()),
            "semantic_recovery_before_synthesis": False,
        }
    if pipeline_id == "external_tket_paulisimp":
        try:
            import pytket.qasm as tket_qasm
            from pytket import passes
            from pytket.circuit import OpType
        except ImportError as exc:
            raise UnsupportedPipeline(str(exc)) from exc
        materialized = transpile(source, basis_gates=bridge_basis, optimization_level=0)
        input_qasm = qasm2.dumps(materialized)
        native = tket_qasm.circuit_from_qasm_str(input_qasm)
        sequence = [
            passes.DecomposeBoxes(),
            passes.RemoveRedundancies(),
            passes.PauliSimp(),
            passes.RemoveRedundancies(),
            passes.AutoRebase({OpType.CX, OpType.Rz, OpType.H}, allow_swaps=False),
            passes.RemoveRedundancies(),
        ]
        for compiler_pass in sequence:
            compiler_pass.apply(native)
        output_qasm = tket_qasm.circuit_to_qasm_str(native)
        output = qasm2.loads(output_qasm)
        return output, {
            "bridge_format": "OpenQASM2 -> TKET CX-Rz-H -> OpenQASM2",
            "bridge_input_gates": len(materialized.data),
            "bridge_input_bytes": len(input_qasm.encode()),
            "bridge_output_bytes": len(output_qasm.encode()),
            "semantic_recovery_before_synthesis": True,
            "external_pass_sequence": [type(item).__name__ for item in sequence],
        }
    raise UnsupportedPipeline(f"unknown pipeline {pipeline_id}")


def circuit_metrics(circuit: Any) -> dict[str, int]:
    counts = circuit.count_ops()
    return {
        "logical_qubits": int(circuit.num_qubits),
        "output_gates": int(sum(counts.values())),
        "output_depth": int(circuit.depth()),
        "output_cx": int(counts.get("cx", 0)),
        "logical_rotations": int(sum(counts.get(name, 0) for name in ("rx", "ry", "rz"))),
    }


def snap_rational_pi(angle: float, tolerance: float) -> tuple[Fraction, float]:
    ratio = float(angle) / math.pi
    snapped = Fraction(ratio).limit_denominator(10**9)
    error = abs(ratio - float(snapped))
    if error > tolerance:
        raise ValueError(f"angle/pi snap error {error} exceeds {tolerance}")
    return snapped, error


def exact_circuit_from_qiskit(circuit: Any, name: str, tolerance: float) -> tuple[ExactCircuit, float]:
    operations: list[ExactOperation] = []
    maximum_snap_error = 0.0
    width = int(circuit.num_qubits)
    cliffords = {"h", "s", "sdg", "x", "y", "z", "cx", "cz", "swap"}
    for instruction in circuit.data:
        gate = instruction.operation.name
        qubits = tuple(qubit_index(circuit, qubit) for qubit in instruction.qubits)
        if gate in {"barrier", "id"}:
            continue
        if gate in cliffords:
            operations.append(ExactOperation.clifford(gate, *qubits))
            continue
        if gate not in {"rx", "ry", "rz"} or len(qubits) != 1:
            raise UnsupportedPipeline(f"certificate adapter does not support gate {gate}")
        coefficient, error = snap_rational_pi(float(instruction.operation.params[0]), tolerance)
        maximum_snap_error = max(maximum_snap_error, error)
        if gate == "rz":
            operations.append(ExactOperation.rz(qubits[0], coefficient))
        else:
            bit = 1 << qubits[0]
            axis = PauliAxis(width, bit, 0 if gate == "rx" else bit)
            operations.append(ExactOperation.rotation(axis, coefficient))
    global_phase, error = snap_rational_pi(float(circuit.global_phase), tolerance)
    maximum_snap_error = max(maximum_snap_error, error)
    return ExactCircuit.of(
        width,
        operations,
        global_phase_over_pi=global_phase,
        name=name,
    ), maximum_snap_error


def certify_output(source: Any, output: Any, tolerance: float) -> dict[str, Any]:
    import numpy as np
    from qiskit import qasm2
    from qiskit import transpile
    from qiskit.quantum_info import Operator

    reference = transpile(source, basis_gates=["cx", "rz", "h"], optimization_level=0)
    reference_operator = Operator(reference)
    output_operator = Operator(output)
    dense_passed = bool(reference_operator.equiv(output_operator, rtol=1e-9, atol=1e-9))
    overlap = np.trace(reference_operator.data.conj().T @ output_operator.data)
    dimension = reference_operator.data.shape[0]
    dense_projective_distance = math.sqrt(
        max(0.0, 2.0 * dimension - 2.0 * abs(complex(overlap))) / dimension
    )
    exact_reference, reference_snap = exact_circuit_from_qiskit(
        reference, "qre-reference", tolerance
    )
    exact_output, output_snap = exact_circuit_from_qiskit(output, "qre-output", tolerance)
    symbolic = check_equivalence(exact_reference, exact_output)
    symbolic_certificate = symbolic.get("independent_certificate") or {}
    dense_payload = {
        "schema": "ucc.correctness-certificate.v1",
        "kind": "dense_unitary_projective_n_le_6_v1",
        "accepted": dense_passed,
        "equivalence": "up_to_global_phase",
        "width": int(source.num_qubits),
        "maximum_supported_width": 6,
        "reference_qasm_sha256": hashlib.sha256(qasm2.dumps(reference).encode()).hexdigest(),
        "candidate_qasm_sha256": hashlib.sha256(qasm2.dumps(output).encode()).hexdigest(),
        "observed_projective_frobenius_distance": dense_projective_distance,
        "qiskit_operator_equiv_rtol": 1e-9,
        "qiskit_operator_equiv_atol": 1e-9,
        "symbolic_crosscheck_status": symbolic["status"],
    }
    dense_payload["certificate_sha256"] = hashlib.sha256(
        canonical_json(dense_payload)
    ).hexdigest()
    if dense_passed and symbolic["status"] == "completed_valid":
        selected_kind = symbolic.get("kind")
        selected_sha256 = symbolic_certificate.get("certificate_sha256")
        selected_domain = "exact_symbolic_plus_dense_crosscheck"
    elif dense_passed and int(source.num_qubits) <= 6:
        selected_kind = dense_payload["kind"]
        selected_sha256 = dense_payload["certificate_sha256"]
        selected_domain = "independent_dense_n_le_6"
    else:
        selected_kind = None
        selected_sha256 = None
        selected_domain = None
    accepted = dense_passed and selected_sha256 is not None
    return {
        "accepted": accepted,
        "dense_passed": dense_passed,
        "dense_projective_frobenius_distance": dense_projective_distance,
        "symbolic_status": symbolic["status"],
        "certificate_kind": selected_kind,
        "certificate_sha256": selected_sha256,
        "certificate_domain": selected_domain,
        "reference_input_sha256": symbolic_certificate.get("reference_input_sha256"),
        "candidate_input_sha256": symbolic_certificate.get("candidate_input_sha256"),
        "dense_certificate": dense_payload,
        "maximum_angle_snap_error_over_pi": max(reference_snap, output_snap),
        "reason": symbolic.get("reason"),
    }


def rotation_histogram(circuit: Any) -> Counter[str]:
    histogram: Counter[str] = Counter()
    for instruction in circuit.data:
        if instruction.operation.name not in {"rx", "ry", "rz"}:
            continue
        angle = float(instruction.operation.params[0])
        ratio = angle / math.pi
        key = f"{ratio:.18g}|{angle.hex()}"
        histogram[key] += 1
    return histogram


@dataclass
class GridSynthesisRecord:
    angle_key: str
    angle_over_pi: str
    angle_ieee_hex: str
    decimal_precision: int
    t_per_rotation: int
    reported_error: float
    checker_passed: bool
    runtime_s: float
    stdout_sha256: str
    stderr_sha256: str


class GridSynthCache:
    def __init__(self, executable: Path, timeout_s: float):
        self.executable = executable
        self.timeout_s = timeout_s
        self.records: dict[tuple[str, int], GridSynthesisRecord] = {}

    def get(self, angle_key: str, precision: int) -> GridSynthesisRecord:
        cache_key = (angle_key, precision)
        if cache_key in self.records:
            return self.records[cache_key]
        ratio_text, angle_hex = angle_key.split("|", 1)
        command = [
            str(self.executable),
            ratio_text,
            "--precision",
            str(precision),
            "--check",
            "--details",
        ]
        started = time.perf_counter()
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=self.timeout_s,
            check=False,
        )
        runtime_s = time.perf_counter() - started
        if completed.returncode != 0:
            raise RuntimeError(
                f"grid_synth failed for {ratio_text}/p={precision}: {completed.stderr[-500:]}"
            )
        checker_passed = "Check flag = 1" in completed.stderr
        error_match = re.search(r"^error = ([^\n]+)$", completed.stderr, re.MULTILINE)
        t_match = re.search(r"^T count = (\d+)$", completed.stderr, re.MULTILINE)
        exact_clifford = "Angle is multiple of pi/4, answer is known exactly" in completed.stderr
        if not checker_passed or (
            not exact_clifford and (error_match is None or t_match is None)
        ):
            raise RuntimeError(
                "grid_synth did not emit checked error and T-count records "
                f"for {ratio_text}/p={precision}"
            )
        # staq's exact pi/4 branch prints only the checked Clifford+T word.
        # It intentionally omits the approximate-branch `error`/`T count`
        # diagnostics, so count literal T tokens and assign exact error zero.
        reported_error = 0.0 if exact_clifford else float(error_match.group(1))
        t_per_rotation = (
            sum(token == "T" for token in completed.stdout.split())
            if exact_clifford
            else int(t_match.group(1))
        )
        if reported_error > 10.0 ** (-precision) * (1.0 + 1e-6):
            raise RuntimeError(
                f"grid_synth error {reported_error} exceeds decimal radius 1e-{precision}"
            )
        record = GridSynthesisRecord(
            angle_key=angle_key,
            angle_over_pi=ratio_text,
            angle_ieee_hex=angle_hex,
            decimal_precision=precision,
            t_per_rotation=t_per_rotation,
            reported_error=reported_error,
            checker_passed=True,
            runtime_s=runtime_s,
            stdout_sha256=hashlib.sha256(completed.stdout.encode()).hexdigest(),
            stderr_sha256=hashlib.sha256(completed.stderr.encode()).hexdigest(),
        )
        self.records[cache_key] = record
        return record


def synthesize_histogram(
    histogram: Counter[str],
    epsilon_synthesis: float,
    policy: str,
    cache: GridSynthCache,
) -> dict[str, Any]:
    if not histogram:
        return {
            "allocation_policy": policy,
            "logical_rotations": 0,
            "logical_t_states": 0,
            "allocated_synthesis_error": 0.0,
            "reported_synthesis_error_union_bound": 0.0,
            "allocation_steps": 0,
            "angle_records": [],
        }
    equal = equal_decimal_allocation(histogram, epsilon_synthesis)
    equal_precision = int(next(iter(equal["groups"].values()))["decimal_precision"])
    if policy == "equal_decimal":
        allocation = equal
    elif policy == "t_cost_greedy":
        cost_table: dict[str, dict[int, int]] = {}
        for angle_key in histogram:
            cost_table[angle_key] = {
                precision: cache.get(angle_key, precision).t_per_rotation
                for precision in range(max(1, equal_precision - 3), equal_precision + 1)
            }
        allocation = t_cost_greedy_allocation(
            histogram, epsilon_synthesis, cost_table
        )
    else:
        raise ValueError(f"unknown allocation policy {policy}")
    logical_t_states = 0
    reported_total = 0.0
    angle_records = []
    for angle_key, item in allocation["groups"].items():
        precision = int(item["decimal_precision"])
        record = cache.get(angle_key, precision)
        multiplicity = int(item["multiplicity"])
        logical_t_states += multiplicity * record.t_per_rotation
        reported_total += multiplicity * record.reported_error
        angle_records.append(
            {
                **asdict(record),
                "multiplicity": multiplicity,
                "t_subtotal": multiplicity * record.t_per_rotation,
                "allocated_error_subtotal": multiplicity * float(item["epsilon_per_rotation"]),
                "reported_error_subtotal": multiplicity * record.reported_error,
            }
        )
    if float(allocation["allocated_total"]) > epsilon_synthesis * (1.0 + 1e-12):
        raise AssertionError("synthesis allocation exceeded its budget")
    if reported_total > float(allocation["allocated_total"]) * (1.0 + 1e-6):
        raise AssertionError("reported synthesis error exceeded allocated union bound")
    return {
        "allocation_policy": policy,
        "logical_rotations": sum(histogram.values()),
        "logical_t_states": logical_t_states,
        "allocated_synthesis_error": float(allocation["allocated_total"]),
        "reported_synthesis_error_union_bound": reported_total,
        "allocation_steps": len(allocation.get("steps", [])),
        "equal_decimal_precision": equal_precision,
        "angle_records": angle_records,
    }


def logical_error_per_patch_cycle(distance: int, profile: Mapping[str, Any]) -> float:
    ratio = float(profile["physical_error_rate"]) / float(profile["threshold"])
    if not 0.0 < ratio < 1.0:
        raise ValueError("surface-code profile requires physical_error_rate < threshold")
    return float(profile["logical_error_prefactor"]) * ratio ** ((distance + 1) / 2)


def schedule_qre(
    metrics: Mapping[str, int],
    logical_t_states: int,
    logical_error_budget: float,
    profile: Mapping[str, Any],
    factory_profile: Mapping[str, Any],
) -> dict[str, Any]:
    requested_factories = int(factory_profile["requested_factories"])
    factories = 0 if logical_t_states == 0 else min(requested_factories, logical_t_states)
    minimum = int(profile["minimum_odd_distance"])
    maximum = int(profile["maximum_odd_distance"])
    if minimum % 2 == 0 or maximum % 2 == 0:
        raise ValueError("code-distance limits must be odd")
    selected: dict[str, Any] | None = None
    for distance in range(minimum, maximum + 1, 2):
        clifford_cycles = int(math.ceil(
            int(metrics["output_depth"])
            * float(profile["clifford_layer_d_cycles"])
            * distance
        ))
        t_batches = 0 if factories == 0 else math.ceil(logical_t_states / factories)
        factory_cycles = int(math.ceil(
            t_batches * float(profile["factory_period_d_cycles"]) * distance
        ))
        cycles = max(1, clifford_cycles + factory_cycles)
        patch_error = logical_error_per_patch_cycle(distance, profile)
        data_failure = int(metrics["logical_qubits"]) * cycles * patch_error
        factory_failure = (
            factories * int(profile["factory_logical_patches"]) * cycles * patch_error
        )
        distillation_failure = (
            logical_t_states
            * float(profile["distillation_output_coefficient"])
            * patch_error**3
        )
        logical_failure = data_failure + factory_failure + distillation_failure
        if logical_failure <= logical_error_budget:
            selected = {
                "code_distance": distance,
                "clifford_cycles": clifford_cycles,
                "factory_cycles": factory_cycles,
                "cycles": cycles,
                "logical_error_per_patch_cycle": patch_error,
                "data_logical_failure_bound": data_failure,
                "factory_logical_failure_bound": factory_failure,
                "distillation_failure_bound": distillation_failure,
                "logical_failure_bound": logical_failure,
            }
            break
    if selected is None:
        raise RuntimeError("no code distance satisfies the logical-error budget")
    distance = int(selected["code_distance"])
    data_qubits = int(math.ceil(
        float(profile["data_patch_qubits_coefficient"])
        * distance**2
        * int(metrics["logical_qubits"])
    ))
    factory_qubits = int(math.ceil(
        float(profile["factory_qubits_coefficient"])
        * distance**2
        * factories
    ))
    physical_qubits = data_qubits + factory_qubits
    runtime_seconds = int(selected["cycles"]) * float(profile["cycle_time_seconds"])
    return {
        **selected,
        "factory_profile": factory_profile["id"],
        "requested_factories": requested_factories,
        "factories": factories,
        "data_physical_qubits": data_qubits,
        "factory_physical_qubits": factory_qubits,
        "physical_qubits": physical_qubits,
        "runtime_seconds": runtime_seconds,
        "spacetime_qubit_cycles": physical_qubits * int(selected["cycles"]),
        "spacetime_qubit_seconds": physical_qubits * runtime_seconds,
    }


def pareto_flags(rows: list[dict[str, Any]]) -> None:
    completed = [row for row in rows if row["status"] == "completed_valid"]
    key_fields = (
        "target_id",
        "pipeline_id",
        "epsilon_total",
        "allocation_policy",
        "qec_profile",
    )
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in completed:
        groups.setdefault(tuple(row[field] for field in key_fields), []).append(row)
    for row in rows:
        row["pareto_qubits_runtime"] = False
    for group in groups.values():
        for row in group:
            dominated = any(
                other is not row
                and other["physical_qubits"] <= row["physical_qubits"]
                and other["runtime_seconds"] <= row["runtime_seconds"]
                and (
                    other["physical_qubits"] < row["physical_qubits"]
                    or other["runtime_seconds"] < row["runtime_seconds"]
                )
                for other in group
            )
            row["pareto_qubits_runtime"] = not dominated


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def package_versions() -> dict[str, str]:
    result = {}
    for package in ("qiskit", "ucc", "pytket", "numpy", "pandas", "pyarrow"):
        try:
            result[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            result[package] = "not-installed"
    return result


def run_campaign(config_path: Path) -> dict[str, Any]:
    config = load_yaml(config_path)
    error_config = config["error_budget"]
    fractions = error_config["fractions"]
    # Validate once before any expensive work.
    for epsilon_total in error_config["epsilon_totals"]:
        split_error_budget(float(epsilon_total), fractions)
    qec_profiles = [load_yaml(resolve(path)) for path in config["qre_profiles"]]
    factory_config = load_yaml(resolve(config["factory_profiles"]))
    factory_profiles = list(factory_config["profiles"])
    synthesizer = config["synthesizer"]
    executable = resolve(synthesizer["executable"])
    source_path = resolve(synthesizer["source"])
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise FileNotFoundError(f"grid_synth executable unavailable: {executable}")
    run_directory = resolve(config["output"]["run_directory"])
    run_directory.mkdir(parents=True, exist_ok=True)
    cache = GridSynthCache(executable, float(synthesizer["per_angle_timeout_s"]))
    rows: list[dict[str, Any]] = []
    compilation_records = []
    angle_uses = []
    seed = int(config["seed"])
    pipeline_configs = {item["id"]: item for item in config["pipelines"]}
    for requested_gates in config["targets_requested_gates"]:
        source = build_target(int(requested_gates))
        target_id = f"hdiag-{requested_gates}"
        for pipeline_id, pipeline_config in pipeline_configs.items():
            started = time.perf_counter()
            try:
                output, bridge = compile_pipeline(source, pipeline_id, seed, config)
                compile_runtime_s = time.perf_counter() - started
                metrics = circuit_metrics(output)
                certificate = certify_output(
                    source,
                    output,
                    float(config["certificate"]["maximum_symbolic_angle_snap_error"]),
                )
            except UnsupportedPipeline as exc:
                compilation_records.append({
                    "target_id": target_id,
                    "pipeline_id": pipeline_id,
                    "status": "unsupported",
                    "reason": str(exc),
                })
                continue
            except Exception as exc:
                compilation_records.append({
                    "target_id": target_id,
                    "pipeline_id": pipeline_id,
                    "status": "predicate_error",
                    "reason": f"{type(exc).__name__}: {exc}",
                })
                continue
            status = "completed_valid" if certificate["accepted"] else (
                "correctness_failure" if not certificate["dense_passed"]
                else certificate["symbolic_status"]
            )
            if status not in VALID_OUTPUT_STATUSES:
                status = "predicate_error"
            histogram = rotation_histogram(output)
            compilation_record = {
                "schema": "ucc.qre.compiled-input.v1",
                "target_id": target_id,
                "requested_gates": int(requested_gates),
                "pipeline_id": pipeline_id,
                "pipeline_category": pipeline_config["category"],
                "pipeline_implementation": pipeline_config["implementation"],
                "status": status,
                "compile_runtime_s": compile_runtime_s,
                **metrics,
                **bridge,
                **{f"certificate_{key}": value for key, value in certificate.items()},
            }
            compilation_records.append(compilation_record)
            if status != "completed_valid":
                continue
            for epsilon_total_value in error_config["epsilon_totals"]:
                budget = split_error_budget(float(epsilon_total_value), fractions)
                for allocation_policy in error_config["synthesis_allocation_policies"]:
                    try:
                        synthesis = synthesize_histogram(
                            histogram,
                            budget.epsilon_synthesis,
                            allocation_policy,
                            cache,
                        )
                    except Exception as exc:
                        for qec_profile in qec_profiles:
                            for factory_profile in factory_profiles:
                                rows.append({
                                    "schema": SCHEMA,
                                    "target_id": target_id,
                                    "requested_gates": int(requested_gates),
                                    "pipeline_id": pipeline_id,
                                    "pipeline_category": pipeline_config["category"],
                                    "epsilon_total": budget.epsilon_total,
                                    "allocation_policy": allocation_policy,
                                    "qec_profile": qec_profile["id"],
                                    "factory_profile": factory_profile["id"],
                                    "status": "synthesis_error",
                                    "reason": f"{type(exc).__name__}: {exc}",
                                })
                        continue
                    synthesis_summary = {
                        key: value for key, value in synthesis.items() if key != "angle_records"
                    }
                    for record in synthesis["angle_records"]:
                        angle_uses.append({
                            "target_id": target_id,
                            "pipeline_id": pipeline_id,
                            "epsilon_total": budget.epsilon_total,
                            "allocation_policy": allocation_policy,
                            **record,
                        })
                    for qec_profile in qec_profiles:
                        for factory_profile in factory_profiles:
                            qre = schedule_qre(
                                metrics,
                                int(synthesis["logical_t_states"]),
                                budget.epsilon_logical,
                                qec_profile,
                                factory_profile,
                            )
                            realized_total_bound = (
                                budget.epsilon_algorithmic
                                + float(synthesis["allocated_synthesis_error"])
                                + float(qre["logical_failure_bound"])
                            )
                            if realized_total_bound > budget.epsilon_total * (1.0 + 1e-12):
                                raise AssertionError("realized error bound exceeded epsilon_total")
                            rows.append({
                                "schema": SCHEMA,
                                "campaign_id": config["campaign_id"],
                                "target_id": target_id,
                                "requested_gates": int(requested_gates),
                                "pipeline_id": pipeline_id,
                                "pipeline_category": pipeline_config["category"],
                                "status": "completed_valid",
                                "seed": seed,
                                **budget.as_dict(),
                                "realized_algorithmic_error_bound": budget.epsilon_algorithmic,
                                "realized_total_error_bound": realized_total_bound,
                                "epsilon_total_slack": budget.epsilon_total - realized_total_bound,
                                "qec_profile": qec_profile["id"],
                                "physical_error_rate": float(qec_profile["physical_error_rate"]),
                                "cycle_time_seconds": float(qec_profile["cycle_time_seconds"]),
                                "certificate_sha256": certificate["certificate_sha256"],
                                "certificate_kind": certificate["certificate_kind"],
                                "certificate_dense_passed": certificate["dense_passed"],
                                "certificate_symbolic_status": certificate["symbolic_status"],
                                "compile_runtime_s": compile_runtime_s,
                                **metrics,
                                **{key: value for key, value in bridge.items() if not isinstance(value, list)},
                                **synthesis_summary,
                                **qre,
                            })
    pareto_flags(rows)
    results_path = run_directory / "qre_cells.jsonl"
    compilation_path = run_directory / "compiled_inputs.jsonl"
    angles_path = run_directory / "angle_synthesis_uses.jsonl"
    cache_path = run_directory / "angle_synthesis_cache.jsonl"
    write_jsonl(results_path, rows)
    write_jsonl(compilation_path, compilation_records)
    write_jsonl(angles_path, angle_uses)
    write_jsonl(cache_path, (asdict(record) for record in cache.records.values()))
    completed_rows = sum(row["status"] == "completed_valid" for row in rows)
    if completed_rows == 0:
        raise RuntimeError("campaign produced no completed_valid QRE rows")
    frozen_parquet = resolve(config["output"]["frozen_parquet"])
    frozen_csv = resolve(config["output"]["frozen_csv"])
    frozen_parquet.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    frame.to_parquet(frozen_parquet, index=False)
    frame.to_csv(frozen_csv, index=False)
    source_files = [
        config_path,
        ROOT / "qre/error_budget_schema.json",
        resolve(config["factory_profiles"]),
        *[resolve(path) for path in config["qre_profiles"]],
        Path(__file__).resolve(),
        ROOT / "scripts/allocate_synthesis_error.py",
        executable,
        source_path,
    ]
    manifest = {
        "schema": "ucc.qre.freeze-manifest.v1",
        "campaign_schema": SCHEMA,
        "campaign_id": config["campaign_id"],
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "host": platform.node(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "packages": package_versions(),
        "row_count": len(rows),
        "completed_valid_rows": completed_rows,
        "status_counts": frame["status"].value_counts(dropna=False).to_dict(),
        "source_sha256": {
            os.path.relpath(path, ROOT): sha256_path(path) for path in source_files
        },
        "artifacts_sha256": {
            os.path.relpath(path, ROOT): sha256_path(path)
            for path in (
                results_path,
                compilation_path,
                angles_path,
                cache_path,
                frozen_parquet,
                frozen_csv,
            )
        },
        "grid_synth": {
            "executable": os.path.relpath(executable, ROOT),
            "upstream_staq_commit": synthesizer["upstream_staq_commit"],
            "deterministic_patch": synthesizer["deterministic_patch"],
            "flags": synthesizer["flags"],
            "checked_unique_angle_precision_pairs": len(cache.records),
        },
        "old_fixed_per_rotation_proxy_consumed": False,
    }
    manifest_path = resolve(config["output"]["freeze_manifest"])
    manifest_path.write_bytes(canonical_json(manifest))
    run_manifest = run_directory / "campaign_manifest.json"
    run_manifest.write_bytes(canonical_json({
        **manifest,
        "freeze_manifest_sha256": sha256_path(manifest_path),
    }))
    return {
        "rows": len(rows),
        "completed_valid_rows": completed_rows,
        "status_counts": manifest["status_counts"],
        "compiled_inputs": len(compilation_records),
        "grid_synth_pairs": len(cache.records),
        "frozen_parquet": str(frozen_parquet),
        "freeze_manifest": str(manifest_path),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "qre/configs/campaign.yaml",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_campaign(args.config.resolve())
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

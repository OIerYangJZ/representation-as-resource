#!/usr/bin/env python3
"""Fixed-total-error rotation synthesis and frozen surface-code QRE.

Arbitrary rotations are actually synthesized by staq_grid_synth.  Equal per-rotation allocation is
rounded down to a decimal precision so that sum_i epsilon_i <= epsilon_synth.
The resulting Clifford+T counts are scheduled by the explicit surface-code
model below; no old T-count proxy is read or reused.
"""

from __future__ import annotations

import argparse
import csv
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
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "ucc.fixed-budget-qre.v1"
TARGET_BASIS = ["cx", "rx", "ry", "rz", "h"]
SIZES = (4_000, 20_000)
METHODS = ("semantic_ucc", "phase_poly_reference", "materialize_qiskit_opt3")
EPSILON_SYNTH = 1e-3
EPSILON_QEC = 9e-3
PHYSICAL_ERROR = 1e-3
CYCLE_TIME_SECONDS = 1e-6
MAX_FACTORIES = 32
GRID_SYNTH_SEED = 20260801


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_case(target_gates: int):
    from qiskit import QuantumCircuit

    width = 4
    block = QuantumCircuit(width)
    for qubit in range(width):
        block.rz(math.pi / (7 + qubit), qubit)
    for control in range(width):
        for target in range(control + 1, width):
            block.cp(math.pi / (11 + control + target), control, target)
    repeats = max(1, (target_gates - 2 * width) // len(block.data))
    circuit = QuantumCircuit(width)
    for qubit in range(width):
        circuit.h(qubit)
    for _ in range(repeats):
        circuit.compose(block, inplace=True)
    for qubit in range(width):
        circuit.h(qubit)
    return circuit


def qubit_index(circuit, qubit) -> int:
    return circuit.find_bit(qubit).index


def canonical_angle(value: float) -> float:
    wrapped = (value + math.pi) % (2 * math.pi) - math.pi
    return 0.0 if abs(wrapped) <= 1e-12 else wrapped


def phase_poly_reference(circuit):
    from qiskit import QuantumCircuit, transpile

    width = circuit.num_qubits
    prefix = circuit.data[:width]
    suffix = circuit.data[-width:]
    if any(item.operation.name != "h" for item in prefix + suffix):
        raise ValueError("missing boundary H layer")
    rz_angles = {qubit: 0.0 for qubit in range(width)}
    cp_angles: dict[tuple[int, int], float] = {}
    for item in circuit.data[width:-width]:
        name = item.operation.name
        qargs = tuple(qubit_index(circuit, q) for q in item.qubits)
        angle = float(item.operation.params[0]) if item.operation.params else 0.0
        if name == "rz" and len(qargs) == 1:
            rz_angles[qargs[0]] += angle
        elif name == "cp" and len(qargs) == 2:
            cp_angles[qargs] = cp_angles.get(qargs, 0.0) + angle
        else:
            raise ValueError(f"unsupported middle-layer gate {name}")
    aggregated = QuantumCircuit(width)
    for qubit in range(width):
        aggregated.h(qubit)
    for qubit, angle in sorted(rz_angles.items()):
        angle = canonical_angle(angle)
        if angle:
            aggregated.rz(angle, qubit)
    for (control, target), angle in sorted(cp_angles.items()):
        angle = canonical_angle(angle)
        if angle:
            aggregated.cp(angle, control, target)
    for qubit in range(width):
        aggregated.h(qubit)
    return transpile(aggregated, basis_gates=TARGET_BASIS, optimization_level=0)


def compile_method(circuit, method: str):
    from qiskit import transpile

    if method == "phase_poly_reference":
        return phase_poly_reference(circuit)
    if method == "materialize_qiskit_opt3":
        return transpile(
            circuit,
            basis_gates=TARGET_BASIS,
            optimization_level=3,
            layout_method="trivial",
            routing_method="none",
        )
    if method == "semantic_ucc":
        import ucc

        return ucc.compile(
            circuit,
            return_format="qiskit",
            target_gateset=set(TARGET_BASIS),
        )
    raise ValueError(method)


def circuit_metrics(circuit) -> dict[str, int]:
    counts = circuit.count_ops()
    return {
        "logical_qubits": int(circuit.num_qubits),
        "output_gates": int(sum(counts.values())),
        "output_depth": int(circuit.depth()),
        "cx_count": int(counts.get("cx", 0)),
        "rotation_count": int(sum(counts.get(name, 0) for name in ("rx", "ry", "rz"))),
    }


def verify_compiled_equivalence(source, compiled) -> bool:
    """Dense four-qubit cross-check, invariant under global phase."""
    from qiskit.quantum_info import Operator

    return bool(Operator(source).equiv(Operator(compiled), rtol=1e-8, atol=1e-8))


def rotation_histogram(circuit) -> Counter[str]:
    result: Counter[str] = Counter()
    for item in circuit.data:
        if item.operation.name not in {"rx", "ry", "rz"}:
            continue
        ratio = float(item.operation.params[0]) / math.pi
        # Hex serialization is the exact identity of the measured IEEE value;
        # the decimal below is supplied to the GMP synthesizer at 18 digits.
        key = f"{ratio:.18g}|{float(item.operation.params[0]).hex()}"
        result[key] += 1
    return result


def synthesize_rotations(
    histogram: Counter[str],
    executable: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rotation_count = sum(histogram.values())
    if rotation_count == 0:
        return {
            "rotation_count": 0,
            "decimal_precision": None,
            "epsilon_per_rotation": 0.0,
            "allocated_total_error": 0.0,
            "t_count": 0,
            "synthesis_runtime_s": 0.0,
        }, []
    decimal_precision = int(math.ceil(math.log10(rotation_count / EPSILON_SYNTH)))
    epsilon_per_rotation = 10.0 ** (-decimal_precision)
    if rotation_count * epsilon_per_rotation > EPSILON_SYNTH:
        raise AssertionError("total synthesis error allocation exceeded")
    records = []
    total_t = 0
    total_runtime = 0.0
    for key, multiplicity in sorted(histogram.items()):
        ratio_text, angle_hex = key.split("|", 1)
        command = [
            str(executable),
            ratio_text,
            "--precision",
            str(decimal_precision),
            "--check",
            "--details",
        ]
        started = time.perf_counter()
        completed = subprocess.run(command, capture_output=True, text=True, timeout=600)
        runtime_s = time.perf_counter() - started
        if completed.returncode != 0:
            raise RuntimeError(
                f"grid synthesis failed for {ratio_text}: {completed.stderr[-1000:]}"
            )
        if "Check flag = 1" not in completed.stderr:
            raise RuntimeError(
                f"grid synthesis checker did not pass for {ratio_text}: "
                f"{completed.stderr[-1000:]}"
            )
        gate_tokens = completed.stdout.split()
        t_per_instance = sum(token == "T" for token in gate_tokens)
        if t_per_instance <= 0:
            # Clifford-exact angles legitimately need no T gates.
            t_per_instance = 0
        total_t += multiplicity * t_per_instance
        total_runtime += runtime_s
        error_match = re.search(r"^error = ([^\n]+)$", completed.stderr, re.MULTILINE)
        reported_error = float(error_match.group(1)) if error_match else 0.0
        if reported_error > epsilon_per_rotation:
            raise RuntimeError(
                f"reported synthesis error {reported_error} exceeds "
                f"allocation {epsilon_per_rotation}"
            )
        records.append(
            {
                "angle_over_pi": ratio_text,
                "angle_ieee_hex": angle_hex,
                "multiplicity": multiplicity,
                "decimal_precision": decimal_precision,
                "t_per_instance": t_per_instance,
                "t_subtotal": multiplicity * t_per_instance,
                "reported_synthesis_error": reported_error,
                "runtime_s": runtime_s,
                "stdout_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
                "stderr_sha256": hashlib.sha256(completed.stderr.encode()).hexdigest(),
                "checker_enabled": True,
            }
        )
    return {
        "rotation_count": rotation_count,
        "decimal_precision": decimal_precision,
        "epsilon_per_rotation": epsilon_per_rotation,
        "allocated_total_error": rotation_count * epsilon_per_rotation,
        "t_count": total_t,
        "max_reported_synthesis_error": max(
            record["reported_synthesis_error"] for record in records
        ),
        "synthesis_runtime_s": total_runtime,
    }, records


def logical_error_per_cycle(distance: int) -> float:
    return 0.1 * (100.0 * PHYSICAL_ERROR) ** ((distance + 1) / 2)


def surface_code_qre(metrics: dict[str, int], t_count: int) -> dict[str, Any]:
    logical_qubits = metrics["logical_qubits"]
    logical_depth = metrics["output_depth"]
    distance = 3
    while True:
        rough_cycles = max(1, logical_depth + 11 * t_count)
        failure_bound = logical_qubits * rough_cycles * logical_error_per_cycle(distance)
        if failure_bound <= EPSILON_QEC:
            break
        distance += 2
        if distance > 99:
            raise RuntimeError("could not meet QEC failure budget")
    factories = 0 if t_count == 0 else max(
        1,
        min(MAX_FACTORIES, math.ceil(11 * t_count / max(1, logical_depth))),
    )
    data_physical_qubits = 2 * distance * distance * logical_qubits
    factory_physical_qubits = factories * 30 * distance * distance
    t_cycles = 0 if t_count == 0 else math.ceil(t_count / factories) * 11 * distance
    clifford_cycles = logical_depth * distance
    cycles = clifford_cycles + t_cycles
    physical_qubits = data_physical_qubits + factory_physical_qubits
    runtime_seconds = cycles * CYCLE_TIME_SECONDS
    failure_bound = logical_qubits * cycles * logical_error_per_cycle(distance)
    return {
        "code_distance": distance,
        "logical_qubits": logical_qubits,
        "logical_clifford_depth": logical_depth,
        "logical_t_count": t_count,
        "factories": factories,
        "physical_qubits": physical_qubits,
        "cycles": cycles,
        "runtime_seconds": runtime_seconds,
        "spacetime_qubit_seconds": physical_qubits * runtime_seconds,
        "qec_failure_union_bound": failure_bound,
        "qec_failure_budget": EPSILON_QEC,
    }


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fields = [
        "requested_gates", "method", "status", "correctness_passed", "logical_qubits",
        "output_gates", "output_depth", "cx_count", "rotation_count",
        "decimal_precision", "allocated_total_error",
        "max_reported_synthesis_error", "t_count",
        "code_distance", "physical_qubits", "cycles", "factories",
        "runtime_seconds", "spacetime_qubit_seconds", "compile_runtime_s",
        "synthesis_runtime_s",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fields})


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid-synth", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.grid_synth.is_file() or not os.access(args.grid_synth, os.X_OK):
        raise SystemExit("--grid-synth must be an executable staq_grid_synth binary")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    detail: list[dict[str, Any]] = []
    for requested in SIZES:
        source = build_case(requested)
        for method in METHODS:
            started = time.perf_counter()
            compiled = compile_method(source, method)
            compile_runtime = time.perf_counter() - started
            metrics = circuit_metrics(compiled)
            correctness_passed = verify_compiled_equivalence(source, compiled)
            if not correctness_passed:
                raise RuntimeError(
                    f"compiled-output dense cross-check failed for {requested}/{method}"
                )
            synthesis, angle_records = synthesize_rotations(
                rotation_histogram(compiled), args.grid_synth
            )
            qre = surface_code_qre(metrics, int(synthesis["t_count"]))
            row = {
                "requested_gates": requested,
                "method": method,
                "status": "completed",
                "correctness_passed": correctness_passed,
                **metrics,
                **synthesis,
                **qre,
                "compile_runtime_s": compile_runtime,
            }
            rows.append(row)
            detail.append({"row": row, "angle_synthesis": angle_records})
            print(
                f"requested={requested} method={method} rotations={metrics['rotation_count']} "
                f"T={synthesis['t_count']} physical={qre['physical_qubits']} "
                f"cycles={qre['cycles']}"
            )
    csv_path = args.output_dir / "fixed_budget_qre.csv"
    write_csv(rows, csv_path)
    json_path = args.output_dir / "fixed_budget_qre.json"
    payload = {
        "schema": SCHEMA,
        "host": platform.node(),
        "python": platform.python_version(),
        "packages": {
            name: importlib.metadata.version(name)
            for name in ("qiskit", "ucc", "numpy")
        },
        "methods": list(METHODS),
        "sizes": list(SIZES),
        "error_budget": {
            "epsilon_synth": EPSILON_SYNTH,
            "allocation": "equal, conservatively rounded to decimal precision",
            "epsilon_qec": EPSILON_QEC,
            "total_bound": EPSILON_SYNTH + EPSILON_QEC,
        },
        "surface_code_model": {
            "physical_error": PHYSICAL_ERROR,
            "logical_error_per_cycle": "0.1*(100*p)^((d+1)/2)",
            "data_patch_physical_qubits": "2*d^2 per logical qubit",
            "15_to_1_factory_physical_qubits": "30*d^2",
            "factory_period_cycles": "11*d",
            "cycle_time_seconds": CYCLE_TIME_SECONDS,
            "max_factories": MAX_FACTORIES,
        },
        "synthesizer": {
            "path": str(args.grid_synth.resolve()),
            "sha256": sha256(args.grid_synth),
            "flags": ["--check", "--details"],
            "candidate_search_seed": GRID_SYNTH_SEED,
            "source": "tools/grid_synth_deterministic.cpp",
            "source_sha256": sha256(
                args.grid_synth.parent / "grid_synth_deterministic.cpp"
            ),
            "upstream_staq_commit": "a2acd39e60ed0e5f1978fa530df7e1e0c7cedf7a",
            "artifact_patch": "replace std::random_device with seed 20260801",
        },
        "correctness": {
            "compiled_output": "Qiskit Operator.equiv, rtol=atol=1e-8",
            "rotation_synthesis": "staq --check; every stderr record must contain Check flag = 1",
        },
        "rows": rows,
        "details": detail,
    }
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = args.output_dir / "SHA256SUMS"
    manifest_paths = [
        csv_path,
        json_path,
        args.output_dir / "README.md",
        args.grid_synth,
        args.grid_synth.parent / "grid_synth_deterministic.cpp",
        Path(__file__).resolve(),
    ]
    manifest.write_text(
        "".join(
            f"{sha256(path)}  {os.path.relpath(path, args.output_dir)}\n"
            for path in manifest_paths
        ),
        encoding="utf-8",
    )
    print(json.dumps({
        "schema": SCHEMA,
        "rows": len(rows),
        "csv_sha256": sha256(csv_path),
        "json_sha256": sha256(json_path),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

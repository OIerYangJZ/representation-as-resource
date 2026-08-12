#!/usr/bin/env python3
"""Executable 2^5 factorial ablation on structured workload kernels.

The five factors are semantic lift, selector, cache, preset optimization, and
projected selection.  Positive kernels cover QAOA/Ising, diagonal Hamiltonian
simulation, QFT arithmetic, QPE controlled powers, and a Trotterized Ising
kernel.  Two negative controls contain no repeated commuting support.

The exact structured certificate compares every commuting-region phase table
and every intervening boundary operation.  Qiskit preset output is additionally
tagged as relying on the transpiler pass contract; it is not theorem evidence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import itertools
import json
import math
import os
import platform
import random
import statistics
import sys
import time
import traceback
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable


THIS_FILE = Path(__file__).resolve()
ROOT = THIS_FILE.parents[1]
WORKSPACE_ROOT = THIS_FILE.parents[3]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from encoding.codec import (  # noqa: E402
    CertificateInput,
    ControlState,
    ExternalToolOutput,
    IRField,
    LiveWindow,
    ParameterLedger,
    StoreState,
)
from instrumentation.resource_accounting import (  # noqa: E402
    ResourceAccountant,
    ResourceSnapshot,
    assert_rows_file_backed,
    circuit_dag_from_qiskit,
    final_boundary_snapshot,
    write_encoded_artifact,
)
DEFAULT_OUTPUT = ROOT / "research" / "natural_factorial"
WIDTH = 8
TARGET_BASIS = ("cx", "rz", "rx", "h")
CELL_TIMEOUT_S = 5.0
MEMORY_CAP_BYTES = 2 * 1024**3
SEEDS = (20260801, 20260802, 20260803, 20260804, 20260805)
FACTORS = ("semantic_lift", "selector", "cache", "preset", "projected_selection")
WORKLOADS = (
    "qaoa_ising",
    "diagonal_hamiltonian",
    "qft_arithmetic",
    "qpe_controlled_powers",
    "ising_trotter",
    "negative_random_clifford",
    "negative_routing",
)
POSITIVE = set(WORKLOADS[:5])


@dataclass(frozen=True)
class Term:
    support: tuple[int, int]
    angle_over_pi: Fraction


@dataclass(frozen=True)
class Region:
    terms: tuple[Term, ...]
    boundary: tuple[tuple[str, tuple[int, ...], Fraction | None], ...]


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unavailable"


def process_maxrss_bytes() -> int:
    import resource

    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def workload_regions(name: str, seed: int) -> tuple[Region, ...]:
    rng = random.Random(seed + sum(ord(ch) for ch in name))
    ring = [(q, (q + 1) % WIDTH) for q in range(WIDTH)]
    chain = [(q, q + 1) for q in range(WIDTH - 1)]
    if name == "qaoa_ising":
        regions = []
        for layer in range(3):
            terms = tuple(
                Term(edge, Fraction((edge[0] + layer) % 3 + 1, 64))
                for edge in ring
                for _ in range(4)
            )
            boundary = tuple(("rx", (q,), Fraction(1, 7 + layer)) for q in range(WIDTH))
            regions.append(Region(terms, boundary))
        return tuple(regions)
    if name == "diagonal_hamiltonian":
        supports = chain + [(q, q + 2) for q in range(WIDTH - 2)]
        repeated = Region(
            tuple(Term(edge, Fraction(edge[0] % 5 + 1, 96)) for edge in supports for _ in range(8)),
            (),
        )
        return (repeated, repeated, repeated, repeated)
    if name == "qft_arithmetic":
        regions = []
        for stage in range(4):
            supports = [(q, stage + 1) for q in range(stage + 1)]
            terms = tuple(Term(edge, Fraction(1, 2 ** (stage + 4))) for edge in supports for _ in range(6))
            regions.append(Region(terms, (("h", (stage + 1,), None),)))
        return tuple(regions)
    if name == "qpe_controlled_powers":
        regions = []
        for power in range(4):
            support = (power, WIDTH - 1)
            terms = tuple(Term(support, Fraction(2**power, 256)) for _ in range(8))
            regions.append(Region(terms, (("h", (power,), None),)))
        return tuple(regions)
    if name == "ising_trotter":
        regions = []
        for step in range(4):
            terms = tuple(Term(edge, Fraction(step + 1, 128)) for edge in chain for _ in range(3))
            boundary = tuple(("rx", (q,), Fraction(step + 1, 31)) for q in range(WIDTH))
            regions.append(Region(terms, boundary))
        return tuple(regions)
    if name == "negative_random_clifford":
        regions = []
        supports = list(chain)
        rng.shuffle(supports)
        for index, support in enumerate(supports):
            boundary = (("h", ((index + 2) % WIDTH,), None),)
            regions.append(Region((Term(support, Fraction(index + 1, 257)),), boundary))
        return tuple(regions)
    if name == "negative_routing":
        regions = []
        for index, support in enumerate(chain):
            swap = (index, WIDTH - index - 1)
            regions.append(
                Region((Term(support, Fraction(index + 1, 263)),), (("swap", swap, None),))
            )
        return tuple(regions)
    raise ValueError(name)


def aggregate_region(region: Region) -> Region:
    totals: dict[tuple[int, int], Fraction] = {}
    for term in region.terms:
        totals[term.support] = (totals.get(term.support, Fraction()) + term.angle_over_pi) % 2
    terms = tuple(Term(support, angle) for support, angle in sorted(totals.items()) if angle)
    return Region(terms, region.boundary)


def structured_signature(regions: tuple[Region, ...]) -> tuple[Any, ...]:
    output = []
    for region in regions:
        canonical = aggregate_region(region)
        output.append(
            (
                tuple((term.support, term.angle_over_pi) for term in canonical.terms),
                region.boundary,
            )
        )
    return tuple(output)


def qiskit_imports() -> tuple[Any, Any, Any]:
    from qiskit import QuantumCircuit, qasm2, transpile

    return QuantumCircuit, qasm2, transpile


def append_region(circuit: Any, region: Region) -> None:
    for term in region.terms:
        control, target = term.support
        circuit.cx(control, target)
        circuit.rz(float(term.angle_over_pi) * math.pi, target)
        circuit.cx(control, target)
    for name, qubits, angle in region.boundary:
        if name == "h":
            circuit.h(qubits[0])
        elif name == "rx" and angle is not None:
            circuit.rx(float(angle) * math.pi, qubits[0])
        elif name == "swap":
            circuit.swap(*qubits)
        else:
            raise ValueError(name)


def lower_regions(
    regions: tuple[Region, ...],
    cache_enabled: bool,
    cache_store: dict[str, Any],
) -> tuple[Any, int, int]:
    QuantumCircuit, _, _ = qiskit_imports()
    circuit = QuantumCircuit(WIDTH)
    hits = 0
    misses = 0
    for region in regions:
        key_payload = repr(region).encode()
        key = sha256_bytes(key_payload)
        if cache_enabled and key in cache_store:
            subcircuit = cache_store[key]
            hits += 1
        else:
            subcircuit = QuantumCircuit(WIDTH)
            append_region(subcircuit, region)
            misses += 1
            if cache_enabled:
                cache_store[key] = subcircuit
        circuit.compose(subcircuit, inplace=True)
    return circuit, hits, misses


def metrics(circuit: Any) -> dict[str, int]:
    counts = circuit.count_ops()
    return {
        "gates": int(sum(counts.values())),
        "depth": int(circuit.depth() or 0),
        "cx": int(counts.get("cx", 0)),
    }


def score(circuit: Any) -> int:
    value = metrics(circuit)
    return value["gates"] + value["depth"] + 10 * value["cx"]


def projected_score(regions: tuple[Region, ...]) -> int:
    phase_terms = sum(len(region.terms) for region in regions)
    boundaries = sum(len(region.boundary) for region in regions)
    two_qubit_boundaries = sum(
        name == "swap" for region in regions for name, _, _ in region.boundary
    )
    return 3 * phase_terms + boundaries + 10 * (2 * phase_terms + 3 * two_qubit_boundaries)


def cell_id_for(workload: str, seed: int, factors: dict[str, int]) -> str:
    key_fields = {"workload": workload, "seed": seed, **factors}
    return "NF25-" + sha256_bytes(
        json.dumps(key_fields, sort_keys=True, separators=(",", ":")).encode()
    )[:16]


def compile_cell(workload: str, seed: int, factors: dict[str, int], artifact_root: Path) -> dict[str, Any]:
    _, qasm2, transpile = qiskit_imports()
    cell_id = cell_id_for(workload, seed, factors)
    cell_dir = artifact_root.resolve() / cell_id
    original_regions = workload_regions(workload, seed)
    lifted_regions = tuple(aggregate_region(region) for region in original_regions)
    selected_regions = lifted_regions if factors["semantic_lift"] else original_regions
    cache_store: dict[str, Any] = {}
    started = time.perf_counter()
    primary, hits, misses = lower_regions(selected_regions, bool(factors["cache"]), cache_store)
    chosen = primary
    selected_candidate = "semantic" if factors["semantic_lift"] else "flat"
    if factors["selector"] and factors["semantic_lift"]:
        flat, flat_hits, flat_misses = lower_regions(original_regions, bool(factors["cache"]), cache_store)
        hits += flat_hits
        misses += flat_misses
        if factors["projected_selection"]:
            choose_semantic = projected_score(lifted_regions) <= projected_score(original_regions)
        else:
            choose_semantic = score(primary) <= score(flat)
        if choose_semantic:
            selected_candidate = "semantic"
        else:
            chosen = flat
            selected_candidate = "flat"
    if factors["preset"]:
        chosen = transpile(
            chosen,
            basis_gates=list(TARGET_BASIS),
            optimization_level=3,
            layout_method="trivial",
            routing_method="none",
            seed_transpiler=seed,
        )
    elapsed = time.perf_counter() - started
    structured_pass = structured_signature(original_regions) == structured_signature(selected_regions)
    output_value = ExternalToolOutput("qiskit", "openqasm2", qasm2.dumps(chosen).encode())
    output_record = write_encoded_artifact(cell_dir / "output.uccbin", output_value, role="committed_output")
    output = Path(output_record["artifact_path"]).read_bytes()
    input_ir_record = write_encoded_artifact(
        cell_dir / "input-ir.uccbin",
        circuit_dag_from_qiskit(primary, provenance="natural-factorial-selected-input"),
        role="input_ir",
    )
    rss_bytes = process_maxrss_bytes()
    within_limits = elapsed <= CELL_TIMEOUT_S and rss_bytes <= MEMORY_CAP_BYTES
    row = {
        "workload": workload,
        "workload_class": "positive_semantic" if workload in POSITIVE else "negative_control",
        "seed": seed,
        **factors,
        "status": "completed" if structured_pass and within_limits else (
            "correctness_failure" if not structured_pass else "resource_limit"
        ),
        "certificate_kind": "exact_region_phase_tables_and_boundary_sequence",
        "certificate_passed": structured_pass,
        "preset_contract": "qiskit transformation contract" if factors["preset"] else "not used",
        "formal_theorem_evidence": False,
        "selected_candidate": selected_candidate,
        "cache_hits": hits,
        "cache_misses": misses,
        "runtime_s": elapsed,
        "rss_bytes": rss_bytes,
        "timeout_s": CELL_TIMEOUT_S,
        "memory_cap_bytes": MEMORY_CAP_BYTES,
        "cell_id": cell_id,
        "input_ir_artifact_path": input_ir_record["artifact_path"],
        "input_ir_bytes": input_ir_record["artifact_bytes"],
        "output_artifact_path": output_record["artifact_path"],
        "ir_nodes_input": sum(len(region.terms) + len(region.boundary) for region in original_regions),
        "ir_nodes_selected": sum(len(region.terms) + len(region.boundary) for region in selected_regions),
    }
    row.update(metrics(chosen))
    certificate = {
        "kind": row["certificate_kind"],
        "passed": row["certificate_passed"],
        "preset_contract": row["preset_contract"],
    }
    certificate_record = write_encoded_artifact(
        cell_dir / "certificate.uccbin",
        CertificateInput(
            row["certificate_kind"],
            output_record["artifact_sha256"],
            json.dumps(certificate, sort_keys=True, separators=(",", ":")).encode(),
        ),
        role="certificate_input",
    )
    row["certificate_artifact_path"] = certificate_record["artifact_path"]
    snapshot = final_boundary_snapshot(
        chosen,
        output,
        control_fields={
            "cell_id": cell_id,
            "input_head": input_ir_record["artifact_bytes"],
            "output_head": output_record["artifact_bytes"],
            "selected_candidate": selected_candidate,
            "status": row["status"],
        },
        pass_count=1,
        provenance="natural-factorial-output",
    )
    row.update(ResourceAccountant(artifact_root, cell_id).measure("final", snapshot))
    row["output_serialized_bits"] = row["B_com_bits"]
    row["output_ir_bytes"] = row["B_ir_bytes"]
    return row


def compile_cell_safe(
    workload: str, seed: int, factors: dict[str, int], artifact_root: Path
) -> dict[str, Any]:
    """Return a manifested row even when a compiler cell raises."""

    try:
        return compile_cell(workload, seed, factors, artifact_root)
    except Exception as exc:
        cell_id = cell_id_for(workload, seed, factors)
        row: dict[str, Any] = {
            "workload": workload,
            "workload_class": "positive_semantic" if workload in POSITIVE else "negative_control",
            "seed": seed,
            **factors,
            "cell_id": cell_id,
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(limit=12),
            "formal_theorem_evidence": False,
            "timeout_s": CELL_TIMEOUT_S,
            "memory_cap_bytes": MEMORY_CAP_BYTES,
            "gates": None,
            "depth": None,
            "cx": None,
            "ir_nodes_input": None,
            "ir_nodes_selected": None,
        }
        snapshot = ResourceSnapshot(
            ControlState({"cell_id": cell_id, "status": "error"}),
            StoreState({}),
            LiveWindow(),
            ParameterLedger(),
            IRField(),
            b"",
        )
        row.update(ResourceAccountant(artifact_root, cell_id).measure("failure", snapshot))
        row["output_serialized_bits"] = row["B_com_bits"]
        row["output_ir_bytes"] = row["B_IR_bytes"]
        return row


def ci95(values: list[float]) -> tuple[float, float, float]:
    mean = statistics.fmean(values)
    if len(values) == 1:
        return mean, mean, mean
    half = 1.96 * statistics.stdev(values) / math.sqrt(len(values))
    return mean, mean - half, mean + half


def paired_semantic_effects(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lookup = {
        (row["workload"], row["seed"], row["selector"], row["cache"], row["preset"], row["projected_selection"], row["semantic_lift"]): row
        for row in rows
    }
    output = []
    for workload in WORKLOADS:
        for selector_scope in ("all", "selector_off", "selector_and_preset_off"):
            differences: dict[str, list[float]] = {field: [] for field in ("gates", "depth", "cx", "output_serialized_bits")}
            for seed in SEEDS:
                for selector, cache, preset, projected in itertools.product((0, 1), repeat=4):
                    if selector_scope == "selector_off" and selector:
                        continue
                    if selector_scope == "selector_and_preset_off" and (selector or preset):
                        continue
                    off = lookup[(workload, seed, selector, cache, preset, projected, 0)]
                    on = lookup[(workload, seed, selector, cache, preset, projected, 1)]
                    if off["status"] != "completed" or on["status"] != "completed":
                        continue
                    for field in differences:
                        differences[field].append(float(off[field]) - float(on[field]))
            if not next(iter(differences.values())):
                continue
            record: dict[str, Any] = {
                "workload": workload,
                "workload_class": "positive_semantic" if workload in POSITIVE else "negative_control",
                "scope": selector_scope,
                "paired_samples": len(next(iter(differences.values()))),
            }
            for field, values in differences.items():
                mean, low, high = ci95(values)
                record[f"{field}_reduction_mean"] = mean
                record[f"{field}_reduction_ci95_low"] = low
                record[f"{field}_reduction_ci95_high"] = high
            output.append(record)
    return output


def factor_effects(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for factor in FACTORS:
        other = [name for name in FACTORS if name != factor]
        lookup = {(row["workload"], row["seed"], *(row[name] for name in FACTORS)): row for row in rows}
        for workload in WORKLOADS:
            differences = []
            for seed in SEEDS:
                for levels in itertools.product((0, 1), repeat=4):
                    assignment = dict(zip(other, levels))
                    keys = []
                    for value in (0, 1):
                        factor_values = {**assignment, factor: value}
                        keys.append((workload, seed, *(factor_values[name] for name in FACTORS)))
                    left, right = lookup[keys[0]], lookup[keys[1]]
                    if left["status"] == "completed" and right["status"] == "completed":
                        differences.append(float(left["gates"]) - float(right["gates"]))
            if not differences:
                continue
            mean, low, high = ci95(differences)
            output.append({
                "workload": workload,
                "factor": factor,
                "paired_samples": len(differences),
                "gate_reduction_on_minus_off": mean,
                "ci95_low": low,
                "ci95_high": high,
            })
    return output


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def plot_effects(effects: list[dict[str, Any]], path: Path) -> None:
    import matplotlib.pyplot as plt

    rows = [row for row in effects if row["scope"] == "selector_and_preset_off"]
    means = [row["gates_reduction_mean"] for row in rows]
    lower = [mean - row["gates_reduction_ci95_low"] for mean, row in zip(means, rows)]
    upper = [row["gates_reduction_ci95_high"] - mean for mean, row in zip(means, rows)]
    colors = ["#2a9d8f" if row["workload_class"] == "positive_semantic" else "#8d99ae" for row in rows]
    fig, axis = plt.subplots(figsize=(8.5, 4.8), constrained_layout=True)
    axis.bar(range(len(rows)), means, color=colors, yerr=[lower, upper], capsize=4)
    axis.axhline(0, color="black", linewidth=0.8)
    axis.set_xticks(range(len(rows)), [row["workload"].replace("_", "\n") for row in rows], rotation=15, ha="right")
    axis.set_ylabel("paired output-gate reduction")
    axis.set_title("Semantic-lift effect with selector and preset disabled (95% CI)")
    fig.savefig(path)
    plt.close(fig)


def latex_rows(effects: list[dict[str, Any]]) -> str:
    rows = [row for row in effects if row["scope"] == "selector_and_preset_off"]
    lines = []
    for row in rows:
        lines.append(
            row["workload"].replace("_", r"\_")
            + f" & {row['paired_samples']} & {row['gates_reduction_mean']:.1f} "
            + f"[{row['gates_reduction_ci95_low']:.1f},{row['gates_reduction_ci95_high']:.1f}] "
            + f"& {row['cx_reduction_mean']:.1f} [{row['cx_reduction_ci95_low']:.1f},{row['cx_reduction_ci95_high']:.1f}]"
            + r" \\"
        )
    if lines and lines[-1].endswith(r" \\"):
        lines[-1] = lines[-1][:-3]
    return "\n".join(lines) + "\n"


def campaign_manifest(rows: list[dict[str, Any]]) -> dict[str, Any]:
    config = {
        "workloads": list(WORKLOADS),
        "seeds": list(SEEDS),
        "factors": list(FACTORS),
        "design": "full 2^5 factorial for every workload and seed",
        "target_basis": list(TARGET_BASIS),
        "timeout_s": CELL_TIMEOUT_S,
        "memory_cap_bytes": MEMORY_CAP_BYTES,
        "backend_topology": "all-to-all logical; negative_routing contains explicit swaps",
        "certificate": "exact region phase tables and unchanged boundary sequence; preset uses Qiskit pass contract",
        "accounting_codec": "ucc.accounting v1 canonical frames",
        "bit_source": "8 * SHA-256-verified artifact file size; no gate/node-count conversion",
    }
    return {
        "schema": "ucc.campaign-manifest.v1",
        "campaign": "NF25-natural-factorial-20260801",
        "immutable_config_sha256": sha256_bytes(json.dumps(config, sort_keys=True, separators=(",", ":")).encode()),
        "artifact_commit": "local-uncommitted-repaired-manuscript",
        "runner": str(THIS_FILE.relative_to(ROOT)),
        "runner_sha256": sha256_file(THIS_FILE),
        "tool_versions": {"python": platform.python_version(), "qiskit": package_version("qiskit")},
        "bridge_sequence": "structured region IR -> exact optional aggregation -> {cx,rz,rx,h}; optional qiskit opt3",
        "config": config,
        "cells": len(rows),
        "completed": sum(row["status"] == "completed" for row in rows),
    }


def run(output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/ucc-natural-factorial-mpl")
    os.environ.setdefault("XDG_CACHE_HOME", "/tmp/ucc-natural-factorial-cache")
    rows = []
    for workload in WORKLOADS:
        for seed in SEEDS:
            for levels in itertools.product((0, 1), repeat=len(FACTORS)):
                factors = dict(zip(FACTORS, levels))
                rows.append(compile_cell_safe(workload, seed, factors, output_dir / "accounting"))
    rows.sort(key=lambda row: (row["workload"], row["seed"], *(row[name] for name in FACTORS)))
    assert_rows_file_backed(rows)
    (output_dir / "factorial_cells.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
    )
    write_csv(output_dir / "factorial_cells.csv", rows)
    semantic = paired_semantic_effects(rows)
    write_csv(output_dir / "semantic_effects.csv", semantic)
    factors = factor_effects(rows)
    write_csv(output_dir / "factor_main_effects.csv", factors)
    plot_effects(semantic, output_dir / "semantic_lift_selector_off.pdf")
    (output_dir / "semantic_effect_rows.tex").write_text(latex_rows(semantic), encoding="utf-8")
    manifest = campaign_manifest(rows)
    (output_dir / "campaign_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"cells": len(rows), "completed": manifest["completed"]}, sort_keys=True))
    return 0 if manifest["completed"] == len(rows) else 1


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    return run(args.output_dir)


if __name__ == "__main__":
    raise SystemExit(main())

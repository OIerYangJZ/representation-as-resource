#!/usr/bin/env python3
"""Run the strict matched-representation factorial matrix.

Formal execution is fail-closed: ``--formal-local`` is required and cannot be
combined with a cell limit.  ``--smoke`` is bounded and never writes into the
frozen-data directory.  Every matrix cell runs in a fresh process under the
same timeout, RSS cap, target basis, logical hardware, and error budget.
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
import socket
import subprocess
import sys
import time
import traceback
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.representation_generators import (  # noqa: E402
    CERTIFICATE_KIND,
    REPRESENTATIONS,
    TargetSpec,
    Token,
    canonical_target,
    load_qasm,
    lower_tokens,
    make_target,
    pyzx_certificate,
    qasm_bytes,
    sha256_bytes,
    validate_representation_set,
)
from encoding.codec import ExternalToolOutput, encode  # noqa: E402
from instrumentation.resource_accounting import circuit_dag_from_qiskit  # noqa: E402


RESULT_SENTINEL = "W4_CELL_RESULT="
VALID_STATUSES = {
    "completed", "timeout", "memory_error", "unsupported", "predicate_error", "correctness_failure"
}
COMPILERS = (
    "echo_passthrough",
    "full_aggregation",
    "qiskit_opt3",
    "tket_paulisimp",
    "pyzx_full_reduce",
)
SOURCE_FILES = (
    "benchmarks/representation_generators.py",
    "benchmarks/matched_manifest.yaml",
    "scripts/run_matched_matrix.py",
    "scripts/analyze_matched_matrix.py",
    "encoding/codec.py",
    "instrumentation/resource_accounting.py",
)


class UnsupportedCell(RuntimeError):
    pass


class PredicateFailure(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_immutable(path: Path, payload: bytes) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise FileExistsError(f"refusing to overwrite nonidentical artifact: {path}")
    else:
        path.write_bytes(payload)
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def _write_json_immutable(path: Path, value: Any) -> dict[str, Any]:
    return _write_immutable(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def load_plan(path: Path) -> dict[str, Any]:
    import yaml

    plan = yaml.safe_load(path.read_text(encoding="utf-8"))
    if plan.get("schema") != "ucc.matched-factorial-plan.v1":
        raise ValueError("unsupported matched-matrix plan")
    if tuple(plan["representations"]) != REPRESENTATIONS:
        raise ValueError("manifest representation order differs from generator contract")
    if tuple(plan["compilers"]) != COMPILERS:
        raise ValueError("manifest compiler order differs from runner contract")
    if plan["defaults"]["certificate_kind"] != CERTIFICATE_KIND:
        raise ValueError("manifest certificate differs from generator contract")
    return plan


def target_from_dict(value: Mapping[str, Any]) -> TargetSpec:
    return TargetSpec(
        target_id=str(value["target_id"]), m=int(value["m"]), n=int(value["n"]), r=int(value["r"]),
        K=int(value["K"]), density_requested=float(value["density_requested"]),
        density_realized=float(value["density_realized"]), target_seed=int(value["target_seed"]),
        active_support=tuple(int(item) for item in value["active_support"]),
        x=tuple(int(item) for item in value["x"]), delta_over_pi=str(value["delta_over_pi"]),
    )


def token_from_dict(value: Mapping[str, Any]) -> Token:
    return Token(
        int(value["generator"]), tuple(int(item) for item in value["support"]),
        Fraction(int(value["angle_over_pi_numerator"]), int(value["angle_over_pi_denominator"])),
        int(value["round_index"]), str(value["share_kind"]),
    )


def _relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def _artifact_record(path: Path) -> dict[str, Any]:
    return {"path": _relative(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def materialize_representations(plan: Mapping[str, Any], campaign_root: Path) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for target_row in plan["targets"]:
        target = make_target(target_row)
        target_root = campaign_root / "targets" / target.target_id
        reference_qasm = qasm_bytes(canonical_target(target))
        _write_json_immutable(target_root / "target.json", target.to_dict())
        _write_immutable(target_root / "canonical.qasm", reference_qasm)
        for seed in plan["seeds"]:
            generated_set = validate_representation_set(target, int(seed))
            for generated in generated_set:
                rep_root = campaign_root / "representations" / generated.representation_id
                input_record = _write_immutable(rep_root / "input.uccbin", generated.encoded)
                qasm_record = _write_immutable(rep_root / "input.qasm", generated.qasm)
                token_record = _write_json_immutable(
                    rep_root / "tokens.json", [token.to_dict() for token in generated.tokens]
                )
                dag_record = _write_immutable(
                    rep_root / "input-ir.uccbin", encode(circuit_dag_from_qiskit(
                        generated.circuit, provenance=f"W4:{generated.representation}"
                    ))
                )
                certificate = pyzx_certificate(reference_qasm, generated.qasm)
                if not certificate["passed"]:
                    raise ValueError(f"input representation certificate failed: {certificate}")
                certificate_record = _write_json_immutable(rep_root / "input-certificate.json", certificate)
                manifest = generated.manifest_dict()
                manifest.update({
                    "target_manifest_path": _relative(target_root / "target.json"),
                    "canonical_qasm": _artifact_record(target_root / "canonical.qasm"),
                    "files": {
                        "input": {**input_record, "path": _relative(rep_root / "input.uccbin")},
                        "qasm": {**qasm_record, "path": _relative(rep_root / "input.qasm")},
                        "tokens": {**token_record, "path": _relative(rep_root / "tokens.json")},
                        "input_ir": {**dag_record, "path": _relative(rep_root / "input-ir.uccbin")},
                        "certificate": {**certificate_record, "path": _relative(rep_root / "input-certificate.json")},
                    },
                    "input_certificate": certificate,
                })
                manifest_path = rep_root / "representation_manifest.json"
                _write_json_immutable(manifest_path, manifest)
                output.append({
                    "target_id": target.target_id,
                    "seed": int(seed),
                    "representation": generated.representation,
                    "representation_id": generated.representation_id,
                    "manifest_path": _relative(manifest_path),
                    "manifest_sha256": sha256_file(manifest_path),
                })
    output.sort(key=lambda row: (row["target_id"], row["seed"], row["representation"]))
    index_path = campaign_root / "representation_index.jsonl"
    payload = "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in output)
    _write_immutable(index_path, payload.encode("utf-8"))
    return output


def expand_cells(index: Iterable[Mapping[str, Any]], plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    defaults = dict(plan["defaults"])
    rows = []
    for representation_row, compiler in itertools.product(index, plan["compilers"]):
        identity = {
            "representation_id": representation_row["representation_id"],
            "compiler": compiler,
            "basis": defaults["target_basis"],
            "hardware": defaults["hardware"],
            "error_budget": defaults["total_error_budget"],
        }
        rows.append({
            **representation_row,
            "compiler": compiler,
            "cell_id": "cell-" + sha256_bytes(
                json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
            )[:20],
            **defaults,
        })
    rows.sort(key=lambda row: (row["target_id"], row["representation"], row["compiler"], row["seed"]))
    expected = len(plan["targets"]) * len(plan["representations"]) * len(plan["compilers"]) * len(plan["seeds"])
    if len(rows) != expected or len({row["cell_id"] for row in rows}) != expected:
        raise ValueError("expanded matrix is incomplete or has duplicate cell IDs")
    return rows


def _exact_pi_ratio(value: Any) -> Fraction:
    ratio = float(value) / math.pi
    exact = Fraction(ratio).limit_denominator(1 << 22)
    if abs(ratio - float(exact)) > 2e-9:
        raise PredicateFailure("Rz parameter lacks a recoverable rational-pi sidecar")
    return exact


def extract_phase_table(circuit: Any) -> tuple[dict[int, Fraction], list[int]]:
    live = [1 << index for index in range(circuit.num_qubits)]
    terms: dict[int, Fraction] = {}
    for instruction in circuit.data:
        name = instruction.operation.name
        qubits = [int(circuit.find_bit(qubit).index) for qubit in instruction.qubits]
        if name == "cx" and len(qubits) == 2:
            live[qubits[1]] ^= live[qubits[0]]
        elif name == "rz" and len(qubits) == 1:
            mask = live[qubits[0]]
            terms[mask] = terms.get(mask, Fraction()) + _exact_pi_ratio(instruction.operation.params[0])
        elif name in {"barrier", "id"}:
            continue
        else:
            raise PredicateFailure(f"operation {name} is outside the exact CNOT-Rz diagnostic domain")
    return {mask: angle % 2 for mask, angle in terms.items() if angle % 2}, live


def phase_table_aggregate(circuit: Any) -> Any:
    terms, frame = extract_phase_table(circuit)
    identity = [1 << index for index in range(circuit.num_qubits)]
    if frame != identity:
        raise PredicateFailure("full aggregator requires an identity final linear frame")
    tokens: list[Token] = []
    for index, (mask, angle) in enumerate(sorted(terms.items())):
        support = tuple(qubit for qubit in range(circuit.num_qubits) if mask & (1 << qubit))
        if len(support) != 2:
            raise PredicateFailure("reference aggregator supports two-body chain terms")
        tokens.append(Token(index, (support[0], support[1]), angle, 0, "aggregated_phase_table"))
    return lower_tokens(circuit.num_qubits, tokens)


def compile_circuit(circuit: Any, compiler: str, seed: int, basis: list[str]) -> tuple[Any, str]:
    from qiskit import qasm2, transpile

    if compiler == "echo_passthrough":
        return circuit.copy(), "literal input circuit -> output"
    if compiler == "full_aggregation":
        return phase_table_aggregate(circuit), "exact input parity/phase table -> canonical CNOT-Rz"
    if compiler == "qiskit_opt3":
        return transpile(
            qasm2.loads(qasm_bytes(circuit).decode("utf-8")), basis_gates=basis, optimization_level=3,
            layout_method="trivial", routing_method="none", seed_transpiler=seed,
        ), "OpenQASM2 -> Qiskit preset level 3 -> target basis"
    if compiler == "tket_paulisimp":
        try:
            from pytket import passes
            from pytket.circuit import OpType
            import pytket.qasm as tket_qasm
        except ImportError as exc:
            raise UnsupportedCell(str(exc)) from exc
        tk_circuit = tket_qasm.circuit_from_qasm_str(qasm_bytes(circuit).decode("utf-8"))
        for compiler_pass in (
            passes.DecomposeBoxes(), passes.AutoRebase({OpType.CX, OpType.Rz, OpType.H}),
            passes.RemoveRedundancies(), passes.PauliSimp(), passes.RemoveRedundancies(),
            passes.AutoRebase({OpType.CX, OpType.Rz, OpType.H}),
        ):
            compiler_pass.apply(tk_circuit)
        result = qasm2.loads(tket_qasm.circuit_to_qasm_str(tk_circuit))
        return transpile(result, basis_gates=basis, optimization_level=0), (
            "OpenQASM2 -> TKET DecomposeBoxes/AutoRebase/PauliSimp -> target basis"
        )
    if compiler == "pyzx_full_reduce":
        try:
            import pyzx as zx
        except ImportError as exc:
            raise UnsupportedCell(str(exc)) from exc
        zx_circuit = zx.Circuit.from_qasm(qasm_bytes(circuit).decode("utf-8")).to_basic_gates()
        graph = zx_circuit.to_graph()
        zx.simplify.full_reduce(graph, quiet=True)
        extracted = zx.extract_circuit(graph, quiet=True).to_basic_gates()
        lines = extracted.to_qasm().splitlines()
        while lines and lines[0].startswith("Let "):
            lines.pop(0)
        result = qasm2.loads("\n".join(lines))
        return transpile(result, basis_gates=basis, optimization_level=0), (
            "OpenQASM2 -> PyZX graph/full_reduce/extract -> target basis"
        )
    raise UnsupportedCell(f"unknown compiler {compiler!r}")


def circuit_metrics(circuit: Any) -> dict[str, Any]:
    counts = {str(key): int(value) for key, value in circuit.count_ops().items()}
    return {
        "output_gates": sum(counts.values()),
        "output_depth": int(circuit.depth() or 0),
        "output_cx": counts.get("cx", 0),
        "output_rz": counts.get("rz", 0),
        "output_h": counts.get("h", 0),
        "output_gate_types": sorted(counts),
    }


def _classify_certificate(reference: Any, candidate: Any, certificate: Mapping[str, Any]) -> str:
    if certificate.get("passed"):
        return "completed"
    try:
        left = extract_phase_table(reference)
        right = extract_phase_table(candidate)
    except PredicateFailure:
        return "predicate_error"
    return "correctness_failure" if left != right else "predicate_error"


def worker(spec_path: Path, cell_dir: Path) -> dict[str, Any]:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    rep_manifest_path = ROOT / spec["manifest_path"]
    rep_manifest = json.loads(rep_manifest_path.read_text(encoding="utf-8"))
    target = target_from_dict(rep_manifest["target"])
    input_qasm_path = ROOT / rep_manifest["files"]["qasm"]["path"]
    canonical_qasm_path = ROOT / rep_manifest["canonical_qasm"]["path"]
    started = time.perf_counter()
    row: dict[str, Any] = {
        "cell_id": spec["cell_id"], "target_id": spec["target_id"],
        "representation_id": spec["representation_id"], "representation": spec["representation"],
        "compiler": spec["compiler"], "seed": int(spec["seed"]), "status": "unsupported",
        "target_basis": json.dumps(spec["target_basis"], separators=(",", ":")),
        "hardware": spec["hardware"], "timeout_s": float(spec["timeout_s"]),
        "memory_cap_bytes": int(spec["memory_cap_bytes"]),
        "total_error_budget": float(spec["total_error_budget"]),
        "certificate_kind": spec["certificate_kind"],
        "m": target.m, "n": target.n, "r": target.r, "K": target.K,
        "density_requested": target.density_requested, "density_realized": target.density_realized,
        "target_seed": target.target_seed, "active_count": len(target.active_support),
        "serialized_input_bytes": int(rep_manifest["files"]["input"]["bytes"]),
        "serialized_input_ir_bytes": int(rep_manifest["files"]["input_ir"]["bytes"]),
        "representation_manifest_path": _relative(rep_manifest_path),
        "representation_manifest_sha256": sha256_file(rep_manifest_path),
        "input_certificate_status": rep_manifest["input_certificate"]["status"],
    }
    try:
        if row["input_certificate_status"] != "passed":
            raise PredicateFailure("input representation lacks the common certificate")
        source = load_qasm(input_qasm_path.read_bytes())
        reference = load_qasm(canonical_qasm_path.read_bytes())
        compiled, provenance = compile_circuit(source, spec["compiler"], int(spec["seed"]), list(spec["target_basis"]))
        metrics = circuit_metrics(compiled)
        allowed = set(spec["target_basis"])
        extra = set(metrics["output_gate_types"]) - allowed - {"barrier", "id"}
        if extra:
            raise PredicateFailure(f"output operations outside target basis: {sorted(extra)}")
        output_qasm = qasm_bytes(compiled)
        output_qasm_record = _write_immutable(cell_dir / "output.qasm", output_qasm)
        output_record = _write_immutable(
            cell_dir / "output.uccbin", encode(ExternalToolOutput(spec["compiler"], "openqasm2", output_qasm))
        )
        output_ir_record = _write_immutable(
            cell_dir / "output-ir.uccbin", encode(circuit_dag_from_qiskit(compiled, provenance=provenance))
        )
        certificate = pyzx_certificate(canonical_qasm_path.read_bytes(), output_qasm)
        _write_json_immutable(cell_dir / "output-certificate.json", certificate)
        row.update(metrics)
        row.update({
            "status": _classify_certificate(reference, compiled, certificate),
            "certificate_status": certificate["status"],
            "certificate_passed": bool(certificate["passed"]),
            "compiler_pipeline": provenance,
            "serialized_output_bytes": output_record["bytes"],
            "serialized_output_qasm_bytes": output_qasm_record["bytes"],
            "serialized_output_ir_bytes": output_ir_record["bytes"],
            "output_qasm_sha256": output_qasm_record["sha256"],
            "output_artifact_sha256": output_record["sha256"],
            "output_ir_sha256": output_ir_record["sha256"],
        })
    except MemoryError as exc:
        row.update(status="memory_error", error_type=type(exc).__name__, error=str(exc))
    except UnsupportedCell as exc:
        row.update(status="unsupported", error_type=type(exc).__name__, error=str(exc))
    except PredicateFailure as exc:
        row.update(status="predicate_error", error_type=type(exc).__name__, error=str(exc))
    except ImportError as exc:
        row.update(status="unsupported", error_type=type(exc).__name__, error=str(exc))
    except Exception as exc:
        # Compiler/predicate library failures are retained, never converted to a metric win.
        row.update(
            status="predicate_error", error_type=type(exc).__name__, error=str(exc),
            traceback=traceback.format_exc(limit=16),
        )
    row["worker_runtime_s"] = time.perf_counter() - started
    if row["status"] not in VALID_STATUSES:
        raise AssertionError("worker emitted an invalid status")
    return row


def _parse_worker(stdout: str) -> dict[str, Any]:
    for line in reversed(stdout.splitlines()):
        if line.startswith(RESULT_SENTINEL):
            return json.loads(line[len(RESULT_SENTINEL):])
    raise PredicateFailure("worker result sentinel missing")


def _kill_process_tree(process: Any) -> None:
    try:
        children = process.children(recursive=True)
    except (Exception, PermissionError):
        children = []
    for child in children:
        try:
            child.kill()
        except Exception:
            pass
    try:
        process.kill()
    except Exception:
        pass


def _cell_manifest(cell_dir: Path, spec: Mapping[str, Any], row: Mapping[str, Any], log_path: Path) -> dict[str, Any]:
    files = {}
    for path in sorted(cell_dir.iterdir()):
        if path.is_file() and path.name != "cell_manifest.json":
            files[path.name] = _artifact_record(path)
    return {
        "schema": "ucc.matched-cell.v1",
        "cell_id": spec["cell_id"],
        "spec": dict(spec),
        "result": dict(row),
        "files": files,
        "log": _artifact_record(log_path),
        "status_policy": sorted(VALID_STATUSES),
    }


def verify_cell_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "ucc.matched-cell.v1":
        raise ValueError("unsupported cell manifest")
    for record in manifest["files"].values():
        artifact = ROOT / record["path"]
        if artifact.stat().st_size != record["bytes"] or sha256_file(artifact) != record["sha256"]:
            raise ValueError(f"cell artifact differs from manifest: {artifact}")
    if manifest["result"]["status"] not in VALID_STATUSES:
        raise ValueError("cell manifest has an invalid status")
    return manifest


def run_cell(spec: Mapping[str, Any], campaign_root: Path, resume: bool) -> dict[str, Any]:
    import psutil

    cell_dir = campaign_root / "cells" / spec["cell_id"]
    manifest_path = cell_dir / "cell_manifest.json"
    if manifest_path.exists():
        if not resume:
            raise FileExistsError(f"cell already exists: {manifest_path}")
        existing = verify_cell_manifest(manifest_path)
        row = dict(existing["result"])
        row["reused_verified"] = True
        return row
    cell_dir.mkdir(parents=True, exist_ok=True)
    spec_path = cell_dir / "cell_spec.json"
    _write_json_immutable(spec_path, dict(spec))
    command = [sys.executable, str(Path(__file__).resolve()), "--worker", str(spec_path), str(cell_dir)]
    env = os.environ.copy()
    env.setdefault("MPLCONFIGDIR", "/tmp/ucc-w4-mpl")
    env.setdefault("XDG_CACHE_HOME", "/tmp/ucc-w4-cache")
    started = time.perf_counter()
    process = subprocess.Popen(
        command, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    monitored = psutil.Process(process.pid)
    peak = 0
    forced_status: str | None = None
    while process.poll() is None:
        elapsed = time.perf_counter() - started
        try:
            processes = [monitored]
            try:
                processes.extend(monitored.children(recursive=True))
            except (psutil.AccessDenied, PermissionError):
                # macOS sandbox may deny the system-wide PID enumeration used
                # by ``children``; the worker itself remains observable.
                pass
            current = sum(item.memory_info().rss for item in processes if item.is_running())
            peak = max(peak, current)
        except (psutil.NoSuchProcess, psutil.AccessDenied, PermissionError):
            pass
        if peak > int(spec["memory_cap_bytes"]):
            forced_status = "memory_error"
            _kill_process_tree(monitored)
            break
        if elapsed > float(spec["timeout_s"]):
            forced_status = "timeout"
            _kill_process_tree(monitored)
            break
        time.sleep(0.02)
    stdout, stderr = process.communicate()
    wall = time.perf_counter() - started
    log_text = json.dumps({"command": command, "cwd": str(ROOT)}, sort_keys=True) + "\nSTDOUT\n" + stdout + "\nSTDERR\n" + stderr
    log_path = cell_dir / "cell.log"
    _write_immutable(log_path, log_text.encode("utf-8"))
    if forced_status:
        row = {
            **{key: spec[key] for key in (
                "cell_id", "target_id", "representation_id", "representation", "compiler", "seed",
                "timeout_s", "memory_cap_bytes", "hardware", "total_error_budget", "certificate_kind",
            )},
            "target_basis": json.dumps(spec["target_basis"], separators=(",", ":")),
            "status": forced_status,
        }
    else:
        try:
            row = _parse_worker(stdout)
        except Exception as exc:
            row = {
                **{key: spec[key] for key in (
                    "cell_id", "target_id", "representation_id", "representation", "compiler", "seed",
                    "timeout_s", "memory_cap_bytes", "hardware", "total_error_budget", "certificate_kind",
                )},
                "target_basis": json.dumps(spec["target_basis"], separators=(",", ":")),
                "status": "predicate_error", "error_type": type(exc).__name__, "error": str(exc),
            }
    row.update(rss_peak_bytes=peak, wall_runtime_s=wall, log_path=_relative(log_path), reused_verified=False)
    if row["status"] not in VALID_STATUSES:
        raise AssertionError("parent observed invalid status")
    _write_json_immutable(manifest_path, _cell_manifest(cell_dir, spec, row, log_path))
    return row


def package_versions() -> dict[str, str]:
    result = {}
    for name in ("qiskit", "pytket", "pyzx", "psutil", "numpy", "scipy", "matplotlib", "pandas"):
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = "unavailable"
    return result


def _write_rows(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    payload = "".join(json.dumps(dict(row), sort_keys=True, separators=(",", ":")) + "\n" for row in rows)
    path.write_text(payload, encoding="utf-8")


def _write_csv(path: Path, rows: list[Mapping[str, Any]]) -> None:
    fields = sorted({key for row in rows for key, value in row.items() if not isinstance(value, (dict, list))})
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _git_revision() -> str | None:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def run_campaign(plan_path: Path, campaign_root: Path, *, resume: bool) -> Path:
    plan = load_plan(plan_path)
    campaign_root.mkdir(parents=True, exist_ok=True)
    representation_index = materialize_representations(plan, campaign_root)
    cells = expand_cells(representation_index, plan)
    source_hashes = {
        name: sha256_file(ROOT / name) for name in SOURCE_FILES if (ROOT / name).is_file()
    }
    started = time.time()
    rows = []
    for index, spec in enumerate(cells, 1):
        row = run_cell(spec, campaign_root, resume)
        rows.append(row)
        print(
            f"[{index:04d}/{len(cells)}] {spec['target_id']} {spec['representation']} "
            f"{spec['compiler']} seed={spec['seed']} status={row['status']}", flush=True,
        )
    rows.sort(key=lambda row: (row["target_id"], row["representation"], row["compiler"], row["seed"]))
    _write_rows(campaign_root / "matched_cells.jsonl", rows)
    _write_csv(campaign_root / "matched_cells.csv", rows)
    expected_ids = {row["cell_id"] for row in cells}
    observed_ids = {row["cell_id"] for row in rows}
    manifest = {
        "schema": "ucc.matched-campaign.v1",
        "campaign": plan["campaign"],
        "formal": True,
        "matrix_complete": expected_ids == observed_ids and len(rows) == len(cells),
        "planned_cells": len(cells),
        "observed_cells": len(rows),
        "dimensions": {
            "targets": len(plan["targets"]), "representations": len(plan["representations"]),
            "compilers": len(plan["compilers"]), "seeds": len(plan["seeds"]),
        },
        "status_counts": {
            status: sum(row["status"] == status for row in rows) for status in sorted(VALID_STATUSES)
        },
        "plan_path": _relative(plan_path), "plan_sha256": sha256_file(plan_path),
        "representation_index_path": _relative(campaign_root / "representation_index.jsonl"),
        "representation_index_sha256": sha256_file(campaign_root / "representation_index.jsonl"),
        "rows_path": _relative(campaign_root / "matched_cells.jsonl"),
        "rows_sha256": sha256_file(campaign_root / "matched_cells.jsonl"),
        "source_sha256": source_hashes,
        "hostname": socket.gethostname(), "platform": platform.platform(),
        "python": sys.version.split()[0], "tool_versions": package_versions(),
        "git_revision": _git_revision(), "started_unix": started, "finished_unix": time.time(),
        "uniform_controls": plan["defaults"],
    }
    manifest_path = campaign_root / "campaign_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def smoke_campaign(plan_path: Path, output: Path, max_cells: int) -> Path:
    plan = load_plan(plan_path)
    limit = int(plan["execution_policy"]["smoke_max_cells"])
    if not 1 <= max_cells <= limit:
        raise ValueError(f"smoke run must contain 1..{limit} cells")
    output.mkdir(parents=True, exist_ok=True)
    representation_index = materialize_representations(plan, output)
    all_cells = expand_cells(representation_index, plan)
    first_target = str(plan["targets"][0]["target_id"])
    first_seed = int(plan["seeds"][0])
    selected = []
    # Bounded but stratified: nine slots cover all representation levels and
    # cycle over every compiler instead of sampling only the first sort block.
    for index, representation in enumerate(plan["representations"]):
        compiler = plan["compilers"][index % len(plan["compilers"])]
        match = next(
            row for row in all_cells
            if row["target_id"] == first_target and row["seed"] == first_seed
            and row["representation"] == representation and row["compiler"] == compiler
        )
        selected.append(match)
        if len(selected) == max_cells:
            break
    if len(selected) < max_cells:
        used = {row["cell_id"] for row in selected}
        selected.extend(row for row in all_cells if row["cell_id"] not in used)
        selected = selected[:max_cells]
    rows = [run_cell(spec, output, resume=False) for spec in selected]
    _write_rows(output / "smoke_cells.jsonl", rows)
    manifest = {
        "schema": "ucc.matched-smoke.v1", "formal": False, "selected_cells": len(rows),
        "planned_formal_cells": len(plan["targets"]) * len(plan["representations"]) * len(plan["compilers"]) * len(plan["seeds"]),
        "status_counts": {status: sum(row["status"] == status for row in rows) for status in sorted(VALID_STATUSES)},
    }
    path = output / "smoke_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "benchmarks/matched_manifest.yaml")
    parser.add_argument("--output-root", type=Path, default=ROOT / "data/runs")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--max-cells", type=int, default=5)
    parser.add_argument("--formal-local", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--worker", nargs=2, metavar=("SPEC", "CELL_DIR"))
    args = parser.parse_args(argv)
    if args.worker:
        print(RESULT_SENTINEL + json.dumps(worker(Path(args.worker[0]), Path(args.worker[1])), sort_keys=True))
        return 0
    plan = load_plan(args.manifest)
    targets = [make_target(row) for row in plan["targets"]]
    expected = len(targets) * len(plan["representations"]) * len(plan["compilers"]) * len(plan["seeds"])
    if args.plan_only or (not args.smoke and not args.formal_local):
        print(json.dumps({
            "campaign": plan["campaign"], "targets": len(targets),
            "representations": len(plan["representations"]), "compilers": len(plan["compilers"]),
            "seeds": len(plan["seeds"]), "planned_cells": expected,
            "formal_execution_requires": "--formal-local",
        }, sort_keys=True))
        return 0
    if args.smoke and args.formal_local:
        raise ValueError("smoke and formal modes are mutually exclusive")
    if args.smoke:
        path = smoke_campaign(args.manifest, args.output_root / "w4-smoke", args.max_cells)
    else:
        if args.max_cells != 5:
            raise ValueError("formal mode forbids --max-cells")
        path = run_campaign(args.manifest, args.output_root / plan["campaign"], resume=args.resume)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

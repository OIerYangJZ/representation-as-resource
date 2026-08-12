#!/usr/bin/env python3
"""Run W5 native/unified external baselines with explicit bridge accounting."""

from __future__ import annotations

import argparse
import csv
import importlib.metadata
import itertools
import json
import os
import platform
import socket
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.representation_generators import (  # noqa: E402
    CERTIFICATE_KIND,
    Token,
    load_qasm,
    lower_tokens,
    pyzx_certificate,
    qasm_bytes,
    sha256_bytes,
)
from encoding.codec import ExternalToolOutput, encode  # noqa: E402
from instrumentation.resource_accounting import circuit_dag_from_qiskit  # noqa: E402
from scripts.run_matched_matrix import (  # noqa: E402
    PredicateFailure,
    UnsupportedCell,
    circuit_metrics,
    extract_phase_table,
    sha256_file,
)


RESULT_SENTINEL = "W5_BASELINE_RESULT="
VALID_STATUSES = {
    "completed", "timeout", "memory_error", "unsupported", "predicate_error", "correctness_failure"
}
CONFIG_DIR = ROOT / "baselines/configs"
FAMILY_CONFIGS = (
    "qiskit_local.yaml", "tket_paulisimp.yaml", "pyzx_full_reduce.yaml", "authors_reference.yaml"
)
SOURCE_FILES = (
    "baselines/BASELINE_REGISTRY.md",
    "baselines/configs/campaign.yaml",
    *(f"baselines/configs/{name}" for name in FAMILY_CONFIGS),
    "scripts/run_external_baselines.py",
    "scripts/audit_bridge_loss.py",
    "benchmarks/representation_generators.py",
    "scripts/run_matched_matrix.py",
    "encoding/codec.py",
    "instrumentation/resource_accounting.py",
)


def load_yaml(path: Path) -> dict[str, Any]:
    import yaml

    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return value


def load_campaign_config(path: Path = CONFIG_DIR / "campaign.yaml") -> dict[str, Any]:
    value = load_yaml(path)
    if value.get("schema") != "ucc.external-baseline-campaign-plan.v1":
        raise ValueError("unsupported external baseline campaign plan")
    if value["certificate_kind"] != CERTIFICATE_KIND:
        raise ValueError("W5 campaign must use the W4 common certificate")
    return value


def load_baseline_configs() -> list[dict[str, Any]]:
    output = []
    for filename in FAMILY_CONFIGS:
        path = CONFIG_DIR / filename
        family = load_yaml(path)
        if family.get("schema") != "ucc.external-baseline-family.v1":
            raise ValueError(f"unsupported baseline family: {path}")
        for config in family["configs"]:
            row = {
                **config,
                "tool": family["tool"], "package": family["package"],
                "category": family["category"], "semantic_capable": bool(family["semantic_capable"]),
                "bridge": family["bridge"], "config_path": str(path.relative_to(ROOT)),
                "config_sha256": sha256_file(path),
            }
            output.append(row)
    if len(output) != 8 or len({row["id"] for row in output}) != len(output):
        raise ValueError("expected eight unique native/unified baseline configurations")
    for tool in {row["tool"] for row in output}:
        modes = {row["mode"] for row in output if row["tool"] == tool}
        if modes != {"recommended_native", "unified_target_basis"}:
            raise ValueError(f"tool {tool} lacks its native/unified pair")
    return sorted(output, key=lambda row: row["id"])


def _write_immutable(path: Path, payload: bytes) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise FileExistsError(f"refusing to overwrite nonidentical artifact: {path}")
    else:
        path.write_bytes(payload)
    return {"path": _relative(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def _write_json_immutable(path: Path, value: Any) -> dict[str, Any]:
    return _write_immutable(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def _relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def _artifact(path: Path) -> dict[str, Any]:
    return {"path": _relative(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _metrics(prefix: str, circuit: Any) -> dict[str, Any]:
    raw = circuit_metrics(circuit)
    return {
        f"{prefix}_gates": raw["output_gates"], f"{prefix}_depth": raw["output_depth"],
        f"{prefix}_cx": raw["output_cx"], f"{prefix}_rz": raw["output_rz"],
        f"{prefix}_h": raw["output_h"],
        f"{prefix}_gate_types": json.dumps(raw["output_gate_types"], separators=(",", ":")),
    }


def _tket_payload(circuit: Any) -> bytes:
    commands = []
    for command in circuit.get_commands():
        commands.append({
            "op": command.op.type.name,
            "params": [str(item) for item in command.op.params],
            "args": [str(item) for item in command.args],
        })
    return _json_bytes({"qubits": circuit.n_qubits, "bits": circuit.n_bits, "commands": commands})


def _tket_metrics(prefix: str, circuit: Any) -> dict[str, Any]:
    commands = circuit.get_commands()
    names = [command.op.type.name for command in commands]
    return {
        f"{prefix}_gates": len(commands), f"{prefix}_depth": int(circuit.depth()),
        f"{prefix}_cx": sum(name == "CX" for name in names),
        f"{prefix}_rz": sum(name == "Rz" for name in names),
        f"{prefix}_h": sum(name == "H" for name in names),
        f"{prefix}_gate_types": json.dumps(sorted(set(names)), separators=(",", ":")),
    }


def _pyzx_metrics(prefix: str, circuit: Any) -> dict[str, Any]:
    names = [type(gate).__name__ for gate in circuit.gates]
    return {
        f"{prefix}_gates": len(circuit.gates), f"{prefix}_depth": int(circuit.depth()),
        f"{prefix}_cx": sum(name == "CNOT" for name in names),
        f"{prefix}_rz": sum(name in {"ZPhase", "Z"} for name in names),
        f"{prefix}_h": sum(name == "HAD" for name in names),
        f"{prefix}_gate_types": json.dumps(sorted(set(names)), separators=(",", ":")),
    }


def _pyzx_qasm(circuit: Any) -> bytes:
    lines = circuit.to_qasm().splitlines()
    while lines and lines[0].startswith("Let "):
        lines.pop(0)
    return ("\n".join(lines) + "\n").encode("utf-8")


def _phase_table_payload(circuit: Any) -> tuple[bytes, int]:
    terms, frame = extract_phase_table(circuit)
    identity = [1 << index for index in range(circuit.num_qubits)]
    if frame != identity:
        raise UnsupportedCell("authors reference requires an identity final linear frame")
    payload = {
        "schema": "ucc.authors-phase-polynomial.v1",
        "width": circuit.num_qubits,
        "global_phase": "ignored",
        "terms": [
            {"parity_mask": mask, "coefficient_over_pi": [angle.numerator, angle.denominator]}
            for mask, angle in sorted(terms.items())
        ],
        "final_linear_frame": frame,
    }
    return _json_bytes(payload), len(terms)


def _lower_phase_table(circuit: Any) -> Any:
    terms, frame = extract_phase_table(circuit)
    if frame != [1 << index for index in range(circuit.num_qubits)]:
        raise UnsupportedCell("authors reference requires an identity final linear frame")
    tokens = []
    for index, (mask, angle) in enumerate(sorted(terms.items())):
        support = tuple(q for q in range(circuit.num_qubits) if mask & (1 << q))
        if len(support) != 2:
            raise UnsupportedCell("authors reference is frozen for two-body phase gadgets")
        tokens.append(Token(index, (support[0], support[1]), angle, 0, "authors_exact_phase_table"))
    return lower_tokens(circuit.num_qubits, tokens)


def _classify_certificate(reference: Any, candidate: Any, certificate: Mapping[str, Any]) -> str:
    if certificate.get("passed"):
        return "completed"
    try:
        left = extract_phase_table(reference)
        right = extract_phase_table(candidate)
    except PredicateFailure:
        return "predicate_error"
    return "correctness_failure" if left != right else "predicate_error"


def bridge_input(input_qasm: bytes, tool: str) -> tuple[Any, Any, bytes, bytes, dict[str, Any]]:
    """Return native object, post-bridge Qiskit circuit, native bytes, QASM, metrics."""

    from qiskit import qasm2

    if tool == "qiskit":
        post = qasm2.loads(input_qasm.decode("utf-8"))
        payload = qasm_bytes(post)
        return post, post, payload, payload, _metrics("post_bridge_native", post)
    if tool == "pytket":
        try:
            import pytket.qasm as tket_qasm
        except ImportError as exc:
            raise UnsupportedCell(str(exc)) from exc
        native = tket_qasm.circuit_from_qasm_str(input_qasm.decode("utf-8"))
        native_payload = _tket_payload(native)
        bridge_qasm = tket_qasm.circuit_to_qasm_str(native).encode("utf-8")
        post = qasm2.loads(bridge_qasm.decode("utf-8"))
        return native, post, native_payload, bridge_qasm, _tket_metrics("post_bridge_native", native)
    if tool == "pyzx":
        try:
            import pyzx as zx
        except ImportError as exc:
            raise UnsupportedCell(str(exc)) from exc
        native = zx.Circuit.from_qasm(input_qasm.decode("utf-8")).to_basic_gates()
        native_payload = native.to_graph().to_json().encode("utf-8")
        bridge_qasm = _pyzx_qasm(native)
        post = qasm2.loads(bridge_qasm.decode("utf-8"))
        return native, post, native_payload, bridge_qasm, _pyzx_metrics("post_bridge_native", native)
    if tool == "authors_exact_phase_table":
        post = qasm2.loads(input_qasm.decode("utf-8"))
        native_payload, term_count = _phase_table_payload(post)
        metrics = {
            "post_bridge_native_gates": term_count, "post_bridge_native_depth": 1 if term_count else 0,
            "post_bridge_native_cx": 0, "post_bridge_native_rz": term_count,
            "post_bridge_native_h": 0, "post_bridge_native_gate_types": '["phase_gadget"]',
        }
        return post, post, native_payload, qasm_bytes(post), metrics
    raise UnsupportedCell(f"unknown bridge tool {tool!r}")


def compile_baseline(post_qasm: bytes, config: Mapping[str, Any], seed: int, target_basis: list[str]) -> tuple[Any, bytes, bytes, dict[str, Any], str]:
    """Return certificate circuit, native bytes, certificate QASM, native metrics, provenance."""

    from qiskit import qasm2, transpile

    tool = config["tool"]
    unified = config["mode"] == "unified_target_basis"
    if tool == "qiskit":
        source = qasm2.loads(post_qasm.decode("utf-8"))
        output = transpile(
            source, basis_gates=target_basis if unified else None, optimization_level=3,
            layout_method="trivial", routing_method="none", seed_transpiler=seed,
        )
        native_qasm = qasm_bytes(output)
        payload = (
            encode(circuit_dag_from_qiskit(output, provenance=config["id"]))
            if unified
            else encode(ExternalToolOutput("qiskit", "openqasm2-native", native_qasm))
        )
        return output, payload, native_qasm, _metrics("native_output", output), "Qiskit preset level 3"
    if tool == "pytket":
        try:
            from pytket import passes
            from pytket.circuit import OpType
            import pytket.qasm as tket_qasm
        except ImportError as exc:
            raise UnsupportedCell(str(exc)) from exc
        output = tket_qasm.circuit_from_qasm_str(post_qasm.decode("utf-8"))
        sequence = [passes.DecomposeBoxes(), passes.RemoveRedundancies(), passes.PauliSimp(), passes.RemoveRedundancies()]
        if unified:
            sequence += [passes.AutoRebase({OpType.CX, OpType.Rz, OpType.H}, allow_swaps=False), passes.RemoveRedundancies()]
        for compiler_pass in sequence:
            compiler_pass.apply(output)
        native_payload = _tket_payload(output)
        certificate_qasm = tket_qasm.circuit_to_qasm_str(output).encode("utf-8")
        certificate_circuit = qasm2.loads(certificate_qasm.decode("utf-8"))
        return certificate_circuit, native_payload, certificate_qasm, _tket_metrics("native_output", output), (
            "TKET PauliSimp native" if not unified else "TKET PauliSimp plus unified AutoRebase"
        )
    if tool == "pyzx":
        try:
            import pyzx as zx
        except ImportError as exc:
            raise UnsupportedCell(str(exc)) from exc
        source = zx.Circuit.from_qasm(post_qasm.decode("utf-8")).to_basic_gates()
        graph = source.to_graph()
        zx.simplify.full_reduce(graph, quiet=True)
        native_payload = graph.to_json().encode("utf-8")
        extracted = zx.extract_circuit(graph, quiet=True).to_basic_gates()
        certificate_qasm = _pyzx_qasm(extracted)
        certificate_circuit = qasm2.loads(certificate_qasm.decode("utf-8"))
        native_metrics = _pyzx_metrics("native_output", extracted)
        if unified:
            certificate_circuit = transpile(certificate_circuit, basis_gates=target_basis, optimization_level=0)
            certificate_qasm = qasm_bytes(certificate_circuit)
        return certificate_circuit, native_payload, certificate_qasm, native_metrics, (
            "PyZX full_reduce/extract native" if not unified else "PyZX full_reduce/extract plus unified Qiskit rebase"
        )
    if tool == "authors_exact_phase_table":
        source = qasm2.loads(post_qasm.decode("utf-8"))
        native_payload, term_count = _phase_table_payload(source)
        certificate_circuit = _lower_phase_table(source)
        native_metrics = {
            "native_output_gates": term_count, "native_output_depth": 1 if term_count else 0,
            "native_output_cx": 0, "native_output_rz": term_count, "native_output_h": 0,
            "native_output_gate_types": '["phase_gadget"]',
        }
        return certificate_circuit, native_payload, qasm_bytes(certificate_circuit), native_metrics, (
            "authors exact phase-polynomial IR with certificate lowering" if not unified
            else "authors exact phase-polynomial extraction and CX-Rz-CX lowering"
        )
    raise UnsupportedCell(f"unknown compiler tool {tool!r}")


def _config_version(config: Mapping[str, Any]) -> str:
    if config["package"] == "repository":
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else "unavailable"
    try:
        return importlib.metadata.version(config["package"])
    except importlib.metadata.PackageNotFoundError:
        return "unavailable"


def _dist_commit(package: str) -> tuple[str | None, str]:
    if package == "repository":
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False)
        return (result.stdout.strip() or None, "repository_git_revision")
    try:
        dist = importlib.metadata.distribution(package)
    except importlib.metadata.PackageNotFoundError:
        return None, "package_unavailable"
    for file in dist.files or ():
        if str(file).endswith("direct_url.json"):
            try:
                value = json.loads((Path(dist.locate_file(file))).read_text(encoding="utf-8"))
                commit = value.get("vcs_info", {}).get("commit_id")
                if commit:
                    return str(commit), "installed_direct_url_vcs_info"
            except Exception:
                pass
    return None, "installed_distribution_has_no_vcs_commit_metadata"


def expand_specs(campaign: Mapping[str, Any], configs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    index_path = ROOT / campaign["input_index"]
    inputs = [json.loads(line) for line in index_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(inputs) != 216:
        raise ValueError("W5 requires the complete 216-input W4 representation index")
    output = []
    for input_row, config in itertools.product(inputs, configs):
        identity = {"representation_id": input_row["representation_id"], "baseline_id": config["id"]}
        output.append({
            **input_row, **config,
            "baseline_id": config["id"],
            "cell_id": "w5-" + sha256_bytes(json.dumps(identity, sort_keys=True).encode("utf-8"))[:20],
            "target_basis": campaign["target_basis"], "hardware": campaign["hardware"],
            "timeout_s": campaign["timeout_s"], "memory_cap_bytes": campaign["memory_cap_bytes"],
            "total_error_budget": campaign["total_error_budget"],
            "certificate_kind": campaign["certificate_kind"],
        })
    output.sort(key=lambda row: (row["target_id"], row["representation"], row["baseline_id"], row["seed"]))
    expected = 216 * len(configs)
    if len(output) != expected or len({row["cell_id"] for row in output}) != expected:
        raise ValueError("external baseline matrix is incomplete or duplicated")
    return output


def worker(spec_path: Path, cell_dir: Path) -> dict[str, Any]:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    rep_path = ROOT / spec["manifest_path"]
    rep = json.loads(rep_path.read_text(encoding="utf-8"))
    input_qasm_path = ROOT / rep["files"]["qasm"]["path"]
    canonical_path = ROOT / rep["canonical_qasm"]["path"]
    input_qasm = input_qasm_path.read_bytes()
    canonical_qasm = canonical_path.read_bytes()
    reference = load_qasm(canonical_qasm)
    started = time.perf_counter()
    row: dict[str, Any] = {
        "cell_id": spec["cell_id"], "baseline_id": spec["baseline_id"], "tool": spec["tool"],
        "category": spec["category"], "semantic_capable": bool(spec["semantic_capable"]),
        "config_mode": spec["mode"], "representation": spec["representation"],
        "representation_id": spec["representation_id"], "target_id": spec["target_id"],
        "seed": int(spec["seed"]), "status": "unsupported", "status_stage": "initialization",
        "tool_version": _config_version(spec),
        "pass_sequence": json.dumps(spec["pass_sequence"], separators=(",", ":")),
        "bridge_format": spec["bridge"], "config_path": spec["config_path"],
        "config_sha256": spec["config_sha256"],
        "target_basis": json.dumps(spec["target_basis"], separators=(",", ":")),
        "hardware": spec["hardware"], "timeout_s": float(spec["timeout_s"]),
        "memory_cap_bytes": int(spec["memory_cap_bytes"]),
        "total_error_budget": float(spec["total_error_budget"]),
        "certificate_kind": spec["certificate_kind"],
        "m": int(rep["target"]["m"]), "n": int(rep["target"]["n"]),
        "r": int(rep["target"]["r"]), "K": int(rep["target"]["K"]),
        "density_realized": float(rep["target"]["density_realized"]),
        "pre_bridge_ir_bytes": int(rep["files"]["input_ir"]["bytes"]),
        "serialized_input_bytes": int(rep["files"]["input"]["bytes"]),
        "representation_manifest_path": _relative(rep_path),
        "representation_manifest_sha256": sha256_file(rep_path),
        "input_certificate_status": rep["input_certificate"]["status"],
        "output_basis": json.dumps(spec.get("output_basis", []), separators=(",", ":")),
    }
    row["tool_commit"], row["tool_commit_source"] = _dist_commit(spec["package"])
    try:
        if row["input_certificate_status"] != "passed":
            raise PredicateFailure("input representation lacks the common W4 certificate")
        source = load_qasm(input_qasm)
        row.update(_metrics("pre_bridge", source))
        bridge_started = time.perf_counter()
        _, post, native_bridge_payload, post_qasm, native_bridge_metrics = bridge_input(input_qasm, spec["tool"])
        row["bridge_runtime_s"] = time.perf_counter() - bridge_started
        row.update(native_bridge_metrics)
        row.update(_metrics("post_bridge", post))
        bridge_record = _write_immutable(cell_dir / "bridge-native.bin", native_bridge_payload)
        post_qasm_record = _write_immutable(cell_dir / "post-bridge.qasm", post_qasm)
        post_ir_payload = encode(circuit_dag_from_qiskit(post, provenance=f"W5-bridge:{spec['tool']}"))
        post_ir_record = _write_immutable(cell_dir / "post-bridge-ir.uccbin", post_ir_payload)
        row.update({
            "bridge_serialized_bytes": bridge_record["bytes"],
            "post_bridge_qasm_bytes": post_qasm_record["bytes"],
            "post_bridge_ir_bytes": post_ir_record["bytes"],
            "bridge_delta_gates": row["post_bridge_gates"] - row["pre_bridge_gates"],
            "bridge_delta_depth": row["post_bridge_depth"] - row["pre_bridge_depth"],
            "bridge_delta_cx": row["post_bridge_cx"] - row["pre_bridge_cx"],
            "bridge_delta_ir_bytes": post_ir_record["bytes"] - row["pre_bridge_ir_bytes"],
        })
        bridge_certificate = pyzx_certificate(canonical_qasm, qasm_bytes(post))
        _write_json_immutable(cell_dir / "bridge-certificate.json", bridge_certificate)
        row["bridge_certificate_status"] = bridge_certificate["status"]
        row["bridge_certificate_passed"] = bool(bridge_certificate["passed"])
        bridge_status = _classify_certificate(reference, post, bridge_certificate)
        if bridge_status != "completed":
            row.update(status=bridge_status, status_stage="input_bridge")
            return _finish(row, started)
        compiler_started = time.perf_counter()
        candidate, native_payload, certificate_qasm, native_metrics, provenance = compile_baseline(
            post_qasm, spec, int(spec["seed"]), list(spec["target_basis"])
        )
        row["compiler_runtime_s"] = time.perf_counter() - compiler_started
        row.update(native_metrics)
        native_record = _write_immutable(cell_dir / "native-output.bin", native_payload)
        output_qasm_record = _write_immutable(cell_dir / "certificate-output.qasm", certificate_qasm)
        output_value_record = _write_immutable(
            cell_dir / "certificate-output.uccbin",
            encode(ExternalToolOutput(spec["tool"], "openqasm2", certificate_qasm)),
        )
        try:
            output_ir_payload = encode(circuit_dag_from_qiskit(candidate, provenance=provenance))
            output_ir_encoding = "ucc-circuit-dag"
        except TypeError:
            # Native Qiskit optimization may synthesize matrix-valued instructions.
            # Charge the literal native OpenQASM serialization instead of treating
            # this instrumentation limitation as a compiler failure.
            output_ir_payload = encode(
                ExternalToolOutput(spec["tool"], "openqasm2-certificate", certificate_qasm)
            )
            output_ir_encoding = "external-tool-openqasm2"
        output_ir_record = _write_immutable(cell_dir / "certificate-output-ir.uccbin", output_ir_payload)
        row.update(_metrics("certificate_output", candidate))
        row.update({
            "native_output_ir_bytes": native_record["bytes"],
            "certificate_output_qasm_bytes": output_qasm_record["bytes"],
            "certificate_output_serialized_bytes": output_value_record["bytes"],
            "certificate_output_ir_bytes": output_ir_record["bytes"],
            "certificate_output_ir_encoding": output_ir_encoding,
            "compiler_pipeline": provenance,
        })
        if spec["mode"] == "unified_target_basis":
            allowed = set(spec["target_basis"])
            observed = set(json.loads(row["certificate_output_gate_types"]))
            extra = observed - allowed - {"barrier", "id"}
            if extra:
                raise PredicateFailure(f"unified output has gates outside target basis: {sorted(extra)}")
        certificate_started = time.perf_counter()
        certificate = pyzx_certificate(canonical_qasm, certificate_qasm)
        row["certificate_runtime_s"] = time.perf_counter() - certificate_started
        _write_json_immutable(cell_dir / "output-certificate.json", certificate)
        row.update({
            "output_certificate_status": certificate["status"],
            "output_certificate_passed": bool(certificate["passed"]),
            "status": _classify_certificate(reference, candidate, certificate),
            "status_stage": "completed" if certificate["passed"] else "output_certificate",
        })
    except MemoryError as exc:
        row.update(status="memory_error", status_stage="compiler", error_type=type(exc).__name__, error=str(exc))
    except UnsupportedCell as exc:
        row.update(status="unsupported", status_stage="bridge_or_compiler", error_type=type(exc).__name__, error=str(exc))
    except PredicateFailure as exc:
        row.update(status="predicate_error", status_stage="predicate", error_type=type(exc).__name__, error=str(exc))
    except ImportError as exc:
        row.update(status="unsupported", status_stage="dependency", error_type=type(exc).__name__, error=str(exc))
    except Exception as exc:
        row.update(
            status="predicate_error", status_stage="unexpected_tool_or_predicate_exception",
            error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc(limit=16),
        )
    return _finish(row, started)


def _finish(row: dict[str, Any], started: float) -> dict[str, Any]:
    row["worker_runtime_s"] = time.perf_counter() - started
    if row["status"] not in VALID_STATUSES:
        raise AssertionError("invalid W5 status")
    return row


def _parse_worker(stdout: str) -> dict[str, Any]:
    for line in reversed(stdout.splitlines()):
        if line.startswith(RESULT_SENTINEL):
            return json.loads(line[len(RESULT_SENTINEL):])
    raise PredicateFailure("worker result sentinel missing")


def _kill_process_tree(process: Any) -> None:
    try:
        children = process.children(recursive=True)
    except Exception:
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


def _cell_manifest(cell_dir: Path, spec: Mapping[str, Any], row: Mapping[str, Any]) -> dict[str, Any]:
    files = {
        path.name: _artifact(path) for path in sorted(cell_dir.iterdir())
        if path.is_file() and path.name != "cell_manifest.json"
    }
    return {
        "schema": "ucc.external-baseline-cell.v1", "cell_id": spec["cell_id"],
        "spec": dict(spec), "result": dict(row), "files": files,
        "status_policy": sorted(VALID_STATUSES),
    }


def verify_cell_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != "ucc.external-baseline-cell.v1":
        raise ValueError("unsupported W5 cell manifest")
    for record in value["files"].values():
        artifact = ROOT / record["path"]
        if artifact.stat().st_size != record["bytes"] or sha256_file(artifact) != record["sha256"]:
            raise ValueError(f"W5 cell artifact differs from manifest: {artifact}")
    if value["result"]["status"] not in VALID_STATUSES:
        raise ValueError("W5 cell manifest has invalid status")
    return value


def run_cell(spec: Mapping[str, Any], campaign_root: Path, resume: bool) -> dict[str, Any]:
    import psutil

    cell_dir = campaign_root / "cells" / spec["cell_id"]
    manifest_path = cell_dir / "cell_manifest.json"
    if manifest_path.exists():
        if not resume:
            raise FileExistsError(f"existing W5 cell requires --resume: {manifest_path}")
        row = dict(verify_cell_manifest(manifest_path)["result"])
        row["reused_verified"] = True
        return row
    cell_dir.mkdir(parents=True, exist_ok=True)
    spec_path = cell_dir / "cell_spec.json"
    _write_json_immutable(spec_path, dict(spec))
    command = [sys.executable, str(Path(__file__).resolve()), "--worker", str(spec_path), str(cell_dir)]
    env = os.environ.copy()
    env.setdefault("MPLCONFIGDIR", "/tmp/ucc-w5-mpl")
    env.setdefault("XDG_CACHE_HOME", "/tmp/ucc-w5-cache")
    started = time.perf_counter()
    process = subprocess.Popen(command, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    monitored = psutil.Process(process.pid)
    peak = 0
    forced_status = None
    while process.poll() is None:
        elapsed = time.perf_counter() - started
        try:
            processes = [monitored]
            try:
                processes.extend(monitored.children(recursive=True))
            except (psutil.AccessDenied, PermissionError):
                pass
            peak = max(peak, sum(item.memory_info().rss for item in processes if item.is_running()))
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
    log_record = _write_immutable(
        cell_dir / "cell.log",
        (json.dumps({"command": command, "cwd": str(ROOT)}, sort_keys=True) + "\nSTDOUT\n" + stdout + "\nSTDERR\n" + stderr).encode("utf-8"),
    )
    if forced_status:
        row = {
            **{key: spec[key] for key in (
                "cell_id", "baseline_id", "tool", "category", "semantic_capable", "mode",
                "representation", "representation_id", "target_id", "seed", "timeout_s",
                "memory_cap_bytes", "hardware", "total_error_budget", "certificate_kind",
            )},
            "config_mode": spec["mode"], "target_basis": json.dumps(spec["target_basis"], separators=(",", ":")),
            "status": forced_status, "status_stage": "parent_resource_limit",
        }
    else:
        try:
            row = _parse_worker(stdout)
        except Exception as exc:
            row = {
                **{key: spec[key] for key in (
                    "cell_id", "baseline_id", "tool", "category", "semantic_capable", "representation",
                    "representation_id", "target_id", "seed", "timeout_s", "memory_cap_bytes", "hardware",
                    "total_error_budget", "certificate_kind",
                )},
                "config_mode": spec["mode"], "target_basis": json.dumps(spec["target_basis"], separators=(",", ":")),
                "status": "predicate_error", "status_stage": "worker_protocol",
                "error_type": type(exc).__name__, "error": str(exc),
            }
    row.update(rss_peak_bytes=peak, wall_runtime_s=wall, log_path=log_record["path"], reused_verified=False)
    _write_json_immutable(manifest_path, _cell_manifest(cell_dir, spec, row))
    return row


def _write_rows(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.write_text("".join(json.dumps(dict(row), sort_keys=True, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def _write_csv(path: Path, rows: list[Mapping[str, Any]]) -> None:
    fields = sorted({key for row in rows for key, value in row.items() if not isinstance(value, (dict, list))})
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _git_revision() -> str | None:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def run_campaign(output_root: Path, resume: bool) -> Path:
    campaign = load_campaign_config()
    configs = load_baseline_configs()
    specs = expand_specs(campaign, configs)
    campaign_root = output_root / campaign["campaign"]
    campaign_root.mkdir(parents=True, exist_ok=True)
    rows = []
    started = time.time()
    for index, spec in enumerate(specs, 1):
        row = run_cell(spec, campaign_root, resume)
        rows.append(row)
        print(
            f"[{index:04d}/{len(specs)}] {spec['target_id']} {spec['representation']} "
            f"{spec['baseline_id']} seed={spec['seed']} status={row['status']}", flush=True,
        )
    rows.sort(key=lambda row: (row["target_id"], row["representation"], row["baseline_id"], row["seed"]))
    rows_path = campaign_root / "external_baseline_cells.jsonl"
    _write_rows(rows_path, rows)
    _write_csv(campaign_root / "external_baseline_cells.csv", rows)
    status_counts = {status: sum(row["status"] == status for row in rows) for status in sorted(VALID_STATUSES)}
    config_records = []
    for config in configs:
        commit, source = _dist_commit(config["package"])
        config_records.append({
            **config, "tool_version": _config_version(config), "tool_commit": commit,
            "tool_commit_source": source,
        })
    manifest = {
        "schema": "ucc.external-baseline-campaign.v1", "campaign": campaign["campaign"],
        "formal": True, "matrix_complete": len(rows) == len(specs) and len({row["cell_id"] for row in rows}) == len(specs),
        "planned_cells": len(specs), "observed_cells": len(rows),
        "dimensions": {"representations": 216, "baseline_configs": len(configs)},
        "status_counts": status_counts,
        "campaign_config": campaign, "baseline_configs": config_records,
        "registry_sha256": sha256_file(ROOT / campaign["registry"]),
        "input_index_sha256": sha256_file(ROOT / campaign["input_index"]),
        "rows_path": _relative(rows_path), "rows_sha256": sha256_file(rows_path),
        "source_sha256": {name: sha256_file(ROOT / name) for name in SOURCE_FILES if (ROOT / name).is_file()},
        "hostname": socket.gethostname(), "platform": platform.platform(), "python": sys.version.split()[0],
        "git_revision": _git_revision(), "started_unix": started, "finished_unix": time.time(),
    }
    manifest_path = campaign_root / "campaign_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def smoke(output_root: Path, max_cells: int) -> Path:
    if not 1 <= max_cells <= 8:
        raise ValueError("W5 smoke must contain 1..8 cells")
    campaign = load_campaign_config()
    configs = load_baseline_configs()
    all_specs = expand_specs(campaign, configs)
    first_inputs = []
    for index, config in enumerate(configs):
        candidates = [row for row in all_specs if row["baseline_id"] == config["id"]]
        first_inputs.append(candidates[index % len(candidates)])
    selected = first_inputs[:max_cells]
    root = output_root / "w5-smoke"
    rows = [run_cell(spec, root, resume=False) for spec in selected]
    _write_rows(root / "smoke_cells.jsonl", rows)
    path = root / "smoke_manifest.json"
    path.write_text(json.dumps({
        "schema": "ucc.external-baseline-smoke.v1", "formal": False, "cells": len(rows),
        "status_counts": {status: sum(row["status"] == status for row in rows) for status in sorted(VALID_STATUSES)},
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=ROOT / "data/runs")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--max-cells", type=int, default=8)
    parser.add_argument("--formal-local", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--worker", nargs=2, metavar=("SPEC", "CELL_DIR"))
    args = parser.parse_args(argv)
    if args.worker:
        print(RESULT_SENTINEL + json.dumps(worker(Path(args.worker[0]), Path(args.worker[1])), sort_keys=True))
        return 0
    campaign = load_campaign_config()
    configs = load_baseline_configs()
    specs = expand_specs(campaign, configs)
    if args.plan_only or (not args.smoke and not args.formal_local):
        print(json.dumps({
            "campaign": campaign["campaign"], "inputs": 216, "baseline_configs": len(configs),
            "planned_cells": len(specs), "categories": sorted({row["category"] for row in configs}),
            "formal_execution_requires": "--formal-local",
        }, sort_keys=True))
        return 0
    if args.smoke and args.formal_local:
        raise ValueError("smoke and formal modes are mutually exclusive")
    path = smoke(args.output_root, args.max_cells) if args.smoke else run_campaign(args.output_root, args.resume)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

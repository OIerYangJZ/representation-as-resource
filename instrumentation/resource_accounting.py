#!/usr/bin/env python3
"""File-backed implementation of the manuscript's formal bit budgets.

No function in this module derives bits from gate, token or node counts.
Every reported bit quantity is eight times the ``stat`` size of an artifact
that was written by :mod:`encoding.codec` (or, for ``B_com``, of an actual
immutable prefix of such an output artifact).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Mapping

from encoding.codec import (
    SCHEMA,
    SCHEMA_VERSION,
    AggregateRecord,
    CertificateInput,
    CircuitDAG,
    CommittedOutput,
    ControlState,
    ExternalToolOutput,
    FlatUpdateStream,
    IRField,
    IREdge,
    IRNode,
    Instruction,
    LiveWindow,
    ParameterEntry,
    ParameterLedger,
    PauliSupport,
    SemanticStream,
    StoreState,
    SymbolicParameter,
    UpdateRecord,
    decode_exact,
    encode,
    semantic_signature,
)


ACCOUNTING_SCHEMA = "ucc.resource-accounting.v1"
FIELD_FILES = {
    "control": "control.uccbin",
    "store": "store.uccbin",
    "window": "window.uccbin",
    "parameter": "parameter.uccbin",
    "ir": "ir.uccbin",
    "committed": "committed-prefix.bin",
}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_component(value: str) -> str:
    if not value or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_." for ch in value):
        raise ValueError(f"unsafe artifact path component: {value!r}")
    return value


def _write_and_measure(path: Path, payload: bytes, *, role: str, codec_type: str) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise FileExistsError(f"refusing to overwrite nonidentical immutable artifact: {path}")
    else:
        path.write_bytes(payload)
    byte_count = path.stat().st_size
    if byte_count != len(payload):
        raise OSError(f"short artifact write: {path}")
    return {
        "role": role,
        "path": path.name,
        "bytes": byte_count,
        "bits": 8 * byte_count,
        "sha256": sha256_file(path),
        "codec_type": codec_type,
    }


def _write_text_immutable(path: Path, text: str) -> None:
    payload = text.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise FileExistsError(f"refusing to overwrite nonidentical immutable artifact: {path}")
    else:
        path.write_bytes(payload)


@dataclass(frozen=True)
class ResourceSnapshot:
    """Five disjoint restart fields plus the literal committed prefix."""

    control: ControlState
    store: StoreState
    window: LiveWindow
    parameter: ParameterLedger
    ir: IRField
    committed_prefix: bytes = b""
    pass_count: int = 1
    pass_index: int = 0
    description_mode: str = "self_contained"
    dictionary_sha256: str | None = None
    dictionary_bytes: int = 0

    def __post_init__(self) -> None:
        if self.pass_count < 1 or not 0 <= self.pass_index < self.pass_count:
            raise ValueError("pass index must lie in [0, pass_count)")
        if self.description_mode not in {"self_contained", "conditional"}:
            raise ValueError("unknown description mode")
        if self.description_mode == "conditional":
            if (
                self.dictionary_sha256 is None
                or len(self.dictionary_sha256) != 64
                or any(ch not in "0123456789abcdef" for ch in self.dictionary_sha256)
            ):
                raise ValueError("conditional accounting must name the dictionary SHA-256")
        elif self.dictionary_sha256 is not None or self.dictionary_bytes:
            raise ValueError("self-contained accounting cannot hide dictionary bytes")
        if self.dictionary_bytes < 0:
            raise ValueError("dictionary byte count must be nonnegative")


def _measurement_from_manifest(manifest: Mapping[str, Any], manifest_path: Path) -> dict[str, Any]:
    files = manifest["files"]
    measurement: dict[str, Any] = {
        "accounting_schema": manifest["schema"],
        "codec_schema": manifest["codec"]["schema"],
        "codec_version": manifest["codec"]["version"],
        "p": manifest["passes"]["count"],
        "pass_index": manifest["passes"]["index"],
        "description_mode": manifest["description"]["mode"],
        "dictionary_sha256": manifest["description"]["dictionary_sha256"],
        "dictionary_bytes": manifest["description"]["dictionary_bytes"],
        "artifact_manifest_path": str(manifest_path),
    }
    for name in ("control", "store", "window", "parameter", "ir", "committed"):
        byte_count = int(files[name]["bytes"])
        formal = "com" if name == "committed" else name
        measurement[f"B_{formal}_bytes"] = byte_count
        measurement[f"B_{formal}_bits"] = 8 * byte_count
        measurement[f"{name}_bytes"] = byte_count
        measurement[f"{name}_bits"] = 8 * byte_count
        measurement[f"{name}_sha256"] = files[name]["sha256"]
        measurement[f"{name}_artifact_path"] = str(manifest_path.parent / files[name]["path"])
    measurement["B_IR_bytes"] = measurement["B_ir_bytes"]
    measurement["B_IR_bits"] = measurement["B_ir_bits"]
    cut_bytes = sum(measurement[f"B_{name}_bytes"] for name in ("control", "store", "window", "parameter", "ir"))
    measurement["B_cut_bytes"] = cut_bytes
    measurement["B_cut_bits"] = 8 * cut_bytes
    measurement["B_cross_bytes"] = cut_bytes
    measurement["B_cross_bits"] = 8 * cut_bytes
    measurement["artifact_manifest_sha256"] = sha256_file(manifest_path)
    return measurement


class ResourceAccountant:
    """Write immutable cut directories and report only measured file sizes."""

    def __init__(self, root: Path | str, run_id: str):
        self.root = Path(root).resolve()
        self.run_id = _safe_component(run_id)

    def measure(self, cut_id: str, snapshot: ResourceSnapshot) -> dict[str, Any]:
        cut_dir = self.root / self.run_id / _safe_component(cut_id)
        cut_dir.mkdir(parents=True, exist_ok=True)
        objects = {
            "control": snapshot.control,
            "store": snapshot.store,
            "window": snapshot.window,
            "parameter": snapshot.parameter,
            "ir": snapshot.ir,
        }
        files: dict[str, Any] = {}
        for name, value in objects.items():
            files[name] = _write_and_measure(
                cut_dir / FIELD_FILES[name], encode(value), role=f"B_{name}", codec_type=type(value).__name__
            )
        files["committed"] = _write_and_measure(
            cut_dir / FIELD_FILES["committed"],
            bytes(snapshot.committed_prefix),
            role="B_com",
            codec_type="CommittedOutputPrefix",
        )
        manifest = {
            "schema": ACCOUNTING_SCHEMA,
            "codec": {"schema": SCHEMA, "version": SCHEMA_VERSION},
            "run_id": self.run_id,
            "cut_id": cut_id,
            "passes": {"count": snapshot.pass_count, "index": snapshot.pass_index},
            "description": {
                "mode": snapshot.description_mode,
                "dictionary_sha256": snapshot.dictionary_sha256,
                "dictionary_bytes": snapshot.dictionary_bytes,
                "dictionary_charged_in_cut": False,
                "note": "conditional dictionaries are named public side information; self-contained mode forbids them",
            },
            "files": files,
            "bit_rule": "bits = 8 * os.stat(file).st_size; no count-to-bit conversion",
        }
        manifest_path = cut_dir / "manifest.json"
        _write_text_immutable(manifest_path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        verified = verify_manifest(manifest_path)
        return _measurement_from_manifest(verified, manifest_path)


def verify_manifest(path: Path | str) -> dict[str, Any]:
    """Re-measure every named file and reject missing or edited artifacts."""

    manifest_path = Path(path).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != ACCOUNTING_SCHEMA:
        raise ValueError(f"unsupported accounting manifest: {manifest.get('schema')!r}")
    if manifest.get("codec") != {"schema": SCHEMA, "version": SCHEMA_VERSION}:
        raise ValueError("manifest names a different codec")
    for name, filename in FIELD_FILES.items():
        record = manifest["files"].get(name)
        if record is None or record.get("path") != filename:
            raise ValueError(f"manifest lacks the canonical {name} artifact")
        artifact_path = manifest_path.parent / filename
        byte_count = artifact_path.stat().st_size
        if byte_count != record["bytes"] or 8 * byte_count != record["bits"]:
            raise ValueError(f"size mismatch for {artifact_path}")
        if sha256_file(artifact_path) != record["sha256"]:
            raise ValueError(f"digest mismatch for {artifact_path}")
        if name != "committed":
            decode_exact(artifact_path.read_bytes())
    return manifest


def load_measurement(path: Path | str) -> dict[str, Any]:
    manifest_path = Path(path).resolve()
    return _measurement_from_manifest(verify_manifest(manifest_path), manifest_path)


def write_encoded_artifact(path: Path | str, value: Any, *, role: str) -> dict[str, Any]:
    """Write one complete codec object and a verifiable adjacent manifest."""

    artifact_path = Path(path).resolve()
    record = _write_and_measure(artifact_path, encode(value), role=role, codec_type=type(value).__name__)
    manifest = {
        "schema": "ucc.encoded-artifact.v1",
        "codec": {"schema": SCHEMA, "version": SCHEMA_VERSION},
        "artifact": record,
    }
    manifest_path = artifact_path.with_name(artifact_path.name + ".manifest.json")
    _write_text_immutable(manifest_path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    decoded = decode_exact(artifact_path.read_bytes())
    if decoded != value:
        raise ValueError("artifact failed immediate semantic round trip")
    return {
        "artifact_path": str(artifact_path),
        "artifact_manifest_path": str(manifest_path),
        "artifact_sha256": record["sha256"],
        "artifact_bytes": record["bytes"],
        "artifact_bits": record["bits"],
        "codec_schema": SCHEMA,
        "codec_version": SCHEMA_VERSION,
    }


def parameter_from_number(value: Any) -> SymbolicParameter:
    """Losslessly charge a numeric tool parameter, including IEEE floats."""

    if isinstance(value, Fraction):
        coefficient = value
    elif isinstance(value, int) and not isinstance(value, bool):
        coefficient = Fraction(value)
    elif isinstance(value, float):
        coefficient = Fraction(*value.as_integer_ratio())
    else:
        try:
            numeric = float(value)
        except (TypeError, ValueError) as exc:
            raise TypeError(f"unsupported nonnumeric circuit parameter {value!r}") from exc
        coefficient = Fraction(*numeric.as_integer_ratio())
    return SymbolicParameter(coefficient)


def circuit_dag_from_qiskit(circuit: Any, *, provenance: str = "qiskit") -> CircuitDAG:
    """Serialize an actual Qiskit circuit as an address-complete dependency DAG."""

    nodes: list[IRNode] = []
    edges: set[tuple[int, int, int]] = set()
    last_on_qubit: dict[int, int] = {}
    for node_id, item in enumerate(circuit.data):
        operands = tuple(int(circuit.find_bit(qubit).index) for qubit in item.qubits)
        parameters = tuple(parameter_from_number(value) for value in item.operation.params)
        instruction = Instruction(str(item.operation.name), operands, PauliSupport(), parameters)
        nodes.append(IRNode(node_id, instruction))
        for port, qubit in enumerate(operands):
            if qubit in last_on_qubit:
                edges.add((last_on_qubit[qubit], node_id, port))
            last_on_qubit[qubit] = node_id
    return CircuitDAG(
        int(circuit.num_qubits),
        tuple(nodes),
        tuple(IREdge(source, target, port) for source, target, port in sorted(edges)),
        {"provenance": provenance},
    )


def parameter_ledger_from_dags(dags: Iterable[CircuitDAG]) -> ParameterLedger:
    entries: list[ParameterEntry] = []
    for object_index, dag in enumerate(dags):
        for node in dag.nodes:
            for slot, parameter in enumerate(node.instruction.parameters):
                entries.append(ParameterEntry((object_index, node.node_id, slot), parameter))
    return ParameterLedger(tuple(entries))


def final_boundary_snapshot(
    circuit: Any,
    output_frame: bytes,
    *,
    control_fields: Mapping[str, Any],
    pass_count: int,
    provenance: str,
) -> ResourceSnapshot:
    """Construct the observable final API-boundary snapshot for a runner cell."""

    dag = circuit_dag_from_qiskit(circuit, provenance=provenance)
    return ResourceSnapshot(
        ControlState(dict(control_fields)),
        StoreState({}),
        LiveWindow(()),
        parameter_ledger_from_dags((dag,)),
        IRField((dag,)),
        output_frame,
        pass_count=pass_count,
        pass_index=pass_count - 1,
    )


def assert_rows_file_backed(rows: Iterable[Mapping[str, Any]]) -> None:
    """Fail closed before any plot or table consumes a formal bit field."""

    for row in rows:
        manifest_path = row.get("artifact_manifest_path")
        if not manifest_path:
            raise ValueError("bit-bearing row has no artifact_manifest_path")
        measured = load_measurement(manifest_path)
        for key in (
            "B_control_bits", "B_store_bits", "B_window_bits", "B_parameter_bits",
            "B_ir_bits", "B_IR_bits", "B_com_bits", "B_cut_bits", "B_cross_bits",
        ):
            if int(row.get(key, -1)) != measured[key]:
                raise ValueError(f"row field {key} does not match {manifest_path}")


def build_example_trace(output_dir: Path) -> list[dict[str, Any]]:
    """Create a deterministic, small, non-experimental accounting fixture."""

    output_dir = output_dir.resolve()
    support = PauliSupport(((0, "Z"), (128, "Z")))
    aggregate = SemanticStream(
        129,
        (AggregateRecord(128, support, SymbolicParameter(Fraction(3, 17))),),
    )
    flat = FlatUpdateStream(
        129,
        2,
        (
            UpdateRecord(0, 128, support, SymbolicParameter(Fraction(5, 17))),
            UpdateRecord(1, 128, support, SymbolicParameter(Fraction(-2, 17))),
        ),
    )
    if semantic_signature(aggregate) != semantic_signature(flat):
        raise AssertionError("example representations do not implement the same unitary")

    input_dir = output_dir / "inputs"
    semantic_record = write_encoded_artifact(input_dir / "semantic.uccbin", aggregate, role="semantic_input")
    flat_record = write_encoded_artifact(input_dir / "flat.uccbin", flat, role="flat_input")
    external = ExternalToolOutput("reference", "ucc-target-basis", b"RZZ 0 128 3/17\n")
    external_record = write_encoded_artifact(input_dir / "external-output.uccbin", external, role="external_output")
    certificate = CertificateInput("exact-aggregate", external_record["artifact_sha256"], b"3/17@Z0Z128")
    certificate_record = write_encoded_artifact(input_dir / "certificate-input.uccbin", certificate, role="certificate_input")

    instruction = Instruction("rzz", (0, 128), support, (SymbolicParameter(Fraction(3, 17)),))
    dag = CircuitDAG(129, (IRNode(128, instruction),), (), {"source": "example"})
    final_output = encode(CommittedOutput("ucc-target-basis", b"RZZ 0 128 3/17\n"))
    prefixes = (b"", final_output[: len(final_output) // 2], final_output)
    accountant = ResourceAccountant(output_dir / "cuts", "example")
    rows = []
    for cut_index, prefix in enumerate(prefixes):
        snapshot = ResourceSnapshot(
            ControlState({
                "codec_version": SCHEMA_VERSION,
                "input_head": cut_index,
                "output_head": len(prefix),
                "pass_count": 2,
                "pass_index": min(cut_index, 1),
            }),
            StoreState({"aggregate_slots": [128]} if cut_index else {}),
            LiveWindow((instruction,) if cut_index == 1 else ()),
            ParameterLedger((ParameterEntry((0, 128, 0), instruction.parameters[0]),)) if cut_index else ParameterLedger(),
            IRField((dag,)) if cut_index == 2 else IRField(),
            prefix,
            pass_count=2,
            pass_index=min(cut_index, 1),
        )
        row = {"event": cut_index, **accountant.measure(f"cut-{cut_index:03d}", snapshot)}
        rows.append(row)
    assert_rows_file_backed(rows)
    trace_path = output_dir / "trace.jsonl"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    _write_text_immutable(
        trace_path,
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
    )
    _write_text_immutable(
        output_dir / "trace-manifest.json",
        json.dumps(
            {
                "schema": "ucc.accounting-example.v1",
                "semantic_input": semantic_record,
                "flat_input": flat_record,
                "external_output": external_record,
                "certificate_input": certificate_record,
                "trace": str(trace_path),
                "trace_sha256": sha256_file(trace_path),
                "events": len(rows),
            },
            indent=2,
            sort_keys=True,
        ) + "\n",
    )
    return rows


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--build-example",
        type=Path,
        metavar="DIR",
        help="write the deterministic file-backed example trace",
    )
    args = parser.parse_args(argv)
    if args.build_example is None:
        parser.error("--build-example DIR is required")
    rows = build_example_trace(args.build_example)
    print(json.dumps({"events": len(rows), "output": str(args.build_example.resolve())}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ACCOUNTING_SCHEMA", "FIELD_FILES", "ResourceSnapshot", "ResourceAccountant",
    "verify_manifest", "load_measurement", "write_encoded_artifact",
    "circuit_dag_from_qiskit", "parameter_ledger_from_dags",
    "final_boundary_snapshot", "assert_rows_file_backed", "build_example_trace",
]

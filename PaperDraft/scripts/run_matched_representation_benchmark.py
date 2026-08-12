#!/usr/bin/env python3
"""Matched-representation and multifactor packing benchmark.

Every design point describes one target

    U_x = product_j exp(-i*pi*x_j*Z_j Z_{j+1}/(8K)).

Seven lossless encodings of that target are crossed with every configured
compiler.  Cells run in fresh processes under one timeout and RSS cap.  The
worker emits only one JSON record; the parent freezes JSONL/CSV summaries,
confidence intervals, plots, and a campaign manifest.

This is a configured-pipeline diagnostic.  Only the exact CNOT--RZ
coefficient certificate is used as theorem-domain evidence.  Dense and PyZX
rewrite checks are explicitly labeled diagnostic fallbacks.
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
import random
import statistics
import subprocess
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
    AggregateRecord,
    CertificateInput,
    ControlState,
    ExternalToolOutput,
    FlatUpdateStream,
    IRField,
    LiveWindow,
    ParameterLedger,
    PauliSupport,
    SemanticStream,
    StoreState,
    SymbolicParameter,
    UpdateRecord,
    decode_exact,
    encode as accounting_encode,
)
from instrumentation.resource_accounting import (  # noqa: E402
    ResourceAccountant,
    ResourceSnapshot,
    assert_rows_file_backed,
    circuit_dag_from_qiskit,
    final_boundary_snapshot,
    write_encoded_artifact,
)
DEFAULT_OUTPUT = ROOT / "research" / "matched_representation"
TARGET_BASIS = ("cx", "rz", "h")
TIMEOUT_S = 30.0
MEMORY_CAP_BYTES = 2 * 1024**3
ATOL = 1e-9
RTOL = 1e-9
RESULT_SENTINEL = "MATCHED_CELL_JSON="
REPRESENTATIONS = (
    "semantic_aggregate",
    "contiguous_flat",
    "round_robin_flat",
    "random_commuting_order",
    "masked_share_flat",
    "locally_folded",
    "bridge_qasm2",
)
COMPILERS = (
    "semantic_reference",
    "phase_polynomial_reference",
    "qiskit_opt3",
    "tket_paulisimp",
    "pyzx_full_reduce",
)
COMPILER_CLASS = {
    "semantic_reference": "instrumented semantic reference",
    "phase_polynomial_reference": "instrumented global phase table",
    "qiskit_opt3": "configured local/preset diagnostic",
    "tket_paulisimp": "external Pauli-network/global semantic",
    "pyzx_full_reduce": "external ZX/global-IR semantic",
}


# Balanced, reproducible design: every requested axis changes, without
# pretending that this is the full Cartesian product.  The schedule axis is
# the seven-representation cross below.
DESIGN = (
    (4, 2, 4, 0.25, 20260801),
    (8, 4, 8, 0.50, 20260802),
    (16, 8, 16, 0.75, 20260803),
    (32, 2, 8, 1.00, 20260804),
    (64, 4, 4, 0.50, 20260805),
    (6, 8, 16, 0.25, 20260801),
    (12, 2, 4, 0.75, 20260802),
    (24, 4, 8, 1.00, 20260803),
    (48, 8, 16, 0.50, 20260804),
    (5, 4, 8, 0.75, 20260805),
    (10, 8, 4, 1.00, 20260801),
    (20, 2, 16, 0.50, 20260802),
    (40, 4, 4, 0.25, 20260803),
    (7, 8, 8, 1.00, 20260804),
    (14, 2, 16, 0.75, 20260805),
)


@dataclass(frozen=True)
class Token:
    generator: int
    support: tuple[int, int]
    angle_over_pi: Fraction
    round_index: int


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unavailable"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def uvarint(value: int) -> bytes:
    if value < 0:
        raise ValueError("uvarint is nonnegative")
    output = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        output.append(byte | (0x80 if value else 0))
        if not value:
            return bytes(output)


def svarint(value: int) -> bytes:
    zigzag = 2 * value if value >= 0 else -2 * value - 1
    return uvarint(zigzag)


def frame(payload: bytes) -> bytes:
    return uvarint(len(payload)) + payload


def token_codec(width: int, m: int, representation: str, tokens: list[Token]) -> bytes:
    """Unified address-complete codec used for flat representation bits."""

    del m, representation
    stream = FlatUpdateStream(
        width,
        max((token.round_index for token in tokens), default=-1) + 1,
        tuple(
            UpdateRecord(
                token.round_index,
                token.generator,
                PauliSupport(tuple((qubit, "Z") for qubit in token.support)),
                SymbolicParameter(token.angle_over_pi),
            )
            for token in tokens
        ),
    )
    return accounting_encode(stream)


def design_point(index: int) -> dict[str, Any]:
    m, r, K, density, seed = DESIGN[index]
    rng = random.Random(seed * 1009 + m * 97 + r * 17 + K)
    active_count = max(1, min(m, round(m * density)))
    active = sorted(rng.sample(range(m), active_count))
    x = [0] * m
    for generator in active:
        x[generator] = rng.randrange(1, K)
    payload = {
        "design_index": index,
        "m": m,
        "n": m + 1,
        "r": r,
        "K": K,
        "density_requested": density,
        "density_realized": active_count / m,
        "active_count": active_count,
        "seed": seed,
        "x": x,
        "x_distribution": "uniform on {1,...,K-1} over an exact-size uniform support sample",
        "delta_over_pi": f"1/{4*K}",
        "coefficient_span": "[0,pi/4); no 2pi target wraparound",
    }
    payload["target_id"] = "ux-" + sha256_bytes(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    )[:16]
    return payload


def split_tokens(point: dict[str, Any], order: str) -> list[Token]:
    m, r, K = point["m"], point["r"], point["K"]
    x = point["x"]
    records = [
        Token(j, (j, j + 1), Fraction(x[j], 4 * K * r), t)
        for t in range(r)
        for j in range(m)
        if x[j]
    ]
    if order == "round_robin":
        return records
    if order == "contiguous":
        return sorted(records, key=lambda item: (item.generator, item.round_index))
    if order == "random":
        shuffled = list(records)
        random.Random(point["seed"] + 7919).shuffle(shuffled)
        return shuffled
    raise ValueError(order)


def masked_tokens(point: dict[str, Any]) -> list[Token]:
    m, r, K = point["m"], point["r"], point["K"]
    modulus = 8 * K  # Delta*modulus = 2*pi
    rng = random.Random(point["seed"] + 104729)
    by_generator: dict[int, list[int]] = {}
    for j, coefficient in enumerate(point["x"]):
        if not coefficient:
            continue
        prefix = [rng.randrange(modulus) for _ in range(r - 1)]
        prefix.append((coefficient - sum(prefix)) % modulus)
        by_generator[j] = prefix
    return [
        Token(j, (j, j + 1), Fraction(by_generator[j][t], 4 * K), t)
        for t in range(r)
        for j in sorted(by_generator)
    ]


def representation_tokens(point: dict[str, Any], representation: str) -> list[Token]:
    m, K = point["m"], point["K"]
    if representation in {"semantic_aggregate", "bridge_qasm2"}:
        return [
            Token(j, (j, j + 1), Fraction(value, 4 * K), 0)
            for j, value in enumerate(point["x"])
            if value
        ]
    if representation == "contiguous_flat":
        return split_tokens(point, "contiguous")
    if representation == "round_robin_flat":
        return split_tokens(point, "round_robin")
    if representation == "random_commuting_order":
        return split_tokens(point, "random")
    if representation == "masked_share_flat":
        return masked_tokens(point)
    if representation == "locally_folded":
        source = split_tokens(point, "contiguous")
        result: list[Token] = []
        for j in range(m):
            local = [token for token in source if token.generator == j]
            for offset in range(0, len(local), 2):
                chunk = local[offset : offset + 2]
                if chunk:
                    result.append(
                        Token(
                            j,
                            (j, j + 1),
                            sum((token.angle_over_pi for token in chunk), Fraction()),
                            offset // 2,
                        )
                    )
        return result
    raise ValueError(representation)


def qiskit_imports() -> tuple[Any, Any, Any, Any]:
    from qiskit import QuantumCircuit, qasm2, transpile
    from qiskit.quantum_info import Operator

    return QuantumCircuit, qasm2, transpile, Operator


def lower_tokens(width: int, tokens: list[Token]) -> Any:
    QuantumCircuit, _, _, _ = qiskit_imports()
    circuit = QuantumCircuit(width)
    for token in tokens:
        control, target = token.support
        circuit.cx(control, target)
        circuit.rz(float(token.angle_over_pi) * math.pi, target)
        circuit.cx(control, target)
    return circuit


def qasm_bytes(circuit: Any) -> bytes:
    _, qasm2, _, _ = qiskit_imports()
    return qasm2.dumps(circuit).encode("utf-8")


def target_circuit(point: dict[str, Any]) -> Any:
    return lower_tokens(point["n"], representation_tokens(point, "semantic_aggregate"))


def representation_circuit(point: dict[str, Any], representation: str) -> tuple[Any, bytes]:
    tokens = representation_tokens(point, representation)
    circuit = lower_tokens(point["n"], tokens)
    if representation == "bridge_qasm2":
        _, qasm2, _, _ = qiskit_imports()
        payload = qasm_bytes(circuit)
        circuit = qasm2.loads(payload.decode("utf-8"))
        encoded = accounting_encode(ExternalToolOutput("qiskit", "openqasm2", payload))
    elif representation == "semantic_aggregate":
        encoded = accounting_encode(
            SemanticStream(
                point["n"],
                tuple(
                    AggregateRecord(
                        token.generator,
                        PauliSupport(tuple((qubit, "Z") for qubit in token.support)),
                        SymbolicParameter(token.angle_over_pi),
                    )
                    for token in tokens
                ),
            )
        )
    else:
        encoded = token_codec(point["n"], point["m"], representation, tokens)
    return circuit, encoded


def canonical_angle(angle: Fraction) -> Fraction:
    return angle % 2


def aggregate_tokens(point: dict[str, Any], representation: str) -> Any:
    totals: dict[tuple[int, int], Fraction] = {}
    for token in representation_tokens(point, representation):
        totals[token.support] = totals.get(token.support, Fraction()) + token.angle_over_pi
    canonical = [
        Token(index, support, canonical_angle(angle), 0)
        for index, (support, angle) in enumerate(sorted(totals.items()))
        if canonical_angle(angle)
    ]
    return lower_tokens(point["n"], canonical)


def exact_pi_ratio(value: Any) -> Fraction:
    ratio = float(value) / math.pi
    exact = Fraction(ratio).limit_denominator(1 << 20)
    if abs(ratio - float(exact)) > 2e-9:
        raise ValueError("floating angle has no rational-pi sidecar recovery")
    return exact


def extract_phase_table(circuit: Any) -> tuple[dict[int, Fraction], list[int]]:
    live = [1 << index for index in range(circuit.num_qubits)]
    terms: dict[int, Fraction] = {}
    for instruction in circuit.data:
        name = instruction.operation.name
        qargs = [int(circuit.find_bit(q).index) for q in instruction.qubits]
        if name == "cx" and len(qargs) == 2:
            live[qargs[1]] ^= live[qargs[0]]
        elif name == "rz" and len(qargs) == 1:
            mask = live[qargs[0]]
            terms[mask] = terms.get(mask, Fraction()) + exact_pi_ratio(
                instruction.operation.params[0]
            )
        elif name in {"barrier", "id"}:
            continue
        else:
            raise ValueError(f"operation {name} is outside CNOT--RZ domain")
    terms = {mask: angle % 2 for mask, angle in terms.items() if angle % 2}
    return terms, live


def compile_phase_polynomial(circuit: Any) -> Any:
    terms, frame = extract_phase_table(circuit)
    identity = [1 << index for index in range(circuit.num_qubits)]
    if frame != identity:
        raise ValueError("phase reference requires an identity final linear frame")
    tokens = []
    for index, (mask, angle) in enumerate(sorted(terms.items())):
        support = tuple(q for q in range(circuit.num_qubits) if mask & (1 << q))
        if len(support) != 2:
            raise ValueError("reference lowering supports two-body chain terms")
        tokens.append(Token(index, (support[0], support[1]), angle, 0))
    return lower_tokens(circuit.num_qubits, tokens)


def qasm_roundtrip(circuit: Any) -> Any:
    _, qasm2, _, _ = qiskit_imports()
    return qasm2.loads(qasm_bytes(circuit).decode("utf-8"))


def compile_method(point: dict[str, Any], representation: str, circuit: Any, method: str) -> tuple[Any, str]:
    _, qasm2, transpile, _ = qiskit_imports()
    if method == "semantic_reference":
        return aggregate_tokens(point, representation), "decode codec -> exact support table -> {cx,rz} lowering"
    if method == "phase_polynomial_reference":
        return compile_phase_polynomial(qasm_roundtrip(circuit)), "QASM2 -> exact parity/phase table -> {cx,rz} lowering"
    if method == "qiskit_opt3":
        return transpile(
            qasm_roundtrip(circuit),
            basis_gates=list(TARGET_BASIS),
            optimization_level=3,
            layout_method="trivial",
            routing_method="none",
            seed_transpiler=point["seed"],
        ), "QASM2 -> qiskit transpile opt3 -> {cx,rz,h}"
    if method == "tket_paulisimp":
        from pytket import passes
        from pytket.circuit import OpType
        import pytket.qasm as tket_qasm

        tk_circuit = tket_qasm.circuit_from_qasm_str(qasm_bytes(circuit).decode())
        sequence = (
            passes.DecomposeBoxes(),
            passes.AutoRebase({OpType.CX, OpType.Rz, OpType.H}),
            passes.RemoveRedundancies(),
            passes.PauliSimp(),
            passes.RemoveRedundancies(),
            passes.AutoRebase({OpType.CX, OpType.Rz, OpType.H}),
        )
        for compiler_pass in sequence:
            compiler_pass.apply(tk_circuit)
        qasm = tket_qasm.circuit_to_qasm_str(tk_circuit)
        return transpile(
            qasm2.loads(qasm), basis_gates=list(TARGET_BASIS), optimization_level=0
        ), "QASM2 -> TKET DecomposeBoxes/PauliSimp -> {cx,rz,h}"
    if method == "pyzx_full_reduce":
        import pyzx as zx

        zxc = zx.Circuit.from_qasm(qasm_bytes(circuit).decode()).to_basic_gates()
        graph = zxc.to_graph()
        zx.simplify.full_reduce(graph, quiet=True)
        compiled_zx = zx.extract_circuit(graph, quiet=True).to_basic_gates()
        provenance = "QASM2 -> ZX graph/full_reduce/extract_circuit -> {cx,rz,h}"
        lines = compiled_zx.to_qasm().splitlines()
        while lines and lines[0].startswith("Let "):
            lines.pop(0)
        return transpile(
            qasm2.loads("\n".join(lines)),
            basis_gates=list(TARGET_BASIS),
            optimization_level=0,
        ), provenance
    raise ValueError(method)


def circuit_metrics(circuit: Any) -> dict[str, Any]:
    counts = circuit.count_ops()
    return {
        "gates": int(sum(counts.values())),
        "depth": int(circuit.depth() or 0),
        "cx": int(counts.get("cx", 0)),
        "gate_types": sorted(str(name) for name in counts),
    }


def exact_phase_certificate(target: Any, candidate: Any) -> dict[str, Any]:
    try:
        target_terms, target_frame = extract_phase_table(target)
        candidate_terms, candidate_frame = extract_phase_table(candidate)
    except Exception as exc:
        return {"kind": "exact_cnot_rz", "status": "unsupported", "passed": False, "reason": str(exc)}
    passed = target_frame == candidate_frame and target_terms == candidate_terms
    return {
        "kind": "exact_cnot_rz",
        "status": "passed" if passed else "rejected",
        "passed": passed,
        "coefficient_rule": "Q*pi modulo 2*pi per parity support",
        "global_phase": "ignored",
        "frame_equal": target_frame == candidate_frame,
        "term_count_target": len(target_terms),
        "term_count_candidate": len(candidate_terms),
    }


def diagnostic_certificate(target: Any, candidate: Any) -> dict[str, Any]:
    exact = exact_phase_certificate(target, candidate)
    if exact["status"] != "unsupported":
        return exact
    if target.num_qubits <= 8:
        _, _, _, Operator = qiskit_imports()
        passed = bool(Operator(target).equiv(Operator(candidate), rtol=RTOL, atol=ATOL))
        return {
            "kind": "dense_unitary_diagnostic",
            "status": "passed" if passed else "rejected",
            "passed": passed,
            "atol": ATOL,
            "rtol": RTOL,
            "formal_theorem_evidence": False,
            "exact_domain_reason": exact["reason"],
        }
    try:
        import pyzx as zx

        left = zx.Circuit.from_qasm(qasm_bytes(target).decode())
        right = zx.Circuit.from_qasm(qasm_bytes(candidate).decode())
        passed = left.verify_equality(right, up_to_global_phase=True) is True
        return {
            "kind": "pyzx_rewrite_identity_diagnostic",
            "status": "passed" if passed else "inconclusive",
            "passed": passed,
            "formal_theorem_evidence": False,
            "exact_domain_reason": exact["reason"],
        }
    except Exception as exc:
        return {
            "kind": "certificate_unsupported",
            "status": "unsupported",
            "passed": False,
            "formal_theorem_evidence": False,
            "reason": f"{type(exc).__name__}: {exc}",
        }


def worker(design_index: int, representation: str, compiler: str, artifact_root: Path) -> dict[str, Any]:
    point = design_point(design_index)
    started = time.perf_counter()
    row: dict[str, Any] = {
        **point,
        "representation": representation,
        "schedule": representation,
        "compiler": compiler,
        "compiler_class": COMPILER_CLASS[compiler],
        "status": "error",
        "timeout_s": TIMEOUT_S,
        "memory_cap_bytes": MEMORY_CAP_BYTES,
        "target_basis": list(TARGET_BASIS),
        "error_budget": 0,
    }
    cell_id = "MR25-" + sha256_bytes(
        json.dumps(
            {"target_id": point["target_id"], "representation": representation, "compiler": compiler},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    )[:16]
    row["cell_id"] = cell_id
    try:
        original = target_circuit(point)
        represented, encoded = representation_circuit(point, representation)
        cell_dir = artifact_root.resolve() / cell_id
        input_record = write_encoded_artifact(
            cell_dir / "input.uccbin", decode_exact(encoded), role="compiler_input"
        )
        row["representation_sha256"] = input_record["artifact_sha256"]
        row["serialized_input_bits"] = input_record["artifact_bits"]
        row["input_artifact_path"] = input_record["artifact_path"]
        bridge_value = ExternalToolOutput("qiskit", "openqasm2", qasm_bytes(represented))
        bridge_record = write_encoded_artifact(cell_dir / "bridge.uccbin", bridge_value, role="compiler_bridge")
        row["bridge_serialized_bits"] = bridge_record["artifact_bits"]
        row["bridge_artifact_path"] = bridge_record["artifact_path"]
        input_dag = circuit_dag_from_qiskit(represented, provenance="matched-input")
        input_ir_record = write_encoded_artifact(cell_dir / "input-ir.uccbin", input_dag, role="input_ir")
        row["input_ir_bytes"] = input_ir_record["artifact_bytes"]
        row["input_ir_artifact_path"] = input_ir_record["artifact_path"]
        compiled, provenance = compile_method(point, representation, represented, compiler)
        output_value = ExternalToolOutput(compiler, "openqasm2", qasm_bytes(compiled))
        output_record = write_encoded_artifact(cell_dir / "output.uccbin", output_value, role="committed_output")
        output = Path(output_record["artifact_path"]).read_bytes()
        row.update(circuit_metrics(compiled))
        row["output_artifact_path"] = output_record["artifact_path"]
        row["bridge_sequence"] = provenance
        certificate = diagnostic_certificate(original, compiled)
        certificate_record = write_encoded_artifact(
            cell_dir / "certificate.uccbin",
            CertificateInput(
                certificate["kind"],
                output_record["artifact_sha256"],
                json.dumps(certificate, sort_keys=True, separators=(",", ":")).encode(),
            ),
            role="certificate_input",
        )
        row["certificate_artifact_path"] = certificate_record["artifact_path"]
        row["certificate"] = certificate
        row["certificate_kind"] = certificate["kind"]
        row["certificate_status"] = certificate["status"]
        row["formal_theorem_evidence"] = certificate["kind"] == "exact_cnot_rz" and certificate["passed"]
        row["status"] = "completed" if certificate["passed"] else (
            "correctness_failure" if certificate["status"] == "rejected" else "certificate_unsupported"
        )
        snapshot = final_boundary_snapshot(
            compiled,
            output,
            control_fields={
                "cell_id": cell_id,
                "compiler": compiler,
                "input_head": input_record["artifact_bytes"],
                "output_head": output_record["artifact_bytes"],
                "representation": representation,
                "status": row["status"],
            },
            pass_count=1,
            provenance=provenance,
        )
        row.update(ResourceAccountant(artifact_root, cell_id).measure("final", snapshot))
        row["output_serialized_bits"] = row["B_com_bits"]
        row["output_ir_bytes"] = row["B_ir_bytes"]
        row["ir_bytes"] = max(row["input_ir_bytes"], row["output_ir_bytes"])
    except Exception as exc:
        row["status"] = "error"
        row["error"] = f"{type(exc).__name__}: {exc}"
        row["traceback"] = traceback.format_exc(limit=12)
    row["runtime_s"] = round(time.perf_counter() - started, 6)
    return row


def parse_result(stdout: str) -> dict[str, Any]:
    for line in reversed(stdout.splitlines()):
        if line.startswith(RESULT_SENTINEL):
            return json.loads(line[len(RESULT_SENTINEL) :])
    raise ValueError("worker result sentinel missing")


def _attach_failure_accounting(row: dict[str, Any], artifact_root: Path) -> dict[str, Any]:
    cell_id = row.get("cell_id") or "MR25-" + sha256_bytes(
        json.dumps(
            {
                "target_id": row["target_id"],
                "representation": row["representation"],
                "compiler": row["compiler"],
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    )[:16]
    row["cell_id"] = cell_id
    snapshot = ResourceSnapshot(
        ControlState({
            "cell_id": cell_id,
            "compiler": row["compiler"],
            "representation": row["representation"],
            "status": row["status"],
        }),
        StoreState({}),
        LiveWindow(()),
        ParameterLedger(),
        IRField(),
        b"",
    )
    row.update(ResourceAccountant(artifact_root, cell_id).measure("failure", snapshot))
    row["output_serialized_bits"] = row["B_com_bits"]
    row["output_ir_bytes"] = row["B_ir_bytes"]
    row["ir_bytes"] = row["B_ir_bytes"]
    return row


def run_cell(design_index: int, representation: str, compiler: str, artifact_root: Path) -> dict[str, Any]:
    import psutil

    command = [
        sys.executable,
        str(THIS_FILE),
        "--worker",
        str(design_index),
        representation,
        compiler,
        "--artifact-root",
        str(artifact_root),
    ]
    env = os.environ.copy()
    env.setdefault("XDG_CONFIG_HOME", "/tmp/ucc-matched-xdg")
    env.setdefault("XDG_CACHE_HOME", "/tmp/ucc-matched-cache")
    env.setdefault("MPLCONFIGDIR", "/tmp/ucc-matched-mpl")
    started = time.perf_counter()
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    monitored = psutil.Process(process.pid)
    peak = 0
    forced_status: str | None = None
    while process.poll() is None:
        elapsed = time.perf_counter() - started
        try:
            rss = monitored.memory_info().rss
            peak = max(peak, rss)
        except (psutil.NoSuchProcess, psutil.AccessDenied, PermissionError):
            pass
        if peak > MEMORY_CAP_BYTES:
            forced_status = "memory_cap"
            process.kill()
            break
        if elapsed > TIMEOUT_S:
            forced_status = "timeout"
            process.kill()
            break
        time.sleep(0.02)
    stdout, stderr = process.communicate()
    elapsed = round(time.perf_counter() - started, 6)
    if forced_status:
        point = design_point(design_index)
        return _attach_failure_accounting({
            **point,
            "representation": representation,
            "schedule": representation,
            "compiler": compiler,
            "compiler_class": COMPILER_CLASS[compiler],
            "status": forced_status,
            "runtime_s": elapsed,
            "rss_peak_bytes": peak,
            "timeout_s": TIMEOUT_S,
            "memory_cap_bytes": MEMORY_CAP_BYTES,
            "target_basis": list(TARGET_BASIS),
            "error_budget": 0,
        }, artifact_root)
    try:
        row = parse_result(stdout)
    except Exception as exc:
        point = design_point(design_index)
        row = {
            **point,
            "representation": representation,
            "schedule": representation,
            "compiler": compiler,
            "compiler_class": COMPILER_CLASS[compiler],
            "status": "worker_error",
            "runtime_s": elapsed,
            "error": f"{type(exc).__name__}: {exc}",
            "stderr": stderr[-4000:],
            "timeout_s": TIMEOUT_S,
            "memory_cap_bytes": MEMORY_CAP_BYTES,
            "target_basis": list(TARGET_BASIS),
            "error_budget": 0,
        }
    if not row.get("artifact_manifest_path"):
        row = _attach_failure_accounting(row, artifact_root)
    row["rss_peak_bytes"] = peak
    row["wall_runtime_s"] = elapsed
    return row


def ci95(values: list[float]) -> tuple[float | None, float | None, float | None]:
    if not values:
        return None, None, None
    mean = statistics.fmean(values)
    if len(values) == 1:
        return mean, mean, mean
    half = 1.96 * statistics.stdev(values) / math.sqrt(len(values))
    return mean, mean - half, mean + half


def wilson(successes: int, total: int) -> tuple[float, float, float]:
    z = 1.96
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return p, max(0.0, center - half), min(1.0, center + half)


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    assert_rows_file_backed(rows)
    output = []
    for representation in REPRESENTATIONS:
        for compiler in COMPILERS:
            group = [row for row in rows if row["representation"] == representation and row["compiler"] == compiler]
            completed = [row for row in group if row["status"] == "completed"]
            rate, rate_low, rate_high = wilson(len(completed), len(group))
            record: dict[str, Any] = {
                "representation": representation,
                "compiler": compiler,
                "compiler_class": COMPILER_CLASS[compiler],
                "cells": len(group),
                "completed": len(completed),
                "completion_rate": rate,
                "completion_ci95_low": rate_low,
                "completion_ci95_high": rate_high,
            }
            for field in ("runtime_s", "rss_peak_bytes", "B_ir_bits", "B_com_bits", "gates", "depth", "cx"):
                values = [float(row[field]) for row in completed if row.get(field) is not None]
                mean, low, high = ci95(values)
                record[f"{field}_mean"] = mean
                record[f"{field}_ci95_low"] = low
                record[f"{field}_ci95_high"] = high
            output.append(record)
    return output


def factor_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    factors = {
        "m": sorted({row["m"] for row in rows}),
        "r": sorted({row["r"] for row in rows}),
        "K": sorted({row["K"] for row in rows}),
        "density_realized": sorted({row["density_realized"] for row in rows}),
        "seed": sorted({row["seed"] for row in rows}),
        "schedule": list(REPRESENTATIONS),
    }
    output = []
    for factor, levels in factors.items():
        for level in levels:
            for compiler in COMPILERS:
                group = [row for row in rows if row["compiler"] == compiler and row[factor] == level]
                completed = [row for row in group if row["status"] == "completed"]
                if not group:
                    continue
                rate, low, high = wilson(len(completed), len(group))
                runtime = ci95([float(row["runtime_s"]) for row in completed])
                gates = ci95([float(row["gates"]) for row in completed])
                output.append({
                    "factor": factor,
                    "level": level,
                    "compiler": compiler,
                    "cells": len(group),
                    "completed": len(completed),
                    "completion_rate": rate,
                    "completion_ci95_low": low,
                    "completion_ci95_high": high,
                    "runtime_s_mean": runtime[0],
                    "runtime_s_ci95_low": runtime[1],
                    "runtime_s_ci95_high": runtime[2],
                    "gates_mean": gates[0],
                    "gates_ci95_low": gates[1],
                    "gates_ci95_high": gates[2],
                })
    return output


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = sorted({key for row in rows for key in row if not isinstance(row[key], (dict, list))})
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fields})


def plot_summary(summary: list[dict[str, Any]], output: Path) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    completion = np.zeros((len(REPRESENTATIONS), len(COMPILERS)))
    output_bits = np.full_like(completion, np.nan, dtype=float)
    lookup = {(row["representation"], row["compiler"]): row for row in summary}
    for i, representation in enumerate(REPRESENTATIONS):
        for j, compiler in enumerate(COMPILERS):
            row = lookup[(representation, compiler)]
            completion[i, j] = row["completion_rate"]
            if row["B_com_bits_mean"] is not None:
                output_bits[i, j] = row["B_com_bits_mean"]
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 5.6), constrained_layout=True)
    images = [
        axes[0].imshow(completion, vmin=0, vmax=1, cmap="viridis", aspect="auto"),
        axes[1].imshow(np.log2(output_bits), cmap="magma", aspect="auto"),
    ]
    axes[0].set_title("(a) Certified completion rate")
    axes[1].set_title("(b) Mean serialized output bits (log2)")
    short_compilers = ["semantic", "phase-ref", "qiskit", "TKET", "PyZX-ZX"]
    for axis in axes:
        axis.set_xticks(range(len(COMPILERS)), short_compilers, rotation=35, ha="right")
        axis.set_yticks(range(len(REPRESENTATIONS)), [name.replace("_", " ") for name in REPRESENTATIONS])
    fig.colorbar(images[0], ax=axes[0], fraction=0.046, label="fraction")
    fig.colorbar(images[1], ax=axes[1], fraction=0.046, label="log2 bits")
    fig.savefig(output)
    plt.close(fig)


def latex_matrix(summary: list[dict[str, Any]]) -> str:
    lookup = {(row["representation"], row["compiler"]): row for row in summary}
    labels = {
        "semantic_aggregate": "semantic aggregate",
        "contiguous_flat": "contiguous flat",
        "round_robin_flat": "round-robin flat",
        "random_commuting_order": "random commuting",
        "masked_share_flat": "masked-share flat",
        "locally_folded": "locally folded",
        "bridge_qasm2": "QASM2 bridge",
    }
    lines = []
    for representation in REPRESENTATIONS:
        cells = []
        for compiler in COMPILERS:
            row = lookup[(representation, compiler)]
            if row["completed"]:
                cells.append(f"{row['completed']}/{row['cells']}; {row['gates_mean']:.1f}")
            else:
                cells.append(f"0/{row['cells']}; --")
        lines.append(labels[representation] + " & " + " & ".join(cells) + r" \\")
    if lines and lines[-1].endswith(r" \\"):
        lines[-1] = lines[-1][:-3]
    return "\n".join(lines) + "\n"


def campaign_manifest(rows: list[dict[str, Any]]) -> dict[str, Any]:
    versions = {name: package_version(name) for name in ("qiskit", "pytket", "pyzx", "ucc", "psutil")}
    config = {
        "design": [list(item) for item in DESIGN],
        "representations": list(REPRESENTATIONS),
        "compilers": list(COMPILERS),
        "target_basis": list(TARGET_BASIS),
        "timeout_s": TIMEOUT_S,
        "memory_cap_bytes": MEMORY_CAP_BYTES,
        "error_budget": 0,
        "dense_tolerance": {"atol": ATOL, "rtol": RTOL},
        "codec": "ucc.accounting v1 canonical prefix-free frames for semantic, flat, bridge, output, certificate, and all five cut fields",
        "bit_source": "8 * actual artifact file size, verified against SHA-256 before aggregation or plotting",
        "ir_bytes": "canonical serialized dependency DAG with node/edge/qubit addresses and parameters split into B_parameter",
        "certificate_policy": ["exact CNOT--RZ phase table", "dense unitary diagnostic for n<=8", "PyZX rewrite-identity diagnostic otherwise"],
    }
    config_hash = sha256_bytes(json.dumps(config, sort_keys=True, separators=(",", ":")).encode())
    return {
        "schema": "ucc.campaign-manifest.v1",
        "campaign": "MR25-matched-representation-20260801",
        "immutable_config_sha256": config_hash,
        "artifact_commit": "local-uncommitted-repaired-manuscript",
        "runner": str(THIS_FILE.relative_to(ROOT)),
        "runner_sha256": sha256_file(THIS_FILE),
        "backend_topology": "all-to-all logical; no routing",
        "native_gate_set": list(TARGET_BASIS),
        "seeds": sorted({row["seed"] for row in rows}),
        "timeout_s": TIMEOUT_S,
        "memory_cap_bytes": MEMORY_CAP_BYTES,
        "tool_versions": versions,
        "bridge_sequences": {compiler: COMPILER_CLASS[compiler] for compiler in COMPILERS},
        "certificate": config["certificate_policy"],
        "config": config,
        "cells": len(rows),
        "completed": sum(row["status"] == "completed" for row in rows),
        "status_counts": {status: sum(row["status"] == status for row in rows) for status in sorted({row["status"] for row in rows})},
    }


def run_parent(output_dir: Path) -> int:
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/ucc-matched-mpl")
    os.environ.setdefault("XDG_CACHE_HOME", "/tmp/ucc-matched-cache")
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    total = len(DESIGN) * len(REPRESENTATIONS) * len(COMPILERS)
    index = 0
    for design_index in range(len(DESIGN)):
        for representation in REPRESENTATIONS:
            for compiler in COMPILERS:
                index += 1
                row = run_cell(design_index, representation, compiler, output_dir / "accounting")
                rows.append(row)
                print(
                    f"[{index:03d}/{total}] d={design_index} rep={representation} compiler={compiler} status={row['status']}",
                    flush=True,
                )
    rows.sort(key=lambda row: (row["design_index"], row["representation"], row["compiler"]))
    jsonl = output_dir / "matched_cells.jsonl"
    jsonl.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    write_csv(output_dir / "matched_cells.csv", rows)
    summary = summarize(rows)
    write_csv(output_dir / "matched_summary.csv", summary)
    factors = factor_summary(rows)
    write_csv(output_dir / "factor_summary.csv", factors)
    plot_summary(summary, output_dir / "matched_representation_matrix.pdf")
    (output_dir / "representation_matrix_rows.tex").write_text(latex_matrix(summary), encoding="utf-8")
    manifest = campaign_manifest(rows)
    (output_dir / "campaign_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"cells": len(rows), "status_counts": manifest["status_counts"]}, sort_keys=True))
    return 0


def refresh_existing(output_dir: Path) -> int:
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/ucc-matched-mpl")
    os.environ.setdefault("XDG_CACHE_HOME", "/tmp/ucc-matched-cache")
    rows = [
        json.loads(line)
        for line in (output_dir / "matched_cells.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != len(DESIGN) * len(REPRESENTATIONS) * len(COMPILERS):
        raise ValueError("existing cell file is not the complete configured matrix")
    if any(not row.get("artifact_manifest_path") for row in rows):
        raise ValueError(
            "legacy rows have no file-backed accounting manifests; rerun the campaign instead of reconstructing bits from counts"
        )
    summary = summarize(rows)
    write_csv(output_dir / "matched_summary.csv", summary)
    write_csv(output_dir / "factor_summary.csv", factor_summary(rows))
    plot_summary(summary, output_dir / "matched_representation_matrix.pdf")
    (output_dir / "representation_matrix_rows.tex").write_text(latex_matrix(summary), encoding="utf-8")
    (output_dir / "campaign_manifest.json").write_text(
        json.dumps(campaign_manifest(rows), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"refreshed_cells": len(rows)}, sort_keys=True))
    return 0


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--refresh-existing", action="store_true")
    parser.add_argument("--worker", nargs=3, metavar=("DESIGN_INDEX", "REPRESENTATION", "COMPILER"))
    parser.add_argument("--single", nargs=3, metavar=("DESIGN_INDEX", "REPRESENTATION", "COMPILER"))
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_OUTPUT / "accounting")
    args = parser.parse_args(argv)
    if args.worker:
        design_index, representation, compiler = args.worker
        row = worker(int(design_index), representation, compiler, args.artifact_root)
        print(RESULT_SENTINEL + json.dumps(row, sort_keys=True))
        return 0
    if args.single:
        design_index, representation, compiler = args.single
        print(json.dumps(worker(int(design_index), representation, compiler, args.artifact_root), indent=2, sort_keys=True))
        return 0
    if args.refresh_existing:
        return refresh_existing(args.output_dir)
    return run_parent(args.output_dir)


if __name__ == "__main__":
    raise SystemExit(main())

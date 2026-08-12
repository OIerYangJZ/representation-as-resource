#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import platform
import signal
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


THIS_FILE = Path(__file__).resolve()
OUTPUT_DIR = THIS_FILE.parent
REPO_ROOT = THIS_FILE.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("XDG_CONFIG_HOME", "/tmp/xdg-config")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/xdg-cache")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/mplconfig")

TARGET_BASIS = ["cx", "rx", "ry", "rz", "h"]
FULL_SIZES = (4_000, 10_000, 20_000, 50_000, 100_000)
SMOKE_SIZES = (48,)
DEFAULT_FULL_TIMEOUT_S = 600
DEFAULT_SMOKE_TIMEOUT_S = 20
CORRECTNESS_FULL_REPEATS = 9_999
CORRECTNESS_SMOKE_REPEATS = 3

REQUIRED_ROW_FIELDS = (
    "experiment_family",
    "instance_name",
    "n",
    "size",
    "r",
    "method_key",
    "paper_method_name",
    "timeout_s",
    "status",
    "wall_time_s",
    "gate_count",
    "depth",
    "cx_count",
    "rz_rotation_count",
    "notes",
    "source_command_or_script",
)


@dataclass(frozen=True)
class MethodInfo:
    key: str
    paper_name: str
    tool_sequence: str
    artifact_flags: str
    notes: str


METHOD_INFO: dict[str, MethodInfo] = {
    "semantic_ucc": MethodInfo(
        "semantic_ucc",
        "semantic UCC (Fourier-layer IR enabled)",
        "ucc.compile(..., target_gateset={cx, rx, ry, rz, h}) with Fourier-layer IR enabled",
        "UCC_DISABLE_FOURIER_LAYER_IR unset",
        "Artifact method; preserves the Fourier-layer semantic path.",
    ),
    "no_fourier_ucc": MethodInfo(
        "no_fourier_ucc",
        "artifact UCC (Fourier-layer IR disabled)",
        "ucc.compile(..., target_gateset={cx, rx, ry, rz, h}) with Fourier-layer IR disabled",
        "UCC_DISABLE_FOURIER_LAYER_IR=1",
        "Causal ablation; completed rows report output metrics rather than only timeout markers.",
    ),
    "qiskit_opt3": MethodInfo(
        "qiskit_opt3",
        "qiskit opt3",
        "qiskit.transpile(circuit, basis_gates=TARGET_BASIS, optimization_level=3, layout_method='trivial', routing_method='none')",
        "none",
        "Materialize-first Qiskit preset baseline.",
    ),
    "qiskit_commutative_inverse": MethodInfo(
        "qiskit_commutative_inverse",
        "qiskit commutative inverse",
        "PassManager([CommutativeInverseCancellation()]).run(circuit), then qiskit opt0 target-basis lowering",
        "none",
        "Targeted inverse/commutation control already present in earlier scripts.",
    ),
    "pyzx_configured": MethodInfo(
        "pyzx_configured",
        "PyZX configured bridge",
        "qiskit qasm2 -> pyzx.Circuit.from_qasm -> to_basic_gates -> zx.optimize.basic_optimization -> qiskit qasm2 -> qiskit opt0 target-basis cleanup",
        "none",
        "Matches the previously configured PyZX bridge mode.",
    ),
    "pyzx_full_reduce": MethodInfo(
        "pyzx_full_reduce",
        "PyZX full_reduce",
        "qiskit qasm2 -> pyzx.Circuit.from_qasm -> to_basic_gates -> graph -> zx.simplify.full_reduce -> zx.extract_circuit -> qiskit qasm2 -> qiskit opt0 target-basis cleanup",
        "none",
        "Explicit strong PyZX simplification pipeline.",
    ),
    "tket_fullpeephole": MethodInfo(
        "tket_fullpeephole",
        "TKET FullPeephole",
        "Qiskit-to-TKET bridge if available; otherwise qiskit opt0 target-basis qasm2 -> pytket.qasm -> FullPeepholeOptimise -> qasm2 -> qiskit opt0 target-basis cleanup",
        "none",
        "The qasm fallback is disclosed in call-sequence/provenance output when pytket-qiskit is unavailable.",
    ),
    "tket_paulisimp": MethodInfo(
        "tket_paulisimp",
        "TKET PauliSimp",
        "Qiskit-to-TKET bridge if available; otherwise qiskit opt0 target-basis qasm2 -> pytket.qasm -> PauliSimp -> qasm2 -> qiskit opt0 target-basis cleanup",
        "none",
        "Included if pytket.passes.PauliSimp is importable.",
    ),
    "tket_guided_paulisimp": MethodInfo(
        "tket_guided_paulisimp",
        "TKET GuidedPauliSimp",
        "Qiskit-to-TKET bridge if available; otherwise qiskit opt0 target-basis qasm2 -> pytket.qasm -> GuidedPauliSimp -> qasm2 -> qiskit opt0 target-basis cleanup",
        "none",
        "Included if pytket.passes.GuidedPauliSimp is importable.",
    ),
    "phase_poly_reference": MethodInfo(
        "phase_poly_reference",
        "phase-polynomial reference",
        "recognize the H-D^r-H witness shape, aggregate commuting rz/cp coefficients, then qiskit opt0 target-basis lowering",
        "none",
        "Narrow semantic-capable reference; not a UCC implementation.",
    ),
}

MAIN_METHODS = (
    "qiskit_opt3",
    "qiskit_commutative_inverse",
    "pyzx_configured",
    "pyzx_full_reduce",
    "tket_fullpeephole",
    "tket_paulisimp",
    "tket_guided_paulisimp",
    "semantic_ucc",
    "phase_poly_reference",
)
ABLATION_METHODS = (
    "semantic_ucc",
    "no_fourier_ucc",
    "qiskit_opt3",
    "qiskit_commutative_inverse",
    "phase_poly_reference",
)
RESOURCE_METHODS = (
    "semantic_ucc",
    "phase_poly_reference",
    "qiskit_opt3",
    "no_fourier_ucc",
)
CORRECTNESS_METHODS = (
    "semantic_ucc",
    "phase_poly_reference",
)


@dataclass(frozen=True)
class CircuitCase:
    experiment_family: str
    instance_name: str
    n: int
    size: int | None
    repeats: int
    block_gate_count: int
    actual_input_gates: int
    circuit: Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _import_qiskit():
    from qiskit import QuantumCircuit
    from qiskit import transpile as qiskit_transpile
    from qiskit.quantum_info import Operator
    from qiskit.transpiler import PassManager
    from qiskit.transpiler.passes import CommutativeInverseCancellation

    return {
        "QuantumCircuit": QuantumCircuit,
        "transpile": qiskit_transpile,
        "Operator": Operator,
        "PassManager": PassManager,
        "CommutativeInverseCancellation": CommutativeInverseCancellation,
    }


def _phase_diagonal_block(num_qubits: int):
    qiskit = _import_qiskit()
    QuantumCircuit = qiskit["QuantumCircuit"]
    block = QuantumCircuit(num_qubits)
    for qubit in range(num_qubits):
        block.rz(math.pi / (7 + qubit), qubit)
    for control in range(num_qubits):
        for target in range(control + 1, num_qubits):
            block.cp(math.pi / (11 + control + target), control, target)
    return block


def build_fourier_phase_sandwich(
    *,
    experiment_family: str,
    target_gates: int | None = None,
    repeats: int | None = None,
    num_qubits: int = 4,
) -> CircuitCase:
    qiskit = _import_qiskit()
    QuantumCircuit = qiskit["QuantumCircuit"]
    block = _phase_diagonal_block(num_qubits)
    overhead = 2 * num_qubits
    block_gate_count = len(block.data)
    if repeats is None:
        if target_gates is None:
            raise ValueError("target_gates or repeats is required")
        repeats = max(1, (target_gates - overhead) // max(1, block_gate_count))
    actual_input_gates = overhead + repeats * block_gate_count
    circuit = QuantumCircuit(num_qubits)
    for qubit in range(num_qubits):
        circuit.h(qubit)
    for _ in range(repeats):
        circuit.compose(block, inplace=True)
    for qubit in range(num_qubits):
        circuit.h(qubit)
    circuit.name = "fourier_phase_sandwich"
    size = target_gates if target_gates is not None else actual_input_gates
    return CircuitCase(
        experiment_family=experiment_family,
        instance_name=f"fourier_phase_sandwich_n{num_qubits}_r{repeats}",
        n=num_qubits,
        size=size,
        repeats=repeats,
        block_gate_count=block_gate_count,
        actual_input_gates=actual_input_gates,
        circuit=circuit,
    )


def circuit_metrics(circuit) -> dict[str, Any]:
    count_ops = circuit.count_ops()
    total_gates = int(sum(count_ops.values()))
    rotations = (
        int(count_ops.get("rz", 0))
        + int(count_ops.get("rx", 0))
        + int(count_ops.get("ry", 0))
    )
    return {
        "gate_count": total_gates,
        "depth": int(circuit.depth()),
        "cx_count": int(count_ops.get("cx", 0)),
        "rz_rotation_count": rotations,
        "gate_types": sorted(str(name) for name in count_ops.keys()),
        "num_qubits": int(circuit.num_qubits),
    }


def build_base_row(
    *,
    case: CircuitCase,
    method_key: str,
    timeout_s: int,
    source_command: str,
) -> dict[str, Any]:
    info = METHOD_INFO[method_key]
    return {
        "experiment_family": case.experiment_family,
        "instance_name": case.instance_name,
        "n": case.n,
        "size": case.size,
        "r": case.repeats,
        "actual_input_gates": case.actual_input_gates,
        "block_gate_count": case.block_gate_count,
        "method_key": method_key,
        "paper_method_name": info.paper_name,
        "timeout_s": int(timeout_s),
        "status": "error",
        "wall_time_s": None,
        "gate_count": None,
        "depth": None,
        "cx_count": None,
        "rz_rotation_count": None,
        "notes": "",
        "source_command_or_script": source_command,
    }


def _with_target_basis(circuit, optimization_level: int = 0):
    qiskit = _import_qiskit()
    return qiskit["transpile"](
        circuit,
        basis_gates=TARGET_BASIS,
        optimization_level=optimization_level,
        layout_method="trivial" if optimization_level else None,
        routing_method="none" if optimization_level else None,
    )


def compile_qiskit_opt3(circuit):
    qiskit = _import_qiskit()
    return qiskit["transpile"](
        circuit,
        basis_gates=TARGET_BASIS,
        optimization_level=3,
        layout_method="trivial",
        routing_method="none",
    ), "qiskit.transpile optimization_level=3"


def compile_qiskit_commutative_inverse(circuit):
    qiskit = _import_qiskit()
    simplified = qiskit["PassManager"](
        [qiskit["CommutativeInverseCancellation"]()]
    ).run(circuit)
    compiled = qiskit["transpile"](
        simplified,
        basis_gates=TARGET_BASIS,
        optimization_level=0,
    )
    return compiled, "CommutativeInverseCancellation then qiskit target-basis opt0"


def _qasm2_cleanup_to_qiskit(qasm_text: str):
    from qiskit import qasm2

    lines = qasm_text.splitlines()
    while lines and lines[0].startswith("Let "):
        lines = lines[1:]
    loaded = qasm2.loads("\n".join(lines))
    return _with_target_basis(loaded, optimization_level=0)


def compile_pyzx_configured(circuit):
    try:
        import pyzx as zx
        from qiskit import qasm2
    except Exception as exc:
        raise RuntimeError(f"PyZX configured bridge unavailable: {exc}") from exc

    qasm_str = qasm2.dumps(circuit)
    zxc = zx.Circuit.from_qasm(qasm_str)
    zxc = zxc.to_basic_gates()
    zx.optimize.basic_optimization(zxc)
    compiled = _qasm2_cleanup_to_qiskit(zxc.to_qasm())
    return compiled, "PyZX Circuit.from_qasm -> to_basic_gates -> basic_optimization"


def compile_pyzx_full_reduce(circuit):
    try:
        import pyzx as zx
        from qiskit import qasm2
    except Exception as exc:
        raise RuntimeError(f"PyZX full_reduce unavailable: {exc}") from exc

    qasm_str = qasm2.dumps(circuit)
    zxc = zx.Circuit.from_qasm(qasm_str).to_basic_gates()
    graph = zxc.to_graph()
    zx.simplify.full_reduce(graph)
    extracted = zx.extract_circuit(graph.copy()).to_basic_gates()
    compiled = _qasm2_cleanup_to_qiskit(extracted.to_qasm())
    return compiled, "PyZX to_graph -> simplify.full_reduce -> extract_circuit"


def _tket_bridge_available() -> bool:
    try:
        import pytket.extensions.qiskit  # noqa: F401

        return True
    except Exception:
        return False


def _run_tket_pass(circuit, pass_name: str):
    try:
        from pytket import passes as tket_passes
    except Exception as exc:
        raise RuntimeError(f"pytket unavailable: {exc}") from exc

    if not hasattr(tket_passes, pass_name):
        raise RuntimeError(f"pytket.passes.{pass_name} is not available")
    PassClass = getattr(tket_passes, pass_name)

    if _tket_bridge_available():
        from pytket.extensions.qiskit import qiskit_to_tk, tk_to_qiskit

        tk_circuit = qiskit_to_tk(circuit)
        PassClass().apply(tk_circuit)
        compiled = _with_target_basis(tk_to_qiskit(tk_circuit), optimization_level=0)
        return compiled, f"pytket.extensions.qiskit bridge -> {pass_name}"

    import pytket.qasm as tket_qasm
    from qiskit import qasm2

    lowered = _with_target_basis(circuit, optimization_level=0)
    tk_circuit = tket_qasm.circuit_from_qasm_str(qasm2.dumps(lowered))
    PassClass().apply(tk_circuit)
    compiled = _qasm2_cleanup_to_qiskit(tket_qasm.circuit_to_qasm_str(tk_circuit))
    return compiled, f"qasm2 fallback bridge -> {pass_name}"


def compile_tket_fullpeephole(circuit):
    return _run_tket_pass(circuit, "FullPeepholeOptimise")


def compile_tket_paulisimp(circuit):
    return _run_tket_pass(circuit, "PauliSimp")


def compile_tket_guided_paulisimp(circuit):
    return _run_tket_pass(circuit, "GuidedPauliSimp")


def compile_ucc(circuit, *, disable_fourier: bool):
    try:
        import ucc
    except Exception as exc:
        raise RuntimeError(f"ucc import unavailable: {exc}") from exc

    old_value = os.environ.get("UCC_DISABLE_FOURIER_LAYER_IR")
    if disable_fourier:
        os.environ["UCC_DISABLE_FOURIER_LAYER_IR"] = "1"
    else:
        os.environ.pop("UCC_DISABLE_FOURIER_LAYER_IR", None)
    try:
        compiled = ucc.compile(
            circuit,
            return_format="qiskit",
            target_gateset=set(TARGET_BASIS),
        )
    finally:
        if old_value is None:
            os.environ.pop("UCC_DISABLE_FOURIER_LAYER_IR", None)
        else:
            os.environ["UCC_DISABLE_FOURIER_LAYER_IR"] = old_value
    flag = "UCC_DISABLE_FOURIER_LAYER_IR=1" if disable_fourier else "Fourier IR enabled"
    return compiled, f"ucc.compile with {flag}"


def _qubit_index(circuit, qubit) -> int:
    return circuit.find_bit(qubit).index


def _canonical_angle(angle: float) -> float:
    period = 2.0 * math.pi
    wrapped = (angle + math.pi) % period - math.pi
    if abs(wrapped) <= 1e-12:
        return 0.0
    return wrapped


def _is_full_h_layer(circuit, instructions) -> bool:
    if len(instructions) != circuit.num_qubits:
        return False
    seen = set()
    for instruction in instructions:
        if instruction.operation.name != "h" or len(instruction.qubits) != 1:
            return False
        seen.add(_qubit_index(circuit, instruction.qubits[0]))
    return seen == set(range(circuit.num_qubits))


def compile_phase_poly_reference(circuit):
    qiskit = _import_qiskit()
    QuantumCircuit = qiskit["QuantumCircuit"]
    num_qubits = circuit.num_qubits
    if len(circuit.data) < 2 * num_qubits:
        raise RuntimeError("Circuit is too small to contain H-D-H layers")
    prefix = circuit.data[:num_qubits]
    suffix = circuit.data[-num_qubits:]
    if not _is_full_h_layer(circuit, prefix):
        raise RuntimeError("Expected a full leading H layer")
    if not _is_full_h_layer(circuit, suffix):
        raise RuntimeError("Expected a full trailing H layer")

    rz_angles = {qubit: 0.0 for qubit in range(num_qubits)}
    cp_angles: dict[tuple[int, int], float] = {}
    for instruction in circuit.data[num_qubits:-num_qubits]:
        name = instruction.operation.name
        qargs = [_qubit_index(circuit, qubit) for qubit in instruction.qubits]
        if name == "rz" and len(qargs) == 1:
            rz_angles[qargs[0]] += float(instruction.operation.params[0])
        elif name == "cp" and len(qargs) == 2:
            key = tuple(qargs)
            cp_angles[key] = cp_angles.get(key, 0.0) + float(
                instruction.operation.params[0]
            )
        else:
            raise RuntimeError(
                "Phase-polynomial reference only supports middle-layer rz/cp; "
                f"found {name}"
            )

    aggregated = QuantumCircuit(num_qubits)
    active_terms = 0
    for qubit in range(num_qubits):
        aggregated.h(qubit)
    for qubit in range(num_qubits):
        angle = _canonical_angle(rz_angles[qubit])
        if angle:
            aggregated.rz(angle, qubit)
            active_terms += 1
    for (control, target), raw_angle in sorted(cp_angles.items()):
        angle = _canonical_angle(raw_angle)
        if angle:
            aggregated.cp(angle, control, target)
            active_terms += 1
    for qubit in range(num_qubits):
        aggregated.h(qubit)
    compiled = _with_target_basis(aggregated, optimization_level=0)
    return compiled, f"aggregated {active_terms} active commuting phase terms before lowering"


COMPILE_DISPATCH = {
    "qiskit_opt3": compile_qiskit_opt3,
    "qiskit_commutative_inverse": compile_qiskit_commutative_inverse,
    "pyzx_configured": compile_pyzx_configured,
    "pyzx_full_reduce": compile_pyzx_full_reduce,
    "tket_fullpeephole": compile_tket_fullpeephole,
    "tket_paulisimp": compile_tket_paulisimp,
    "tket_guided_paulisimp": compile_tket_guided_paulisimp,
    "phase_poly_reference": compile_phase_poly_reference,
}


def run_compile_method(method_key: str, circuit):
    if method_key == "semantic_ucc":
        return compile_ucc(circuit, disable_fourier=False)
    if method_key == "no_fourier_ucc":
        return compile_ucc(circuit, disable_fourier=True)
    if method_key in COMPILE_DISPATCH:
        return COMPILE_DISPATCH[method_key](circuit)
    raise RuntimeError(f"Unsupported method key: {method_key}")


def add_resource_fields(row: dict[str, Any]) -> None:
    rotations = row.get("rz_rotation_count")
    if rotations is None:
        row["t_proxy_1e_6"] = None
        row["t_proxy_1e_10"] = None
        row["t_proxy_1e_12"] = None
        return
    for eps, field in (
        (1e-6, "t_proxy_1e_6"),
        (1e-10, "t_proxy_1e_10"),
        (1e-12, "t_proxy_1e_12"),
    ):
        row[field] = int(math.ceil(3 * math.log2(1 / eps)) * rotations)


def worker_source_command(args: argparse.Namespace) -> str:
    parts = [
        str(THIS_FILE.relative_to(REPO_ROOT)),
        "--worker",
        "--experiment-family",
        args.experiment_family,
        "--method-key",
        args.method_key,
        "--timeout-s",
        str(args.timeout_s),
    ]
    if args.size is not None:
        parts.extend(["--size", str(args.size)])
    if args.repeats is not None:
        parts.extend(["--repeats", str(args.repeats)])
    return " ".join(parts)


def run_worker(args: argparse.Namespace) -> dict[str, Any]:
    if args.experiment_family == "correctness_extension":
        case = build_fourier_phase_sandwich(
            experiment_family=args.experiment_family,
            repeats=args.repeats,
        )
    else:
        case = build_fourier_phase_sandwich(
            experiment_family=args.experiment_family,
            target_gates=args.size,
        )
    row = build_base_row(
        case=case,
        method_key=args.method_key,
        timeout_s=args.timeout_s,
        source_command=worker_source_command(args),
    )
    start = time.perf_counter()
    try:
        compiled, note = run_compile_method(args.method_key, case.circuit)
        metrics = circuit_metrics(compiled)
        row.update(metrics)
        row["status"] = "completed"
        row["notes"] = note
        if args.experiment_family == "resource_consequence_check":
            add_resource_fields(row)
        if args.experiment_family == "correctness_extension":
            qiskit = _import_qiskit()
            equivalent = bool(qiskit["Operator"](case.circuit).equiv(qiskit["Operator"](compiled)))
            row["is_equivalent_up_to_global_phase"] = equivalent
            row["notes"] = f"{note}; Operator.equiv={equivalent}"
    except RuntimeError as exc:
        message = str(exc)
        row["status"] = "unavailable" if "unavailable" in message.lower() else "error"
        row["notes"] = message
        if args.experiment_family == "resource_consequence_check":
            add_resource_fields(row)
    except Exception as exc:
        row["status"] = "error"
        row["notes"] = f"{type(exc).__name__}: {exc}"
        row["traceback"] = traceback.format_exc(limit=8)
        if args.experiment_family == "resource_consequence_check":
            add_resource_fields(row)
    row["wall_time_s"] = round(time.perf_counter() - start, 3)
    return row


def launch_worker(
    *,
    python_executable: str,
    experiment_family: str,
    method_key: str,
    timeout_s: int,
    size: int | None = None,
    repeats: int | None = None,
) -> dict[str, Any]:
    cmd = [
        python_executable,
        str(THIS_FILE),
        "--worker",
        "--experiment-family",
        experiment_family,
        "--method-key",
        method_key,
        "--timeout-s",
        str(timeout_s),
    ]
    if size is not None:
        cmd.extend(["--size", str(size)])
    if repeats is not None:
        cmd.extend(["--repeats", str(repeats)])

    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    env.setdefault("XDG_CONFIG_HOME", "/tmp/xdg-config")
    env.setdefault("XDG_CACHE_HOME", "/tmp/xdg-cache")
    env.setdefault("MPLCONFIGDIR", "/tmp/mplconfig")

    start = time.perf_counter()
    process = subprocess.Popen(
        cmd,
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        case = build_fourier_phase_sandwich(
            experiment_family=experiment_family,
            repeats=repeats,
            target_gates=size,
        )
        row = build_base_row(
            case=case,
            method_key=method_key,
            timeout_s=timeout_s,
            source_command=" ".join(cmd),
        )
        row["status"] = "timeout"
        row["wall_time_s"] = round(time.perf_counter() - start, 3)
        row["notes"] = f"worker exceeded uniform timeout budget of {timeout_s} s"
        if experiment_family == "resource_consequence_check":
            add_resource_fields(row)
        return row

    if process.returncode != 0:
        case = build_fourier_phase_sandwich(
            experiment_family=experiment_family,
            repeats=repeats,
            target_gates=size,
        )
        row = build_base_row(
            case=case,
            method_key=method_key,
            timeout_s=timeout_s,
            source_command=" ".join(cmd),
        )
        row["status"] = "error"
        row["wall_time_s"] = round(time.perf_counter() - start, 3)
        row["notes"] = (stderr or stdout or f"worker exited {process.returncode}").strip()
        if experiment_family == "resource_consequence_check":
            add_resource_fields(row)
        return row

    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        case = build_fourier_phase_sandwich(
            experiment_family=experiment_family,
            repeats=repeats,
            target_gates=size,
        )
        row = build_base_row(
            case=case,
            method_key=method_key,
            timeout_s=timeout_s,
            source_command=" ".join(cmd),
        )
        row["status"] = "error"
        row["wall_time_s"] = round(time.perf_counter() - start, 3)
        row["notes"] = f"invalid worker JSON; stdout={stdout[:500]!r}; stderr={stderr[:500]!r}"
        if experiment_family == "resource_consequence_check":
            add_resource_fields(row)
        return row


def run_family(
    *,
    python_executable: str,
    experiment_family: str,
    methods: tuple[str, ...],
    sizes: tuple[int, ...],
    timeout_s: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for size in sizes:
        for method_key in methods:
            print(
                f"{experiment_family}: size={size} method={method_key} timeout={timeout_s}s",
                file=sys.stderr,
                flush=True,
            )
            rows.append(
                launch_worker(
                    python_executable=python_executable,
                    experiment_family=experiment_family,
                    method_key=method_key,
                    size=size,
                    timeout_s=timeout_s,
                )
            )
    return rows


def run_correctness_family(
    *,
    python_executable: str,
    repeats: int,
    timeout_s: int,
) -> list[dict[str, Any]]:
    rows = []
    for method_key in CORRECTNESS_METHODS:
        print(
            f"correctness_extension: repeats={repeats} method={method_key} timeout={timeout_s}s",
            file=sys.stderr,
            flush=True,
        )
        rows.append(
            launch_worker(
                python_executable=python_executable,
                experiment_family="correctness_extension",
                method_key=method_key,
                repeats=repeats,
                timeout_s=timeout_s,
            )
        )
    return rows


def strict_completed_win_count(
    rows: list[dict[str, Any]],
    candidate: str = "semantic_ucc",
    baseline: str = "qiskit_opt3",
) -> tuple[int, int, int]:
    by_instance: dict[tuple[Any, Any], dict[str, dict[str, Any]]] = {}
    for row in rows:
        key = (row.get("instance_name"), row.get("size"))
        by_instance.setdefault(key, {})[row["method_key"]] = row
    wins = 0
    completed_pairs = 0
    baseline_timeouts = 0
    for methods in by_instance.values():
        cand = methods.get(candidate)
        base = methods.get(baseline)
        if not cand or not base:
            continue
        if cand.get("status") == "completed" and base.get("status") == "timeout":
            baseline_timeouts += 1
        if cand.get("status") != "completed" or base.get("status") != "completed":
            continue
        completed_pairs += 1
        cand_key = (cand.get("gate_count"), cand.get("depth"), cand.get("cx_count"))
        base_key = (base.get("gate_count"), base.get("depth"), base.get("cx_count"))
        if cand_key < base_key:
            wins += 1
    return wins, completed_pairs, baseline_timeouts


def write_json(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n")


def write_results_md(path: Path, title: str, rows: list[dict[str, Any]], timeout_s: int) -> None:
    lines = [
        f"# {title}",
        "",
        f"Uniform per-method per-instance timeout budget: `{timeout_s}` seconds.",
        "",
        "| Instance | Size | r | Method | Status | Gates | Depth | CX | Rotations | Wall time | Notes |",
        "|---|---:|---:|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        def fmt(value):
            if value is None:
                return "-"
            if isinstance(value, float):
                return f"{value:.3f}"
            return str(value)

        lines.append(
            "| {instance} | {size} | {r} | {method} | {status} | {gates} | {depth} | {cx} | {rot} | {wall} | {notes} |".format(
                instance=row["instance_name"],
                size=fmt(row["size"]),
                r=fmt(row["r"]),
                method=row["paper_method_name"],
                status=row["status"],
                gates=fmt(row["gate_count"]),
                depth=fmt(row["depth"]),
                cx=fmt(row["cx_count"]),
                rot=fmt(row["rz_rotation_count"]),
                wall=fmt(row["wall_time_s"]),
                notes=str(row.get("notes", "")).replace("\n", " ")[:220],
            )
        )
    if rows and rows[0]["experiment_family"] == "main_external_baselines":
        wins, completed_pairs, timeout_cells = strict_completed_win_count(rows)
        lines.extend(
            [
                "",
                "## Timeout-aware win accounting",
                "",
                f"- Strict structural wins over `qiskit opt3` among completed paired cells: `{wins}/{completed_pairs}`.",
                f"- `qiskit opt3` timeout cells with completed semantic UCC are reported separately as scalability evidence: `{timeout_cells}`.",
                "- Timeout cells are not counted as lexicographic structural wins.",
            ]
        )
    if rows and rows[0]["experiment_family"] == "resource_consequence_check":
        lines.extend(
            [
                "",
                "## Resource proxy fields",
                "",
                "Completed rows in the JSON include `t_proxy_1e_6`, `t_proxy_1e_10`, and `t_proxy_1e_12`, computed from the target-basis rotation count.",
            ]
        )
    path.write_text("\n".join(lines) + "\n")


def output_name(base_name: str, smoke: bool) -> str:
    if smoke:
        return f"smoke_{base_name}"
    return base_name


def write_method_name_map(timeout_s: int, mode: str) -> None:
    if mode == "full":
        budget_text = f"{timeout_s} s"
    else:
        budget_text = f"full default {DEFAULT_FULL_TIMEOUT_S} s; current smoke rows {timeout_s} s"
    lines = [
        "# Round 3 Method Name Map",
        "",
        f"Generated: `{utc_now()}`",
        f"Mode when generated: `{mode}`",
        f"Full-run default comparable timeout: `{DEFAULT_FULL_TIMEOUT_S}` seconds per method per instance.",
        f"Current run timeout budget recorded in rows: `{timeout_s}` seconds per method per instance.",
        "",
        "| JSON key | Paper name | Tool/pass sequence | Artifact flags | Timeout budget disclosure | Notes |",
        "|---|---|---|---|---:|---|",
    ]
    for key in METHOD_INFO:
        info = METHOD_INFO[key]
        lines.append(
            f"| `{info.key}` | {info.paper_name} | {info.tool_sequence} | `{info.artifact_flags}` | {budget_text} | {info.notes} |"
        )
    (OUTPUT_DIR / "method_name_map.md").write_text("\n".join(lines) + "\n")


def write_baseline_call_sequences(timeout_s: int, mode: str) -> None:
    lines = [
        "# Round 3 Baseline Call Sequences",
        "",
        f"Generated: `{utc_now()}`",
        f"Mode when generated: `{mode}`",
        f"Full-run default uniform timeout: `{DEFAULT_FULL_TIMEOUT_S}` seconds.",
        f"Uniform timeout disclosed in current output rows: `{timeout_s}` seconds.",
        "",
        "All pipelines emit target-basis Qiskit circuits over `{cx, rx, ry, rz, h}` before metrics are recorded.",
        "",
        "## qiskit opt3",
        "",
        "```python",
        "compiled = qiskit.transpile(",
        "    circuit,",
        "    basis_gates=TARGET_BASIS,",
        "    optimization_level=3,",
        "    layout_method=\"trivial\",",
        "    routing_method=\"none\",",
        ")",
        "```",
        "",
        "## PyZX configured bridge",
        "",
        "```python",
        "qasm_str = qiskit.qasm2.dumps(circuit)",
        "zxc = pyzx.Circuit.from_qasm(qasm_str)",
        "zxc = zxc.to_basic_gates()",
        "pyzx.optimize.basic_optimization(zxc)",
        "compiled = qiskit.transpile(qiskit.qasm2.loads(zxc.to_qasm()), basis_gates=TARGET_BASIS, optimization_level=0)",
        "```",
        "",
        "## PyZX full_reduce",
        "",
        "```python",
        "qasm_str = qiskit.qasm2.dumps(circuit)",
        "zxc = pyzx.Circuit.from_qasm(qasm_str).to_basic_gates()",
        "graph = zxc.to_graph()",
        "pyzx.simplify.full_reduce(graph)",
        "extracted = pyzx.extract_circuit(graph.copy()).to_basic_gates()",
        "compiled = qiskit.transpile(qiskit.qasm2.loads(extracted.to_qasm()), basis_gates=TARGET_BASIS, optimization_level=0)",
        "```",
        "",
        "## TKET FullPeephole",
        "",
        "```python",
        "tk_circuit = qiskit_to_tk(circuit)  # if pytket.extensions.qiskit is importable",
        "pytket.passes.FullPeepholeOptimise().apply(tk_circuit)",
        "compiled = qiskit.transpile(tk_to_qiskit(tk_circuit), basis_gates=TARGET_BASIS, optimization_level=0)",
        "```",
        "",
        "When the qiskit extension is not importable, the runner uses the disclosed fallback:",
        "",
        "```python",
        "lowered = qiskit.transpile(circuit, basis_gates=TARGET_BASIS, optimization_level=0)",
        "tk_circuit = pytket.qasm.circuit_from_qasm_str(qiskit.qasm2.dumps(lowered))",
        "pytket.passes.FullPeepholeOptimise().apply(tk_circuit)",
        "compiled = qiskit.transpile(qiskit.qasm2.loads(pytket.qasm.circuit_to_qasm_str(tk_circuit)), basis_gates=TARGET_BASIS, optimization_level=0)",
        "```",
        "",
        "## TKET PauliSimp",
        "",
        "Same bridge/fallback as TKET FullPeephole, with:",
        "",
        "```python",
        "pytket.passes.PauliSimp().apply(tk_circuit)",
        "```",
        "",
        "## TKET GuidedPauliSimp",
        "",
        "Same bridge/fallback as TKET FullPeephole, with:",
        "",
        "```python",
        "pytket.passes.GuidedPauliSimp().apply(tk_circuit)",
        "```",
    ]
    (OUTPUT_DIR / "baseline_call_sequences.md").write_text("\n".join(lines) + "\n")


def probe_module(name: str) -> str:
    try:
        module = __import__(name, fromlist=["*"])
        return str(getattr(module, "__version__", "available"))
    except Exception as exc:
        return f"unavailable: {type(exc).__name__}: {exc}"


def write_environment_snapshot(path: Path, timeout_s: int, mode: str) -> None:
    tket_passes = []
    try:
        from pytket import passes as tket_pass_module

        for pass_name in ("FullPeepholeOptimise", "PauliSimp", "GuidedPauliSimp"):
            tket_passes.append(f"{pass_name}={hasattr(tket_pass_module, pass_name)}")
    except Exception as exc:
        tket_passes.append(f"pytket.passes unavailable: {exc}")
    try:
        git_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(REPO_ROOT),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        git_commit = "unavailable"
    try:
        git_status = subprocess.check_output(
            ["git", "status", "--short"],
            cwd=str(REPO_ROOT),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        git_status = "unavailable"

    lines = [
        "# Round 3 Environment Snapshot",
        "",
        f"Generated: `{utc_now()}`",
        f"Mode: `{mode}`",
        f"Uniform timeout budget in this run: `{timeout_s}` seconds",
        f"Repository root: `{REPO_ROOT}`",
        f"Git commit: `{git_commit}`",
        "",
        "## Runtime",
        "",
        f"- Python executable: `{sys.executable}`",
        f"- Python version: `{sys.version.split()[0]}`",
        f"- Platform: `{platform.platform()}`",
        f"- Machine: `{platform.machine()}`",
        "",
        "## Package Versions / Availability",
        "",
        f"- qiskit: `{probe_module('qiskit')}`",
        f"- pyzx: `{probe_module('pyzx')}`",
        f"- pytket: `{probe_module('pytket')}`",
        f"- pytket.extensions.qiskit: `{probe_module('pytket.extensions.qiskit')}`",
        f"- ucc: `{probe_module('ucc')}`",
        f"- TKET passes: `{', '.join(tket_passes)}`",
        "",
        "## Git Working Tree Snapshot",
        "",
        "```text",
        git_status or "clean",
        "```",
    ]
    path.write_text("\n".join(lines) + "\n")


def write_table_provenance_map(path: Path, timeout_s: int, mode: str, prefix: str) -> None:
    lines = [
        "# Round 3 Table/Figure Provenance Map",
        "",
        f"Generated: `{utc_now()}`",
        f"Mode: `{mode}`",
        f"Uniform timeout budget to disclose for comparable external-baseline cells: `{timeout_s}` seconds.",
        "",
        "| Manuscript surface | New source file | Methods / rows | Required caption note |",
        "|---|---|---|---|",
        f"| Main fixed-width Fourier witness table | `{prefix}round3_main_external_baselines_results.json` and `.md` | qiskit opt3, qiskit commutative inverse, PyZX configured bridge, PyZX full_reduce, TKET FullPeephole, TKET PauliSimp, TKET GuidedPauliSimp, semantic UCC, phase-polynomial reference | State the uniform timeout and do not count timeout cells as lexicographic wins. |",
        f"| No-Fourier ablation table | `{prefix}round3_fourier_ablation_completion_results.json` and `.md` | semantic UCC, no-Fourier UCC, qiskit opt3, qiskit commutative inverse, phase-polynomial reference | Report completed no-Fourier output gate counts; use timeout only for genuinely unfinished rows. |",
        f"| Resource-consequence table | `{prefix}round3_resource_consequence_check_results.json` and `.md` | semantic-first, phase-poly reference, materialize-first qiskit opt3, no-Fourier UCC | Use the same row provenance and timeout as the ablation/main rows where methods overlap. |",
        f"| Correctness certificate extension | `{prefix}round3_correctness_extension_results.json` and `.md` | semantic UCC and phase-polynomial reference at n=4, R=9999 in full mode | State whether Operator.equiv completed; if not, report timeout/error rather than implying certification. |",
        "| Figure legends | `method_name_map.md` | all method keys and paper names | Use canonical names exactly, especially `semantic UCC (Fourier-layer IR enabled)`, `artifact UCC (Fourier-layer IR disabled)`, `PyZX full_reduce`, and `qiskit opt3`. |",
        "| External-baseline prose | `baseline_call_sequences.md` | exact tool/pass calls | Disclose PyZX full_reduce and TKET PauliSimp/GuidedPauliSimp call sequences and the TKET bridge/fallback path. |",
        "| Environment/provenance appendix | `round3_environment_snapshot.md`, this map, and JSON rows | machine, package versions, method availability, source commands, timeouts | Every main experimental table should cite these files or equivalent artifact bundle paths. |",
    ]
    path.write_text("\n".join(lines) + "\n")


def write_summary_for_paper_patch(
    path: Path,
    *,
    mode: str,
    timeout_s: int,
    main_rows: list[dict[str, Any]],
    ablation_rows: list[dict[str, Any]],
) -> None:
    wins, completed_pairs, timeout_cells = strict_completed_win_count(main_rows)
    no_fourier_completed = [
        row
        for row in ablation_rows
        if row["method_key"] == "no_fourier_ucc" and row["status"] == "completed"
    ]
    lines = [
        "# Round 3 Summary For Paper Patch",
        "",
        f"Generated: `{utc_now()}`",
        f"Mode: `{mode}`",
        f"Uniform timeout budget used by these generated rows: `{timeout_s}` seconds per method per instance.",
        "",
        "Do not edit theorem statements, formal proof text, or formal-core patch from this file. This is experiment/provenance patch guidance only.",
        "",
        "## Rewrite the 42/42 claim",
        "",
        f"Replace timeout-inclusive win language with: strict structural wins among completed paired `semantic_ucc` vs `qiskit_opt3` cells are `{wins}/{completed_pairs}` in this run. Separately report qiskit timeout cells with completed semantic UCC as scalability evidence: `{timeout_cells}` cells.",
        "",
        "Timeout cells must not be counted as lexicographic wins. The lexicographic metric applies only when both compared rows have status `completed` and all structural metrics are present.",
        "",
        "## Timeout budgets",
        "",
        f"Every caption-facing statement should say that comparable external-baseline cells used a uniform `{timeout_s}` second per-method per-instance timeout in this repair run. If the full run is rerun with `--timeout-s 300`, replace the number everywhere and rely on row-level `timeout_s` values.",
        "",
        "## Method names",
        "",
        "Use the JSON keys and paper names in `method_name_map.md`. Avoid old labels such as `baseline UCC`, `optimized UCC`, `Qiskit O3`, or mixed-case `qiskit opt3` variants unless they are explicitly mapped.",
        "",
        "## Figure legends",
        "",
        "Use `semantic UCC (Fourier-layer IR enabled)`, `artifact UCC (Fourier-layer IR disabled)`, `qiskit opt3`, `PyZX configured bridge`, `PyZX full_reduce`, `TKET FullPeephole`, `TKET PauliSimp`, and `TKET GuidedPauliSimp` consistently.",
        "",
        "## PyZX and TKET descriptions",
        "",
        "Describe PyZX configured bridge and PyZX full_reduce as separate baselines. Describe TKET FullPeephole, PauliSimp, and GuidedPauliSimp separately, and disclose whether the run used the qiskit extension bridge or the qasm fallback recorded in `baseline_call_sequences.md`.",
        "",
        "## Phase-polynomial reference and Nam-style merging",
        "",
        "Describe `phase_poly_reference` as a narrow semantic-capable reference that aggregates explicit commuting-diagonal coefficients before lowering. Known rotation-merging approaches, including Nam-style rotation aggregation when the phase polynomial is available or reconstructed, belong on the semantic-capable side of the classification rather than as a local flat-pipeline counterexample.",
        "",
        "## No-Fourier ablation",
        "",
        f"Report no-Fourier UCC completed output gate counts whenever the row completes. In this run, completed no-Fourier rows: `{len(no_fourier_completed)}`. Timeout rows should remain timeout rows, with the disclosed budget, and should not be used as structural win cells.",
        "",
        "## Unfavorable results",
        "",
        "If PyZX full_reduce, TKET PauliSimp, or TKET GuidedPauliSimp recovers the bounded form, report that directly. The framing should become: default configured pipelines fail unless they instantiate or reconstruct the aggregation capability; semantic-capable modes pay the information toll and can succeed.",
    ]
    path.write_text("\n".join(lines) + "\n")


def write_run_log(
    path: Path,
    *,
    mode: str,
    timeout_s: int,
    sizes: tuple[int, ...],
    correctness_repeats: int,
    output_paths: list[Path],
) -> None:
    lines = [
        "# Round 3 Run Log",
        "",
        f"Generated: `{utc_now()}`",
        f"Mode: `{mode}`",
        f"Python executable: `{sys.executable}`",
        f"Uniform timeout: `{timeout_s}` seconds",
        f"Sizes: `{', '.join(str(size) for size in sizes)}`",
        f"Correctness repeats: `{correctness_repeats}`",
        "",
        "## Entry Points",
        "",
        "Smoke:",
        "",
        "```bash",
        "./.venv/bin/python research/round3_protocol_repair/run_round3_protocol_repair.py --smoke",
        "```",
        "",
        "Full:",
        "",
        "```bash",
        "./.venv/bin/python research/round3_protocol_repair/run_round3_protocol_repair.py --full --timeout-s 600",
        "```",
        "",
        "Full with shorter disclosed budget:",
        "",
        "```bash",
        "./.venv/bin/python research/round3_protocol_repair/run_round3_protocol_repair.py --full --timeout-s 300",
        "```",
        "",
        "## Files Written",
        "",
    ]
    for path_item in output_paths:
        lines.append(f"- `{path_item.relative_to(REPO_ROOT)}`")
    lines.extend(
        [
            "",
            "Old frozen result files were not overwritten by this workflow.",
        ]
    )
    path.write_text("\n".join(lines) + "\n")


def run_parent(args: argparse.Namespace) -> None:
    mode = "smoke" if args.smoke else "full"
    timeout_s = args.timeout_s
    if timeout_s is None:
        timeout_s = DEFAULT_SMOKE_TIMEOUT_S if args.smoke else DEFAULT_FULL_TIMEOUT_S
    sizes = tuple(args.sizes) if args.sizes else (SMOKE_SIZES if args.smoke else FULL_SIZES)
    correctness_repeats = (
        args.correctness_repeats
        if args.correctness_repeats is not None
        else (CORRECTNESS_SMOKE_REPEATS if args.smoke else CORRECTNESS_FULL_REPEATS)
    )
    prefix = "smoke_" if args.smoke else ""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_method_name_map(timeout_s, mode)
    write_baseline_call_sequences(timeout_s, mode)

    main_rows = run_family(
        python_executable=args.python_executable,
        experiment_family="main_external_baselines",
        methods=MAIN_METHODS,
        sizes=sizes,
        timeout_s=timeout_s,
    )
    ablation_rows = run_family(
        python_executable=args.python_executable,
        experiment_family="fourier_ablation_completion",
        methods=ABLATION_METHODS,
        sizes=sizes,
        timeout_s=timeout_s,
    )
    resource_rows = run_family(
        python_executable=args.python_executable,
        experiment_family="resource_consequence_check",
        methods=RESOURCE_METHODS,
        sizes=sizes,
        timeout_s=timeout_s,
    )
    correctness_rows = run_correctness_family(
        python_executable=args.python_executable,
        repeats=correctness_repeats,
        timeout_s=timeout_s,
    )

    output_paths: list[Path] = [
        OUTPUT_DIR / "method_name_map.md",
        OUTPUT_DIR / "baseline_call_sequences.md",
    ]

    result_specs = [
        (
            output_name("round3_main_external_baselines_results.json", args.smoke),
            output_name("round3_main_external_baselines_results.md", args.smoke),
            "Round 3 Main External Baselines Results",
            main_rows,
        ),
        (
            output_name("round3_fourier_ablation_completion_results.json", args.smoke),
            output_name("round3_fourier_ablation_completion_results.md", args.smoke),
            "Round 3 Fourier Ablation Completion Results",
            ablation_rows,
        ),
        (
            output_name("round3_resource_consequence_check_results.json", args.smoke),
            output_name("round3_resource_consequence_check_results.md", args.smoke),
            "Round 3 Resource Consequence Check Results",
            resource_rows,
        ),
        (
            output_name("round3_correctness_extension_results.json", args.smoke),
            output_name("round3_correctness_extension_results.md", args.smoke),
            "Round 3 Correctness Extension Results",
            correctness_rows,
        ),
    ]
    for json_name, md_name, title, rows in result_specs:
        json_path = OUTPUT_DIR / json_name
        md_path = OUTPUT_DIR / md_name
        write_json(json_path, rows)
        write_results_md(md_path, title, rows, timeout_s)
        output_paths.extend([json_path, md_path])

    table_map_path = OUTPUT_DIR / output_name("round3_table_provenance_map.md", args.smoke)
    env_path = OUTPUT_DIR / output_name("round3_environment_snapshot.md", args.smoke)
    summary_path = OUTPUT_DIR / output_name("round3_summary_for_paper_patch.md", args.smoke)
    log_path = OUTPUT_DIR / output_name("round3_run_log.md", args.smoke)
    write_table_provenance_map(table_map_path, timeout_s, mode, prefix)
    write_environment_snapshot(env_path, timeout_s, mode)
    write_summary_for_paper_patch(
        summary_path,
        mode=mode,
        timeout_s=timeout_s,
        main_rows=main_rows,
        ablation_rows=ablation_rows,
    )
    output_paths.extend([table_map_path, env_path, summary_path])
    write_run_log(
        log_path,
        mode=mode,
        timeout_s=timeout_s,
        sizes=sizes,
        correctness_repeats=correctness_repeats,
        output_paths=output_paths + [log_path],
    )
    output_paths.append(log_path)

    print("Round 3 protocol repair run complete.")
    for path in output_paths:
        print(path.relative_to(REPO_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Round 3 experimental protocol repair runner.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true", help="Run tiny schema/import smoke tests.")
    mode.add_argument("--full", action="store_true", help="Run the full repaired protocol.")
    mode.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--timeout-s", type=int, default=None)
    parser.add_argument("--python-executable", default=sys.executable)
    parser.add_argument("--sizes", type=int, nargs="*")
    parser.add_argument("--correctness-repeats", type=int)
    parser.add_argument("--experiment-family", choices=(
        "main_external_baselines",
        "fourier_ablation_completion",
        "resource_consequence_check",
        "correctness_extension",
    ))
    parser.add_argument("--method-key", choices=tuple(METHOD_INFO))
    parser.add_argument("--size", type=int)
    parser.add_argument("--repeats", type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.worker:
        if args.timeout_s is None:
            args.timeout_s = DEFAULT_FULL_TIMEOUT_S
        if args.experiment_family is None or args.method_key is None:
            raise SystemExit("--worker requires --experiment-family and --method-key")
        if args.experiment_family == "correctness_extension":
            if args.repeats is None:
                raise SystemExit("--worker correctness_extension requires --repeats")
        elif args.size is None:
            raise SystemExit("--worker requires --size")
        print(json.dumps(run_worker(args), sort_keys=True))
        return
    run_parent(args)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Round 6 unbounded-witness and public-baseline experiment harness.

Every method/instance runs in a fresh worker process. The parent enforces one
uniform wall-clock budget and checkpoints after every cell.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import signal
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


THIS_FILE = Path(__file__).resolve()
OUT = THIS_FILE.parent
ROOT = THIS_FILE.parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TARGET_BASIS = ["cx", "rx", "ry", "rz", "h"]
FULL_SIZES = (4_000, 10_000, 20_000, 50_000, 100_000)
SMOKE_SIZES = (48,)
DEFAULT_TIMEOUT_S = 600
SMOKE_TIMEOUT_S = 30
STAQ_BINARY = OUT / "tools" / "staq_rotation_optimizer"
STAQ_SOURCE = OUT / "tools" / "staq"
OPERATOR_ATOL = 1e-9
OPERATOR_RTOL = 1e-9

FAMILIES = ("rational_cp", "unbounded_independent_pauli")
METHODS = (
    "semantic_ucc",
    "qiskit_opt3",
    "pyzx_full_reduce",
    "tket_guided_paulisimp",
    "tket_paulisimp_unrebased",
    "tket_paulisimp_rebased",
    "staq_rotation_folding",
)

METHOD_NAMES = {
    "semantic_ucc": "semantic UCC (Fourier-layer IR enabled)",
    "qiskit_opt3": "qiskit opt3",
    "pyzx_full_reduce": "PyZX full_reduce",
    "tket_guided_paulisimp": "TKET GuidedPauliSimp",
    "tket_paulisimp_unrebased": "TKET PauliSimp (unrebased configuration)",
    "tket_paulisimp_rebased": "TKET PauliSimp (rebased)",
    "staq_rotation_folding": "staq rotation folding",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def qiskit_imports() -> dict[str, Any]:
    from qiskit import QuantumCircuit, qasm2, transpile
    from qiskit.quantum_info import Operator

    return {
        "QuantumCircuit": QuantumCircuit,
        "qasm2": qasm2,
        "transpile": transpile,
        "Operator": Operator,
    }


def append_h_layer(circuit) -> None:
    for qubit in range(circuit.num_qubits):
        circuit.h(qubit)


def append_rational_cp_block(circuit) -> None:
    for qubit in range(4):
        circuit.rz(math.pi / (7 + qubit), qubit)
    for control in range(4):
        for target in range(control + 1, 4):
            circuit.cp(math.pi / (11 + control + target), control, target)


def append_unbounded_pauli_block(circuit) -> None:
    pair_terms = (
        (math.pi * math.sqrt(2) / 11, 0, 1),
        (math.pi / 13, 1, 2),
        (math.pi / 17, 2, 3),
    )
    for theta, left, right in pair_terms:
        circuit.rz(theta, left)
        circuit.rz(theta, right)
        circuit.cp(-2 * theta, left, right)
    circuit.rz(math.pi / 19, 0)


def build_case(family: str, requested_gates: int) -> tuple[Any, dict[str, Any]]:
    if family not in FAMILIES:
        raise KeyError(f"unknown family {family}")
    qiskit = qiskit_imports()
    circuit = qiskit["QuantumCircuit"](4)
    block_gate_count = 10
    boundary_gate_count = 8
    repeats = max(1, (requested_gates - boundary_gate_count) // block_gate_count)
    append_h_layer(circuit)
    block_builder = (
        append_rational_cp_block
        if family == "rational_cp"
        else append_unbounded_pauli_block
    )
    for _ in range(repeats):
        block_builder(circuit)
    append_h_layer(circuit)
    actual_gates = len(circuit.data)
    expected = boundary_gate_count + block_gate_count * repeats
    if actual_gates != expected:
        raise AssertionError(f"actual gate count {actual_gates} != expected {expected}")
    circuit.name = f"{family}_n4_r{repeats}"
    metadata = {
        "family_key": family,
        "instance_name": circuit.name,
        "requested_gates": requested_gates,
        "actual_input_gates": actual_gates,
        "r": repeats,
        "n": 4,
        "m": 10 if family == "rational_cp" else 4,
        "support_rank_f2": 4,
        "block_gate_count": block_gate_count,
        "boundary_gate_count": boundary_gate_count,
        "angle_specification": (
            "rational Qiskit RZ/CP angles; exact global-phase period T=131040"
            if family == "rational_cp"
            else "theta=(pi*sqrt(2)/11,pi/13,pi/17,pi/19); first ratio is symbolically irrational"
        ),
        "unbounded_noncollision_by_proposition": family
        == "unbounded_independent_pauli",
        "support_rank_verified": family == "unbounded_independent_pauli",
    }
    return circuit, metadata


def lower_target(circuit, optimization_level: int = 0):
    qiskit = qiskit_imports()
    return qiskit["transpile"](
        circuit,
        basis_gates=TARGET_BASIS,
        optimization_level=optimization_level,
        layout_method="trivial" if optimization_level else None,
        routing_method="none" if optimization_level else None,
    )


def metrics(circuit) -> dict[str, Any]:
    counts = circuit.count_ops()
    return {
        "gate_count": int(sum(counts.values())),
        "depth": int(circuit.depth()),
        "cx_count": int(counts.get("cx", 0)),
        "rotation_count": int(
            counts.get("rx", 0) + counts.get("ry", 0) + counts.get("rz", 0)
        ),
        "gate_types": sorted(str(key) for key in counts),
    }


def compile_semantic_ucc(circuit):
    import ucc

    old = os.environ.pop("UCC_DISABLE_FOURIER_LAYER_IR", None)
    try:
        compiled = ucc.compile(
            circuit,
            return_format="qiskit",
            target_gateset=set(TARGET_BASIS),
        )
    finally:
        if old is not None:
            os.environ["UCC_DISABLE_FOURIER_LAYER_IR"] = old
    return compiled, "ucc.compile; Fourier-layer IR enabled"


def compile_qiskit_opt3(circuit):
    return lower_target(circuit, 3), (
        "qiskit.transpile(basis_gates=TARGET_BASIS, optimization_level=3, "
        "layout_method='trivial', routing_method='none')"
    )


def qasm_output_to_qiskit(qasm_text: str):
    qiskit = qiskit_imports()
    lines = qasm_text.splitlines()
    while lines and lines[0].startswith("Let "):
        lines.pop(0)
    return lower_target(qiskit["qasm2"].loads("\n".join(lines)), 0)


def compile_pyzx_full_reduce(circuit):
    import pyzx as zx

    qiskit = qiskit_imports()
    zxc = zx.Circuit.from_qasm(qiskit["qasm2"].dumps(circuit)).to_basic_gates()
    graph = zxc.to_graph()
    zx.simplify.full_reduce(graph)
    extracted = zx.extract_circuit(graph.copy()).to_basic_gates()
    return qasm_output_to_qiskit(extracted.to_qasm()), (
        "QASM2 -> PyZX basic gates -> graph -> full_reduce -> extract -> target basis"
    )


def tket_input(circuit):
    try:
        from pytket.extensions.qiskit import qiskit_to_tk, tk_to_qiskit

        return qiskit_to_tk(circuit), "pytket.extensions.qiskit direct bridge", tk_to_qiskit
    except Exception:
        import pytket.qasm as tket_qasm

        qiskit = qiskit_imports()
        lowered = lower_target(circuit, 0)
        tk_circuit = tket_qasm.circuit_from_qasm_str(
            qiskit["qasm2"].dumps(lowered)
        )

        def convert_back(value):
            return qasm_output_to_qiskit(tket_qasm.circuit_to_qasm_str(value))

        return tk_circuit, "QASM2 target-basis fallback bridge", convert_back


def compile_tket_guided(circuit):
    from pytket import passes

    tk_circuit, bridge, convert_back = tket_input(circuit)
    passes.GuidedPauliSimp().apply(tk_circuit)
    return lower_target(convert_back(tk_circuit), 0), f"{bridge} -> GuidedPauliSimp"


def compile_tket_paulisimp_unrebased(circuit):
    from pytket import passes

    tk_circuit, bridge, convert_back = tket_input(circuit)
    passes.PauliSimp().apply(tk_circuit)
    return lower_target(convert_back(tk_circuit), 0), f"{bridge} -> PauliSimp"


def compile_tket_paulisimp_rebased(circuit):
    from pytket import passes
    from pytket.circuit import OpType

    tk_circuit, bridge, convert_back = tket_input(circuit)
    sequence = (
        passes.DecomposeBoxes(),
        passes.AutoRebase({OpType.CX, OpType.Rz, OpType.Rx}),
        passes.RemoveRedundancies(),
        passes.PauliSimp(),
        passes.RemoveRedundancies(),
    )
    for compiler_pass in sequence:
        compiler_pass.apply(tk_circuit)
    return lower_target(convert_back(tk_circuit), 0), (
        f"{bridge} -> DecomposeBoxes -> AutoRebase({{CX,Rz,Rx}}) -> "
        "RemoveRedundancies -> PauliSimp -> RemoveRedundancies"
    )


def compile_staq_rotation_folding(circuit):
    if not STAQ_BINARY.is_file():
        raise RuntimeError(f"public staq binary unavailable at {STAQ_BINARY}")
    qiskit = qiskit_imports()
    lowered = lower_target(circuit, 0)
    qasm_input = qiskit["qasm2"].dumps(lowered)
    process = subprocess.run(
        [str(STAQ_BINARY)],
        input=qasm_input,
        text=True,
        capture_output=True,
        check=False,
    )
    if process.returncode != 0:
        raise RuntimeError(
            f"staq rotation optimizer exited {process.returncode}: {process.stderr.strip()}"
        )
    if not process.stdout.strip():
        raise RuntimeError("staq rotation optimizer produced empty output")
    compiled = qasm_output_to_qiskit(process.stdout)
    return compiled, (
        "qiskit opt0 to {cx,rx,ry,rz,h} QASM2 -> public staq "
        "rotation optimizer -> QASM2 -> qiskit opt0 target-basis cleanup"
    )


COMPILE: dict[str, Callable[[Any], tuple[Any, str]]] = {
    "semantic_ucc": compile_semantic_ucc,
    "qiskit_opt3": compile_qiskit_opt3,
    "pyzx_full_reduce": compile_pyzx_full_reduce,
    "tket_guided_paulisimp": compile_tket_guided,
    "tket_paulisimp_unrebased": compile_tket_paulisimp_unrebased,
    "tket_paulisimp_rebased": compile_tket_paulisimp_rebased,
    "staq_rotation_folding": compile_staq_rotation_folding,
}


def numerical_equivalence(original, compiled) -> tuple[bool, float]:
    import numpy as np

    Operator = qiskit_imports()["Operator"]
    left = Operator(original).data
    right = Operator(compiled).data
    index = np.unravel_index(np.argmax(np.abs(right)), right.shape)
    if abs(right[index]) < 1e-15:
        return False, float("inf")
    phase = left[index] / right[index]
    phase /= abs(phase)
    error = float(np.max(np.abs(left - phase * right)))
    threshold = OPERATOR_ATOL + OPERATOR_RTOL * float(np.max(np.abs(left)))
    return error <= threshold, error


def classify_exception(exc: BaseException) -> str:
    text = str(exc).lower()
    if "predicate requirements are not satisfied" in text:
        return "predicate_error"
    if "conversion" in text or "unsupported" in text or "qasm" in text:
        return "unsupported_conversion"
    if "unavailable" in text or "no module named" in text:
        return "unavailable"
    return "error"


def base_row(family: str, size: int, method: str, timeout_s: int) -> tuple[dict, Any]:
    circuit, metadata = build_case(family, size)
    row = {
        **metadata,
        "paper_method_name": METHOD_NAMES[method],
        "method_key": method,
        "timeout_s": timeout_s,
        "status": "error",
        "wall_time_s": None,
        "gate_count": None,
        "depth": None,
        "cx_count": None,
        "rotation_count": None,
        "gate_types": None,
        "equivalence_checked": False,
        "equivalent_up_to_global_phase": None,
        "operator_max_abs_error": None,
        "operator_atol": OPERATOR_ATOL,
        "operator_rtol": OPERATOR_RTOL,
        "notes": "",
        "source_command_or_script": (
            f"{THIS_FILE.relative_to(ROOT)} --worker --family {family} "
            f"--size {size} --method {method} --timeout-s {timeout_s}"
        ),
    }
    return row, circuit


def worker(args: argparse.Namespace) -> dict:
    row, circuit = base_row(args.family, args.size, args.method, args.timeout_s)
    start = time.perf_counter()
    try:
        compiled, note = COMPILE[args.method](circuit)
        row.update(metrics(compiled))
        equivalent, error = numerical_equivalence(circuit, compiled)
        row["equivalence_checked"] = True
        row["equivalent_up_to_global_phase"] = equivalent
        row["operator_max_abs_error"] = error
        row["notes"] = note
        row["status"] = "completed" if equivalent else "correctness_failure"
        if not equivalent:
            row["notes"] += f"; numerical operator check failed: {error}"
    except Exception as exc:
        row["status"] = classify_exception(exc)
        row["notes"] = f"{type(exc).__name__}: {exc}"
        row["traceback"] = traceback.format_exc(limit=12)
    row["wall_time_s"] = round(time.perf_counter() - start, 3)
    return row


def log_name(family: str, size: int, method: str, prefix: str) -> Path:
    return OUT / "logs" / f"{prefix}{family}_{size}_{method}.log"


def launch_worker(
    python_executable: str,
    family: str,
    size: int,
    method: str,
    timeout_s: int,
    prefix: str,
) -> dict:
    cmd = [
        python_executable,
        str(THIS_FILE),
        "--worker",
        "--family",
        family,
        "--size",
        str(size),
        "--method",
        method,
        "--timeout-s",
        str(timeout_s),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env.setdefault("XDG_CONFIG_HOME", "/tmp/xdg-config")
    env.setdefault("XDG_CACHE_HOME", "/tmp/xdg-cache")
    env.setdefault("MPLCONFIGDIR", "/tmp/mplconfig")
    start = time.perf_counter()
    process = subprocess.Popen(
        cmd,
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout, stderr = process.communicate()
    elapsed = round(time.perf_counter() - start, 3)
    path = log_name(family, size, method, prefix)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "command: " + " ".join(cmd) + "\n"
        + f"returncode: {process.returncode}\n"
        + f"elapsed_s: {elapsed}\n"
        + "--- stdout ---\n"
        + stdout
        + "\n--- stderr ---\n"
        + stderr,
        encoding="utf-8",
    )
    if timed_out:
        row, _ = base_row(family, size, method, timeout_s)
        row.update(
            {
                "status": "timeout",
                "wall_time_s": elapsed,
                "notes": f"worker exceeded uniform {timeout_s} s budget",
                "log_path": str(path.relative_to(ROOT)),
            }
        )
        return row
    if process.returncode != 0:
        row, _ = base_row(family, size, method, timeout_s)
        row.update(
            {
                "status": "error",
                "wall_time_s": elapsed,
                "notes": (stderr or stdout or "worker failed")[:2000],
                "log_path": str(path.relative_to(ROOT)),
            }
        )
        return row
    try:
        row = json.loads(stdout)
    except json.JSONDecodeError:
        row, _ = base_row(family, size, method, timeout_s)
        row.update(
            {
                "status": "error",
                "wall_time_s": elapsed,
                "notes": "worker stdout was not valid JSON",
            }
        )
    row["log_path"] = str(path.relative_to(ROOT))
    return row


def write_results(path: Path, rows: list[dict]) -> None:
    ordered = sorted(
        rows,
        key=lambda row: (
            FAMILIES.index(row["family_key"]),
            row["requested_gates"],
            METHODS.index(row["method_key"]),
        ),
    )
    path.write_text(json.dumps(ordered, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_derived_results(prefix: str, rows: list[dict]) -> None:
    for family, filename in (
        ("unbounded_independent_pauli", f"{prefix}unbounded_witness_results.json"),
        ("rational_cp", f"{prefix}rational_cp_round6_results.json"),
    ):
        write_results(OUT / filename, [row for row in rows if row["family_key"] == family])
    write_results(
        OUT / f"{prefix}public_phase_folding_results.json",
        [row for row in rows if row["method_key"] == "staq_rotation_folding"],
    )
    write_results(
        OUT / f"{prefix}tket_paulisimp_results.json",
        [row for row in rows if row["method_key"].startswith("tket_paulisimp")],
    )


def format_value(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def write_summary(prefix: str, rows: list[dict], timeout_s: int) -> None:
    lines = [
        "# Unbounded Witness and Public-Baseline Summary",
        "",
        f"Generated: `{utc_now()}`",
        f"Uniform per-cell timeout: `{timeout_s}` seconds.",
        "",
        "The unbounded theorem certificate is symbolic (exact support rank plus Proposition 1). Operator checks below are implementation checks only. Timeout/error cells are statuses, never structural wins.",
        "",
        "| Family | Requested | Actual | r | Method | Status | Gates | Depth | CX | Runtime | Equiv |",
        "|---|---:|---:|---:|---|---|---:|---:|---:|---:|---|",
    ]
    for row in sorted(rows, key=lambda item: (item["family_key"], item["requested_gates"], item["method_key"])):
        lines.append(
            "| {family} | {req} | {actual} | {r} | {method} | {status} | {gates} | {depth} | {cx} | {wall} | {equiv} |".format(
                family=row["family_key"],
                req=row["requested_gates"],
                actual=row["actual_input_gates"],
                r=row["r"],
                method=row["paper_method_name"],
                status=row["status"],
                gates=format_value(row["gate_count"]),
                depth=format_value(row["depth"]),
                cx=format_value(row["cx_count"]),
                wall=format_value(row["wall_time_s"]),
                equiv=format_value(row["equivalent_up_to_global_phase"]),
            )
        )
    (OUT / f"{prefix}unbounded_witness_summary.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unavailable"


def write_environment(prefix: str, timeout_s: int) -> None:
    staq_commit = "unavailable"
    if (STAQ_SOURCE / ".git").exists():
        result = subprocess.run(
            ["git", "-C", str(STAQ_SOURCE), "rev-parse", "HEAD"],
            text=True,
            capture_output=True,
        )
        if result.returncode == 0:
            staq_commit = result.stdout.strip()
    try:
        from pytket import passes

        predicates = str(passes.PauliSimp().get_preconditions())
    except Exception as exc:
        predicates = f"unavailable: {exc}"
    lines = [
        "# Round 6 Environment Snapshot",
        "",
        f"Generated: `{utc_now()}`",
        f"Uniform timeout: `{timeout_s}` seconds",
        f"Python: `{sys.version.splitlines()[0]}`",
        f"Platform: `{platform.platform()}`",
        f"Machine: `{platform.machine()}`",
        f"qiskit: `{package_version('qiskit')}`",
        f"PyZX: `{package_version('pyzx')}`",
        f"pytket: `{package_version('pytket')}`",
        f"pytket-qiskit: `{package_version('pytket-qiskit')}`",
        f"UCC: `{package_version('ucc')}`",
        f"staq commit: `{staq_commit}`",
        f"staq binary: `{STAQ_BINARY}`",
        f"staq binary SHA-256: `{sha256(STAQ_BINARY) if STAQ_BINARY.exists() else 'unavailable'}`",
        "",
        "## PauliSimp required predicates",
        "",
        f"`{predicates}`",
    ]
    (OUT / f"{prefix}round6_environment_snapshot.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def parent(args: argparse.Namespace) -> None:
    prefix = "smoke_" if args.smoke else ""
    sizes = tuple(args.sizes or (SMOKE_SIZES if args.smoke else FULL_SIZES))
    timeout_s = args.timeout_s or (SMOKE_TIMEOUT_S if args.smoke else DEFAULT_TIMEOUT_S)
    families = tuple(args.families or FAMILIES)
    methods = tuple(args.methods or METHODS)
    all_path = OUT / f"{prefix}round6_all_results.json"
    rows: list[dict] = []
    if args.resume and all_path.exists():
        rows = json.loads(all_path.read_text(encoding="utf-8"))
    done = {
        (row["family_key"], row["requested_gates"], row["method_key"])
        for row in rows
    }
    for family in families:
        for size in sizes:
            for method in methods:
                key = (family, size, method)
                if key in done:
                    print(f"skip completed checkpoint {key}", file=sys.stderr, flush=True)
                    continue
                print(
                    f"family={family} size={size} method={method} budget={timeout_s}s",
                    file=sys.stderr,
                    flush=True,
                )
                row = launch_worker(
                    args.python_executable, family, size, method, timeout_s, prefix
                )
                rows.append(row)
                done.add(key)
                write_results(all_path, rows)
                write_derived_results(prefix, rows)
                write_summary(prefix, rows, timeout_s)
    write_environment(prefix, timeout_s)
    print(f"wrote {all_path.relative_to(ROOT)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--full", action="store_true")
    mode.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--family", choices=FAMILIES)
    parser.add_argument("--families", nargs="*", choices=FAMILIES)
    parser.add_argument("--size", type=int)
    parser.add_argument("--sizes", nargs="*", type=int)
    parser.add_argument("--method", choices=METHODS)
    parser.add_argument("--methods", nargs="*", choices=METHODS)
    parser.add_argument("--timeout-s", type=int)
    parser.add_argument("--python-executable", default=sys.executable)
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.worker:
        if args.family is None or args.size is None or args.method is None:
            raise SystemExit("worker requires --family, --size, and --method")
        if args.timeout_s is None:
            args.timeout_s = DEFAULT_TIMEOUT_S
        print(json.dumps(worker(args), sort_keys=True))
    else:
        parent(args)


if __name__ == "__main__":
    main()

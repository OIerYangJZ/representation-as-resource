#!/usr/bin/env python3
"""Real-toolchain packing-family scaling experiment for the v7.2 manuscript.

Running this file without arguments executes the fixed 5x5 sweep. Each cell is
isolated in a fresh worker process and receives the same 600 second wall-clock
budget. Internal ``--worker`` arguments are used only by the parent process.
"""

from __future__ import annotations

import csv
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
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable


THIS_FILE = Path(__file__).resolve()
ROOT = THIS_FILE.parents[1]
WORKSPACE_ROOT = ROOT.parents[1]
RUN_DIR = ROOT / "research" / "packing_scaling"
LOG_DIR = RUN_DIR / "logs"
FIGURE_DIR = ROOT / "figures"
RANK_SCRIPT = THIS_FILE.with_name("verify_packing_support_rank.py")
_LOCAL_STAQ = RUN_DIR / "tools" / "staq_rotation_optimizer_macos_arm64"
STAQ_BINARY = _LOCAL_STAQ if _LOCAL_STAQ.exists() else (
    RUN_DIR / "tools" / "staq_rotation_optimizer"
)
TARGET_BASIS = ["cx", "rx", "ry", "rz", "h"]
SWEEP = (4, 8, 16, 32, 64)
METHODS = (
    "semantic_ucc",
    "qiskit_opt3",
    "tket_paulisimp_rebased",
    "staq_rotation_folding",
    "phase_poly_reference",
)
R = 4
ALPHA = math.pi / 4.0
TOKEN_ANGLE = ALPHA / R
TIMEOUT_S = 600
ATOL = 1e-9
RTOL = 1e-9
RESULT_SENTINEL = "PACKING_CELL_JSON="

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


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


def qubit_index(circuit: Any, qubit: Any) -> int:
    return int(circuit.find_bit(qubit).index)


def build_instance(m: int) -> tuple[Any, dict[str, Any]]:
    if m not in SWEEP:
        raise ValueError(f"m={m} is outside the frozen sweep")
    qiskit = qiskit_imports()
    n = m + 1
    circuit = qiskit["QuantumCircuit"](n)
    generator_order: list[int] = []
    for _round_index in range(R):
        for j in range(m):
            generator_order.append(j + 1)
            circuit.rz(TOKEN_ANGLE, j)
            circuit.rz(TOKEN_ANGLE, j + 1)
            circuit.cp(-2.0 * TOKEN_ANGLE, j, j + 1)
    expected_order = list(range(1, m + 1)) * R
    if generator_order != expected_order:
        raise AssertionError("balanced round-robin order changed")
    if len(circuit.data) != 3 * R * m:
        raise AssertionError("input gate count does not equal 3*r*m")
    circuit.name = f"packing_chain_m{m}_n{n}_r{R}"
    return circuit, {
        "m": m,
        "n": n,
        "r": R,
        "alpha": ALPHA,
        "alpha_over_pi": "1/4",
        "per_token_angle": TOKEN_ANGLE,
        "per_token_angle_over_pi": "1/16",
        "x": [1] * m,
        "input_two_body_tokens": R * m,
        "input_gates": 3 * R * m,
        "generator_order": generator_order,
        "order_rule": "balanced round-robin; generators are not grouped across rounds",
        "lowering": "RZ_i(theta) RZ_j(theta) CP_ij(-2 theta)",
    }


def lower_target(circuit: Any, optimization_level: int = 0) -> Any:
    qiskit = qiskit_imports()
    return qiskit["transpile"](
        circuit,
        basis_gates=TARGET_BASIS,
        optimization_level=optimization_level,
        layout_method="trivial" if optimization_level else None,
        routing_method="none" if optimization_level else None,
    )


def metrics(circuit: Any) -> dict[str, Any]:
    counts = circuit.count_ops()
    return {
        "gates": int(sum(counts.values())),
        "depth": int(circuit.depth()),
        "cx": int(counts.get("cx", 0)),
        "gate_types": sorted(str(name) for name in counts),
    }


def compile_semantic_ucc(circuit: Any) -> tuple[Any, str]:
    import ucc

    previous = os.environ.pop("UCC_DISABLE_FOURIER_LAYER_IR", None)
    try:
        compiled = ucc.compile(
            circuit,
            return_format="qiskit",
            target_gateset=set(TARGET_BASIS),
        )
    finally:
        if previous is not None:
            os.environ["UCC_DISABLE_FOURIER_LAYER_IR"] = previous
    return compiled, (
        "ucc.compile with Fourier-layer IR enabled "
        "(UCC_DISABLE_FOURIER_LAYER_IR unset)"
    )


def compile_qiskit_opt3(circuit: Any) -> tuple[Any, str]:
    return lower_target(circuit, 3), (
        "qiskit.transpile optimization_level=3, layout_method='trivial', "
        "routing_method='none'"
    )


def qasm_output_to_qiskit(qasm_text: str) -> Any:
    qiskit = qiskit_imports()
    lines = qasm_text.splitlines()
    while lines and lines[0].startswith("Let "):
        lines.pop(0)
    return lower_target(qiskit["qasm2"].loads("\n".join(lines)), 0)


def compile_tket_paulisimp_rebased(circuit: Any) -> tuple[Any, str]:
    from pytket import passes
    from pytket.circuit import OpType
    import pytket.qasm as tket_qasm

    qiskit = qiskit_imports()
    preamble = lower_target(circuit, 0)
    tk_circuit = tket_qasm.circuit_from_qasm_str(
        qiskit["qasm2"].dumps(preamble)
    )
    sequence = (
        passes.DecomposeBoxes(),
        passes.AutoRebase({OpType.CX, OpType.Rz, OpType.Rx}),
        passes.RemoveRedundancies(),
        passes.PauliSimp(),
        passes.RemoveRedundancies(),
    )
    for compiler_pass in sequence:
        compiler_pass.apply(tk_circuit)
    compiled = qasm_output_to_qiskit(
        tket_qasm.circuit_to_qasm_str(tk_circuit)
    )
    return compiled, (
        "qiskit opt0 generic preamble -> QASM2 -> DecomposeBoxes -> "
        "AutoRebase({CX,Rz,Rx}) -> RemoveRedundancies -> PauliSimp -> "
        "RemoveRedundancies -> target-basis cleanup"
    )


def compile_staq_rotation_folding(circuit: Any) -> tuple[Any, str]:
    if not STAQ_BINARY.is_file():
        raise RuntimeError(f"staq binary unavailable at {STAQ_BINARY}")
    qiskit = qiskit_imports()
    preamble = lower_target(circuit, 0)
    process = subprocess.run(
        [str(STAQ_BINARY)],
        input=qiskit["qasm2"].dumps(preamble),
        text=True,
        capture_output=True,
        check=False,
    )
    if process.returncode:
        raise RuntimeError(
            f"staq rotation optimizer exited {process.returncode}: "
            f"{process.stderr.strip()}"
        )
    if not process.stdout.strip():
        raise RuntimeError("staq rotation optimizer produced empty QASM")
    return qasm_output_to_qiskit(process.stdout), (
        "qiskit opt0 generic QASM2 preamble -> public staq fold_rotations "
        "(commit a2acd39; disclosed generic double-precision QASM2 patch) -> "
        "qiskit opt0 target-basis cleanup"
    )


def canonical_angle(angle: float) -> float:
    value = (float(angle) + math.pi) % (2.0 * math.pi) - math.pi
    return 0.0 if abs(value) <= 1e-12 else value


def compile_phase_poly_reference(circuit: Any) -> tuple[Any, str]:
    """Aggregate a plain commuting RZ/CP layer with no H boundaries."""

    qiskit = qiskit_imports()
    rz_angles = {qubit: 0.0 for qubit in range(circuit.num_qubits)}
    cp_angles: dict[tuple[int, int], float] = {}
    for instruction in circuit.data:
        name = instruction.operation.name
        qargs = [qubit_index(circuit, qubit) for qubit in instruction.qubits]
        if name == "rz" and len(qargs) == 1:
            rz_angles[qargs[0]] += float(instruction.operation.params[0])
        elif name == "cp" and len(qargs) == 2:
            key = tuple(qargs)
            cp_angles[key] = cp_angles.get(key, 0.0) + float(
                instruction.operation.params[0]
            )
        else:
            raise RuntimeError(
                "no-boundary phase reference supports only rz/cp; "
                f"found {name}"
            )
    aggregated = qiskit["QuantumCircuit"](circuit.num_qubits)
    active_terms = 0
    for qubit, raw_angle in sorted(rz_angles.items()):
        angle = canonical_angle(raw_angle)
        if angle:
            aggregated.rz(angle, qubit)
            active_terms += 1
    for (control, target), raw_angle in sorted(cp_angles.items()):
        angle = canonical_angle(raw_angle)
        if angle:
            aggregated.cp(angle, control, target)
            active_terms += 1
    return lower_target(aggregated, 0), (
        f"no-boundary mode: aggregated {active_terms} active commuting rz/cp "
        "terms, then qiskit opt0 target-basis lowering"
    )


COMPILE: dict[str, Callable[[Any], tuple[Any, str]]] = {
    "semantic_ucc": compile_semantic_ucc,
    "qiskit_opt3": compile_qiskit_opt3,
    "tket_paulisimp_rebased": compile_tket_paulisimp_rebased,
    "staq_rotation_folding": compile_staq_rotation_folding,
    "phase_poly_reference": compile_phase_poly_reference,
}


def numerical_certificate(original: Any, compiled: Any) -> dict[str, Any]:
    import numpy as np

    operator = qiskit_imports()["Operator"]
    expected = operator(original).data
    actual = operator(compiled).data
    pivot = np.unravel_index(np.argmax(np.abs(actual)), actual.shape)
    if abs(actual[pivot]) < 1e-15:
        return {
            "kind": "exact_numerical_global_phase",
            "passed": False,
            "max_abs_error": float("inf"),
            "threshold": None,
            "atol": ATOL,
            "rtol": RTOL,
        }
    phase = expected[pivot] / actual[pivot]
    phase /= abs(phase)
    error = float(np.max(np.abs(expected - phase * actual)))
    threshold = ATOL + RTOL * float(np.max(np.abs(expected)))
    return {
        "kind": "exact_numerical_global_phase",
        "passed": error <= threshold,
        "max_abs_error": error,
        "threshold": threshold,
        "atol": ATOL,
        "rtol": RTOL,
    }


def exact_pi_ratio(angle: Any) -> Fraction:
    """Recover the declared rational-pi sidecar or reject the angle."""

    ratio = float(angle) / math.pi
    exact = Fraction(ratio).limit_denominator(4096)
    if abs(ratio - float(exact)) > 1e-10:
        raise ValueError(
            "floating-only angle outside exact rational-pi certificate domain"
        )
    return exact


def extract_phase_polynomial_a(circuit: Any) -> tuple[dict[int, Fraction], list[int]]:
    """Generator implementation A: bit-packed live parity masks."""

    live = [1 << index for index in range(circuit.num_qubits)]
    terms: dict[int, Fraction] = {}
    for instruction in circuit.data:
        name = instruction.operation.name
        qargs = [qubit_index(circuit, qubit) for qubit in instruction.qubits]
        if name == "cx" and len(qargs) == 2:
            live[qargs[1]] ^= live[qargs[0]]
        elif name == "rz" and len(qargs) == 1:
            mask = live[qargs[0]]
            terms[mask] = terms.get(mask, Fraction(0)) + exact_pi_ratio(
                instruction.operation.params[0]
            )
        elif name in {"barrier", "id"}:
            continue
        else:
            raise ValueError(f"non-phase-polynomial operation: {name}")
    return terms, live


def extract_phase_polynomial_b(circuit: Any) -> tuple[dict[int, Fraction], list[int]]:
    """Checker implementation B: explicit GF(2) coefficient rows."""

    width = circuit.num_qubits
    rows = [[int(i == j) for j in range(width)] for i in range(width)]
    terms: dict[int, Fraction] = {}
    for item in circuit.data:
        opname = str(item.operation.name)
        indices = tuple(qubit_index(circuit, q) for q in item.qubits)
        if opname == "cx" and len(indices) == 2:
            control, target = indices
            rows[target] = [
                (left + right) % 2
                for left, right in zip(rows[target], rows[control])
            ]
        elif opname == "rz" and len(indices) == 1:
            packed = sum(
                (bit & 1) << position
                for position, bit in enumerate(rows[indices[0]])
            )
            terms[packed] = terms.setdefault(packed, Fraction(0)) + exact_pi_ratio(
                item.operation.params[0]
            )
        elif opname in ("barrier", "id"):
            pass
        else:
            raise ValueError(f"checker rejected operation: {opname}")
    final_rows = [
        sum((bit & 1) << position for position, bit in enumerate(row))
        for row in rows
    ]
    return terms, final_rows


def expected_chain_terms_independent(m: int) -> dict[int, Fraction]:
    """Target generator, expressed directly from a_j=e_j+e_{j+1}."""

    result: dict[int, Fraction] = {}
    for j in range(m):
        character = (1 << j) + (1 << (j + 1))
        result[character] = Fraction(1, 4)
    return result


def normalized_terms(terms: dict[int, Fraction]) -> dict[int, Fraction]:
    """Canonical exact coefficients in Q*pi/(2*pi*Z)."""

    result: dict[int, Fraction] = {}
    for mask, raw_angle in terms.items():
        angle = raw_angle % 2
        if angle:
            result[int(mask)] = angle
    return result


def symbolic_certificate(compiled: Any, m: int) -> dict[str, Any]:
    """Generate and independently check a Hadamard-free phase certificate."""

    try:
        terms_a_raw, final_a = extract_phase_polynomial_a(compiled)
        terms_b_raw, final_b = extract_phase_polynomial_b(compiled)
    except Exception as exc:
        return {
            "kind": "exact_symbolic_phase_polynomial",
            "passed": False,
            "predicate_satisfied": False,
            "reason": f"{type(exc).__name__}: {exc}",
        }

    terms_a = normalized_terms(terms_a_raw)
    terms_b = normalized_terms(terms_b_raw)
    expected = normalized_terms(expected_chain_terms_independent(m))
    identity = [1 << index for index in range(m + 1)]
    all_masks = sorted(set(terms_a) | set(terms_b) | set(expected))
    passed = (
        final_a == identity
        and final_b == identity
        and terms_a == terms_b
        and terms_a == expected
    )
    term_rows = [
        {
            "mask_hex": hex(mask),
            "support": [
                index for index in range(m + 1) if mask & (1 << index)
            ],
            "generator_angle_over_pi": str(terms_a.get(mask, Fraction(0))),
            "checker_angle_over_pi": str(terms_b.get(mask, Fraction(0))),
            "expected_angle_over_pi": str(expected.get(mask, Fraction(0))),
        }
        for mask in all_masks
    ]
    return {
        "kind": "exact_symbolic_phase_polynomial",
        "passed": passed,
        "predicate_satisfied": True,
        "hadamard_free_adjustment": True,
        "generator_implementation": "bit-packed live parity masks",
        "checker_implementation": "explicit GF(2) coefficient rows",
        "linear_map_identity_generator": final_a == identity,
        "linear_map_identity_checker": final_b == identity,
        "coefficient_domain": "Q*pi/(2*pi*Z)",
        "generator_checker_equal": terms_a == terms_b,
        "generator_target_equal": terms_a == expected,
        "checker_target_equal": terms_b == expected,
        "tolerance": None,
        "terms": term_rows,
    }


def representation_bits(m: int) -> tuple[int, int]:
    n = m + 1
    bits_sem = m + 2 * math.ceil(math.log2(m + 2)) + 8
    bits_echo = (3 * R * m) * (2 * math.ceil(math.log2(n)) + 6)
    return int(bits_sem), int(bits_echo)


def classify_exception(exc: BaseException) -> str:
    text = str(exc).lower()
    if "predicate" in text:
        return "predicate_error"
    if "unsupported" in text or "qasm" in text or "conversion" in text:
        return "unsupported"
    return "error"


def base_row(m: int, method: str) -> dict[str, Any]:
    n = m + 1
    bits_sem, bits_echo = representation_bits(m)
    return {
        "m": m,
        "n": n,
        "path": method,
        "status": "error",
        "gates": None,
        "depth": None,
        "cx": None,
        "runtime_s": None,
        "certificate": None,
        "bits_repr": bits_sem if method in {
            "semantic_ucc", "phase_poly_reference"
        } else bits_echo,
        "bits_sem": bits_sem,
        "bits_echo": bits_echo,
        "counting_line": m,
        "timeout_s": TIMEOUT_S,
    }


def worker(m: int, method: str) -> dict[str, Any]:
    row = base_row(m, method)
    original, instance = build_instance(m)
    row["instance"] = instance
    started = time.perf_counter()
    try:
        compiled, provenance = COMPILE[method](original)
        row.update(metrics(compiled))
        certificate = (
            numerical_certificate(original, compiled)
            if m == 4
            else symbolic_certificate(compiled, m)
        )
        row["certificate_detail"] = certificate
        row["certificate"] = (
            "numerical_pass" if m == 4 else "symbolic_pass"
        ) if certificate["passed"] else (
            "numerical_fail" if m == 4 else "symbolic_fail"
        )
        row["pipeline_provenance"] = provenance
        if certificate["passed"]:
            row["status"] = "completed"
        elif not certificate.get("predicate_satisfied", True):
            row["status"] = "predicate_error"
        else:
            row["status"] = "correctness_failure"
    except Exception as exc:
        row["status"] = classify_exception(exc)
        row["certificate"] = "not_completed"
        row["notes"] = f"{type(exc).__name__}: {exc}"
        row["traceback"] = traceback.format_exc(limit=20)
    row["runtime_s"] = round(time.perf_counter() - started, 6)
    return row


def parse_worker_result(stdout: str) -> dict[str, Any]:
    for line in reversed(stdout.splitlines()):
        if line.startswith(RESULT_SENTINEL):
            return json.loads(line[len(RESULT_SENTINEL):])
    raise RuntimeError("worker did not emit a result sentinel")


def run_cell(m: int, method: str) -> dict[str, Any]:
    command = [
        sys.executable,
        str(THIS_FILE),
        "--worker",
        str(m),
        method,
    ]
    environment = os.environ.copy()
    python_paths = [str(WORKSPACE_ROOT), str(ROOT)]
    if environment.get("PYTHONPATH"):
        python_paths.append(environment["PYTHONPATH"])
    environment["PYTHONPATH"] = os.pathsep.join(python_paths)
    environment.setdefault("XDG_CONFIG_HOME", "/tmp/ucc-packing-xdg")
    environment.setdefault("XDG_CACHE_HOME", "/tmp/ucc-packing-cache")
    environment.setdefault("MPLCONFIGDIR", "/tmp/ucc-packing-mpl")
    started = time.perf_counter()
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout, stderr = process.communicate()
    elapsed = round(time.perf_counter() - started, 6)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"m{m}_{method}.log"
    log_path.write_text(
        "command: " + " ".join(command) + "\n"
        + f"returncode: {process.returncode}\n"
        + f"elapsed_s: {elapsed}\n"
        + "--- stdout ---\n"
        + stdout
        + "\n--- stderr ---\n"
        + stderr,
        encoding="utf-8",
    )
    if timed_out:
        row = base_row(m, method)
        row.update(
            {
                "status": "timeout",
                "runtime_s": elapsed,
                "certificate": "not_completed",
                "notes": f"worker exceeded {TIMEOUT_S} s wall-clock budget",
            }
        )
    else:
        try:
            row = parse_worker_result(stdout)
        except Exception as exc:
            row = base_row(m, method)
            row.update(
                {
                    "status": "error",
                    "runtime_s": elapsed,
                    "certificate": "not_completed",
                    "notes": f"{type(exc).__name__}: {exc}",
                }
            )
    row["log_path"] = str(log_path.relative_to(ROOT))
    row["worker_returncode"] = process.returncode
    return row


def validate_representation_rules() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    ratios: list[float] = []
    for m in SWEEP:
        bits_sem, bits_echo = representation_bits(m)
        ratio = bits_echo / m
        records.append(
            {
                "m": m,
                "n": m + 1,
                "bits_sem": bits_sem,
                "bits_echo": bits_echo,
                "counting_line": m,
                "bits_sem_ge_counting": bits_sem >= m,
                "semantic_gap_bound": (
                    bits_sem - m
                    <= 3 * math.ceil(math.log2(m)) + 10
                ),
                "echo_ratio": ratio,
            }
        )
        ratios.append(ratio)
    if not all(row["bits_sem_ge_counting"] for row in records):
        raise AssertionError("bits_sem(m) >= m failed")
    if not all(row["semantic_gap_bound"] for row in records):
        raise AssertionError("semantic additive-gap assertion failed")
    if not all(
        right + 1e-12 >= left for left, right in zip(ratios, ratios[1:])
    ):
        raise AssertionError("echo/m is not monotone nondecreasing")
    return records


def run_rank_verifier() -> dict[str, Any]:
    process = subprocess.run(
        [sys.executable, str(RANK_SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    (RUN_DIR / "rank_verifier.log").write_text(
        "command: " + sys.executable + " " + str(RANK_SCRIPT) + "\n"
        + f"returncode: {process.returncode}\n"
        + "--- stdout ---\n"
        + process.stdout
        + "\n--- stderr ---\n"
        + process.stderr,
        encoding="utf-8",
    )
    if process.returncode:
        raise RuntimeError("rank verifier failed; see rank_verifier.log")
    payload = json.loads(process.stdout)
    if not payload.get("all_passed"):
        raise AssertionError("rank verifier did not certify every m")
    return payload


def write_csv(rows: list[dict[str, Any]]) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "m", "n", "path", "status", "gates", "depth", "cx",
        "runtime_s", "certificate", "bits_repr",
    ]
    with (FIGURE_DIR / "packing_scaling.csv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fieldnames})


def make_figure(rows: list[dict[str, Any]]) -> None:
    import matplotlib.pyplot as plt

    labels = {
        "semantic_ucc": "semantic UCC",
        "qiskit_opt3": "Qiskit opt3",
        "tket_paulisimp_rebased": "TKET PauliSimp",
        "staq_rotation_folding": "staq folding",
        "phase_poly_reference": "phase-poly ref.",
    }
    markers = {
        "semantic_ucc": "o",
        "qiskit_opt3": "s",
        "tket_paulisimp_rebased": "^",
        "staq_rotation_folding": "D",
        "phase_poly_reference": "P",
    }
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.size": 9,
            "axes.labelsize": 9,
            "legend.fontsize": 7.5,
            "pdf.fonttype": 42,
        }
    )
    figure, axes = plt.subplots(1, 2, figsize=(7.2, 3.05))
    left, right = axes
    for method in METHODS:
        completed = [
            row for row in rows
            if row["path"] == method and row["status"] == "completed"
        ]
        if completed:
            left.plot(
                [row["m"] for row in completed],
                [row["gates"] for row in completed],
                marker=markers[method],
                linewidth=1.35,
                markersize=4.5,
                label=labels[method],
            )
        for row in rows:
            if row["path"] == method and row["status"] != "completed":
                left.annotate(
                    row["status"],
                    (row["m"], max(1, 3 * R * row["m"])),
                    rotation=45,
                    fontsize=5.5,
                    alpha=0.8,
                )
    left.set_xscale("log", base=2)
    left.set_yscale("log")
    left.set_xticks(SWEEP, [str(m) for m in SWEEP])
    left.set_xlabel(r"$m$")
    left.set_ylabel("completed output gates")
    left.grid(True, which="both", alpha=0.22)
    left.legend(frameon=False, loc="best")
    left.text(0.02, 0.96, "(a)", transform=left.transAxes, va="top")

    bits_sem = [representation_bits(m)[0] for m in SWEEP]
    bits_echo = [representation_bits(m)[1] for m in SWEEP]
    right.plot(SWEEP, bits_sem, "o-", linewidth=1.35, label=r"$bits_{\rm sem}$")
    right.plot(SWEEP, bits_echo, "s-", linewidth=1.35, label=r"$bits_{\rm echo}$")
    right.plot(SWEEP, list(SWEEP), "k--", linewidth=1.1, label=r"$m$")
    right.set_xscale("log", base=2)
    right.set_yscale("log")
    right.set_xticks(SWEEP, [str(m) for m in SWEEP])
    right.set_xlabel(r"$m$")
    right.set_ylabel("representation bits")
    right.grid(True, which="both", alpha=0.22)
    right.legend(frameon=False, loc="best")
    right.text(0.02, 0.96, "(b)", transform=right.transAxes, va="top")
    figure.tight_layout(w_pad=2.0)
    figure.savefig(FIGURE_DIR / "packing_scaling.pdf", bbox_inches="tight")
    plt.close(figure)


def package_versions() -> dict[str, str]:
    result: dict[str, str] = {}
    for package in ("qiskit", "pyzx", "pytket", "ucc", "numpy", "matplotlib"):
        try:
            result[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            result[package] = "unavailable"
    return result


def write_environment_snapshot(started_at: str) -> dict[str, Any]:
    uname = platform.uname()
    snapshot = {
        "started_at_utc": started_at,
        "hostname": uname.node,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "python_executable": sys.executable,
        "packages": package_versions(),
        "target_basis": TARGET_BASIS,
        "timeout_s_per_cell": TIMEOUT_S,
        "staq_binary": str(STAQ_BINARY),
        "staq_binary_sha256": sha256(STAQ_BINARY) if STAQ_BINARY.exists() else None,
        "staq_upstream_commit": "a2acd39e60ed0e5f1978fa530df7e1e0c7cedf7a",
        "staq_patch": (
            "generic QASM2 numeric parsing/printing precision patch only; "
            "no family labels or fold_rotations changes"
        ),
        "ucc_disable_fourier_layer_ir": os.environ.get(
            "UCC_DISABLE_FOURIER_LAYER_IR"
        ),
    }
    (RUN_DIR / "environment_snapshot.json").write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return snapshot


def write_readme() -> None:
    text = """# Packing-family scaling frozen run

This directory records real configured-pipeline diagnostics for the growing-m
packing family. These rows do not prove, test, or validate the streaming
commitment-memory theorem. Status outcomes are separate from completed numeric
cells.

## Deterministic representation rules

- Semantic encoding bits: `bits_sem(m) = m + 2*ceil(log2(m+2)) + 8`
  (m-bit support mask + width field + fixed header).
- Echo encoding bits: `bits_echo(m) = (3*r*m) * (2*ceil(log2(n)) + 6)`
  (per-gate: two qubit indices + opcode/param tag).
- Counting line: `y = m` (Kraft-tight binary prefix-free lower bound).
- Assertions: `bits_sem(m) >= m` for all m;
  `bits_sem(m) - m <= 3*ceil(log2 m) + 10`;
  `bits_echo(m) / m` grows ~ `Theta(log m)` (monotone increasing ratio
  suffices).

The phase-polynomial reference uses the disclosed no-boundary extension: it
aggregates the plain commuting RZ/CP layer directly, then lowers once with
Qiskit optimization level 0.
"""
    (RUN_DIR / "README.md").write_text(text, encoding="utf-8")


def write_checkpoint(payload: dict[str, Any]) -> None:
    (RUN_DIR / "packing_scaling_frozen.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_hashes() -> None:
    candidates = [
        path for path in sorted(ROOT.rglob("*"))
        if path.is_file()
        and (
            path == THIS_FILE
            or path == RANK_SCRIPT
            or path == FIGURE_DIR / "packing_scaling.csv"
            or path == FIGURE_DIR / "packing_scaling.pdf"
            or RUN_DIR in path.parents
        )
        and path.name not in {"SHA256SUMS", "FILE_MANIFEST.tsv"}
    ]
    lines = [f"{sha256(path)}  {path.relative_to(ROOT)}" for path in candidates]
    (RUN_DIR / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    started_at = utc_now()
    ranks = run_rank_verifier()
    representation = validate_representation_rules()
    environment = write_environment_snapshot(started_at)
    write_readme()
    rows: list[dict[str, Any]] = []
    payload: dict[str, Any] = {
        "experiment": "packing-family scaling",
        "scope": (
            "configured-pipeline diagnostics; not a theorem validation or "
            "measurement of commitment-memory split"
        ),
        "started_at_utc": started_at,
        "finished_at_utc": None,
        "sweep": list(SWEEP),
        "methods": list(METHODS),
        "timeout_s_per_method_instance": TIMEOUT_S,
        "rank_verification": ranks,
        "representation_rules": representation,
        "environment": environment,
        "rows": rows,
    }
    write_checkpoint(payload)
    for m in SWEEP:
        for method in METHODS:
            row = run_cell(m, method)
            rows.append(row)
            write_checkpoint(payload)
            print(
                f"m={m} method={method} status={row['status']} "
                f"runtime_s={row['runtime_s']}",
                flush=True,
            )
    write_csv(rows)
    make_figure(rows)
    payload["finished_at_utc"] = utc_now()
    payload["all_completed_certificates_pass"] = all(
        row["certificate"] in {"numerical_pass", "symbolic_pass"}
        for row in rows
        if row["status"] == "completed"
    )
    payload["status_counts"] = {
        status: sum(row["status"] == status for row in rows)
        for status in sorted({str(row["status"]) for row in rows})
    }
    write_checkpoint(payload)
    write_hashes()
    return 0


def dispatch() -> int:
    if len(sys.argv) == 1:
        return main()
    if len(sys.argv) == 4 and sys.argv[1] == "--worker":
        m = int(sys.argv[2])
        method = sys.argv[3]
        if method not in METHODS:
            raise KeyError(method)
        row = worker(m, method)
        print(RESULT_SENTINEL + json.dumps(row, sort_keys=True))
        return 0
    raise SystemExit("usage: packing_scaling_real.py")


if __name__ == "__main__":
    raise SystemExit(dispatch())

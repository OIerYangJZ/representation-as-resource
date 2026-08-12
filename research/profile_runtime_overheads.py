from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from qiskit import transpile as qiskit_transpile

from hardware_aware_backend import LineBackend
from hardware_aware_instances import build_case as build_hardware_case
from real_instance_benchmarks import build_case as build_real_case


THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
TARGET_BASIS = ["cx", "rx", "ry", "rz", "h"]
DEFAULT_SEED = 12345
BACKEND = LineBackend(20, name="line20")
CASES = (
    "phase_estimation_real",
    "grover_real",
    "qaoa_real",
    "hw_mqt_qaoa_20",
)


@dataclass
class CaseConfig:
    circuit: Any
    target_gateset: set[str] | None
    target_backend: Any | None


def build_case_config(case_name: str) -> CaseConfig:
    if case_name in {
        "phase_estimation_real",
        "grover_real",
        "qaoa_real",
    }:
        return CaseConfig(
            circuit=build_real_case(case_name).circuit,
            target_gateset=set(TARGET_BASIS),
            target_backend=None,
        )
    if case_name == "hw_mqt_qaoa_20":
        return CaseConfig(
            circuit=build_hardware_case(case_name).circuit,
            target_gateset=None,
            target_backend=BACKEND,
        )
    raise KeyError(f"Unknown case: {case_name}")


def circuit_metrics(circuit) -> dict:
    count_ops = circuit.count_ops()
    return {
        "total_gates": int(sum(count_ops.values())),
        "depth": int(circuit.depth()),
        "cx_count": int(count_ops.get("cx", 0)),
    }


def classify_transpile_call(kwargs: dict) -> str:
    optimization_level = kwargs.get("optimization_level")
    backend = kwargs.get("backend")
    basis_gates = kwargs.get("basis_gates")

    if backend is not None:
        return f"backend_transpile_opt{optimization_level}"
    if basis_gates is not None and optimization_level == 0:
        return "basis_translate_or_normalize"
    if basis_gates is not None and optimization_level == 3:
        return "source_preset_opt3"
    return f"other_transpile_opt{optimization_level}"


@contextmanager
def patched_attribute(obj: Any, attr: str, value: Any):
    original = getattr(obj, attr)
    setattr(obj, attr, value)
    try:
        yield original
    finally:
        setattr(obj, attr, original)


def run_qiskit_opt3(case_name: str, seed_transpiler: int) -> dict:
    case = build_case_config(case_name)
    start = time.perf_counter()
    if case.target_backend is not None:
        compiled = qiskit_transpile(
            case.circuit,
            backend=case.target_backend,
            optimization_level=3,
            seed_transpiler=seed_transpiler,
        )
    else:
        compiled = qiskit_transpile(
            case.circuit,
            basis_gates=TARGET_BASIS,
            optimization_level=3,
            layout_method="trivial",
            routing_method="none",
        )
    runtime_s = round(time.perf_counter() - start, 3)
    return {
        "runtime_s": runtime_s,
        "output": circuit_metrics(compiled),
    }


def run_full_optimized_profile(case_name: str, seed_transpiler: int) -> dict:
    case = build_case_config(case_name)
    ucc_compile_module = importlib.import_module("ucc.compile")
    ucc_defaults_module = importlib.import_module("ucc.transpilers.ucc_defaults")

    stats = defaultdict(float)
    counts = defaultdict(int)

    def timed_wrapper(name: str, fn: Callable):
        def wrapped(*args, **kwargs):
            start = time.perf_counter()
            try:
                return fn(*args, **kwargs)
            finally:
                elapsed = time.perf_counter() - start
                stats[name] += elapsed
                counts[name] += 1

        return wrapped

    original_qiskit_transpile = ucc_compile_module.qiskit_transpile

    def wrapped_qiskit_transpile(*args, **kwargs):
        bucket = classify_transpile_call(kwargs)
        start = time.perf_counter()
        try:
            return original_qiskit_transpile(*args, **kwargs)
        finally:
            elapsed = time.perf_counter() - start
            stats[f"qiskit_transpile::{bucket}"] += elapsed
            counts[f"qiskit_transpile::{bucket}"] += 1

    original_translate = ucc_compile_module.translate

    def wrapped_translate(*args, **kwargs):
        start = time.perf_counter()
        try:
            return original_translate(*args, **kwargs)
        finally:
            elapsed = time.perf_counter() - start
            stats["translate"] += elapsed
            counts["translate"] += 1

    patched = [
        (ucc_compile_module, "qiskit_transpile", wrapped_qiskit_transpile),
        (ucc_compile_module, "translate", wrapped_translate),
        (
            ucc_compile_module,
            "_run_commutative_inverse_cancellation",
            timed_wrapper(
                "_run_commutative_inverse_cancellation",
                ucc_compile_module._run_commutative_inverse_cancellation,
            ),
        ),
        (
            ucc_compile_module,
            "_structural_pre_simplify",
            timed_wrapper(
                "_structural_pre_simplify",
                ucc_compile_module._structural_pre_simplify,
            ),
        ),
        (
            ucc_compile_module,
            "_select_lowest_cost_circuit",
            timed_wrapper(
                "_select_lowest_cost_circuit",
                ucc_compile_module._select_lowest_cost_circuit,
            ),
        ),
        (
            ucc_compile_module,
            "_compile_backend_default_portfolio",
            timed_wrapper(
                "_compile_backend_default_portfolio",
                ucc_compile_module._compile_backend_default_portfolio,
            ),
        ),
        (
            ucc_defaults_module.UCCDefault1,
            "run",
            timed_wrapper("UCCDefault1.run", ucc_defaults_module.UCCDefault1.run),
        ),
    ]

    stack = []
    try:
        for obj, attr, value in patched:
            ctx = patched_attribute(obj, attr, value)
            ctx.__enter__()
            stack.append(ctx)

        import ucc

        start = time.perf_counter()
        compiled = ucc.compile(
            case.circuit,
            return_format="qiskit",
            target_gateset=case.target_gateset,
            target_backend=case.target_backend,
            seed_transpiler=seed_transpiler,
        )
        total_runtime = time.perf_counter() - start
    finally:
        while stack:
            stack.pop().__exit__(None, None, None)

    component_rows = []
    for name, elapsed in sorted(stats.items(), key=lambda item: item[1], reverse=True):
        component_rows.append(
            {
                "component": name,
                "runtime_s": round(elapsed, 3),
                "pct_total": round(100.0 * elapsed / total_runtime, 1)
                if total_runtime
                else 0.0,
                "calls": int(counts[name]),
            }
        )

    return {
        "runtime_s": round(total_runtime, 3),
        "output": circuit_metrics(compiled),
        "components": component_rows,
    }


def markdown_summary(payload: dict, seed_transpiler: int) -> str:
    lines = [
        "# Runtime Overhead Profiling",
        "",
        "This compares direct `qiskit opt3` against the current `full_optimized` branch",
        "and attributes the runtime overhead to high-level components inside the optimized path.",
        "",
        f"Seed transpiler: `{seed_transpiler}`",
        "",
    ]
    for case_name, result in payload.items():
        qiskit_result = result["qiskit_opt3"]
        optimized_result = result["full_optimized"]
        lines.extend(
            [
                f"## {case_name}",
                "",
                "| Method | Runtime | Output Gates | Depth | CX |",
                "|---|---:|---:|---:|---:|",
                f"| qiskit_opt3 | {qiskit_result['runtime_s']} s | {qiskit_result['output']['total_gates']:,} | {qiskit_result['output']['depth']:,} | {qiskit_result['output']['cx_count']:,} |",
                f"| full_optimized | {optimized_result['runtime_s']} s | {optimized_result['output']['total_gates']:,} | {optimized_result['output']['depth']:,} | {optimized_result['output']['cx_count']:,} |",
                "",
                "| full_optimized component | Runtime | % total | Calls |",
                "|---|---:|---:|---:|",
            ]
        )
        for row in optimized_result["components"]:
            lines.append(
                f"| {row['component']} | {row['runtime_s']} s | {row['pct_total']}% | {row['calls']} |"
            )
        lines.append("")
    return "\n".join(lines)


def run_parent(seed_transpiler: int) -> dict:
    payload = {}
    for case_name in CASES:
        payload[case_name] = {
            "qiskit_opt3": run_qiskit_opt3(case_name, seed_transpiler),
            "full_optimized": run_full_optimized_profile(case_name, seed_transpiler),
        }
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Profile high-level runtime overheads in the full optimized branch."
    )
    parser.add_argument("--seed-transpiler", type=int, default=DEFAULT_SEED)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--md-out", type=Path)
    args = parser.parse_args()

    payload = run_parent(args.seed_transpiler)

    if args.json_out is not None:
        args.json_out.write_text(json.dumps(payload, indent=2))
    if args.md_out is not None:
        args.md_out.write_text(
            markdown_summary(payload, seed_transpiler=args.seed_transpiler)
        )

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

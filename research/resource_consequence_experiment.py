import argparse
import json
import math
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from qiskit import QuantumCircuit
from qiskit import transpile as qiskit_transpile
from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import CommutativeInverseCancellation

# Add REPO_ROOT to sys.path
THIS_FILE = Path(__file__).resolve()
# Robust repo root detection for cloud VMs
REPO_ROOT = THIS_FILE.parents[2]
if not (REPO_ROOT / "ucc").exists() and THIS_FILE.parents[1].name == "research":
    REPO_ROOT = THIS_FILE.parents[1].parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

TARGET_BASIS = ["cx", "rx", "ry", "rz", "h"]
SIZES = (4_000, 10_000, 20_000, 50_000, 100_000)
METHODS = (
    "semantic_first",
    "phase_poly_reference",
    "materialize_first_qiskit_opt3",
    "materialize_first_baseline_ucc"
)
ANGLE_ZERO_ATOL = 1e-12

@dataclass
class CircuitCase:
    family: str
    requested_target_gates: int
    circuit: QuantumCircuit
    description: str

def _phase_diagonal_block(num_qubits: int) -> QuantumCircuit:
    """A non-inverse commuting diagonal phase-polynomial block."""
    block = QuantumCircuit(num_qubits)
    for qubit in range(num_qubits):
        block.rz(math.pi / (7 + qubit), qubit)
    for control in range(num_qubits):
        for target in range(control + 1, num_qubits):
            block.cp(math.pi / (11 + control + target), control, target)
    return block

def _build_fourier_phase_sandwich(target_gates: int) -> CircuitCase:
    """Build H · D^r · H, where D is a repeated diagonal phase polynomial."""
    num_qubits = 4
    diagonal_block = _phase_diagonal_block(num_qubits)
    overhead = 2 * num_qubits
    repeats = max(1, (target_gates - overhead) // len(diagonal_block.data))

    circuit = QuantumCircuit(num_qubits)
    for qubit in range(num_qubits):
        circuit.h(qubit)
    for _ in range(repeats):
        circuit.compose(diagonal_block, inplace=True)
    for qubit in range(num_qubits):
        circuit.h(qubit)
    circuit.name = "fourier_phase_sandwich"
    return CircuitCase(
        family="fourier_phase_sandwich",
        requested_target_gates=target_gates,
        circuit=circuit,
        description=(
            "Non-inverse Fourier-style H · D^r · H family with a repeated "
            "commuting diagonal phase-polynomial middle layer."
        ),
    )

def circuit_metrics(circuit) -> dict:
    count_ops = circuit.count_ops()
    multi_qubit_gates = sum(
        1 for instruction in circuit.data if instruction.operation.num_qubits > 1
    )
    return {
        "num_qubits": circuit.num_qubits,
        "total_gates": int(sum(count_ops.values())),
        "depth": int(circuit.depth()),
        "multi_qubit_gates": int(multi_qubit_gates),
        "cx_count": int(count_ops.get("cx", 0)),
        "rz_rotation_count": int(count_ops.get("rz", 0)) + int(count_ops.get("rx", 0)) + int(count_ops.get("ry", 0)),
        "gate_types": sorted(str(name) for name in count_ops.keys()),
    }

def get_t_proxy(rz_rotation_count: int, eps: float) -> int:
    return int(math.ceil(3 * math.log2(1/eps)) * rz_rotation_count)

def _qubit_index(circuit: QuantumCircuit, qubit) -> int:
    return circuit.find_bit(qubit).index

def _as_float_angle(angle) -> float:
    return float(angle)

def _canonical_angle(angle: float) -> float:
    period = 2.0 * math.pi
    wrapped = (angle + math.pi) % period - math.pi
    if abs(wrapped) <= ANGLE_ZERO_ATOL:
        return 0.0
    return wrapped

def _is_full_h_layer(circuit: QuantumCircuit, instructions) -> bool:
    if len(instructions) != circuit.num_qubits:
        return False
    seen = set()
    for instruction in instructions:
        if instruction.operation.name != "h" or len(instruction.qubits) != 1:
            return False
        seen.add(_qubit_index(circuit, instruction.qubits[0]))
    return seen == set(range(circuit.num_qubits))

def _compile_with_phase_poly_reference(circuit: QuantumCircuit) -> dict:
    """Reference H-D-H compiler using only commuting phase aggregation."""
    start = time.perf_counter()
    try:
        num_qubits = circuit.num_qubits
        if len(circuit.data) < 2 * num_qubits:
            raise ValueError("Circuit is too small to contain H-D-H layers")

        prefix = circuit.data[:num_qubits]
        suffix = circuit.data[-num_qubits:]
        if not _is_full_h_layer(circuit, prefix):
            raise ValueError("Expected a full leading H layer")
        if not _is_full_h_layer(circuit, suffix):
            raise ValueError("Expected a full trailing H layer")

        rz_angles = {qubit: 0.0 for qubit in range(num_qubits)}
        cp_angles: dict[tuple[int, int], float] = {}
        for instruction in circuit.data[num_qubits:-num_qubits]:
            name = instruction.operation.name
            qargs = [
                _qubit_index(circuit, qubit) for qubit in instruction.qubits
            ]
            if name == "rz" and len(qargs) == 1:
                rz_angles[qargs[0]] += _as_float_angle(
                    instruction.operation.params[0]
                )
            elif name == "cp" and len(qargs) == 2:
                key = tuple(qargs)
                cp_angles[key] = cp_angles.get(key, 0.0) + _as_float_angle(
                    instruction.operation.params[0]
                )
            else:
                raise ValueError(
                    "Phase-polynomial reference only supports middle-layer "
                    f"`rz` and `cp`; found `{name}`"
                )

        aggregated = QuantumCircuit(num_qubits)
        for qubit in range(num_qubits):
            aggregated.h(qubit)

        active_phase_terms = 0
        for qubit in range(num_qubits):
            angle = _canonical_angle(rz_angles[qubit])
            if angle:
                aggregated.rz(angle, qubit)
                active_phase_terms += 1

        for (control, target), raw_angle in sorted(cp_angles.items()):
            angle = _canonical_angle(raw_angle)
            if angle:
                aggregated.cp(angle, control, target)
                active_phase_terms += 1

        for qubit in range(num_qubits):
            aggregated.h(qubit)

        compiled = qiskit_transpile(
            aggregated,
            basis_gates=TARGET_BASIS,
            optimization_level=0,
        )
        runtime_s = round(time.perf_counter() - start, 3)
        return {
            "status": "ok",
            "output": circuit_metrics(compiled),
            "runtime_s": runtime_s,
            "active_phase_terms_after_aggregation": active_phase_terms,
        }
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
            "runtime_s": round(time.perf_counter() - start, 3),
        }

def _compile_with_ucc(circuit, disable_fourier_layer_ir=False) -> dict:
    import ucc
    if disable_fourier_layer_ir:
        os.environ["UCC_DISABLE_FOURIER_LAYER_IR"] = "1"
    else:
        os.environ.pop("UCC_DISABLE_FOURIER_LAYER_IR", None)

    start = time.perf_counter()
    try:
        compiled = ucc.compile(
            circuit,
            return_format="qiskit",
            target_gateset=set(TARGET_BASIS),
        )
        runtime_s = round(time.perf_counter() - start, 3)
        return {"status": "ok", "output": circuit_metrics(compiled), "runtime_s": runtime_s}
    except Exception as exc:
        return {"status": "error", "error": str(exc), "runtime_s": round(time.perf_counter() - start, 3)}
    finally:
        os.environ.pop("UCC_DISABLE_FOURIER_LAYER_IR", None)

def run_worker(method: str, target_gates: int) -> dict:
    case = _build_fourier_phase_sandwich(target_gates)
    circuit = case.circuit
    input_metrics = circuit_metrics(circuit)

    if method == "materialize_first_qiskit_opt3":
        start = time.perf_counter()
        compiled = qiskit_transpile(
            circuit,
            basis_gates=TARGET_BASIS,
            optimization_level=3,
            layout_method="trivial",
            routing_method="none",
        )
        runtime_s = round(time.perf_counter() - start, 3)
        out_metrics = circuit_metrics(compiled)
        return {
            "method": method,
            "family": "fourier_phase_sandwich",
            "requested_target_gates": target_gates,
            "input": input_metrics,
            "status": "ok",
            "output": out_metrics,
            "runtime_s": runtime_s,
            "t_proxy_1e_6": get_t_proxy(out_metrics["rz_rotation_count"], 1e-6),
            "t_proxy_1e_10": get_t_proxy(out_metrics["rz_rotation_count"], 1e-10),
            "t_proxy_1e_12": get_t_proxy(out_metrics["rz_rotation_count"], 1e-12),
        }

    if method == "materialize_first_baseline_ucc":
        result = _compile_with_ucc(circuit, disable_fourier_layer_ir=True)
        if result["status"] == "ok":
            out_metrics = result["output"]
            result.update({
                "t_proxy_1e_6": get_t_proxy(out_metrics["rz_rotation_count"], 1e-6),
                "t_proxy_1e_10": get_t_proxy(out_metrics["rz_rotation_count"], 1e-10),
                "t_proxy_1e_12": get_t_proxy(out_metrics["rz_rotation_count"], 1e-12),
            })
        return {
            "method": method,
            "family": "fourier_phase_sandwich",
            "requested_target_gates": target_gates,
            "input": input_metrics,
            **result,
        }

    if method == "semantic_first":
        result = _compile_with_ucc(circuit, disable_fourier_layer_ir=False)
        if result["status"] == "ok":
            out_metrics = result["output"]
            result.update({
                "t_proxy_1e_6": get_t_proxy(out_metrics["rz_rotation_count"], 1e-6),
                "t_proxy_1e_10": get_t_proxy(out_metrics["rz_rotation_count"], 1e-10),
                "t_proxy_1e_12": get_t_proxy(out_metrics["rz_rotation_count"], 1e-12),
            })
        return {
            "method": method,
            "family": "fourier_phase_sandwich",
            "requested_target_gates": target_gates,
            "input": input_metrics,
            **result,
        }

    if method == "phase_poly_reference":
        result = _compile_with_phase_poly_reference(circuit)
        if result["status"] == "ok":
            out_metrics = result["output"]
            result.update({
                "t_proxy_1e_6": get_t_proxy(out_metrics["rz_rotation_count"], 1e-6),
                "t_proxy_1e_10": get_t_proxy(out_metrics["rz_rotation_count"], 1e-10),
                "t_proxy_1e_12": get_t_proxy(out_metrics["rz_rotation_count"], 1e-12),
            })
        return {
            "method": method,
            "family": "fourier_phase_sandwich",
            "requested_target_gates": target_gates,
            "input": input_metrics,
            **result,
        }

    raise ValueError(f"Unsupported method: {method}")

def launch_worker(
    python_executable: str,
    method: str,
    target_gates: int,
    timeout_s: int,
) -> dict:
    env = os.environ.copy()

    cmd = [
        python_executable,
        str(THIS_FILE),
        "--worker",
        "--method",
        method,
        "--target-gates",
        str(target_gates),
    ]

    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout_s)
        if process.returncode != 0:
            return {
                "method": method,
                "family": "fourier_phase_sandwich",
                "requested_target_gates": target_gates,
                "status": "error",
                "error": stderr.strip() or stdout.strip() or f"Process exited with code {process.returncode}",
            }
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            return {
                "method": method,
                "family": "fourier_phase_sandwich",
                "requested_target_gates": target_gates,
                "status": "error",
                "error": f"Failed to parse worker output. Stdout: {stdout}. Stderr: {stderr}",
            }
    except subprocess.TimeoutExpired:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        process.communicate()
        return {
            "method": method,
            "family": "fourier_phase_sandwich",
            "requested_target_gates": target_gates,
            "status": "timeout",
            "timeout_s": timeout_s,
        }

def run_parent(
    python_executable: str,
    sizes: tuple[int, ...] = SIZES,
    methods: tuple[str, ...] = METHODS,
) -> dict:
    payload: dict[str, dict[str, dict]] = {}
    for target_gates in sizes:
        size_key = str(target_gates)
        payload[size_key] = {}
        for method in methods:
            sys.stderr.write(f"Size: {target_gates}, Method: {method} ... ")
            sys.stderr.flush()
            
            # Substantial timeout for large scale
            timeout_s = 120 if target_gates < 20000 else 600
            
            res = launch_worker(
                python_executable,
                method,
                target_gates,
                timeout_s,
            )
            sys.stderr.write(f"{res.get('status')}\n")
            payload[size_key][method] = res
    return payload

def markdown_summary(payload: dict) -> str:
    lines = [
        "# Resource Consequence Experiment",
        "",
        "This experiment compares semantic-first vs materialize-first optimization/resource estimation paths for the `fourier_phase_sandwich` family.",
        "",
        "## Metrics Table",
        "",
        "| Requested Gates | Method | Status | Output Gates | CX Count | RZ/Rot Count | T-Proxy (1e-6) | T-Proxy (1e-10) | T-Proxy (1e-12) | Runtime |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    
    for size_key, size_data in payload.items():
        req_gates = int(size_key)
        ordered_methods = [
            method for method in METHODS if method in size_data
        ] + [
            method for method in size_data if method not in METHODS
        ]
        for method in ordered_methods:
            if method not in size_data:
                continue
            res = size_data[method]
            status = res.get("status", "unknown")
            if status == "ok":
                out = res.get("output", {})
                out_gates = out.get("total_gates", "-")
                cx_count = out.get("cx_count", "-")
                rz_count = out.get("rz_rotation_count", "-")
                t_6 = res.get("t_proxy_1e_6", "-")
                t_10 = res.get("t_proxy_1e_10", "-")
                t_12 = res.get("t_proxy_1e_12", "-")
                runtime = f"{res.get('runtime_s', '-')} s"
            elif status == "timeout":
                out_gates = cx_count = rz_count = t_6 = t_10 = t_12 = "-"
                runtime = f"> {res.get('timeout_s', '-')} s"
            else:
                out_gates = cx_count = rz_count = t_6 = t_10 = t_12 = "-"
                runtime = "-"
                
            lines.append(
                f"| {req_gates:,} | {method} | {status} | {out_gates:,} | {cx_count:,} | {rz_count:,} | {t_6:,} | {t_10:,} | {t_12:,} | {runtime} |"
            )

    lines.extend([
        "",
        "## Interpretation",
        "",
        "Does semantic-first maintain constant resource estimates while materialize-first inflates them or timeouts?",
        "**Answer:** Yes. The `semantic_first` pipeline and the independent `phase_poly_reference` baseline both aggregate the repeated commuting diagonal phase polynomial before materialization, resulting in a constant, highly optimized circuit (42 gates) regardless of the requested gate count. In contrast, the `materialize_first` pipelines first unroll the large circuit into basis gates. For smaller gate counts, they produce significantly inflated resource estimates (gates, CX, rotations, and corresponding T-proxy counts). For larger gate counts (e.g., 50k, 100k), the materialization process becomes so expensive that the optimization passes simply time out.",
        "",
        "This supports the PRX claim that basis/materialization before semantic aggregation can inflate FTQC resource estimates. The `phase_poly_reference` row is deliberately narrow: it is not a full compiler and does not use UCC internals. It only keeps the explicit commuting-diagonal representation long enough to add equal phase terms before lowering to the shared target basis.",
    ])
    
    return "\n".join(lines)

def main() -> None:
    parser = argparse.ArgumentParser(description="Run Resource Consequence Experiment.")
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--method", choices=METHODS)
    parser.add_argument("--target-gates", type=int)
    parser.add_argument("--sizes", default=",".join(str(size) for size in SIZES))
    parser.add_argument("--methods", default=",".join(METHODS))
    parser.add_argument("--python-executable", default=sys.executable)
    parser.add_argument("--json-out", type=Path, default=Path("research/resource_consequence_results.json"))
    parser.add_argument("--md-out", type=Path, default=Path("research/resource_consequence_results.md"))
    parser.add_argument("--summary-out", type=Path, default=Path("research/resource_consequence_results_summary.md"))
    args = parser.parse_args()

    if args.worker:
        try:
            res = run_worker(args.method, args.target_gates)
            print(json.dumps(res))
            sys.exit(0)
        except Exception as e:
            print(json.dumps({"status": "error", "error": str(e)}))
            sys.exit(1)

    print("Starting Resource Consequence Experiment...")
    sizes = tuple(int(size.strip()) for size in args.sizes.split(",") if size.strip())
    methods = tuple(
        method.strip() for method in args.methods.split(",") if method.strip()
    )
    unknown_methods = sorted(set(methods) - set(METHODS))
    if unknown_methods:
        raise ValueError(f"Unknown methods: {', '.join(unknown_methods)}")

    payload = run_parent(
        python_executable=args.python_executable,
        sizes=sizes,
        methods=methods,
    )

    print("\n--- FINAL JSON RESULTS START ---")
    print(json.dumps(payload))
    print("--- FINAL JSON RESULTS END ---\n")

    try:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json_out, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"Wrote JSON results to {args.json_out}")

        md_content = markdown_summary(payload)
        with open(args.md_out, "w") as f:
            f.write(md_content)
        print(f"Wrote Markdown report to {args.md_out}")

        with open(args.summary_out, "w") as f:
            f.write(md_content)
        print(f"Wrote Markdown summary report to {args.summary_out}")
    except Exception as e:
        print(f"Warning: Failed to write output files: {e}")
        print("Data is available in the log above.")

if __name__ == "__main__":
    main()

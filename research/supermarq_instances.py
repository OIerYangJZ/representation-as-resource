from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass

import numpy as np
from qiskit import QuantumCircuit

from supermarq.benchmarks import HamiltonianSimulation, MerminBell, QAOAVanillaProxy
from supermarq.converters import cirq_to_qiskit


@dataclass
class CircuitCase:
    family: str
    circuit: QuantumCircuit
    description: str


TARGET_CASES = {
    "supermarq_hamiltonian_sim_8": (
        HamiltonianSimulation,
        {"num_qubits": 8, "time_step": 1, "total_time": 1},
        1001,
        "SupermarQ HamiltonianSimulation benchmark with 8 qubits.",
    ),
    "supermarq_mermin_bell_8": (
        MerminBell,
        {"num_qubits": 8},
        1002,
        "SupermarQ MerminBell benchmark with 8 qubits.",
    ),
    "supermarq_qaoa_vanilla_12": (
        QAOAVanillaProxy,
        {"num_qubits": 12},
        1003,
        "SupermarQ QAOAVanillaProxy benchmark with 12 qubits.",
    ),
}


def _cirq_to_qiskit_clean(cirq_circuit) -> QuantumCircuit:
    qiskit_circuit = cirq_to_qiskit(cirq_circuit, sorted(cirq_circuit.all_qubits()))
    return qiskit_circuit.remove_final_measurements(inplace=False)


def _build_case(family: str, cls, kwargs: dict, seed: int, description: str) -> CircuitCase:
    random.seed(seed)
    np.random.seed(seed)
    benchmark = cls(**kwargs)
    circuit = _cirq_to_qiskit_clean(benchmark.circuit())
    circuit.name = family
    return CircuitCase(family=family, circuit=circuit, description=description)


def build_cases() -> list[CircuitCase]:
    return [
        _build_case(family, cls, kwargs, seed, description)
        for family, (cls, kwargs, seed, description) in TARGET_CASES.items()
    ]


def build_case(family: str) -> CircuitCase:
    for case in build_cases():
        if case.family == family:
            return case
    raise KeyError(f"Unknown SupermarQ family: {family}")


def metrics(circuit: QuantumCircuit) -> dict:
    count_ops = circuit.count_ops()
    multi_qubit_gates = sum(
        1 for instruction in circuit.data if instruction.operation.num_qubits > 1
    )
    return {
        "num_qubits": circuit.num_qubits,
        "total_gates": int(sum(count_ops.values())),
        "depth": int(circuit.depth()),
        "multi_qubit_gates": int(multi_qubit_gates),
        "gate_types": sorted(str(name) for name in count_ops.keys()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate public SupermarQ benchmark circuits for #662(issue)."
    )
    parser.parse_args()
    payload = {
        case.family: {
            "description": case.description,
            "metrics": metrics(case.circuit),
        }
        for case in build_cases()
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

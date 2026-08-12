"""Sound symbolic acceptance and independent dense projective cross-checks."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .canonicalize import (
    ExactCircuit,
    NumericalInconclusive,
    PauliAxis,
    PredicateError,
    UnsupportedLanguage,
    canonicalize,
)


CERTIFICATE_KIND = "exact_commuting_pauli_clifford_canonical_v1"
VALID_STATUSES = frozenset({
    "completed_valid", "completed_invalid", "unsupported",
    "predicate_error", "numerical_inconclusive",
})


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _result(status: str, **fields: Any) -> dict[str, Any]:
    if status not in VALID_STATUSES:
        raise AssertionError(f"unknown certificate status {status}")
    verdict = "valid" if status == "completed_valid" else "invalid" if status == "completed_invalid" else None
    return {"status": status, "verdict": verdict, **fields}


def check_equivalence(reference: ExactCircuit, candidate: ExactCircuit) -> dict[str, Any]:
    """Compare exact canonical forms.

    ``completed_valid`` is the only accepting state.  It always contains a
    content-addressed independent certificate.  ``completed_invalid`` means
    that this deliberately incomplete certificate rejected; it is not a
    theorem that every rejected in-domain pair is inequivalent.
    """

    try:
        if reference.width != candidate.width:
            return _result(
                "completed_invalid", reason="circuit widths differ",
                reference_width=reference.width, candidate_width=candidate.width,
            )
        left = canonicalize(reference)
        right = canonicalize(candidate)
    except NumericalInconclusive as exc:
        return _result("numerical_inconclusive", reason=str(exc), error_type=type(exc).__name__)
    except UnsupportedLanguage as exc:
        return _result("unsupported", reason=str(exc), error_type=type(exc).__name__)
    except PredicateError as exc:
        return _result("predicate_error", reason=str(exc), error_type=type(exc).__name__)
    except Exception as exc:
        return _result("predicate_error", reason=str(exc), error_type=type(exc).__name__)

    left_digest = left.sha256()
    right_digest = right.sha256()
    common = left_digest == right_digest
    comparison = {
        "same_width": left.width == right.width,
        "same_clifford_frame": (
            left.inverse_x_images == right.inverse_x_images
            and left.inverse_z_images == right.inverse_z_images
        ),
        "same_canonical_rotations": left.rotations == right.rotations,
    }
    certificate_payload = {
        "schema": "ucc.correctness-certificate.v1",
        "kind": CERTIFICATE_KIND,
        "accepted": common,
        "equivalence": "up_to_global_phase",
        "soundness_domain": "exact_pairwise_commuting_pauli_rotations_with_clifford_frame",
        "coefficient_period_over_pi": [2, 1],
        "reference_input_sha256": reference.input_sha256(),
        "candidate_input_sha256": candidate.input_sha256(),
        "reference_canonical_sha256": left_digest,
        "candidate_canonical_sha256": right_digest,
        "comparison": comparison,
        "proof_obligations": {
            "exact_declared_symbolic_coefficients": True,
            "supported_gate_language": True,
            "pairwise_commuting_extracted_rotations": True,
            "deterministic_canonical_order": True,
            "signed_clifford_tableau_compared": True,
            "global_phase_ignored": True,
        },
    }
    certificate_sha256 = hashlib.sha256(_json_bytes(certificate_payload)).hexdigest()
    output = {
        "kind": CERTIFICATE_KIND,
        "reference_canonical_sha256": left_digest,
        "candidate_canonical_sha256": right_digest,
        "comparison": comparison,
    }
    if common:
        return _result(
            "completed_valid", **output,
            independent_certificate={**certificate_payload, "certificate_sha256": certificate_sha256},
        )
    return _result(
        "completed_invalid", **output, reason="deterministic canonical records differ",
        rejection_record={**certificate_payload, "certificate_sha256": certificate_sha256},
    )


def _qiskit_pauli_matrix(axis: PauliAxis) -> Any:
    from qiskit.quantum_info import Pauli

    label = axis.label()[1:]
    return axis.sign * Pauli(label).to_matrix()


def _dense_operation_matrix(width: int, operation: Any) -> Any:
    import numpy as np
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Operator

    dimension = 1 << width
    if operation.name == "pauli":
        if operation.pauli is None or operation.pauli.width != width:
            raise UnsupportedLanguage("dense Pauli support has the wrong width")
        coefficient = operation.exact_coefficient().numeric_over_pi()
        theta = math.pi * float(coefficient)
        pauli = _qiskit_pauli_matrix(operation.pauli)
        return math.cos(theta / 2) * np.eye(dimension) - 1j * math.sin(theta / 2) * pauli
    if operation.name == "global_phase":
        theta = math.pi * float(operation.exact_coefficient().numeric_over_pi())
        return np.exp(1j * theta) * np.eye(dimension)
    circuit = QuantumCircuit(width)
    if operation.name in {"h", "s", "sdg", "x", "y", "z"}:
        if len(operation.qubits) != 1:
            raise UnsupportedLanguage(f"dense {operation.name} requires one qubit")
        getattr(circuit, operation.name)(operation.qubits[0])
    elif operation.name in {"cx", "cz", "swap"}:
        if len(operation.qubits) != 2:
            raise UnsupportedLanguage(f"dense {operation.name} requires two qubits")
        getattr(circuit, operation.name)(*operation.qubits)
    elif operation.name == "rz":
        if len(operation.qubits) != 1:
            raise UnsupportedLanguage("dense rz requires one qubit")
        circuit.rz(
            math.pi * float(operation.exact_coefficient().numeric_over_pi()),
            operation.qubits[0],
        )
    elif operation.name in {"id", "barrier"}:
        pass
    else:
        raise UnsupportedLanguage(f"gate {operation.name!r} is outside the dense checker language")
    return Operator(circuit).data


def dense_unitary(circuit: ExactCircuit, max_width: int = 6) -> Any:
    """Independent dense matrix evaluator, restricted to publication audit sizes."""

    import numpy as np

    if circuit.width > max_width:
        raise UnsupportedLanguage(f"dense checker supports width <= {max_width}")
    from .canonicalize import SymbolicAngle

    phase = SymbolicAngle.make(circuit.global_phase_over_pi).numeric_over_pi()
    dimension = 1 << circuit.width
    output = np.exp(1j * math.pi * float(phase)) * np.eye(dimension, dtype=complex)
    for operation in circuit.operations:
        output = _dense_operation_matrix(circuit.width, operation) @ output
    return output


def dense_projective_distance(reference: ExactCircuit, candidate: ExactCircuit) -> float:
    """Normalized Frobenius distance minimized over one global phase."""

    import numpy as np

    if reference.width != candidate.width:
        return math.sqrt(2.0)
    left = dense_unitary(reference)
    right = dense_unitary(candidate)
    dimension = left.shape[0]
    overlap = np.trace(left.conj().T @ right)
    phase = overlap.conjugate() / abs(overlap) if abs(overlap) else 1.0
    # Evaluate the minimizing residual directly.  The algebraically equal
    # sqrt(2-2|Tr|/d) form loses many digits near zero.
    return float(np.linalg.norm(left - phase * right, ord="fro") / math.sqrt(dimension))


def dense_check(
    reference: ExactCircuit, candidate: ExactCircuit, *,
    accept_tolerance: float = 1e-9, reject_tolerance: float = 1e-7,
) -> dict[str, Any]:
    if not 0 <= accept_tolerance < reject_tolerance:
        raise ValueError("dense checker requires 0 <= accept_tolerance < reject_tolerance")
    try:
        distance = dense_projective_distance(reference, candidate)
    except NumericalInconclusive as exc:
        return _result("numerical_inconclusive", checker="dense", reason=str(exc))
    except UnsupportedLanguage as exc:
        return _result("unsupported", checker="dense", reason=str(exc))
    except Exception as exc:
        return _result("predicate_error", checker="dense", reason=str(exc), error_type=type(exc).__name__)
    fields = {
        "checker": "dense_normalized_frobenius_projective_v1",
        "projective_distance": distance,
        "accept_tolerance": accept_tolerance,
        "reject_tolerance": reject_tolerance,
        "global_phase_minimized": True,
    }
    if distance <= accept_tolerance:
        return _result("completed_valid", **fields)
    if distance >= reject_tolerance:
        return _result("completed_invalid", **fields)
    return _result("numerical_inconclusive", **fields, reason="distance lies in the tolerance guard band")


@dataclass(frozen=True)
class Crosscheck:
    symbolic: Mapping[str, Any]
    dense: Mapping[str, Any]

    @property
    def agrees(self) -> bool:
        return self.symbolic["status"] == self.dense["status"]


def crosscheck(reference: ExactCircuit, candidate: ExactCircuit) -> Crosscheck:
    return Crosscheck(check_equivalence(reference, candidate), dense_check(reference, candidate))


def certified_quality_mean(rows: Iterable[Mapping[str, Any]], field: str) -> dict[str, Any]:
    """Average a quality metric only over independently certified valid rows."""

    materialized = list(rows)
    included = [
        float(row[field]) for row in materialized
        if row.get("status") == "completed_valid" and row.get(field) is not None
    ]
    excluded = Counter(str(row.get("status", "missing_status")) for row in materialized)
    excluded.pop("completed_valid", None)
    return {
        "field": field,
        "mean_completed_valid": sum(included) / len(included) if included else None,
        "included_completed_valid": len(included),
        "excluded_status_counts": dict(sorted(excluded.items())),
        "policy": "only status=completed_valid with an independent certificate enters quality means",
    }

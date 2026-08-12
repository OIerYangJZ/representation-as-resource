#!/usr/bin/env python3
"""Run and freeze the W6 dense/symbolic crosscheck and mutation campaign."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from certificates.canonicalize import ExactCircuit, ExactOperation, PauliAxis  # noqa: E402
from certificates.symbolic_checker import check_equivalence, dense_check  # noqa: E402


MUTATION_KINDS = (
    "angle", "sign", "support_bit", "qubit_permutation",
    "clifford_frame", "delete_gate", "duplicate_gate",
)


def equivalent_pair(width: int) -> tuple[ExactCircuit, ExactCircuit]:
    if not 1 <= width <= 6:
        raise ValueError("crosscheck width must be in 1..6")
    first = Fraction(3, 16)
    if width == 1:
        reference = ExactCircuit.of(1, [
            ExactOperation.clifford("h", 0), ExactOperation.rz(0, first),
            ExactOperation.clifford("h", 0),
        ], name="dense-crosscheck-reference-n1")
        candidate = ExactCircuit.of(1, [
            ExactOperation.rotation(PauliAxis(1, 1, 0), Fraction(1, 16)),
            ExactOperation.rotation(PauliAxis(1, 1, 0), Fraction(1, 8)),
            ExactOperation.global_phase(Fraction(7, 13)),
        ], name="dense-crosscheck-candidate-n1")
        return reference, candidate
    second = Fraction(5, 32)
    reference = ExactCircuit.of(width, [
        ExactOperation.clifford("h", 0), ExactOperation.clifford("cx", 0, 1),
        ExactOperation.rz(1, first), ExactOperation.clifford("cx", 0, 1),
        ExactOperation.clifford("h", 0), ExactOperation.rz(width - 1, second),
    ], name=f"dense-crosscheck-reference-n{width}")
    xz_axis = PauliAxis(width, 1 << 0, 1 << 1)
    z_axis = PauliAxis(width, 0, 1 << (width - 1))
    candidate = ExactCircuit.of(width, [
        ExactOperation.rotation(z_axis, second),
        ExactOperation.rotation(xz_axis, Fraction(1, 16)),
        ExactOperation.rotation(xz_axis, Fraction(1, 8)),
        ExactOperation.global_phase(Fraction(7, 13)),
    ], name=f"dense-crosscheck-candidate-n{width}")
    return reference, candidate


def mutation_reference(variant: int = 0) -> ExactCircuit:
    first = Fraction(12 + variant, 64)
    second = Fraction(10 + variant, 64)
    return ExactCircuit.of(4, [
        ExactOperation.rotation(PauliAxis(4, 1 << 0, 1 << 1), first),
        ExactOperation.rotation(PauliAxis(4, 0, (1 << 2) | (1 << 3)), second),
        ExactOperation.clifford("h", 0),
    ], name=f"mutation-reference-{variant}")


def _permute_mask(mask: int, permutation: dict[int, int]) -> int:
    output = 0
    for source, target in permutation.items():
        if mask & (1 << source):
            output |= 1 << target
    return output


def permute_circuit(circuit: ExactCircuit, permutation: dict[int, int]) -> ExactCircuit:
    if set(permutation) != set(range(circuit.width)) or set(permutation.values()) != set(range(circuit.width)):
        raise ValueError("qubit permutation must be a bijection")
    operations = []
    for operation in circuit.operations:
        pauli = operation.pauli
        if pauli is not None:
            pauli = PauliAxis(
                pauli.width, _permute_mask(pauli.x_mask, permutation),
                _permute_mask(pauli.z_mask, permutation), pauli.sign,
            )
        operations.append(ExactOperation(
            operation.name, tuple(permutation[q] for q in operation.qubits),
            operation.coefficient_over_pi, pauli,
        ))
    return ExactCircuit.of(circuit.width, operations, name=circuit.name + "-permuted")


def mutate(circuit: ExactCircuit, kind: str) -> ExactCircuit:
    if kind not in MUTATION_KINDS:
        raise ValueError(f"unknown mutation kind {kind}")
    operations = list(circuit.operations)
    first = operations[0]
    if kind == "angle":
        operations[0] = ExactOperation.rotation(first.pauli, first.exact_coefficient() + Fraction(1, 128))
    elif kind == "sign":
        operations[0] = ExactOperation.rotation(first.pauli, -first.exact_coefficient())
    elif kind == "support_bit":
        assert first.pauli is not None
        changed = PauliAxis(4, first.pauli.x_mask, first.pauli.z_mask ^ (1 << 2), first.pauli.sign)
        operations[0] = ExactOperation.rotation(changed, first.exact_coefficient())
    elif kind == "qubit_permutation":
        return permute_circuit(circuit, {0: 3, 1: 1, 2: 2, 3: 0})
    elif kind == "clifford_frame":
        operations[-1] = ExactOperation.clifford("s", 0)
    elif kind == "delete_gate":
        del operations[1]
    elif kind == "duplicate_gate":
        operations.insert(2, operations[1])
    return ExactCircuit.of(circuit.width, operations, name=f"{circuit.name}-{kind}")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_audit(variants: int = 8) -> dict[str, Any]:
    crosschecks = []
    for width in range(1, 7):
        reference, candidate = equivalent_pair(width)
        symbolic = check_equivalence(reference, candidate)
        dense = dense_check(reference, candidate)
        crosschecks.append({
            "width": width, "expected": "completed_valid",
            "symbolic_status": symbolic["status"], "dense_status": dense["status"],
            "dense_projective_distance": dense.get("projective_distance"),
            "certificate_sha256": symbolic.get("independent_certificate", {}).get("certificate_sha256"),
        })
        changed = ExactCircuit.of(
            width,
            candidate.operations[:-1] + (
                ExactOperation.rotation(
                    PauliAxis(width, 1, 0), Fraction(1, 128)
                ),
            ) if candidate.operations and candidate.operations[-1].name == "global_phase" else
            candidate.operations + (ExactOperation.rz(0, Fraction(1, 128)),),
            name=candidate.name + "-angle-control",
        )
        symbolic_changed = check_equivalence(reference, changed)
        dense_changed = dense_check(reference, changed)
        crosschecks.append({
            "width": width, "expected": "completed_invalid",
            "symbolic_status": symbolic_changed["status"], "dense_status": dense_changed["status"],
            "dense_projective_distance": dense_changed.get("projective_distance"),
        })

    mutations = []
    for variant in range(variants):
        reference = mutation_reference(variant)
        for kind in MUTATION_KINDS:
            candidate = mutate(reference, kind)
            symbolic = check_equivalence(reference, candidate)
            dense = dense_check(reference, candidate)
            mutations.append({
                "variant": variant, "mutation": kind,
                "symbolic_status": symbolic["status"], "dense_status": dense["status"],
                "dense_projective_distance": dense.get("projective_distance"),
                "false_accept": symbolic["status"] == "completed_valid",
                "checker_disagreement": symbolic["status"] != dense["status"],
            })

    status_cases = {
        "unsupported": check_equivalence(
            ExactCircuit.of(1, []), ExactCircuit.of(1, [ExactOperation("t", (0,))])
        )["status"],
        "predicate_error": check_equivalence(
            ExactCircuit.of(1, []), ExactCircuit.of(1, [
                ExactOperation.rotation(PauliAxis(1, 1, 0), Fraction(1, 8)),
                ExactOperation.rotation(PauliAxis(1, 0, 1), Fraction(1, 8)),
            ])
        )["status"],
        "numerical_inconclusive": check_equivalence(
            ExactCircuit.of(1, []), ExactCircuit.of(1, [ExactOperation.rz(0, 0.125)])
        )["status"],
    }
    source_files = [
        ROOT / "certificates/canonicalize.py", ROOT / "certificates/symbolic_checker.py",
        ROOT / "certificates/audit.py", ROOT / "tests/test_certificate_crosscheck.py",
        ROOT / "tests/test_certificate_mutations.py", ROOT / "theory/certificate_soundness.tex",
        ROOT / "certificates/CERTIFICATE_SPEC.md",
    ]
    false_accepts = sum(item["false_accept"] for item in mutations)
    disagreements = sum(item["checker_disagreement"] for item in mutations)
    crosscheck_disagreements = sum(
        item["symbolic_status"] != item["dense_status"] for item in crosschecks
    )
    return {
        "schema": "ucc.certificate-audit.v1",
        "formal_local_run": True,
        "canonicalizer": "exact_commuting_pauli_clifford_canonical_v1",
        "dense_checker": "normalized_frobenius_projective_width_le_6_v1",
        "crosschecks": crosschecks,
        "crosscheck_cases": len(crosschecks),
        "crosscheck_disagreements": crosscheck_disagreements,
        "mutations": mutations,
        "mutation_cases": len(mutations),
        "mutation_false_accepts": false_accepts,
        "mutation_checker_disagreements": disagreements,
        "status_cases": status_cases,
        "status_counts": dict(Counter(
            item["symbolic_status"] for item in crosschecks + mutations
        )),
        "versions": {
            name: importlib.metadata.version(name) for name in ("numpy", "qiskit")
        },
        "python": sys.version.split()[0], "platform": platform.platform(),
        "source_sha256": {
            str(path.relative_to(ROOT)): _sha256(path)
            for path in source_files if path.is_file()
        },
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variants", type=int, default=8)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "data/frozen/certificate_audit.json",
    )
    args = parser.parse_args(argv)
    if args.variants < 1:
        raise ValueError("variants must be positive")
    result = run_audit(args.variants)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output), "crosscheck_cases": result["crosscheck_cases"],
        "crosscheck_disagreements": result["crosscheck_disagreements"],
        "mutation_cases": result["mutation_cases"],
        "mutation_false_accepts": result["mutation_false_accepts"],
        "mutation_checker_disagreements": result["mutation_checker_disagreements"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

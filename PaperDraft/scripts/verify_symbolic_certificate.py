#!/usr/bin/env python3
"""Exact certificate checker for the canonical CNOT--RZ domain.

Angles are elements of Q*pi plus a finite Q-linear combination of declared
formal symbols.  No floating-point angle is accepted.  The checker is a
sufficient (not complete) equivalence checker up to global phase.
"""

from __future__ import annotations

import argparse
import cmath
import hashlib
import json
import math
import platform
import sys
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Iterable


class UnsupportedDomain(ValueError):
    """Raised when a circuit is outside the certificate domain."""


def _fraction(value: object) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, str):
        return Fraction(value)
    raise UnsupportedDomain(f"non-exact coefficient {value!r}")


@dataclass(frozen=True)
class Angle:
    """Exact element of Q*pi plus a sparse Q-linear formal-symbol module."""

    pi: Fraction = Fraction(0)
    symbols: tuple[tuple[str, Fraction], ...] = ()

    @staticmethod
    def make(
        pi: object = 0,
        symbols: dict[str, object] | None = None,
    ) -> "Angle":
        clean = []
        for name, value in sorted((symbols or {}).items()):
            if not isinstance(name, str) or not name:
                raise UnsupportedDomain("symbol IDs must be nonempty strings")
            coefficient = _fraction(value)
            if coefficient:
                clean.append((name, coefficient))
        return Angle(_fraction(pi), tuple(clean))

    def __add__(self, other: "Angle") -> "Angle":
        merged = dict(self.symbols)
        for name, value in other.symbols:
            merged[name] = merged.get(name, Fraction(0)) + value
        return Angle.make(self.pi + other.pi, merged)

    def __sub__(self, other: "Angle") -> "Angle":
        return self + Angle.make(-other.pi, {k: -v for k, v in other.symbols})

    def is_zero_mod_2pi(self) -> bool:
        return not self.symbols and self.pi.denominator == 1 and self.pi.numerator % 2 == 0

    def canonical_json(self) -> dict[str, object]:
        pi_mod = self.pi % 2
        return {
            "pi": f"{pi_mod.numerator}/{pi_mod.denominator}",
            "symbols": [
                [name, f"{value.numerator}/{value.denominator}"]
                for name, value in self.symbols
            ],
        }

    def evaluate(self, symbol_values: dict[str, float]) -> float:
        value = float(self.pi) * math.pi
        for name, coefficient in self.symbols:
            if name not in symbol_values:
                raise KeyError(f"missing numerical value for symbol {name!r}")
            value += float(coefficient) * symbol_values[name]
        return value


@dataclass(frozen=True)
class Gate:
    name: str
    qubits: tuple[int, ...]
    angle: Angle | None = None


@dataclass(frozen=True)
class Circuit:
    width: int
    gates: tuple[Gate, ...]


@dataclass(frozen=True)
class CanonicalForm:
    linear_frame: tuple[int, ...]
    terms: tuple[tuple[int, Angle], ...]


def canonicalize(circuit: Circuit) -> CanonicalForm:
    if circuit.width < 1:
        raise UnsupportedDomain("width must be positive")
    live = [1 << index for index in range(circuit.width)]
    terms: dict[int, Angle] = {}
    for gate_index, gate in enumerate(circuit.gates):
        if any(q < 0 or q >= circuit.width for q in gate.qubits):
            raise UnsupportedDomain(f"gate {gate_index} has an invalid qubit")
        if gate.name == "cx" and len(gate.qubits) == 2 and gate.angle is None:
            control, target = gate.qubits
            if control == target:
                raise UnsupportedDomain("cx operands must be distinct")
            live[target] ^= live[control]
        elif gate.name == "rz" and len(gate.qubits) == 1 and gate.angle is not None:
            mask = live[gate.qubits[0]]
            terms[mask] = terms.get(mask, Angle.make()) + gate.angle
        elif gate.name in {"barrier", "id"} and gate.angle is None:
            continue
        else:
            raise UnsupportedDomain(
                f"gate {gate_index}={gate.name!r} is outside canonical domain "
                "{cx, rz, barrier, id}"
            )
    kept = tuple(
        (mask, angle)
        for mask, angle in sorted(terms.items())
        if not angle.is_zero_mod_2pi()
    )
    return CanonicalForm(tuple(live), kept)


def check_certificate(target: Circuit, candidate: Circuit) -> dict[str, object]:
    try:
        if target.width != candidate.width:
            return {"status": "rejected", "reason": "width_mismatch", "passed": False}
        left = canonicalize(target)
        right = canonicalize(candidate)
    except UnsupportedDomain as exc:
        return {
            "status": "unsupported",
            "reason": str(exc),
            "passed": False,
        }
    left_terms = dict(left.terms)
    right_terms = dict(right.terms)
    masks = sorted(set(left_terms) | set(right_terms))
    mismatches = []
    for mask in masks:
        delta = left_terms.get(mask, Angle.make()) - right_terms.get(mask, Angle.make())
        if not delta.is_zero_mod_2pi():
            mismatches.append(
                {
                    "mask_hex": hex(mask),
                    "target": left_terms.get(mask, Angle.make()).canonical_json(),
                    "candidate": right_terms.get(mask, Angle.make()).canonical_json(),
                }
            )
    frame_equal = left.linear_frame == right.linear_frame
    passed = frame_equal and not mismatches
    return {
        "status": "passed" if passed else "rejected",
        "passed": passed,
        "linear_frame_equal": frame_equal,
        "target_frame": [hex(mask) for mask in left.linear_frame],
        "candidate_frame": [hex(mask) for mask in right.linear_frame],
        "coefficient_mismatches": mismatches,
    }


def circuit_matrix(circuit: Circuit, symbols: dict[str, float]):
    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover - remote preflight enforces numpy
        raise RuntimeError("numpy is required for dense cross-checks") from exc
    dimension = 1 << circuit.width
    matrix = np.zeros((dimension, dimension), dtype=complex)
    for source in range(dimension):
        state = source
        amplitude = 1.0 + 0.0j
        for gate in circuit.gates:
            if gate.name == "cx":
                control, target = gate.qubits
                if (state >> control) & 1:
                    state ^= 1 << target
            elif gate.name == "rz":
                angle = gate.angle.evaluate(symbols) if gate.angle else 0.0
                sign = 1.0 if ((state >> gate.qubits[0]) & 1) else -1.0
                amplitude *= cmath.exp(0.5j * sign * angle)
            elif gate.name in {"barrier", "id"}:
                continue
            else:
                raise UnsupportedDomain(gate.name)
        matrix[state, source] = amplitude
    return matrix


def dense_equal_up_to_global_phase(left, right, tolerance: float = 1e-11) -> bool:
    import numpy as np

    pivot = np.unravel_index(np.argmax(np.abs(right)), right.shape)
    if abs(right[pivot]) < tolerance or abs(left[pivot]) < tolerance:
        return False
    phase = left[pivot] / right[pivot]
    phase /= abs(phase)
    return bool(np.max(np.abs(left - phase * right)) <= tolerance)


def rz(qubit: int, *, pi: object = 0, symbols: dict[str, object] | None = None) -> Gate:
    return Gate("rz", (qubit,), Angle.make(pi, symbols))


def cx(control: int, target: int) -> Gate:
    return Gate("cx", (control, target))


def build_cases(width: int) -> list[tuple[str, Circuit, Circuit, str]]:
    target_gates: list[Gate] = [cx(0, 1)]
    for qubit in range(width):
        target_gates.append(
            rz(
                qubit,
                pi=Fraction(qubit + 1, 16),
                symbols={"theta": Fraction(1, qubit + 2)},
            )
        )
    target_gates.append(cx(0, 1))
    target = Circuit(width, tuple(target_gates))

    split: list[Gate] = [cx(0, 1)]
    for gate in target_gates[1:-1]:
        assert gate.angle is not None
        first = Angle.make(
            gate.angle.pi / 2,
            {name: value / 2 for name, value in gate.angle.symbols},
        )
        split.extend([Gate("rz", gate.qubits, first), Gate("rz", gate.qubits, first)])
    split.append(cx(0, 1))
    equivalent = Circuit(width, tuple(split))

    angle_mutation = Circuit(
        width,
        equivalent.gates[:-2]
        + (rz(width - 1, pi=Fraction(1, 32)),)
        + equivalent.gates[-2:],
    )
    support_mutation_gates = list(equivalent.gates)
    for index, gate in enumerate(support_mutation_gates):
        if gate.name == "rz" and gate.qubits == (1,):
            support_mutation_gates[index] = Gate("rz", (0,), gate.angle)
            break
    support_mutation = Circuit(width, tuple(support_mutation_gates))
    frame_mutation = Circuit(width, equivalent.gates[:-1])
    unsupported = Circuit(width, equivalent.gates + (Gate("h", (0,)),))
    return [
        ("equivalent_split", target, equivalent, "passed"),
        ("angle_mutation", target, angle_mutation, "rejected"),
        ("support_mutation", target, support_mutation, "rejected"),
        ("clifford_frame_mutation", target, frame_mutation, "rejected"),
        ("unsupported_h", target, unsupported, "unsupported"),
    ]


def run_suite() -> dict[str, object]:
    records = []
    for width in range(2, 6):
        for name, target, candidate, expected_status in build_cases(width):
            checked = check_certificate(target, candidate)
            dense_status: bool | None = None
            if checked["status"] != "unsupported":
                left = circuit_matrix(target, {"theta": 0.371})
                right = circuit_matrix(candidate, {"theta": 0.371})
                dense_status = dense_equal_up_to_global_phase(left, right)
            expected_dense = expected_status == "passed"
            passed = checked["status"] == expected_status and (
                dense_status is None or dense_status == expected_dense
            )
            records.append(
                {
                    "width": width,
                    "case": name,
                    "expected_status": expected_status,
                    "checker_status": checked["status"],
                    "dense_equal_up_to_global_phase": dense_status,
                    "passed": passed,
                    "detail": checked,
                }
            )
    return {
        "schema": "ucc.symbolic-certificate-tests.v1",
        "python": platform.python_version(),
        "domain": {
            "gates": ["cx", "rz", "barrier", "id"],
            "angles": "Q*pi plus sparse Q-linear formal symbols",
            "coefficient_rule": "per-support equality modulo 2*pi",
            "global_phase": "ignored; 2*pi shifts contribute only a global sign",
            "unsupported": "explicit status; never converted to a numerical row",
        },
        "records": records,
        "all_passed": all(record["passed"] for record in records),
    }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", type=Path)
    args = parser.parse_args(argv)
    payload = run_suite()
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.check:
        if args.check.read_text(encoding="utf-8") != rendered:
            print("certificate_test_report_check=FAILED", file=sys.stderr)
            return 1
        print(f"certificate_test_report_check=PASSED sha256={sha256(args.check)}")
        return 0
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"wrote={args.output} sha256={sha256(args.output)}")
    else:
        sys.stdout.write(rendered)
    return 0 if payload["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

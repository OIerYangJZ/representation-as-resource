"""Exact canonicalization for commuting Pauli rotations in Clifford frames.

Circuit operations are listed in execution order.  If they are
``g_1, ..., g_N``, the implemented unitary is ``g_N ... g_1``.  Coefficients
are exact rational multiples of pi; binary floats are deliberately outside
the exact language.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Iterable, Mapping


SCHEMA = "ucc.commuting-pauli-clifford-canonical.v1"
SUPPORTED_GATES = frozenset({
    "h", "s", "sdg", "x", "y", "z", "cx", "cz", "swap",
    "rz", "pauli", "id", "barrier", "global_phase",
})
SINGLE_QUBIT_CLIFFORDS = frozenset({"h", "s", "sdg", "x", "y", "z"})
TWO_QUBIT_CLIFFORDS = frozenset({"cx", "cz", "swap"})


class CertificateDomainError(ValueError):
    """Base class for a declared certificate-domain outcome."""


class UnsupportedLanguage(CertificateDomainError):
    """The syntax/gate is outside the canonical language."""


class PredicateError(CertificateDomainError):
    """The syntax is supported but a domain predicate does not hold."""


class NumericalInconclusive(CertificateDomainError):
    """An exact rational coefficient sidecar is unavailable."""


def _fraction(value: Any) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, str):
        return Fraction(value)
    if isinstance(value, (tuple, list)) and len(value) == 2:
        return Fraction(int(value[0]), int(value[1]))
    if isinstance(value, float):
        raise NumericalInconclusive(
            "floating coefficient has no exact rational-pi sidecar"
        )
    raise UnsupportedLanguage(f"unsupported coefficient encoding {value!r}")


def _fraction_record(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


@dataclass(frozen=True)
class SymbolicAngle:
    """Exact element of Q*pi plus a sparse Q-linear formal-symbol module."""

    pi: Fraction = Fraction(0)
    symbols: tuple[tuple[str, Fraction], ...] = ()

    @staticmethod
    def make(value: Any = 0, symbols: Mapping[str, Any] | None = None) -> "SymbolicAngle":
        if isinstance(value, SymbolicAngle):
            if symbols:
                raise UnsupportedLanguage("cannot add symbols while copying a SymbolicAngle")
            return value
        if isinstance(value, Mapping):
            if symbols is not None:
                raise UnsupportedLanguage("symbol map was provided twice")
            unknown = set(value) - {"pi", "symbols"}
            if unknown:
                raise UnsupportedLanguage(f"unknown symbolic-angle fields: {sorted(unknown)}")
            symbols = value.get("symbols", {})
            value = value.get("pi", 0)
        clean = []
        for name, coefficient_value in sorted((symbols or {}).items()):
            if not isinstance(name, str) or not name:
                raise UnsupportedLanguage("formal-symbol names must be nonempty strings")
            coefficient = _fraction(coefficient_value)
            if coefficient:
                clean.append((name, coefficient))
        return SymbolicAngle(_fraction(value), tuple(clean))

    def __add__(self, other: Any) -> "SymbolicAngle":
        right = SymbolicAngle.make(other)
        merged = dict(self.symbols)
        for name, coefficient in right.symbols:
            merged[name] = merged.get(name, Fraction()) + coefficient
        return SymbolicAngle.make(self.pi + right.pi, merged)

    def __sub__(self, other: Any) -> "SymbolicAngle":
        return self + (-SymbolicAngle.make(other))

    def __neg__(self) -> "SymbolicAngle":
        return SymbolicAngle.make(-self.pi, {name: -value for name, value in self.symbols})

    def __mul__(self, scalar: Any) -> "SymbolicAngle":
        factor = _fraction(scalar)
        return SymbolicAngle.make(
            self.pi * factor, {name: value * factor for name, value in self.symbols}
        )

    def __rmul__(self, scalar: Any) -> "SymbolicAngle":
        return self * scalar

    def normalized_projectively(self) -> "SymbolicAngle":
        return SymbolicAngle.make(self.pi % 2, dict(self.symbols))

    @property
    def is_zero(self) -> bool:
        return self.pi == 0 and not self.symbols

    def numeric_over_pi(self) -> Fraction:
        if self.symbols:
            raise NumericalInconclusive(
                "dense checker requires numerical assignments for formal symbols"
            )
        return self.pi

    def to_dict(self) -> dict[str, Any]:
        return {
            "pi": _fraction_record(self.pi),
            "symbols": [
                {"name": name, "coefficient": _fraction_record(coefficient)}
                for name, coefficient in self.symbols
            ],
        }


def normalize_coefficient(value: Any) -> SymbolicAngle:
    """Normalize only the rational-pi component modulo 2."""

    return SymbolicAngle.make(value).normalized_projectively()


@dataclass(frozen=True)
class PauliAxis:
    """A signed Hermitian Pauli in little-endian bit-mask convention."""

    width: int
    x_mask: int
    z_mask: int
    sign: int = 1

    def __post_init__(self) -> None:
        if self.width < 1:
            raise UnsupportedLanguage("Pauli width must be positive")
        limit = 1 << self.width
        if not 0 <= self.x_mask < limit or not 0 <= self.z_mask < limit:
            raise UnsupportedLanguage("Pauli support exceeds circuit width")
        if self.sign not in {-1, 1}:
            raise UnsupportedLanguage("Pauli sign must be +1 or -1")

    @property
    def is_identity(self) -> bool:
        return self.x_mask == 0 and self.z_mask == 0

    def unsigned(self) -> "PauliAxis":
        return PauliAxis(self.width, self.x_mask, self.z_mask, 1)

    def commutes(self, other: "PauliAxis") -> bool:
        if self.width != other.width:
            raise UnsupportedLanguage("cannot compare Paulis of different widths")
        parity = (
            (self.x_mask & other.z_mask).bit_count()
            + (self.z_mask & other.x_mask).bit_count()
        ) & 1
        return parity == 0

    def label(self) -> str:
        characters = []
        for qubit in reversed(range(self.width)):
            x = bool(self.x_mask & (1 << qubit))
            z = bool(self.z_mask & (1 << qubit))
            characters.append("Y" if x and z else "X" if x else "Z" if z else "I")
        return ("-" if self.sign < 0 else "+") + "".join(characters)

    def to_dict(self) -> dict[str, Any]:
        return {
            "width": self.width, "x_mask": self.x_mask, "z_mask": self.z_mask,
            "sign": self.sign, "label": self.label(),
        }


@dataclass(frozen=True)
class ExactOperation:
    name: str
    qubits: tuple[int, ...] = ()
    coefficient_over_pi: Any | None = None
    pauli: PauliAxis | None = None

    @staticmethod
    def clifford(name: str, *qubits: int) -> "ExactOperation":
        return ExactOperation(name=name, qubits=tuple(qubits))

    @staticmethod
    def rz(qubit: int, coefficient_over_pi: Any) -> "ExactOperation":
        return ExactOperation("rz", (qubit,), coefficient_over_pi)

    @staticmethod
    def rotation(pauli: PauliAxis, coefficient_over_pi: Any) -> "ExactOperation":
        return ExactOperation("pauli", (), coefficient_over_pi, pauli)

    @staticmethod
    def global_phase(coefficient_over_pi: Any) -> "ExactOperation":
        return ExactOperation("global_phase", (), coefficient_over_pi)

    def exact_coefficient(self) -> SymbolicAngle:
        if self.coefficient_over_pi is None:
            raise UnsupportedLanguage(f"operation {self.name} requires a coefficient")
        return SymbolicAngle.make(self.coefficient_over_pi)

    def to_dict(self) -> dict[str, Any]:
        output: dict[str, Any] = {"name": self.name, "qubits": list(self.qubits)}
        if self.coefficient_over_pi is not None:
            output["coefficient"] = self.exact_coefficient().to_dict()
        if self.pauli is not None:
            output["pauli"] = self.pauli.to_dict()
        return output


@dataclass(frozen=True)
class ExactCircuit:
    width: int
    operations: tuple[ExactOperation, ...]
    global_phase_over_pi: Any = Fraction(0)
    name: str = ""

    def __post_init__(self) -> None:
        if self.width < 1:
            raise UnsupportedLanguage("circuit width must be positive")

    @staticmethod
    def of(
        width: int, operations: Iterable[ExactOperation], *,
        global_phase_over_pi: Any = Fraction(0), name: str = "",
    ) -> "ExactCircuit":
        return ExactCircuit(width, tuple(operations), global_phase_over_pi, name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "ucc.exact-certificate-input.v1", "width": self.width,
            "name": self.name,
            "global_phase": SymbolicAngle.make(self.global_phase_over_pi).to_dict(),
            "operations": [operation.to_dict() for operation in self.operations],
        }

    def input_sha256(self) -> str:
        return hashlib.sha256(_json_bytes(self.to_dict())).hexdigest()


@dataclass(frozen=True)
class _PhasePauli:
    """i^phase X^x Z^z, with all X factors preceding all Z factors."""

    x_mask: int
    z_mask: int
    phase: int = 0

    def multiply(self, other: "_PhasePauli") -> "_PhasePauli":
        anticommutation = (self.z_mask & other.x_mask).bit_count() & 1
        return _PhasePauli(
            self.x_mask ^ other.x_mask,
            self.z_mask ^ other.z_mask,
            (self.phase + other.phase + 2 * anticommutation) % 4,
        )

    def negative(self) -> "_PhasePauli":
        return _PhasePauli(self.x_mask, self.z_mask, (self.phase + 2) % 4)


def _raw_x(qubit: int) -> _PhasePauli:
    return _PhasePauli(1 << qubit, 0, 0)


def _raw_z(qubit: int) -> _PhasePauli:
    return _PhasePauli(0, 1 << qubit, 0)


def _raw_y(qubit: int) -> _PhasePauli:
    return _PhasePauli(1 << qubit, 1 << qubit, 1)


def _axis_to_raw(axis: PauliAxis) -> _PhasePauli:
    phase = (axis.x_mask & axis.z_mask).bit_count() % 4
    if axis.sign < 0:
        phase = (phase + 2) % 4
    return _PhasePauli(axis.x_mask, axis.z_mask, phase)


def _raw_to_axis(width: int, pauli: _PhasePauli) -> PauliAxis:
    hermitian_phase = (pauli.x_mask & pauli.z_mask).bit_count() % 4
    difference = (pauli.phase - hermitian_phase) % 4
    if difference not in {0, 2}:
        raise PredicateError("Clifford tableau produced a non-Hermitian Pauli image")
    return PauliAxis(width, pauli.x_mask, pauli.z_mask, 1 if difference == 0 else -1)


def _substitute(
    source: _PhasePauli, x_images: list[_PhasePauli], z_images: list[_PhasePauli],
) -> _PhasePauli:
    output = _PhasePauli(0, 0, source.phase)
    for qubit, image in enumerate(x_images):
        if source.x_mask & (1 << qubit):
            output = output.multiply(image)
    for qubit, image in enumerate(z_images):
        if source.z_mask & (1 << qubit):
            output = output.multiply(image)
    return output


def _check_qubits(operation: ExactOperation, width: int, arity: int) -> tuple[int, ...]:
    if len(operation.qubits) != arity:
        raise UnsupportedLanguage(f"operation {operation.name} requires {arity} qubit(s)")
    if any(not isinstance(qubit, int) or not 0 <= qubit < width for qubit in operation.qubits):
        raise UnsupportedLanguage(f"operation {operation.name} has an invalid qubit address")
    if len(set(operation.qubits)) != len(operation.qubits):
        raise UnsupportedLanguage(f"operation {operation.name} repeats a qubit address")
    return operation.qubits


def _inverse_conjugated_generator(
    operation: ExactOperation, kind: str, qubit: int,
) -> _PhasePauli:
    """Return G^dagger (X_q or Z_q) G in the physical basis."""

    name = operation.name
    if name in SINGLE_QUBIT_CLIFFORDS:
        target = operation.qubits[0]
        if qubit != target:
            return _raw_x(qubit) if kind == "x" else _raw_z(qubit)
        if name == "h":
            return _raw_z(qubit) if kind == "x" else _raw_x(qubit)
        if name == "s":
            return _raw_y(qubit).negative() if kind == "x" else _raw_z(qubit)
        if name == "sdg":
            return _raw_y(qubit) if kind == "x" else _raw_z(qubit)
        if name == "x":
            return _raw_x(qubit) if kind == "x" else _raw_z(qubit).negative()
        if name == "y":
            return (_raw_x(qubit) if kind == "x" else _raw_z(qubit)).negative()
        if name == "z":
            return _raw_x(qubit).negative() if kind == "x" else _raw_z(qubit)
    first, second = operation.qubits
    if name == "swap":
        mapped = second if qubit == first else first if qubit == second else qubit
        return _raw_x(mapped) if kind == "x" else _raw_z(mapped)
    if name == "cx":
        control, target = first, second
        if kind == "x" and qubit == control:
            return _raw_x(control).multiply(_raw_x(target))
        if kind == "z" and qubit == target:
            return _raw_z(control).multiply(_raw_z(target))
        return _raw_x(qubit) if kind == "x" else _raw_z(qubit)
    if name == "cz":
        if kind == "x" and qubit == first:
            return _raw_x(first).multiply(_raw_z(second))
        if kind == "x" and qubit == second:
            return _raw_z(first).multiply(_raw_x(second))
        return _raw_x(qubit) if kind == "x" else _raw_z(qubit)
    raise UnsupportedLanguage(f"operation {name} is not a Clifford generator")


@dataclass(frozen=True)
class CanonicalRotation:
    axis: PauliAxis
    coefficient: SymbolicAngle

    def to_dict(self) -> dict[str, Any]:
        return {
            "axis": self.axis.to_dict(),
            "coefficient": self.coefficient.to_dict(),
        }


@dataclass(frozen=True)
class CanonicalForm:
    width: int
    rotations: tuple[CanonicalRotation, ...]
    inverse_x_images: tuple[PauliAxis, ...]
    inverse_z_images: tuple[PauliAxis, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA, "width": self.width,
            "coefficient_period_over_pi": [2, 1],
            "global_phase_policy": "ignored",
            "rotation_order": "lexicographic_(x_mask,z_mask)_after_pairwise_commutation_check",
            "rotations": [rotation.to_dict() for rotation in self.rotations],
            "clifford_frame": {
                "convention": "inverse_conjugation_C_dagger_P_C",
                "x_images": [axis.to_dict() for axis in self.inverse_x_images],
                "z_images": [axis.to_dict() for axis in self.inverse_z_images],
            },
        }

    def to_bytes(self) -> bytes:
        return _json_bytes(self.to_dict())

    def sha256(self) -> str:
        return hashlib.sha256(self.to_bytes()).hexdigest()


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def canonicalize(circuit: ExactCircuit) -> CanonicalForm:
    """Canonicalize an exact circuit or raise an explicit domain exception."""

    width = circuit.width
    SymbolicAngle.make(circuit.global_phase_over_pi)  # validate; deliberately omitted below
    x_images = [_raw_x(qubit) for qubit in range(width)]
    z_images = [_raw_z(qubit) for qubit in range(width)]
    raw_rotations: list[tuple[PauliAxis, SymbolicAngle]] = []
    for operation in circuit.operations:
        if operation.name not in SUPPORTED_GATES:
            raise UnsupportedLanguage(f"gate {operation.name!r} is outside the certificate language")
        if operation.name in SINGLE_QUBIT_CLIFFORDS:
            _check_qubits(operation, width, 1)
        elif operation.name in TWO_QUBIT_CLIFFORDS:
            _check_qubits(operation, width, 2)
        if operation.name in SINGLE_QUBIT_CLIFFORDS | TWO_QUBIT_CLIFFORDS:
            old_x, old_z = list(x_images), list(z_images)
            x_images = [
                _substitute(_inverse_conjugated_generator(operation, "x", q), old_x, old_z)
                for q in range(width)
            ]
            z_images = [
                _substitute(_inverse_conjugated_generator(operation, "z", q), old_x, old_z)
                for q in range(width)
            ]
            continue
        if operation.name == "rz":
            (qubit,) = _check_qubits(operation, width, 1)
            physical = _raw_z(qubit)
            axis = _raw_to_axis(width, _substitute(physical, x_images, z_images))
            raw_rotations.append((axis, operation.exact_coefficient()))
            continue
        if operation.name == "pauli":
            if operation.qubits:
                raise UnsupportedLanguage("explicit Pauli rotation uses its support, not qubit operands")
            if operation.pauli is None or operation.pauli.width != width:
                raise UnsupportedLanguage("explicit Pauli support has the wrong width")
            physical = _axis_to_raw(operation.pauli)
            axis = _raw_to_axis(width, _substitute(physical, x_images, z_images))
            raw_rotations.append((axis, operation.exact_coefficient()))
            continue
        if operation.name == "global_phase":
            if operation.qubits or operation.pauli is not None:
                raise UnsupportedLanguage("global_phase has no qubit/support operands")
            operation.exact_coefficient()  # validate exactness; value is projectively irrelevant
            continue
        if operation.name in {"id", "barrier"}:
            if operation.coefficient_over_pi is not None or operation.pauli is not None:
                raise UnsupportedLanguage(f"operation {operation.name} cannot carry a coefficient/support")
            for qubit in operation.qubits:
                if not isinstance(qubit, int) or not 0 <= qubit < width:
                    raise UnsupportedLanguage(f"operation {operation.name} has an invalid address")
            continue
        raise UnsupportedLanguage(f"unhandled operation {operation.name!r}")

    normalized: list[tuple[PauliAxis, SymbolicAngle]] = []
    for signed_axis, coefficient in raw_rotations:
        if signed_axis.is_identity:
            continue  # exp(-i theta I/2) is a global phase
        unsigned = signed_axis.unsigned()
        normalized.append((unsigned, coefficient * signed_axis.sign))
    for index, (left, _) in enumerate(normalized):
        for right, _ in normalized[index + 1:]:
            if not left.commutes(right):
                raise PredicateError("extracted Pauli rotations are not pairwise commuting")
    aggregated: dict[tuple[int, int], SymbolicAngle] = {}
    for axis, coefficient in normalized:
        key = (axis.x_mask, axis.z_mask)
        aggregated[key] = aggregated.get(key, SymbolicAngle()) + coefficient
    rotations = []
    for (x_mask, z_mask), coefficient in sorted(aggregated.items()):
        reduced = normalize_coefficient(coefficient)
        if not reduced.is_zero:
            rotations.append(
                CanonicalRotation(PauliAxis(width, x_mask, z_mask), reduced)
            )
    return CanonicalForm(
        width=width, rotations=tuple(rotations),
        inverse_x_images=tuple(_raw_to_axis(width, item) for item in x_images),
        inverse_z_images=tuple(_raw_to_axis(width, item) for item in z_images),
    )

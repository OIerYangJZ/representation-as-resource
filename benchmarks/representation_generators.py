#!/usr/bin/env python3
"""Lossless matched representations of one commuting Pauli target family.

The target is fixed before a representation seed is chosen:

    U_x = product_j exp[-i pi x_j Z_j Z_{j+1} / (8 K)].

Each generator below returns both a Qiskit circuit (the compiler-facing
semantics) and literal codec bytes (the measured representation).  No compiler
is allowed to regenerate the target from a different target description.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import asdict, dataclass
from fractions import Fraction
from typing import Any, Iterable, Mapping

from encoding.codec import (
    AggregateRecord,
    ExternalToolOutput,
    FlatUpdateStream,
    PauliSupport,
    SemanticStream,
    SymbolicParameter,
    UpdateRecord,
    encode,
)


CERTIFICATE_KIND = "pyzx_rewrite_identity_up_to_global_phase_v1"
REPRESENTATIONS = (
    "semantic_aggregate",
    "contiguous_flat",
    "round_robin_flat",
    "random_commuting_order",
    "masked_share_update",
    "locally_folded_flat",
    "qasm_bridge",
    "tket_bridge",
    "zx_bridge",
)


@dataclass(frozen=True)
class TargetSpec:
    target_id: str
    m: int
    n: int
    r: int
    K: int
    density_requested: float
    density_realized: float
    target_seed: int
    active_support: tuple[int, ...]
    x: tuple[int, ...]
    delta_over_pi: str

    def to_dict(self) -> dict[str, Any]:
        row = asdict(self)
        row["active_support"] = list(self.active_support)
        row["x"] = list(self.x)
        return row


@dataclass(frozen=True)
class Token:
    generator: int
    support: tuple[int, int]
    angle_over_pi: Fraction
    round_index: int
    share_kind: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "generator": self.generator,
            "support": list(self.support),
            "angle_over_pi_numerator": self.angle_over_pi.numerator,
            "angle_over_pi_denominator": self.angle_over_pi.denominator,
            "round_index": self.round_index,
            "share_kind": self.share_kind,
        }


@dataclass(frozen=True)
class GeneratedRepresentation:
    target: TargetSpec
    representation: str
    seed: int
    representation_id: str
    circuit: Any
    encoded: bytes
    qasm: bytes
    tokens: tuple[Token, ...]
    generation_parameters: Mapping[str, Any]

    def manifest_dict(self) -> dict[str, Any]:
        return {
            "schema": "ucc.matched-representation.v1",
            "target": self.target.to_dict(),
            "representation": self.representation,
            "representation_id": self.representation_id,
            "seed": self.seed,
            "generation_parameters": dict(self.generation_parameters),
            "serialized_input_bytes": len(self.encoded),
            "serialized_input_sha256": sha256_bytes(self.encoded),
            "qasm_bytes": len(self.qasm),
            "qasm_sha256": sha256_bytes(self.qasm),
            "certificate_kind": CERTIFICATE_KIND,
            "tokens": [token.to_dict() for token in self.tokens],
        }


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _stable_id(prefix: str, payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return prefix + sha256_bytes(encoded)[:20]


def make_target(row: Mapping[str, Any]) -> TargetSpec:
    """Generate a sparse non-all-ones coefficient vector deterministically."""

    m = int(row["m"])
    r = int(row["r"])
    K = int(row["K"])
    density = float(row["density"])
    target_seed = int(row["target_seed"])
    if m < 2 or r < 2 or K < 2 or not 0.0 < density <= 1.0:
        raise ValueError("target requires m>=2, r>=2, K>=2, and density in (0,1]")
    rng = random.Random(target_seed)
    active_count = max(1, min(m - 1, round(m * density)))
    active = tuple(sorted(rng.sample(range(m), active_count)))
    x = [0] * m
    for generator in active:
        x[generator] = rng.randrange(1, K)
    base = {
        "m": m,
        "n": m + 1,
        "r": r,
        "K": K,
        "density_requested": density,
        "density_realized": active_count / m,
        "target_seed": target_seed,
        "active_support": list(active),
        "x": x,
        "delta_over_pi": f"1/{4*K}",
    }
    target_id = str(row.get("target_id") or _stable_id("target-", base))
    return TargetSpec(target_id=target_id, active_support=active, x=tuple(x), **{
        key: base[key]
        for key in ("m", "n", "r", "K", "density_requested", "density_realized", "target_seed", "delta_over_pi")
    })


def _aggregate_tokens(target: TargetSpec) -> list[Token]:
    return [
        Token(j, (j, j + 1), Fraction(value, 4 * target.K), 0, "aggregate")
        for j, value in enumerate(target.x)
        if value
    ]


def _split_tokens(target: TargetSpec, order: str, seed: int) -> list[Token]:
    tokens = [
        Token(j, (j, j + 1), Fraction(target.x[j], 4 * target.K * target.r), round_index, "additive")
        for round_index in range(target.r)
        for j in target.active_support
    ]
    if order == "round_robin":
        return tokens
    if order == "contiguous":
        return sorted(tokens, key=lambda token: (token.generator, token.round_index))
    if order == "random":
        result = list(tokens)
        random.Random(seed).shuffle(result)
        return result
    raise ValueError(f"unknown token order {order!r}")


def _masked_shares(coefficient: int, rounds: int, modulus: int, rng: random.Random) -> list[int]:
    """Return nonzero shares; no share equals the final coefficient modulo Q."""

    for _ in range(10_000):
        prefix = [rng.randrange(1, modulus) for _ in range(rounds - 1)]
        final = (coefficient - sum(prefix)) % modulus
        shares = prefix + [final]
        if all(share not in {0, coefficient % modulus} for share in shares):
            return shares
    raise RuntimeError("failed to sample nonleaking modular shares")


def _masked_tokens(target: TargetSpec, seed: int) -> list[Token]:
    modulus = 8 * target.K  # (modulus)*pi/(4K) = 2pi: only global phase wraps.
    rng = random.Random(seed)
    shares = {
        j: _masked_shares(target.x[j], target.r, modulus, rng)
        for j in target.active_support
    }
    return [
        Token(j, (j, j + 1), Fraction(shares[j][round_index], 4 * target.K), round_index, "masked_modular")
        for round_index in range(target.r)
        for j in target.active_support
    ]


def _locally_folded_tokens(target: TargetSpec) -> list[Token]:
    source = _split_tokens(target, "contiguous", seed=0)
    output: list[Token] = []
    for j in target.active_support:
        local = [token for token in source if token.generator == j]
        for offset in range(0, len(local), 2):
            chunk = local[offset : offset + 2]
            output.append(
                Token(
                    j,
                    (j, j + 1),
                    sum((token.angle_over_pi for token in chunk), Fraction()),
                    offset // 2,
                    "local_pair_fold",
                )
            )
    return output


def tokens_for(target: TargetSpec, representation: str, seed: int) -> list[Token]:
    if representation in {"semantic_aggregate", "qasm_bridge", "tket_bridge", "zx_bridge"}:
        return _aggregate_tokens(target)
    if representation == "contiguous_flat":
        return _split_tokens(target, "contiguous", seed)
    if representation == "round_robin_flat":
        return _split_tokens(target, "round_robin", seed)
    if representation == "random_commuting_order":
        return _split_tokens(target, "random", seed)
    if representation == "masked_share_update":
        return _masked_tokens(target, seed)
    if representation == "locally_folded_flat":
        return _locally_folded_tokens(target)
    raise ValueError(f"unknown representation {representation!r}")


def _qiskit_imports() -> tuple[Any, Any]:
    from qiskit import QuantumCircuit, qasm2

    return QuantumCircuit, qasm2


def lower_tokens(width: int, tokens: Iterable[Token]) -> Any:
    QuantumCircuit, _ = _qiskit_imports()
    circuit = QuantumCircuit(width)
    for token in tokens:
        control, target = token.support
        circuit.cx(control, target)
        circuit.rz(float(token.angle_over_pi) * math.pi, target)
        circuit.cx(control, target)
    return circuit


def qasm_bytes(circuit: Any) -> bytes:
    _, qasm2 = _qiskit_imports()
    return qasm2.dumps(circuit).encode("utf-8")


def load_qasm(payload: bytes | str) -> Any:
    _, qasm2 = _qiskit_imports()
    text = payload.decode("utf-8") if isinstance(payload, bytes) else payload
    return qasm2.loads(text)


def _semantic_encoding(target: TargetSpec, tokens: Iterable[Token]) -> bytes:
    return encode(
        SemanticStream(
            target.n,
            tuple(
                AggregateRecord(
                    token.generator,
                    PauliSupport(tuple((qubit, "Z") for qubit in token.support)),
                    SymbolicParameter(token.angle_over_pi),
                )
                for token in tokens
            ),
        )
    )


def _flat_encoding(target: TargetSpec, tokens: Iterable[Token]) -> bytes:
    tokens = tuple(tokens)
    return encode(
        FlatUpdateStream(
            target.n,
            max((token.round_index for token in tokens), default=-1) + 1,
            tuple(
                UpdateRecord(
                    token.round_index,
                    token.generator,
                    PauliSupport(tuple((qubit, "Z") for qubit in token.support)),
                    SymbolicParameter(token.angle_over_pi),
                )
                for token in tokens
            ),
        )
    )


def _tket_roundtrip(payload: bytes) -> bytes:
    import pytket.qasm as tket_qasm

    circuit = tket_qasm.circuit_from_qasm_str(payload.decode("utf-8"))
    return tket_qasm.circuit_to_qasm_str(circuit).encode("utf-8")


def _zx_roundtrip(payload: bytes) -> bytes:
    import pyzx as zx

    circuit = zx.Circuit.from_qasm(payload.decode("utf-8")).to_basic_gates()
    text = circuit.to_qasm()
    lines = text.splitlines()
    while lines and lines[0].startswith("Let "):
        lines.pop(0)
    return ("\n".join(lines) + "\n").encode("utf-8")


def generate_representation(target: TargetSpec, representation: str, seed: int) -> GeneratedRepresentation:
    if representation not in REPRESENTATIONS:
        raise ValueError(f"unknown representation {representation!r}")
    tokens = tuple(tokens_for(target, representation, seed))
    circuit = lower_tokens(target.n, tokens)
    bridge = None
    if representation == "semantic_aggregate":
        encoded = _semantic_encoding(target, tokens)
    elif representation in {
        "contiguous_flat", "round_robin_flat", "random_commuting_order",
        "masked_share_update", "locally_folded_flat",
    }:
        encoded = _flat_encoding(target, tokens)
    else:
        base_qasm = qasm_bytes(circuit)
        if representation == "qasm_bridge":
            bridged = base_qasm
            bridge = "qiskit-openqasm2-roundtrip"
        elif representation == "tket_bridge":
            bridged = _tket_roundtrip(base_qasm)
            bridge = "qiskit-qasm2-to-tket-qasm2"
        else:
            bridged = _zx_roundtrip(base_qasm)
            bridge = "qiskit-qasm2-to-pyzx-basic-qasm2"
        circuit = load_qasm(bridged)
        encoded = encode(ExternalToolOutput(bridge, "openqasm2", bridged))
    qasm = qasm_bytes(circuit)
    parameters = {
        "seed": seed,
        "rounds": target.r,
        "alphabet_K": target.K,
        "masked_modulus": 8 * target.K if representation == "masked_share_update" else None,
        "order": {
            "contiguous_flat": "generator-major",
            "round_robin_flat": "round-major",
            "random_commuting_order": "seeded-uniform-permutation",
        }.get(representation),
        "bridge": bridge,
        "global_phase_policy": "ignored",
    }
    identity_payload = {
        "target_id": target.target_id,
        "representation": representation,
        "seed": seed,
        "generation_parameters": parameters,
        "encoded_sha256": sha256_bytes(encoded),
        "qasm_sha256": sha256_bytes(qasm),
    }
    representation_id = _stable_id("rep-", identity_payload)
    return GeneratedRepresentation(
        target, representation, seed, representation_id, circuit, encoded, qasm, tokens, parameters
    )


def canonical_target(target: TargetSpec) -> Any:
    return lower_tokens(target.n, _aggregate_tokens(target))


def pyzx_certificate(reference_qasm: bytes, candidate_qasm: bytes) -> dict[str, Any]:
    """Apply one fixed symbolic certificate to every representation and output."""

    import pyzx as zx

    started_reference = sha256_bytes(reference_qasm)
    candidate_digest = sha256_bytes(candidate_qasm)
    try:
        reference = zx.Circuit.from_qasm(reference_qasm.decode("utf-8"))
        candidate = zx.Circuit.from_qasm(candidate_qasm.decode("utf-8"))
        result = reference.verify_equality(candidate, up_to_global_phase=True)
        passed = result is True
        return {
            "kind": CERTIFICATE_KIND,
            "status": "passed" if passed else "inconclusive",
            "passed": passed,
            "up_to_global_phase": True,
            "reference_qasm_sha256": started_reference,
            "candidate_qasm_sha256": candidate_digest,
            "engine_result": repr(result),
        }
    except Exception as exc:
        return {
            "kind": CERTIFICATE_KIND,
            "status": "predicate_error",
            "passed": False,
            "up_to_global_phase": True,
            "reference_qasm_sha256": started_reference,
            "candidate_qasm_sha256": candidate_digest,
            "reason": f"{type(exc).__name__}: {exc}",
        }


def verify_masked_nonleakage(generated: GeneratedRepresentation) -> None:
    if generated.representation != "masked_share_update":
        return
    modulus = 8 * generated.target.K
    for token in generated.tokens:
        share = (token.angle_over_pi * 4 * generated.target.K).numerator
        coefficient = generated.target.x[token.generator]
        if share % modulus in {0, coefficient % modulus}:
            raise ValueError("masked token is zero or directly reveals its aggregate coefficient")


def validate_representation_set(target: TargetSpec, seed: int) -> list[GeneratedRepresentation]:
    reference = qasm_bytes(canonical_target(target))
    generated = [generate_representation(target, name, seed) for name in REPRESENTATIONS]
    for item in generated:
        verify_masked_nonleakage(item)
        certificate = pyzx_certificate(reference, item.qasm)
        if not certificate["passed"]:
            raise ValueError(
                f"representation {item.representation_id} did not pass {CERTIFICATE_KIND}: {certificate}"
            )
    if len({item.representation_id for item in generated}) != len(generated):
        raise ValueError("representation_id collision")
    return generated


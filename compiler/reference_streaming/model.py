#!/usr/bin/env python3
"""Formal W1 instances and output semantics for reference compilers."""

from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Mapping

from encoding.codec import (
    AggregateRecord,
    FlatUpdateStream,
    PauliSupport,
    SemanticStream,
    SymbolicParameter,
    UpdateRecord,
    decode_all,
    encode,
)


OUTPUT_SCHEMA = "ucc.reference-output.v1"


@dataclass(frozen=True)
class RunConfig:
    compiler: str
    m: int
    r: int
    K: int
    epsilon_factor: float
    passes: int
    memory_fraction: float
    schedule: str
    seed: int
    delta: float = 0.0
    campaign: str = "w3-tradeoff-v1"

    def __post_init__(self) -> None:
        if self.m < 1 or self.r < 2 or self.K < 2 or self.passes < 1:
            raise ValueError("require m>=1, r>=2, K>=2, passes>=1")
        if not 0.0 < self.epsilon_factor < 1.0:
            raise ValueError("epsilon_factor must lie strictly between zero and one")
        if not 0.0 <= self.memory_fraction <= 1.0:
            raise ValueError("memory_fraction must lie in [0,1]")
        if self.schedule not in {"round_major", "permuted_within_round"}:
            raise ValueError("unsupported schedule")
        if not 0.0 <= self.delta < 0.5:
            raise ValueError("delta must lie in [0,1/2)")

    @property
    def Q(self) -> int:
        return self.K + 1

    @property
    def delta_step(self) -> float:
        return 2.0 * math.pi / self.Q

    @property
    def epsilon(self) -> float:
        return self.epsilon_factor * math.sin(math.pi / (2.0 * self.Q))

    @property
    def packing_separation(self) -> float:
        return 2.0 * math.sin(math.pi / (2.0 * self.Q))

    @property
    def cap_coordinates(self) -> int:
        if self.memory_fraction <= 0:
            return 0
        return min(self.m, max(1, math.ceil(self.memory_fraction * self.m)))

    @property
    def requested_payload_cap_bits(self) -> int:
        return self.cap_coordinates * math.ceil(math.log2(self.Q))

    @property
    def information_lower_bits(self) -> float:
        if self.delta == 0:
            entropy = 0.0
        else:
            entropy = -self.delta * math.log2(self.delta) - (1.0 - self.delta) * math.log2(1.0 - self.delta)
        return (1.0 - self.delta) * self.m * math.log2(self.K) - entropy

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value.update(
            {
                "Q": self.Q,
                "Delta": self.delta_step,
                "epsilon": self.epsilon,
                "packing_separation": self.packing_separation,
                "cap_coordinates": self.cap_coordinates,
                "requested_payload_cap_bits": self.requested_payload_cap_bits,
                "L_delta_bits": self.information_lower_bits,
            }
        )
        return value

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RunConfig":
        fields = {key: value[key] for key in cls.__dataclass_fields__ if key in value}
        return cls(**fields)

    def run_id(self) -> str:
        canonical = json.dumps(asdict(self), sort_keys=True, separators=(",", ":")).encode("utf-8")
        digest = hashlib.sha256(canonical).hexdigest()[:12]
        return f"{self.compiler}-m{self.m}-r{self.r}-K{self.K}-p{self.passes}-s{self.seed}-{digest}"


def _support(generator: int) -> PauliSupport:
    return PauliSupport(((generator, "Z"),))


def build_dispersed_instance(config: RunConfig) -> tuple[tuple[int, ...], SemanticStream, FlatUpdateStream]:
    """Generate canonical masked shares without placing ``x_j`` in any token."""

    rng = random.Random(config.seed)
    x = tuple(rng.randrange(config.K) for _ in range(config.m))
    shares = [[rng.randrange(config.Q) for _ in range(config.m)] for _ in range(config.r - 1)]
    shares.append(
        [
            (x[generator] - sum(shares[round_index][generator] for round_index in range(config.r - 1)))
            % config.Q
            for generator in range(config.m)
        ]
    )
    records: list[UpdateRecord] = []
    schedule_rng = random.Random(config.seed ^ 0xA5A5_3C3C_5A5A_C3C3)
    for round_index in range(config.r):
        order = list(range(config.m))
        if config.schedule == "permuted_within_round":
            schedule_rng.shuffle(order)
        for generator in order:
            records.append(
                UpdateRecord(
                    round_index,
                    generator,
                    _support(generator),
                    SymbolicParameter(Fraction(shares[round_index][generator])),
                )
            )
    semantic = SemanticStream(
        config.m,
        tuple(
            AggregateRecord(generator, _support(generator), SymbolicParameter(Fraction(value)))
            for generator, value in enumerate(x)
        ),
    )
    flat = FlatUpdateStream(config.m, config.r, tuple(records))
    return x, semantic, flat


def output_header(config: RunConfig, record_count: int) -> bytes:
    return encode(
        {
            "schema": OUTPUT_SCHEMA,
            "compiler": config.compiler,
            "m": config.m,
            "r": config.r,
            "K": config.K,
            "Q": config.Q,
            "record_count": record_count,
            "representation": "mixed-addressed-additive-records",
        }
    )


def encode_update_output(record: UpdateRecord) -> bytes:
    return encode(
        {
            "kind": "update",
            "round_index": record.round_index,
            "generator": record.generator,
            "support": [[qubit, pauli] for qubit, pauli in record.support.entries],
            "residue": record.parameter.constant.numerator,
        }
    )


def encode_aggregate_output(generator: int, residue: int) -> bytes:
    return encode(
        {
            "kind": "aggregate",
            "generator": generator,
            "support": [[generator, "Z"]],
            "residue": residue,
        }
    )


def verify_output_stream(path: Path | str, config: RunConfig, expected_x: Iterable[int]) -> dict[str, Any]:
    frames = decode_all(Path(path).read_bytes())
    if not frames or not isinstance(frames[0], dict) or frames[0].get("schema") != OUTPUT_SCHEMA:
        raise ValueError("missing reference-output header")
    header = frames[0]
    records = frames[1:]
    if header.get("record_count") != len(records):
        raise ValueError("declared output record count does not match the stream")
    totals = [0] * config.m
    counts = {"update": 0, "aggregate": 0}
    for record in records:
        if not isinstance(record, dict) or record.get("kind") not in counts:
            raise ValueError("unknown output record")
        generator = int(record["generator"])
        if not 0 <= generator < config.m or record.get("support") != [[generator, "Z"]]:
            raise ValueError("output record has an invalid address/support")
        residue = int(record["residue"])
        if not 0 <= residue < config.Q:
            raise ValueError("output residue is not canonical modulo Q")
        totals[generator] = (totals[generator] + residue) % config.Q
        counts[record["kind"]] += 1
    expected = tuple(int(value) for value in expected_x)
    if tuple(totals) != expected:
        raise ValueError(f"output semantic mismatch: got {tuple(totals)}, expected {expected}")
    return {
        "status": "pass",
        "exact_mod_Q": True,
        "projective_error": 0.0,
        "epsilon": config.epsilon,
        "record_count": len(records),
        "update_records": counts["update"],
        "aggregate_records": counts["aggregate"],
        "aggregate_vector_sha256": hashlib.sha256(encode(list(expected))).hexdigest(),
    }


def assert_token_nonrevelation(config: RunConfig, flat: FlatUpdateStream) -> None:
    """Structural audit: a token has only its share, never an aggregate slot."""

    if len(flat.records) != config.m * config.r:
        raise ValueError("flat stream is not a complete r-by-m update family")
    for record in flat.records:
        payload = record.to_payload()
        if set(payload) != {"round", "generator", "support", "parameter"}:
            raise ValueError("flat token schema changed unexpectedly")
        if "aggregate" in payload or "x" in payload or "final" in payload:
            raise ValueError("flat token leaks an aggregate field")


__all__ = [
    "OUTPUT_SCHEMA",
    "RunConfig",
    "assert_token_nonrevelation",
    "build_dispersed_instance",
    "encode_aggregate_output",
    "encode_update_output",
    "output_header",
    "verify_output_stream",
]

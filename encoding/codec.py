"""Canonical, prefix-free binary codec used by theory and instrumentation.

The public :func:`encode`/:func:`decode_exact` pair is deliberately small and
stdlib-only so that experiment runners can import it without a toolchain.  A
complete frame is

    MAGIC | schema-version | type-tag | payload-length | canonical-payload.

All integers, including qubit, generator, node, edge and parameter-location
addresses, are encoded explicitly.  There is no constant-cost token shortcut.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, ClassVar, Iterable, Mapping


MAGIC = b"UCCACCT\x00"
SCHEMA = "ucc.accounting"
SCHEMA_VERSION = 1


class CodecError(ValueError):
    """Raised for malformed, noncanonical or truncated input."""


def encode_uvarint(value: int) -> bytes:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("uvarint requires a nonnegative integer")
    output = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        output.append(byte | (0x80 if value else 0))
        if not value:
            return bytes(output)


def encode_svarint(value: int) -> bytes:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("svarint requires an integer")
    return encode_uvarint(2 * value if value >= 0 else -2 * value - 1)


def _read_uvarint(data: bytes, offset: int) -> tuple[int, int]:
    start = offset
    value = 0
    shift = 0
    while True:
        if offset >= len(data):
            raise CodecError("truncated uvarint")
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            raw = data[start:offset]
            if raw != encode_uvarint(value):
                raise CodecError("noncanonical uvarint")
            return value, offset
        shift += 7
        if shift > 1_000_000:
            raise CodecError("uvarint is unreasonably large")


def _read_svarint(data: bytes, offset: int) -> tuple[int, int]:
    zigzag, offset = _read_uvarint(data, offset)
    return (zigzag // 2 if zigzag % 2 == 0 else -(zigzag // 2) - 1), offset


def _as_fraction(value: Fraction | int) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (Fraction, int)):
        raise TypeError("coefficient must be an int or Fraction")
    return Fraction(value)


def _tuple_pairs(values: Iterable[tuple[int, Any]]) -> tuple[tuple[int, Any], ...]:
    return tuple((int(index), value) for index, value in values)


@dataclass(frozen=True)
class SymbolicParameter:
    """A reduced affine sparse symbolic coefficient plus a rational constant."""

    constant: Fraction = Fraction()
    terms: tuple[tuple[int, Fraction], ...] = ()
    TYPE_TAG: ClassVar[int] = 2

    def __post_init__(self) -> None:
        combined: dict[int, Fraction] = {}
        for symbol, coefficient in _tuple_pairs(self.terms):
            if symbol < 0:
                raise ValueError("symbol address must be nonnegative")
            combined[symbol] = combined.get(symbol, Fraction()) + _as_fraction(coefficient)
        normalized = tuple(sorted((key, value) for key, value in combined.items() if value))
        object.__setattr__(self, "constant", _as_fraction(self.constant))
        object.__setattr__(self, "terms", normalized)

    def __add__(self, other: "SymbolicParameter") -> "SymbolicParameter":
        return SymbolicParameter(self.constant + other.constant, self.terms + other.terms)

    def scaled(self, factor: int) -> "SymbolicParameter":
        if isinstance(factor, bool) or not isinstance(factor, int):
            raise TypeError("symbolic scale factor must be an integer")
        return SymbolicParameter(
            factor * self.constant,
            tuple((symbol, factor * coefficient) for symbol, coefficient in self.terms),
        )

    def to_payload(self) -> dict[str, Any]:
        return {"constant": self.constant, "terms": [[index, value] for index, value in self.terms]}

    @classmethod
    def from_payload(cls, value: Mapping[str, Any]) -> "SymbolicParameter":
        return cls(value["constant"], tuple((item[0], item[1]) for item in value["terms"]))


@dataclass(frozen=True)
class PauliSupport:
    entries: tuple[tuple[int, str], ...] = ()
    TYPE_TAG: ClassVar[int] = 3

    def __post_init__(self) -> None:
        normalized = tuple(sorted((int(qubit), str(pauli).upper()) for qubit, pauli in self.entries))
        if any(qubit < 0 for qubit, _ in normalized):
            raise ValueError("qubit address must be nonnegative")
        if any(pauli not in {"I", "X", "Y", "Z"} for _, pauli in normalized):
            raise ValueError("Pauli letter must be I, X, Y or Z")
        if len({qubit for qubit, _ in normalized}) != len(normalized):
            raise ValueError("Pauli support has a duplicate qubit")
        object.__setattr__(self, "entries", normalized)

    def to_payload(self) -> dict[str, Any]:
        return {"entries": [[qubit, pauli] for qubit, pauli in self.entries]}

    @classmethod
    def from_payload(cls, value: Mapping[str, Any]) -> "PauliSupport":
        return cls(tuple((item[0], item[1]) for item in value["entries"]))


@dataclass(frozen=True)
class Instruction:
    opcode: str
    operands: tuple[int, ...] = ()
    support: PauliSupport = PauliSupport()
    parameters: tuple[SymbolicParameter, ...] = ()
    attributes: Mapping[str, Any] = field(default_factory=dict)
    TYPE_TAG: ClassVar[int] = 4

    def __post_init__(self) -> None:
        operands = tuple(int(item) for item in self.operands)
        if any(item < 0 for item in operands):
            raise ValueError("operand address must be nonnegative")
        object.__setattr__(self, "opcode", str(self.opcode))
        object.__setattr__(self, "operands", operands)
        object.__setattr__(self, "parameters", tuple(self.parameters))
        object.__setattr__(self, "attributes", dict(self.attributes))

    def without_parameters(self) -> "Instruction":
        attributes = dict(self.attributes)
        attributes.setdefault("parameter_slots", len(self.parameters))
        return Instruction(self.opcode, self.operands, self.support, (), attributes)

    def to_payload(self) -> dict[str, Any]:
        return {
            "attributes": dict(self.attributes),
            "opcode": self.opcode,
            "operands": list(self.operands),
            "parameters": [item.to_payload() for item in self.parameters],
            "support": self.support.to_payload(),
        }

    @classmethod
    def from_payload(cls, value: Mapping[str, Any]) -> "Instruction":
        return cls(
            value["opcode"],
            tuple(value["operands"]),
            PauliSupport.from_payload(value["support"]),
            tuple(SymbolicParameter.from_payload(item) for item in value["parameters"]),
            value["attributes"],
        )


@dataclass(frozen=True)
class AggregateRecord:
    generator: int
    support: PauliSupport
    parameter: SymbolicParameter
    multiplicity: int = 1

    def __post_init__(self) -> None:
        if self.generator < 0 or self.multiplicity < 0:
            raise ValueError("generator and multiplicity must be nonnegative")

    def to_payload(self) -> dict[str, Any]:
        return {
            "generator": self.generator,
            "multiplicity": self.multiplicity,
            "parameter": self.parameter.to_payload(),
            "support": self.support.to_payload(),
        }

    @classmethod
    def from_payload(cls, value: Mapping[str, Any]) -> "AggregateRecord":
        return cls(
            value["generator"],
            PauliSupport.from_payload(value["support"]),
            SymbolicParameter.from_payload(value["parameter"]),
            value["multiplicity"],
        )


@dataclass(frozen=True)
class UpdateRecord:
    round_index: int
    generator: int
    support: PauliSupport
    parameter: SymbolicParameter

    def to_payload(self) -> dict[str, Any]:
        if self.round_index < 0 or self.generator < 0:
            raise ValueError("round and generator addresses must be nonnegative")
        return {
            "generator": self.generator,
            "parameter": self.parameter.to_payload(),
            "round": self.round_index,
            "support": self.support.to_payload(),
        }

    @classmethod
    def from_payload(cls, value: Mapping[str, Any]) -> "UpdateRecord":
        return cls(
            value["round"],
            value["generator"],
            PauliSupport.from_payload(value["support"]),
            SymbolicParameter.from_payload(value["parameter"]),
        )


def _validate_description(mode: str, digest: str | None) -> None:
    if mode not in {"self_contained", "conditional"}:
        raise ValueError("description_mode must be self_contained or conditional")
    if mode == "conditional":
        if digest is None or len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise ValueError("conditional descriptions require a lowercase SHA-256 dictionary digest")
    elif digest is not None:
        raise ValueError("self-contained descriptions must not name an external dictionary")


@dataclass(frozen=True)
class SemanticStream:
    width: int
    records: tuple[AggregateRecord, ...]
    description_mode: str = "self_contained"
    dictionary_sha256: str | None = None
    TYPE_TAG: ClassVar[int] = 5

    def __post_init__(self) -> None:
        if self.width < 0:
            raise ValueError("width must be nonnegative")
        _validate_description(self.description_mode, self.dictionary_sha256)
        records = tuple(self.records)
        if any(
            item.generator >= self.width
            or any(qubit >= self.width for qubit, _ in item.support.entries)
            for item in records
        ):
            raise ValueError("semantic-stream address exceeds declared width")
        object.__setattr__(self, "records", records)

    def to_payload(self) -> dict[str, Any]:
        return {
            "description_mode": self.description_mode,
            "dictionary_sha256": self.dictionary_sha256,
            "records": [item.to_payload() for item in self.records],
            "width": self.width,
        }

    @classmethod
    def from_payload(cls, value: Mapping[str, Any]) -> "SemanticStream":
        return cls(
            value["width"],
            tuple(AggregateRecord.from_payload(item) for item in value["records"]),
            value["description_mode"],
            value["dictionary_sha256"],
        )


@dataclass(frozen=True)
class FlatUpdateStream:
    width: int
    rounds: int
    records: tuple[UpdateRecord, ...]
    description_mode: str = "self_contained"
    dictionary_sha256: str | None = None
    TYPE_TAG: ClassVar[int] = 6

    def __post_init__(self) -> None:
        if self.width < 0 or self.rounds < 0:
            raise ValueError("width and rounds must be nonnegative")
        _validate_description(self.description_mode, self.dictionary_sha256)
        records = tuple(self.records)
        if any(
            item.round_index >= self.rounds
            or item.generator >= self.width
            or any(qubit >= self.width for qubit, _ in item.support.entries)
            for item in records
        ):
            raise ValueError("flat-stream round/address exceeds its declaration")
        object.__setattr__(self, "records", records)

    def to_payload(self) -> dict[str, Any]:
        return {
            "description_mode": self.description_mode,
            "dictionary_sha256": self.dictionary_sha256,
            "records": [item.to_payload() for item in self.records],
            "rounds": self.rounds,
            "width": self.width,
        }

    @classmethod
    def from_payload(cls, value: Mapping[str, Any]) -> "FlatUpdateStream":
        return cls(
            value["width"],
            value["rounds"],
            tuple(UpdateRecord.from_payload(item) for item in value["records"]),
            value["description_mode"],
            value["dictionary_sha256"],
        )


@dataclass(frozen=True)
class IRNode:
    node_id: int
    instruction: Instruction

    def to_payload(self) -> dict[str, Any]:
        if self.node_id < 0:
            raise ValueError("node address must be nonnegative")
        return {"instruction": self.instruction.to_payload(), "node_id": self.node_id}

    @classmethod
    def from_payload(cls, value: Mapping[str, Any]) -> "IRNode":
        return cls(value["node_id"], Instruction.from_payload(value["instruction"]))


@dataclass(frozen=True)
class IREdge:
    source: int
    target: int
    port: int = 0

    def to_payload(self) -> dict[str, Any]:
        if min(self.source, self.target, self.port) < 0:
            raise ValueError("edge addresses must be nonnegative")
        return {"port": self.port, "source": self.source, "target": self.target}

    @classmethod
    def from_payload(cls, value: Mapping[str, Any]) -> "IREdge":
        return cls(value["source"], value["target"], value["port"])


@dataclass(frozen=True)
class CircuitDAG:
    width: int
    nodes: tuple[IRNode, ...] = ()
    edges: tuple[IREdge, ...] = ()
    attributes: Mapping[str, Any] = field(default_factory=dict)
    TYPE_TAG: ClassVar[int] = 7

    def __post_init__(self) -> None:
        if self.width < 0:
            raise ValueError("width must be nonnegative")
        nodes = tuple(sorted(self.nodes, key=lambda item: item.node_id))
        if len({item.node_id for item in nodes}) != len(nodes):
            raise ValueError("duplicate IR node address")
        edges = tuple(sorted(self.edges, key=lambda item: (item.source, item.target, item.port)))
        node_ids = {item.node_id for item in nodes}
        if any(edge.source not in node_ids or edge.target not in node_ids for edge in edges):
            raise ValueError("IR edge endpoint does not name a serialized node")
        if any(
            operand >= self.width
            for node in nodes
            for operand in node.instruction.operands
        ) or any(
            qubit >= self.width
            for node in nodes
            for qubit, _ in node.instruction.support.entries
        ):
            raise ValueError("IR qubit address exceeds declared width")
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "edges", edges)
        object.__setattr__(self, "attributes", dict(self.attributes))

    def without_parameters(self) -> "CircuitDAG":
        return CircuitDAG(
            self.width,
            tuple(IRNode(node.node_id, node.instruction.without_parameters()) for node in self.nodes),
            self.edges,
            self.attributes,
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "attributes": dict(self.attributes),
            "edges": [item.to_payload() for item in self.edges],
            "nodes": [item.to_payload() for item in self.nodes],
            "width": self.width,
        }

    @classmethod
    def from_payload(cls, value: Mapping[str, Any]) -> "CircuitDAG":
        return cls(
            value["width"],
            tuple(IRNode.from_payload(item) for item in value["nodes"]),
            tuple(IREdge.from_payload(item) for item in value["edges"]),
            value["attributes"],
        )


@dataclass(frozen=True)
class ExternalToolOutput:
    tool: str
    format: str
    payload: bytes
    TYPE_TAG: ClassVar[int] = 8

    def to_payload(self) -> dict[str, Any]:
        return {"format": self.format, "payload": self.payload, "tool": self.tool}

    @classmethod
    def from_payload(cls, value: Mapping[str, Any]) -> "ExternalToolOutput":
        return cls(value["tool"], value["format"], value["payload"])


@dataclass(frozen=True)
class CertificateInput:
    certificate_kind: str
    artifact_sha256: str
    payload: bytes
    TYPE_TAG: ClassVar[int] = 9

    def __post_init__(self) -> None:
        if len(self.artifact_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in self.artifact_sha256):
            raise ValueError("certificate input requires a lowercase SHA-256 digest")

    def to_payload(self) -> dict[str, Any]:
        return {"artifact_sha256": self.artifact_sha256, "kind": self.certificate_kind, "payload": self.payload}

    @classmethod
    def from_payload(cls, value: Mapping[str, Any]) -> "CertificateInput":
        return cls(value["kind"], value["artifact_sha256"], value["payload"])


@dataclass(frozen=True)
class ControlState:
    fields: Mapping[str, Any]
    TYPE_TAG: ClassVar[int] = 10

    def to_payload(self) -> dict[str, Any]:
        return {"fields": dict(self.fields)}

    @classmethod
    def from_payload(cls, value: Mapping[str, Any]) -> "ControlState":
        return cls(value["fields"])


@dataclass(frozen=True)
class StoreState:
    fields: Mapping[str, Any]
    TYPE_TAG: ClassVar[int] = 11

    def to_payload(self) -> dict[str, Any]:
        return {"fields": dict(self.fields)}

    @classmethod
    def from_payload(cls, value: Mapping[str, Any]) -> "StoreState":
        return cls(value["fields"])


@dataclass(frozen=True)
class LiveWindow:
    instructions: tuple[Instruction, ...] = ()
    TYPE_TAG: ClassVar[int] = 12

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "instructions",
            tuple(item.without_parameters() for item in self.instructions),
        )

    def to_payload(self) -> dict[str, Any]:
        return {"instructions": [item.to_payload() for item in self.instructions]}

    @classmethod
    def from_payload(cls, value: Mapping[str, Any]) -> "LiveWindow":
        return cls(tuple(Instruction.from_payload(item) for item in value["instructions"]))


@dataclass(frozen=True)
class ParameterEntry:
    location: tuple[int, ...]
    parameter: SymbolicParameter

    def to_payload(self) -> dict[str, Any]:
        if any(item < 0 for item in self.location):
            raise ValueError("parameter locations must be nonnegative")
        return {"location": list(self.location), "parameter": self.parameter.to_payload()}

    @classmethod
    def from_payload(cls, value: Mapping[str, Any]) -> "ParameterEntry":
        return cls(tuple(value["location"]), SymbolicParameter.from_payload(value["parameter"]))


@dataclass(frozen=True)
class ParameterLedger:
    entries: tuple[ParameterEntry, ...] = ()
    TYPE_TAG: ClassVar[int] = 13

    def __post_init__(self) -> None:
        object.__setattr__(self, "entries", tuple(sorted(self.entries, key=lambda item: item.location)))

    def to_payload(self) -> dict[str, Any]:
        return {"entries": [item.to_payload() for item in self.entries]}

    @classmethod
    def from_payload(cls, value: Mapping[str, Any]) -> "ParameterLedger":
        return cls(tuple(ParameterEntry.from_payload(item) for item in value["entries"]))


@dataclass(frozen=True)
class IRField:
    objects: tuple[CircuitDAG, ...] = ()
    TYPE_TAG: ClassVar[int] = 14

    def __post_init__(self) -> None:
        object.__setattr__(self, "objects", tuple(item.without_parameters() for item in self.objects))

    def to_payload(self) -> dict[str, Any]:
        return {"objects": [item.to_payload() for item in self.objects]}

    @classmethod
    def from_payload(cls, value: Mapping[str, Any]) -> "IRField":
        return cls(tuple(CircuitDAG.from_payload(item) for item in value["objects"]))


@dataclass(frozen=True)
class CommittedOutput:
    format: str
    payload: bytes
    TYPE_TAG: ClassVar[int] = 15

    def to_payload(self) -> dict[str, Any]:
        return {"format": self.format, "payload": self.payload}

    @classmethod
    def from_payload(cls, value: Mapping[str, Any]) -> "CommittedOutput":
        return cls(value["format"], value["payload"])


_TYPE_CLASSES = {
    cls.TYPE_TAG: cls
    for cls in (
        SymbolicParameter,
        PauliSupport,
        Instruction,
        SemanticStream,
        FlatUpdateStream,
        CircuitDAG,
        ExternalToolOutput,
        CertificateInput,
        ControlState,
        StoreState,
        LiveWindow,
        ParameterLedger,
        IRField,
        CommittedOutput,
    )
}
GENERIC_TAG = 1

# Canonical payload value tags.
_NULL, _FALSE, _TRUE, _UINT, _SINT, _BYTES, _TEXT, _LIST, _MAP, _FRACTION = range(10)


def _encode_value(value: Any) -> bytes:
    if value is None:
        return bytes([_NULL])
    if value is False:
        return bytes([_FALSE])
    if value is True:
        return bytes([_TRUE])
    if isinstance(value, int):
        if value >= 0:
            return bytes([_UINT]) + encode_uvarint(value)
        return bytes([_SINT]) + encode_svarint(value)
    if isinstance(value, Fraction):
        return bytes([_FRACTION]) + encode_svarint(value.numerator) + encode_uvarint(value.denominator)
    if isinstance(value, bytes):
        return bytes([_BYTES]) + encode_uvarint(len(value)) + value
    if isinstance(value, str):
        payload = value.encode("utf-8")
        return bytes([_TEXT]) + encode_uvarint(len(payload)) + payload
    if isinstance(value, (list, tuple)):
        return bytes([_LIST]) + encode_uvarint(len(value)) + b"".join(_encode_value(item) for item in value)
    if isinstance(value, Mapping):
        encoded_items = []
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("canonical maps require string keys")
            key_bytes = key.encode("utf-8")
            encoded_items.append((key_bytes, _encode_value(item)))
        encoded_items.sort(key=lambda item: item[0])
        output = bytearray([_MAP])
        output += encode_uvarint(len(encoded_items))
        for key_bytes, item_bytes in encoded_items:
            output += encode_uvarint(len(key_bytes)) + key_bytes + item_bytes
        return bytes(output)
    raise TypeError(f"unsupported canonical value: {type(value).__name__}")


def _decode_value(data: bytes, offset: int) -> tuple[Any, int]:
    if offset >= len(data):
        raise CodecError("truncated canonical value")
    tag = data[offset]
    offset += 1
    if tag == _NULL:
        return None, offset
    if tag == _FALSE:
        return False, offset
    if tag == _TRUE:
        return True, offset
    if tag == _UINT:
        return _read_uvarint(data, offset)
    if tag == _SINT:
        value, offset = _read_svarint(data, offset)
        if value >= 0:
            raise CodecError("noncanonical signed integer")
        return value, offset
    if tag == _FRACTION:
        numerator, offset = _read_svarint(data, offset)
        denominator, offset = _read_uvarint(data, offset)
        if denominator == 0:
            raise CodecError("zero fraction denominator")
        value = Fraction(numerator, denominator)
        if value.numerator != numerator or value.denominator != denominator:
            raise CodecError("non-reduced fraction")
        return value, offset
    if tag in {_BYTES, _TEXT}:
        length, offset = _read_uvarint(data, offset)
        end = offset + length
        if end > len(data):
            raise CodecError("truncated byte/text value")
        payload = data[offset:end]
        if tag == _TEXT:
            try:
                return payload.decode("utf-8"), end
            except UnicodeDecodeError as exc:
                raise CodecError("invalid UTF-8") from exc
        return payload, end
    if tag == _LIST:
        count, offset = _read_uvarint(data, offset)
        result = []
        for _ in range(count):
            value, offset = _decode_value(data, offset)
            result.append(value)
        return result, offset
    if tag == _MAP:
        count, offset = _read_uvarint(data, offset)
        result: dict[str, Any] = {}
        previous: bytes | None = None
        for _ in range(count):
            length, offset = _read_uvarint(data, offset)
            end = offset + length
            if end > len(data):
                raise CodecError("truncated map key")
            key_bytes = data[offset:end]
            offset = end
            if previous is not None and key_bytes <= previous:
                raise CodecError("map keys are duplicate or not canonical")
            previous = key_bytes
            try:
                key = key_bytes.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise CodecError("invalid UTF-8 map key") from exc
            value, offset = _decode_value(data, offset)
            result[key] = value
        return result, offset
    raise CodecError(f"unknown canonical value tag {tag}")


def encode(value: Any) -> bytes:
    """Encode one typed object or a generic canonical value."""

    if hasattr(value, "TYPE_TAG") and hasattr(value, "to_payload"):
        type_tag = int(value.TYPE_TAG)
        payload = _encode_value(value.to_payload())
    else:
        type_tag = GENERIC_TAG
        payload = _encode_value(value)
    return MAGIC + encode_uvarint(SCHEMA_VERSION) + encode_uvarint(type_tag) + encode_uvarint(len(payload)) + payload


def decode_from(data: bytes, offset: int = 0) -> tuple[Any, int]:
    """Decode one frame at *offset* and return ``(object, next_offset)``."""

    if data[offset : offset + len(MAGIC)] != MAGIC:
        raise CodecError("bad or truncated magic")
    cursor = offset + len(MAGIC)
    version, cursor = _read_uvarint(data, cursor)
    if version != SCHEMA_VERSION:
        raise CodecError(f"unsupported schema version {version}")
    type_tag, cursor = _read_uvarint(data, cursor)
    length, cursor = _read_uvarint(data, cursor)
    end = cursor + length
    if end > len(data):
        raise CodecError("truncated frame payload")
    value, payload_end = _decode_value(data, cursor)
    if payload_end != end:
        raise CodecError("trailing bytes inside frame payload")
    if type_tag == GENERIC_TAG:
        result = value
    else:
        cls = _TYPE_CLASSES.get(type_tag)
        if cls is None:
            raise CodecError(f"unknown type tag {type_tag}")
        if not isinstance(value, Mapping):
            raise CodecError("typed payload is not a map")
        try:
            result = cls.from_payload(value)
        except (KeyError, TypeError, ValueError) as exc:
            raise CodecError(f"invalid typed payload for tag {type_tag}") from exc
    if encode(result) != data[offset:end]:
        raise CodecError("frame is not canonical")
    return result, end


def decode_exact(data: bytes) -> Any:
    value, offset = decode_from(data)
    if offset != len(data):
        raise CodecError("trailing bytes after complete frame")
    return value


def decode_all(data: bytes) -> list[Any]:
    values = []
    offset = 0
    while offset < len(data):
        value, offset = decode_from(data, offset)
        values.append(value)
    return values


def semantic_signature(stream: SemanticStream | FlatUpdateStream) -> tuple[tuple[Any, ...], ...]:
    """Return the exact aggregate semantic signature of either representation."""

    totals: dict[tuple[int, tuple[tuple[int, str], ...]], SymbolicParameter] = {}
    if isinstance(stream, SemanticStream):
        rows = (
            (item.generator, item.support, item.parameter.scaled(item.multiplicity))
            for item in stream.records
        )
    elif isinstance(stream, FlatUpdateStream):
        rows = ((item.generator, item.support, item.parameter) for item in stream.records)
    else:
        raise TypeError("semantic_signature expects a semantic or flat stream")
    for generator, support, parameter in rows:
        key = (generator, support.entries)
        totals[key] = totals.get(key, SymbolicParameter()) + parameter
    return tuple(
        (generator, support, parameter.constant, parameter.terms)
        for (generator, support), parameter in sorted(totals.items())
        if parameter.constant or parameter.terms
    )


__all__ = [
    "MAGIC", "SCHEMA", "SCHEMA_VERSION", "CodecError", "encode_uvarint",
    "encode_svarint", "SymbolicParameter", "PauliSupport", "Instruction",
    "AggregateRecord", "UpdateRecord", "SemanticStream", "FlatUpdateStream",
    "IRNode", "IREdge", "CircuitDAG", "ExternalToolOutput", "CertificateInput",
    "ControlState", "StoreState", "LiveWindow", "ParameterEntry",
    "ParameterLedger", "IRField", "CommittedOutput", "encode", "decode_from",
    "decode_exact", "decode_all", "semantic_signature",
]

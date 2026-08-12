# UCC accounting codec, version 1

This directory is the executable serialization contract for every bit-valued
quantity introduced by the compiler model. The reference implementation is
[`codec.py`](codec.py). It uses only the Python standard library and is the
single codec imported by the cut tracer, matched-representation runner, natural
factorial runner, resource-accounting layer, and tests.

## Complete frame

A complete object is encoded as

```
55 43 43 41 43 43 54 00 | schema_uvarint | type_uvarint |
payload_length_uvarint | canonical_payload
```

The eight initial bytes are `UCCACCT\0`; `schema_uvarint` is currently `1`.
Unsigned integers use base-128 little-endian varints with the continuation bit
in bit 7. Signed integers use zigzag followed by that uvarint. Decoders reject
overlong integers, unknown schema/type tags, truncated frames, non-reduced
fractions, non-UTF-8 text, unsorted or duplicate map keys, and trailing bytes.

The outer payload length makes the set of complete frames prefix-free. It also
allows concatenated frames to be parsed without an external token count or
delimiter. A committed output *prefix* may be an incomplete prefix of one such
frame while a compiler is running; `committed-prefix.bin` contains those exact
immutable bytes. The final committed file is a complete `CommittedOutput` or
`ExternalToolOutput` frame and must decode successfully.

## Canonical payload values

Each payload value begins with one byte:

| Tag | Value | Following data |
|---:|---|---|
| 0 | null | none |
| 1 | false | none |
| 2 | true | none |
| 3 | nonnegative integer | uvarint |
| 4 | negative integer | zigzag uvarint |
| 5 | bytes | byte length, bytes |
| 6 | UTF-8 text | byte length, bytes |
| 7 | list | item count, recursive values |
| 8 | map | entry count, sorted UTF-8 key/value pairs |
| 9 | rational | signed numerator, positive denominator |

Map keys are strings sorted by their raw UTF-8 bytes. Fractions are reduced and
have a positive denominator. Encoding the same semantic object therefore
produces byte-for-byte identical output on every supported platform.

## Typed objects

| Type tag | Python object | Formal role |
|---:|---|---|
| 1 | generic canonical value | metadata without implicit objects |
| 2 | `SymbolicParameter` | reduced sparse symbolic coefficient |
| 3 | `PauliSupport` | complete `(qubit, Pauli)` support |
| 4 | `Instruction` | opcode, operands, support, parameters, attributes |
| 5 | `SemanticStream` | aggregate semantic input |
| 6 | `FlatUpdateStream` | multi-round additive update input |
| 7 | `CircuitDAG` | nodes, edges, ports, width, object metadata |
| 8 | `ExternalToolOutput` | tool/format plus literal external payload |
| 9 | `CertificateInput` | certificate kind, artifact digest, sidecar |
| 10 | `ControlState` | `B_control` |
| 11 | `StoreState` | `B_store` |
| 12 | `LiveWindow` | `B_window` |
| 13 | `ParameterLedger` | `B_parameter` |
| 14 | `IRField` | `B_IR` |
| 15 | `CommittedOutput` | complete write-once output |

`LiveWindow` and `IRField` normalize their instructions by removing parameter
payloads and retaining an explicit parameter-slot count. The removed values are
stored exactly once in `ParameterLedger` under address-complete location tuples.
Thus the five fields are disjoint by construction.

## Growing-width address charge

Qubit, generator, symbol, parameter-location, node, edge-endpoint, port, pass,
and head addresses are all serialized as integers in the objects above. They
cross byte boundaries at 128, 16384, and later powers of 128. No experiment may
replace those bytes by a constant per token, gate count, node count, or a
formula inferred from one of those counts. Sparse Pauli support contains every
qubit address and Pauli letter.

## Representation and dictionary policy

`SemanticStream` contains aggregate records. `FlatUpdateStream` contains
round-indexed updates; only their sum has aggregate semantics. Both have an
explicit `description_mode`:

- `self_contained` forbids an external dictionary digest;
- `conditional` requires the lowercase SHA-256 digest of the exact public
  family dictionary.

Resource manifests additionally record the dictionary file size and whether it
is charged at the measured cut. This prevents a conditional family code from
being reported as self-contained output.

## Measured artifacts

For cut directory `D`, the authoritative files are:

```
D/control.uccbin
D/store.uccbin
D/window.uccbin
D/parameter.uccbin
D/ir.uccbin
D/committed-prefix.bin
D/manifest.json
```

`instrumentation.resource_accounting.ResourceAccountant` writes the six files,
calls `stat` on each, hashes each with SHA-256, writes the manifest, then reads
and verifies the manifest before returning a row. The only permitted bit rule
is

```
B_field = 8 * stat(field_file).st_size
B_cut = B_control + B_store + B_window + B_parameter + B_IR
```

Figures and summaries must call `assert_rows_file_backed` before using bit
fields. A missing artifact, size mismatch, digest mismatch, or hand-edited row
is a hard error.

## Deterministic reference trace

Run from the project root:

```
python3 -B -m instrumentation.resource_accounting \
  --build-example instrumentation/example_trace
```

The checked-in fixture uses width 129 so generator/qubit address 128 takes the
larger varint form. Its semantic and two-round flat inputs both aggregate to
`3/17` on support `Z_0 Z_128`. The fixture includes actual semantic, flat,
external-output, certificate, five-field cut, committed-prefix, manifest, and
trace files. `tests/test_resource_accounting.py` re-creates it in a temporary
directory and verifies every file rather than trusting recorded counts.

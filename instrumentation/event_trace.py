#!/usr/bin/env python3
"""Append-only, file-backed event traces for the reference compilers.

Each restart-state field is encoded with :mod:`encoding.codec` and appended
to a field-specific frame file.  Event rows name the exact byte slice and its
SHA-256 digest.  ``B_com`` is the measured length of the real append-only
output file at that event.  Consequently no formal bit quantity is inferred
from a token, gate, or node count.
"""

from __future__ import annotations

import hashlib
import json
import os
import resource
import sys
import time
from pathlib import Path
from typing import Any, Mapping

from encoding.codec import SCHEMA, SCHEMA_VERSION, decode_exact, encode
from instrumentation.resource_accounting import ResourceSnapshot, sha256_file


TRACE_SCHEMA = "ucc.reference-event-trace.v1"
FIELD_NAMES = ("control", "store", "window", "parameter", "ir")
FIELD_FILES = {name: f"{name}.frames" for name in FIELD_NAMES}
EVENT_FILE = "events.jsonl"
OUTPUT_FILE = "committed-output.stream"
MANIFEST_FILE = "run_manifest.json"


def _json_line(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    # macOS reports bytes, Linux and the approved Ubuntu runner report KiB.
    return value if sys.platform == "darwin" else 1024 * value


def _file_record(path: Path) -> dict[str, Any]:
    size = path.stat().st_size
    return {"path": path.name, "bytes": size, "bits": 8 * size, "sha256": sha256_file(path)}


class EventTraceWriter:
    """Write one immutable run trace.

    A run directory may already contain input artifacts, but none of the trace
    targets may exist.  This prevents an interrupted or resumed campaign from
    silently mixing two executions.
    """

    def __init__(self, run_dir: Path | str, config: Mapping[str, Any], output_header: bytes):
        self.run_dir = Path(run_dir).resolve()
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.config = dict(config)
        self.started_ns = time.monotonic_ns()
        self.event_count = 0
        self._last_output_length = 0
        self._output_digest = hashlib.sha256()
        targets = [self.run_dir / name for name in (*FIELD_FILES.values(), EVENT_FILE, OUTPUT_FILE, MANIFEST_FILE)]
        if any(path.exists() for path in targets):
            existing = [path.name for path in targets if path.exists()]
            raise FileExistsError(f"trace targets already exist: {existing}")
        self._fields = {name: (self.run_dir / filename).open("xb") for name, filename in FIELD_FILES.items()}
        self._events = (self.run_dir / EVENT_FILE).open("xb")
        self._output = (self.run_dir / OUTPUT_FILE).open("xb")
        self.append_output(output_header)

    @property
    def output_bytes(self) -> int:
        return self._output.tell()

    def append_output(self, payload: bytes) -> None:
        if not isinstance(payload, bytes):
            raise TypeError("committed output chunks must be bytes")
        self._output.write(payload)
        self._output.flush()
        self._output_digest.update(payload)

    def record_event(
        self,
        snapshot: ResourceSnapshot,
        *,
        event_kind: str,
        input_position: int,
        pass_index: int,
        round_index: int | None,
        side: str,
        crossing: str | None = None,
        status: str = "ok",
        details: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if side not in {"A", "B", "none"}:
            raise ValueError("event side must be A, B, or none")
        if crossing not in {None, "A_to_B", "B_to_A"}:
            raise ValueError("unknown crossing kind")
        objects = {
            "control": snapshot.control,
            "store": snapshot.store,
            "window": snapshot.window,
            "parameter": snapshot.parameter,
            "ir": snapshot.ir,
        }
        slices: dict[str, Any] = {}
        for name, value in objects.items():
            payload = encode(value)
            stream = self._fields[name]
            offset = stream.tell()
            stream.write(payload)
            stream.flush()
            slices[name] = {
                "path": FIELD_FILES[name],
                "offset": offset,
                "bytes": len(payload),
                "bits": 8 * len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "codec_type": type(value).__name__,
            }
        self._output.flush()
        output_length = self._output.tell()
        output_delta = output_length - self._last_output_length
        if output_delta < 0:
            raise OSError("committed output shrank")
        self._last_output_length = output_length
        b_cross = sum(int(slices[name]["bits"]) for name in FIELD_NAMES)
        row: dict[str, Any] = {
            "schema": TRACE_SCHEMA,
            "event_index": self.event_count,
            "event_kind": event_kind,
            "input_position": int(input_position),
            "pass_index": int(pass_index),
            "round_index": round_index,
            "side": side,
            "crossing": crossing,
            "status": status,
            "control_bytes": slices["control"]["bytes"],
            "store_bytes": slices["store"]["bytes"],
            "window_bytes": slices["window"]["bytes"],
            "parameter_bytes": slices["parameter"]["bytes"],
            "serialized_ir_bytes": slices["ir"]["bytes"],
            "B_control_bits": slices["control"]["bits"],
            "B_store_bits": slices["store"]["bits"],
            "B_window_bits": slices["window"]["bits"],
            "B_parameter_bits": slices["parameter"]["bits"],
            "B_IR_bits": slices["ir"]["bits"],
            "B_cross_bits": b_cross,
            "committed_output_bytes": output_length,
            "B_com_bits": 8 * output_length,
            "committed_delta_bytes": output_delta,
            "committed_delta_bits": 8 * output_delta,
            "current_output_length": output_length,
            "committed_prefix_sha256": self._output_digest.hexdigest(),
            "rss_bytes": _rss_bytes(),
            "wall_time_ns": time.monotonic_ns() - self.started_ns,
            "slices": slices,
            "details": dict(details or {}),
        }
        self._events.write(_json_line(row))
        self._events.flush()
        self.event_count += 1
        return row

    def finalize(self, extra: Mapping[str, Any]) -> Path:
        for stream in (*self._fields.values(), self._events, self._output):
            stream.flush()
            os.fsync(stream.fileno())
            stream.close()
        files = {name: _file_record(self.run_dir / filename) for name, filename in FIELD_FILES.items()}
        files["events"] = _file_record(self.run_dir / EVENT_FILE)
        files["committed_output"] = _file_record(self.run_dir / OUTPUT_FILE)
        manifest = {
            "schema": TRACE_SCHEMA,
            "codec": {"schema": SCHEMA, "version": SCHEMA_VERSION},
            "config": self.config,
            "event_count": self.event_count,
            "files": files,
            "bit_rule": "every B_* field is 8 times an actual frame slice or committed-output file prefix length",
            "extra": dict(extra),
        }
        path = self.run_dir / MANIFEST_FILE
        path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        verify_trace_run(path, verify_slices=True)
        return path


def verify_trace_run(path: Path | str, *, verify_slices: bool = True) -> dict[str, Any]:
    """Verify whole-file hashes and, optionally, every event slice/prefix."""

    manifest_path = Path(path).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != TRACE_SCHEMA:
        raise ValueError("unsupported event-trace manifest")
    if manifest.get("codec") != {"schema": SCHEMA, "version": SCHEMA_VERSION}:
        raise ValueError("event trace names a different codec")
    for record in manifest["files"].values():
        artifact = manifest_path.parent / record["path"]
        size = artifact.stat().st_size
        if size != record["bytes"] or 8 * size != record["bits"]:
            raise ValueError(f"size mismatch for {artifact}")
        if sha256_file(artifact) != record["sha256"]:
            raise ValueError(f"digest mismatch for {artifact}")
    if not verify_slices:
        return manifest

    field_data = {name: (manifest_path.parent / FIELD_FILES[name]).read_bytes() for name in FIELD_NAMES}
    output = (manifest_path.parent / OUTPUT_FILE).read_bytes()
    output_digest = hashlib.sha256()
    output_cursor = 0
    count = 0
    with (manifest_path.parent / EVENT_FILE).open("r", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row.get("schema") != TRACE_SCHEMA or row.get("event_index") != count:
                raise ValueError("noncanonical event ordering")
            b_cross = 0
            for name in FIELD_NAMES:
                record = row["slices"][name]
                start, length = int(record["offset"]), int(record["bytes"])
                payload = field_data[name][start : start + length]
                if len(payload) != length or hashlib.sha256(payload).hexdigest() != record["sha256"]:
                    raise ValueError(f"invalid {name} slice at event {count}")
                decode_exact(payload)
                if 8 * length != record["bits"]:
                    raise ValueError("slice bit count is not file-backed")
                b_cross += 8 * length
            if b_cross != row["B_cross_bits"]:
                raise ValueError("crossing sum mismatch")
            prefix_length = int(row["committed_output_bytes"])
            if prefix_length < output_cursor or prefix_length > len(output):
                raise ValueError("committed prefix is not monotone")
            output_digest.update(output[output_cursor:prefix_length])
            output_cursor = prefix_length
            if output_digest.hexdigest() != row["committed_prefix_sha256"]:
                raise ValueError("committed-prefix digest mismatch")
            if 8 * prefix_length != row["B_com_bits"]:
                raise ValueError("B_com is not the output prefix file length")
            count += 1
    if count != manifest["event_count"]:
        raise ValueError("event count mismatch")
    if output_cursor != len(output):
        raise ValueError("final committed output was not represented by an event")
    return manifest


__all__ = ["TRACE_SCHEMA", "EventTraceWriter", "verify_trace_run"]

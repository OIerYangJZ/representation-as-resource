#!/usr/bin/env python3
"""Event-level tracing for executable masked-share restart serializers.

This is the measured reference implementation for the theorem model.  Every
inter-round cut is resumed from the emitted prefix plus the five serialized
restart fields; no Python object is treated as free state.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import resource
import sys
import time
from pathlib import Path
from typing import Iterable


THIS_FILE = Path(__file__).resolve()
WORKSPACE_ROOT = THIS_FILE.parents[3]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from encoding.codec import (  # noqa: E402
    AggregateRecord,
    CommittedOutput,
    ControlState,
    FlatUpdateStream,
    IRField,
    LiveWindow,
    ParameterLedger,
    PauliSupport,
    SemanticStream,
    StoreState,
    SymbolicParameter,
    UpdateRecord,
    decode_exact,
    encode,
)
from instrumentation.resource_accounting import (  # noqa: E402
    ResourceAccountant,
    ResourceSnapshot,
    assert_rows_file_backed,
    write_encoded_artifact,
)


MAGIC_OUTPUT = b"MSO1"
SCHEMA = "ucc.masked-share-cut-trace.v1"
SIZES = (8, 16, 32, 64)
BETAS = (0.0, 0.25, 0.5, 0.75, 1.0)
SEED = 20260801


def rss_bytes() -> int:
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(raw if sys.platform == "darwin" else raw * 1024)


def deterministic_vectors(m: int) -> tuple[list[int], list[int], list[int]]:
    u = [((SEED + 7 * j + j * j) % 3) for j in range(m)]
    x = [((SEED // 7 + 3 * j + j * j) % 2) for j in range(m)]
    v = [(xj - uj) % 3 for uj, xj in zip(u, x)]
    assert all((uj + vj) % 3 == xj for uj, vj, xj in zip(u, v, x))
    return u, v, x


def _payload_header(m: int, h: int) -> bytes:
    if not 0 <= h <= m:
        raise ValueError("bad retained-coordinate count")
    return MAGIC_OUTPUT + m.to_bytes(4, "big") + h.to_bytes(4, "big")


def _output_frame_header(m: int, h: int) -> bytes:
    payload_length = 12 + 2 * m - h
    placeholder = encode(CommittedOutput("masked-share-v1", bytes(payload_length)))
    return placeholder[:-payload_length]


def _output_payload_prefix(encoded: bytes, m: int, h: int) -> bytes:
    header = _output_frame_header(m, h)
    if not encoded.startswith(header):
        raise ValueError("bad committed-output codec header")
    return encoded[len(header):]


def encode_output_prefix(m: int, h: int, committed_tail: list[int]) -> bytes:
    if len(committed_tail) > m - h:
        raise ValueError("committed tail is longer than its declared region")
    return _output_frame_header(m, h) + _payload_header(m, h) + bytes(committed_tail)


def encode_output_suffix(u: list[int], v: list[int], h: int) -> bytes:
    aggregates = [(u[j] + v[j]) % 3 for j in range(h)]
    return bytes(aggregates + v[h:])


def decode_final_output(encoded: bytes) -> list[int]:
    decoded = decode_exact(encoded)
    if not isinstance(decoded, CommittedOutput) or decoded.format != "masked-share-v1":
        raise ValueError("wrong committed-output object")
    payload = decoded.payload
    if len(payload) < 12 or payload[:4] != MAGIC_OUTPUT:
        raise ValueError("bad output magic")
    m, h = int.from_bytes(payload[4:8], "big"), int.from_bytes(payload[8:12], "big")
    if len(payload) != 12 + 2 * m - h:
        raise ValueError("bad output length")
    tail_u = list(payload[12 : 12 + m - h])
    suffix = list(payload[12 + m - h :])
    head_x = suffix[:h]
    tail_v = suffix[h:]
    return head_x + [(uj + vj) % 3 for uj, vj in zip(tail_u, tail_v)]


def encode_control(m: int, h: int, pass_index: int, prefix_bytes: int) -> bytes:
    return encode(ControlState({
        "m": m,
        "retained_coordinates": h,
        "pass_index": pass_index,
        "committed_prefix_bytes": prefix_bytes,
    }))


def encode_store(retained_u: list[int]) -> bytes:
    return encode(StoreState({"retained_u": list(retained_u)}))


def encode_snapshot(
    m: int,
    h: int,
    pass_index: int,
    prefix: bytes,
    retained_u: list[int],
) -> dict[str, bytes]:
    return {
        "control": encode_control(m, h, pass_index, len(prefix)),
        "store": encode_store(retained_u),
        "window": encode(LiveWindow()),
        "parameter": encode(ParameterLedger()),
        "ir": encode(IRField()),
    }


def decode_snapshot(
    prefix: bytes,
    snapshot: dict[str, bytes],
) -> tuple[int, int, int, list[int]]:
    control = decode_exact(snapshot["control"])
    if not isinstance(control, ControlState):
        raise ValueError("bad control field")
    m = int(control.fields["m"])
    h = int(control.fields["retained_coordinates"])
    pass_index = int(control.fields["pass_index"])
    prefix_bytes = int(control.fields["committed_prefix_bytes"])
    if pass_index not in (1, 2) or prefix_bytes != len(prefix):
        raise ValueError("inconsistent restart control")
    store = decode_exact(snapshot["store"])
    if not isinstance(store, StoreState):
        raise ValueError("bad store field")
    retained_u = list(store.fields["retained_u"])
    if len(retained_u) > h:
        raise ValueError("inconsistent store field")
    if not isinstance(decode_exact(snapshot["window"]), LiveWindow):
        raise ValueError("noncanonical window field")
    if not isinstance(decode_exact(snapshot["parameter"]), ParameterLedger):
        raise ValueError("noncanonical parameter field")
    if not isinstance(decode_exact(snapshot["ir"]), IRField):
        raise ValueError("noncanonical empty field")
    return m, h, pass_index, retained_u


def resume_flat_from_snapshot(
    prefix: bytes,
    snapshot: dict[str, bytes],
    remaining_u: bytes,
    remaining_v: bytes,
) -> bytes:
    """Resume a flat run using only serialized state and unread input bytes."""

    m, h, pass_index, retained_u = decode_snapshot(prefix, snapshot)
    payload_prefix = _output_payload_prefix(prefix, m, h)
    if len(payload_prefix) < 12 or payload_prefix[:4] != MAGIC_OUTPUT:
        raise ValueError("bad output prefix")
    prefix_m = int.from_bytes(payload_prefix[4:8], "big")
    prefix_h = int.from_bytes(payload_prefix[8:12], "big")
    if (prefix_m, prefix_h) != (m, h):
        raise ValueError("output/snapshot header mismatch")
    rebuilt = bytearray(prefix)
    if pass_index == 1:
        committed_tail = list(payload_prefix[12:])
        processed_u = len(retained_u) + len(committed_tail)
        if len(retained_u) != min(processed_u, h):
            raise ValueError("noncanonical first-round retained state")
        if len(remaining_u) != m - processed_u or len(remaining_v) != m:
            raise ValueError("wrong unread first-round input")
        for index, value in enumerate(remaining_u, start=processed_u):
            if index < h:
                retained_u.append(value)
            else:
                rebuilt.append(value)
        full_v = list(remaining_v)
    else:
        base_length = len(_output_frame_header(m, h)) + 12 + m - h
        if len(rebuilt) < base_length or len(retained_u) != h or remaining_u:
            raise ValueError("noncanonical second-round state")
        processed_v = len(rebuilt) - base_length
        if not 0 <= processed_v <= m or len(remaining_v) != m - processed_v:
            raise ValueError("wrong unread second-round input")
        full_v = [0] * processed_v + list(remaining_v)

    payload_offset = len(_output_frame_header(m, h))
    tail_u = list(rebuilt[payload_offset + 12 : payload_offset + 12 + m - h])
    full_u = retained_u + tail_u
    if len(full_u) != m:
        raise ValueError("restart did not reconstruct the first share")
    if pass_index == 1:
        rebuilt.extend(encode_output_suffix(full_u, full_v, h))
    else:
        processed_v = len(rebuilt) - (payload_offset + 12 + m - h)
        for index in range(processed_v, m):
            rebuilt.append(
                (full_u[index] + full_v[index]) % 3
                if index < h else full_v[index]
            )
    return bytes(rebuilt)


def resume_semantic_from_snapshot(
    prefix: bytes,
    snapshot: dict[str, bytes],
    remaining_x: bytes,
) -> bytes:
    """Resume the direct semantic stream from one serialized event cut."""

    m, h, pass_index, retained = decode_snapshot(prefix, snapshot)
    if h != m or pass_index != 1 or retained:
        raise ValueError("noncanonical semantic restart state")
    payload_prefix = _output_payload_prefix(prefix, m, h)
    if len(payload_prefix) < 12 or payload_prefix[:4] != MAGIC_OUTPUT:
        raise ValueError("bad semantic output prefix")
    prefix_m = int.from_bytes(payload_prefix[4:8], "big")
    prefix_h = int.from_bytes(payload_prefix[8:12], "big")
    processed = len(payload_prefix) - 12
    if (prefix_m, prefix_h) != (m, m) or len(remaining_x) != m - processed:
        raise ValueError("wrong unread semantic input")
    return prefix + remaining_x


def event_record(
    *,
    experiment: str,
    representation: str,
    compiler: str,
    m: int,
    beta: float,
    h: int,
    event: str,
    pass_index: int,
    prefix: bytes,
    fields: dict[str, bytes],
    started_ns: int,
    accountant: ResourceAccountant,
    input_record: dict[str, object],
) -> dict[str, object]:
    if fields:
        control = decode_exact(fields["control"])
        store = decode_exact(fields["store"])
        window = decode_exact(fields["window"])
        parameter = decode_exact(fields["parameter"])
        ir = decode_exact(fields["ir"])
    else:
        control = ControlState({"terminal": True, "pass_index": pass_index})
        store, window, parameter, ir = StoreState({}), LiveWindow(), ParameterLedger(), IRField()
    pass_count = 2 if representation == "flat_two_round" else 1
    measurement = accountant.measure(
        event,
        ResourceSnapshot(
            control,
            store,
            window,
            parameter,
            ir,
            prefix,
            pass_count=pass_count,
            pass_index=min(pass_index - 1, pass_count - 1),
        ),
    )
    return {
        "schema": SCHEMA,
        "experiment": experiment,
        "representation": representation,
        "compiler": compiler,
        "m": m,
        "beta": beta,
        "retained_coordinates": h,
        "event": event,
        "pass_index": pass_index,
        "committed_output_bytes": measurement["B_com_bytes"],
        "input_artifact_path": input_record["artifact_path"],
        "input_artifact_sha256": input_record["artifact_sha256"],
        "serialized_input_bits": input_record["artifact_bits"],
        "rss_bytes": rss_bytes(),
        "runtime_ns": time.perf_counter_ns() - started_ns,
        **measurement,
    }


def run_flat_hybrid(
    m: int, beta: float, artifact_root: Path
) -> tuple[list[dict[str, object]], dict[str, object]]:
    started_ns = time.perf_counter_ns()
    u, v, x = deterministic_vectors(m)
    h = int(round(beta * m))
    compiler = "deferred_reference" if h == m else "memory_capped_hybrid_artifact"
    run_id = f"flat-m{m}-h{h}"
    accountant = ResourceAccountant(artifact_root, run_id)
    input_record = write_encoded_artifact(
        artifact_root / run_id / "input.uccbin",
        FlatUpdateStream(
            m,
            2,
            tuple(
                UpdateRecord(
                    round_index,
                    generator,
                    PauliSupport(((generator, "Z"),)),
                    SymbolicParameter(value),
                )
                for round_index, values in enumerate((u, v))
                for generator, value in enumerate(values)
            ),
        ),
        role="flat_input",
    )
    events: list[dict[str, object]] = []
    inter_round_summary: dict[str, object] | None = None

    # Every first-round update is a restart cut.  ``retained_state`` is the
    # only live compiler object; it is serialized and deleted before the
    # independent restart routine receives unread input bytes.
    for processed in range(1, m + 1):
        retained_state = list(u[: min(processed, h)])
        committed_tail = list(u[h:processed]) if processed > h else []
        prefix = encode_output_prefix(m, h, committed_tail)
        snapshot = encode_snapshot(m, h, 1, prefix, retained_state)
        del retained_state
        restarted = resume_flat_from_snapshot(
            bytes(prefix),
            {name: bytes(value) for name, value in snapshot.items()},
            bytes(u[processed:]),
            bytes(v),
        )
        resume_verified = decode_final_output(restarted) == x
        if not resume_verified:
            raise AssertionError("first-round restart did not recover aggregate")
        event = event_record(
            experiment="masked_share_cut_20260801",
            representation="flat_two_round",
            compiler=compiler,
            m=m,
            beta=beta,
            h=h,
            event=f"first_share_{processed}",
            pass_index=1,
            prefix=prefix,
            fields=snapshot,
            started_ns=started_ns,
            accountant=accountant,
            input_record=input_record,
        )
        event["resume_verified"] = resume_verified
        events.append(event)
        if processed == m:
            inter_round_summary = dict(event)
            inter_round_summary["final_output_bytes"] = len(restarted)

    # The second round is traced at every update as well.  At the final event
    # all restart fields are released because no continuation remains.
    first_round_prefix = encode_output_prefix(m, h, u[h:])
    for processed in range(1, m + 1):
        suffix = []
        for index in range(processed):
            suffix.append((u[index] + v[index]) % 3 if index < h else v[index])
        prefix = first_round_prefix + bytes(suffix)
        if processed < m:
            retained_state = list(u[:h])
            snapshot = encode_snapshot(m, h, 2, prefix, retained_state)
            del retained_state
            restarted = resume_flat_from_snapshot(
                bytes(prefix),
                {name: bytes(value) for name, value in snapshot.items()},
                b"",
                bytes(v[processed:]),
            )
            resume_verified = decode_final_output(restarted) == x
            if not resume_verified:
                raise AssertionError("second-round restart did not recover aggregate")
        else:
            snapshot = {}
            resume_verified = decode_final_output(prefix) == x
            if not resume_verified:
                raise AssertionError("final output did not decode to aggregate")
        event = event_record(
            experiment="masked_share_cut_20260801",
            representation="flat_two_round",
            compiler=compiler,
            m=m,
            beta=beta,
            h=h,
            event="final" if processed == m else f"second_share_{processed}",
            pass_index=2,
            prefix=prefix,
            fields=snapshot,
            started_ns=started_ns,
            accountant=accountant,
            input_record=input_record,
        )
        event["resume_verified"] = resume_verified
        events.append(event)
    if inter_round_summary is None:
        raise AssertionError("missing inter-round summary")
    return events, inter_round_summary


def run_semantic(m: int, artifact_root: Path) -> tuple[list[dict[str, object]], dict[str, object]]:
    started_ns = time.perf_counter_ns()
    _, _, x = deterministic_vectors(m)
    run_id = f"semantic-m{m}"
    accountant = ResourceAccountant(artifact_root, run_id)
    input_record = write_encoded_artifact(
        artifact_root / run_id / "input.uccbin",
        SemanticStream(
            m,
            tuple(
                AggregateRecord(
                    generator,
                    PauliSupport(((generator, "Z"),)),
                    SymbolicParameter(value),
                )
                for generator, value in enumerate(x)
            ),
        ),
        role="semantic_input",
    )
    prefix = _output_frame_header(m, m) + _payload_header(m, m)
    # Direct aggregate records may be copied as they arrive.  The live state is
    # only the next index and the empty field delimiters.
    events = []
    for index, value in enumerate(x):
        prefix += bytes([value])
        if index + 1 < m:
            live_state: list[int] = []
            fields = encode_snapshot(m, m, 1, prefix, live_state)
            del live_state
            restarted = resume_semantic_from_snapshot(
                bytes(prefix),
                {name: bytes(field) for name, field in fields.items()},
                bytes(x[index + 1 :]),
            )
            resume_verified = decode_final_output(restarted) == x
        else:
            fields = {}
            resume_verified = decode_final_output(prefix) == x
        if not resume_verified:
            raise AssertionError("semantic restart did not recover aggregate")
        event = event_record(
                experiment="masked_share_cut_20260801",
                representation="semantic_aggregate",
                compiler="semantic_stream_artifact",
                m=m,
                beta=1.0,
                h=0,
                event=f"aggregate_{index + 1}",
                pass_index=1,
                prefix=prefix,
                fields=fields,
                started_ns=started_ns,
                accountant=accountant,
                input_record=input_record,
        )
        event["resume_verified"] = resume_verified
        events.append(event)
    nonfinal = [row for row in events if row["event"] != "final"]
    peak = max(nonfinal or events, key=lambda row: int(row["B_cross_bytes"]))
    summary = dict(peak)
    summary["final_output_bytes"] = len(prefix)
    return events, summary


def write_figure(rows: list[dict[str, object]], path: Path) -> None:
    import matplotlib.pyplot as plt

    assert_rows_file_backed(rows)
    fig, ax = plt.subplots(figsize=(5.8, 3.7))
    for m in SIZES:
        points = [
            row for row in rows
            if row["representation"] == "flat_two_round" and row["m"] == m
        ]
        points.sort(key=lambda row: float(row["beta"]))
        ax.plot(
            [row["B_cross_bytes"] for row in points],
            [row["B_com_bytes"] for row in points],
            marker="o",
            label=rf"flat $m={m}$",
        )
    semantic = [row for row in rows if row["representation"] == "semantic_aggregate"]
    ax.scatter(
        [row["B_cross_bytes"] for row in semantic],
        [row["B_com_bytes"] for row in semantic],
        marker="x",
        s=55,
        color="black",
        label="semantic stream",
    )
    ax.set_xlabel(r"measured $B_{\mathrm{cross}}$ (bytes)")
    ax.set_ylabel(r"measured $B_{\mathrm{com}}$ (bytes)")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/ucc-cut-trace-mpl")
    os.environ.setdefault("XDG_CACHE_HOME", "/tmp/ucc-cut-trace-cache")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    events: list[dict[str, object]] = []
    summary: list[dict[str, object]] = []
    for m in SIZES:
        for beta in BETAS:
            local_events, local_summary = run_flat_hybrid(m, beta, args.output_dir / "accounting")
            events.extend(local_events)
            summary.append(local_summary)
        local_events, local_summary = run_semantic(m, args.output_dir / "accounting")
        events.extend(local_events)
        summary.append(local_summary)

    event_path = args.output_dir / "cut_trace_events.jsonl"
    event_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in events),
        encoding="utf-8",
    )
    summary_path = args.output_dir / "cut_trace_summary.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    figure_path = args.output_dir / "commitment_vs_cross_cut.pdf"
    write_figure(summary, figure_path)
    report = {
        "schema": SCHEMA,
        "host": platform.node(),
        "python": platform.python_version(),
        "pid": os.getpid(),
        "seed": SEED,
        "sizes": list(SIZES),
        "betas": list(BETAS),
        "serializer": "ucc.accounting v1; all plotted bits re-measured from SHA-256-verified files",
        "event_count": len(events),
        "summary_count": len(summary),
        "all_event_restart_checks_passed": all(
            bool(row["resume_verified"]) for row in events
        ),
        "all_summary_restart_checks_passed": all(
            bool(row["resume_verified"]) for row in summary
        ),
        "files": {
            path.name: sha256(path)
            for path in (event_path, summary_path, figure_path)
        },
    }
    report_path = args.output_dir / "cut_trace_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

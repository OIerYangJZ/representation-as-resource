#!/usr/bin/env python3
"""Run one instrumented reference compiler cell."""

from __future__ import annotations

import argparse
import json
import platform
import socket
import sys
import time
from pathlib import Path
from typing import Any

from encoding.codec import FlatUpdateStream, SemanticStream
from instrumentation.event_trace import EventTraceWriter, OUTPUT_FILE, verify_trace_run
from instrumentation.resource_accounting import sha256_file, write_encoded_artifact

from .compilers import effective_fraction, execute_compiler, expected_output_records
from .model import (
    RunConfig,
    assert_token_nonrevelation,
    build_dispersed_instance,
    output_header,
    verify_output_stream,
)


def _input_equivalence(config: RunConfig, semantic: SemanticStream, flat: FlatUpdateStream) -> dict[str, Any]:
    semantic_totals = [0] * config.m
    flat_totals = [0] * config.m
    for record in semantic.records:
        semantic_totals[record.generator] = (
            semantic_totals[record.generator] + record.multiplicity * record.parameter.constant.numerator
        ) % config.Q
    for record in flat.records:
        flat_totals[record.generator] = (
            flat_totals[record.generator] + record.parameter.constant.numerator
        ) % config.Q
    if semantic_totals != flat_totals:
        raise ValueError("semantic and dispersed inputs differ modulo Q")
    return {
        "status": "pass",
        "same_U_x_up_to_global_phase": True,
        "modulus_Q": config.Q,
        "aggregate_vector": semantic_totals,
    }


def _artifact_record(path: Path) -> dict[str, Any]:
    return {
        "path": path.name,
        "bytes": path.stat().st_size,
        "bits": 8 * path.stat().st_size,
        "sha256": sha256_file(path),
    }


def _relative_artifact_record(record: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    result = dict(record)
    sidecar = Path(result["artifact_manifest_path"]).resolve()
    result["artifact_manifest_bytes"] = sidecar.stat().st_size
    result["artifact_manifest_sha256"] = sha256_file(sidecar)
    for key in ("artifact_path", "artifact_manifest_path"):
        if key in result:
            result[key] = str(Path(result[key]).resolve().relative_to(run_dir.resolve()))
    return result


def run_reference_compiler(config: RunConfig, output_root: Path | str) -> Path:
    """Execute a fresh cell and return its verified run manifest."""

    root = Path(output_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    run_dir = root / config.run_id()
    run_dir.mkdir(parents=False, exist_ok=False)
    started = time.time()
    x, semantic, flat = build_dispersed_instance(config)
    assert_token_nonrevelation(config, flat)
    equivalence = _input_equivalence(config, semantic, flat)
    semantic_artifact = _relative_artifact_record(
        write_encoded_artifact(run_dir / "semantic-input.uccbin", semantic, role="semantic_input"), run_dir
    )
    flat_artifact = _relative_artifact_record(
        write_encoded_artifact(run_dir / "flat-input.uccbin", flat, role="dispersed_flat_input"), run_dir
    )
    config_record = config.to_dict()
    config_record["effective_memory_fraction"] = effective_fraction(config)
    trace = EventTraceWriter(
        run_dir,
        config_record,
        output_header(config, expected_output_records(config)),
    )
    execution = execute_compiler(config, flat, trace)
    output_certificate = verify_output_stream(run_dir / OUTPUT_FILE, config, x)
    environment = {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "implementation": platform.python_implementation(),
    }
    log_path = run_dir / "run.log"
    log_rows = (
        {"event": "start", "unix_time": started, "run_id": config.run_id(), "config": config_record},
        {"event": "input_equivalence", **equivalence},
        {"event": "compiler_complete", **execution},
        {"event": "output_certificate", **output_certificate},
        {"event": "environment", **environment},
    )
    log_path.write_text(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in log_rows),
        encoding="utf-8",
    )
    manifest_path = trace.finalize(
        {
            "run_id": config.run_id(),
            "input_artifacts": {
                "semantic": semantic_artifact,
                "flat": flat_artifact,
            },
            "input_equivalence": equivalence,
            "token_nonrevelation": {
                "status": "pass",
                "claim": "each token contains an addressed share only; the aggregate is recovered only modulo Q across rounds",
            },
            "execution": execution,
            "output_certificate": output_certificate,
            "run_log": _artifact_record(log_path),
            "environment": environment,
            "elapsed_seconds": time.time() - started,
        }
    )
    verify_trace_run(manifest_path, verify_slices=True)
    return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-json", required=True, help="JSON object or path to a JSON file")
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()
    raw = args.config_json
    config_data = json.loads(Path(raw).read_text(encoding="utf-8")) if Path(raw).is_file() else json.loads(raw)
    manifest = run_reference_compiler(RunConfig.from_mapping(config_data), args.output_root)
    print(manifest)


if __name__ == "__main__":
    main()

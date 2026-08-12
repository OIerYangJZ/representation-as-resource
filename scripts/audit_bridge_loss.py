#!/usr/bin/env python3
"""Verify, freeze, and report the W5 external-baseline/bridge campaign."""

from __future__ import annotations

import argparse
import csv
import importlib.metadata
import json
import math
import shutil
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_external_baselines import (  # noqa: E402
    VALID_STATUSES,
    load_baseline_configs,
    load_campaign_config,
    sha256_file,
    verify_cell_manifest,
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def _verify_artifact(record: Mapping[str, Any]) -> None:
    path = ROOT / str(record["path"])
    if path.stat().st_size != int(record["bytes"]) or sha256_file(path) != record["sha256"]:
        raise ValueError(f"artifact differs from manifest: {path}")


def _verify_representation(path: Path) -> None:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "ucc.matched-representation.v1":
        raise ValueError(f"unsupported representation manifest: {path}")
    for record in manifest["files"].values():
        _verify_artifact(record)
    _verify_artifact(manifest["canonical_qasm"])
    if manifest["input_certificate"].get("status") != "passed":
        raise ValueError(f"W5 input is not certified: {path}")


def verify_campaign(campaign_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    plan = load_campaign_config()
    configs = load_baseline_configs()
    manifest = json.loads((campaign_root / "campaign_manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != "ucc.external-baseline-campaign.v1" or not manifest.get("formal"):
        raise ValueError("analysis only accepts a formal W5 campaign")
    if not manifest.get("matrix_complete"):
        raise ValueError("W5 campaign is not a complete matrix")
    rows_path = campaign_root / "external_baseline_cells.jsonl"
    if sha256_file(rows_path) != manifest["rows_sha256"]:
        raise ValueError("W5 row digest differs from campaign manifest")
    rows = read_jsonl(rows_path)
    expected = 216 * len(configs)
    if len(rows) != expected or len({row["cell_id"] for row in rows}) != expected:
        raise ValueError(f"expected {expected} unique W5 cells")
    keys = Counter((row["representation_id"], row["baseline_id"]) for row in rows)
    if set(keys.values()) != {1}:
        raise ValueError("W5 representation x baseline key is missing or duplicated")
    expected_ids = {row["id"] for row in configs}
    for representation_id in {row["representation_id"] for row in rows}:
        observed = {row["baseline_id"] for row in rows if row["representation_id"] == representation_id}
        if observed != expected_ids:
            raise ValueError(f"incomplete baseline pair set for {representation_id}")
    controls = {
        (
            row["target_basis"], row["hardware"], float(row["timeout_s"]),
            int(row["memory_cap_bytes"]), float(row["total_error_budget"]), row["certificate_kind"],
        )
        for row in rows
    }
    if len(controls) != 1:
        raise ValueError(f"W5 controls are not uniform: {controls}")
    if any(row["status"] not in VALID_STATUSES for row in rows):
        raise ValueError("invalid W5 status")
    for path in sorted({ROOT / row["representation_manifest_path"] for row in rows}):
        _verify_representation(path)
    for row in rows:
        cell_path = campaign_root / "cells" / row["cell_id"] / "cell_manifest.json"
        cell = verify_cell_manifest(cell_path)
        if cell["result"]["status"] != row["status"]:
            raise ValueError(f"cell/result status mismatch: {row['cell_id']}")
        if row["status"] == "completed":
            if not row.get("bridge_certificate_passed") or not row.get("output_certificate_passed"):
                raise ValueError(f"uncertified completed cell: {row['cell_id']}")
        if row["status"] == "correctness_failure" and row.get("output_certificate_passed"):
            raise ValueError(f"passed certificate labeled correctness failure: {row['cell_id']}")
    actual = {status: sum(row["status"] == status for row in rows) for status in sorted(VALID_STATUSES)}
    if {key: int(value) for key, value in manifest["status_counts"].items()} != actual:
        raise ValueError("W5 manifest status counts differ from the rows")
    if manifest["input_index_sha256"] != sha256_file(ROOT / plan["input_index"]):
        raise ValueError("W4 representation index changed after W5 execution")
    if manifest["registry_sha256"] != sha256_file(ROOT / plan["registry"]):
        raise ValueError("baseline registry changed after W5 execution")
    return manifest, rows


def _median(rows: Iterable[Mapping[str, Any]], field: str) -> float:
    values = [float(row[field]) for row in rows if row.get(field) is not None]
    return float(statistics.median(values)) if values else math.nan


def _summary_record(group: list[dict[str, Any]], keys: Mapping[str, Any]) -> dict[str, Any]:
    completed = [row for row in group if row["status"] == "completed"]
    bridge_ok = [row for row in group if row.get("bridge_certificate_passed")]
    record: dict[str, Any] = {
        **keys, "cells": len(group), "completed": len(completed),
        "completion_probability": len(completed) / len(group) if group else math.nan,
        "bridge_certified": len(bridge_ok),
    }
    counts = Counter(row["status"] for row in group)
    for status in sorted(VALID_STATUSES):
        record[f"status_{status}"] = counts[status]
    for metric in (
        "pre_bridge_gates", "pre_bridge_depth", "pre_bridge_cx", "pre_bridge_ir_bytes",
        "bridge_delta_gates", "bridge_delta_depth", "bridge_delta_cx", "bridge_delta_ir_bytes",
        "bridge_serialized_bytes", "native_output_gates", "native_output_depth", "native_output_cx",
        "native_output_ir_bytes", "certificate_output_gates", "certificate_output_depth",
        "certificate_output_cx", "certificate_output_ir_bytes", "compiler_runtime_s",
        "wall_runtime_s", "rss_peak_bytes",
    ):
        source = bridge_ok if metric.startswith(("pre_bridge", "bridge_")) else completed
        record[f"median_{metric}"] = _median(source, metric)
    for metric in ("bridge_delta_gates", "bridge_delta_depth", "bridge_delta_cx"):
        values = [abs(float(row[metric])) for row in bridge_ok if row.get(metric) is not None]
        record[f"max_abs_{metric}"] = max(values) if values else math.nan
    ratios = [
        float(row["certificate_output_gates"]) / float(row["pre_bridge_gates"])
        for row in completed if row.get("certificate_output_gates") is not None and row.get("pre_bridge_gates")
    ]
    record["median_certificate_gate_ratio"] = float(statistics.median(ratios)) if ratios else math.nan
    return record


def baseline_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for baseline_id in sorted({row["baseline_id"] for row in rows}):
        group = [row for row in rows if row["baseline_id"] == baseline_id]
        first = group[0]
        output.append(_summary_record(group, {
            "baseline_id": baseline_id, "tool": first["tool"], "category": first["category"],
            "config_mode": first["config_mode"], "tool_version": first["tool_version"],
            "tool_commit": first.get("tool_commit"), "tool_commit_source": first["tool_commit_source"],
            "pass_sequence": first["pass_sequence"], "bridge_format": first["bridge_format"],
            "output_basis": first.get("output_basis", ""),
        }))
    return output


def bridge_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # The bridge precedes native/unified selection.  De-duplicate the two modes
    # before computing bridge loss, and verify that they actually agree.
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    fields = (
        "bridge_certificate_status", "bridge_certificate_passed", "pre_bridge_gates",
        "post_bridge_gates", "bridge_delta_gates", "bridge_delta_depth", "bridge_delta_cx",
        "bridge_delta_ir_bytes", "bridge_serialized_bytes",
    )
    for row in rows:
        key = (row["representation_id"], row["tool"])
        previous = unique.get(key)
        if previous is not None and any(previous.get(field) != row.get(field) for field in fields):
            raise ValueError(f"native/unified bridge measurements disagree for {key}")
        unique[key] = row
    deduplicated = list(unique.values())
    output = []
    for tool in sorted({row["tool"] for row in deduplicated}):
        for representation in sorted({row["representation"] for row in deduplicated}):
            group = [
                row for row in deduplicated
                if row["tool"] == tool and row["representation"] == representation
            ]
            output.append(_summary_record(group, {"tool": tool, "representation": representation}))
    return output


def _write_csv(path: Path, rows: list[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_parquet(rows: list[dict[str, Any]], path: Path) -> None:
    import pandas as pd

    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False, engine="pyarrow", compression="zstd")
    payload = path.read_bytes()
    if payload[:4] != b"PAR1" or payload[-4:] != b"PAR1":
        raise ValueError("frozen W5 artifact is not Apache Parquet")
    reread = pd.read_parquet(path, engine="pyarrow")
    if len(reread) != len(rows) or set(reread["cell_id"]) != {row["cell_id"] for row in rows}:
        raise ValueError("W5 Parquet round trip changed the cells")


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return "--"
    return f"{float(value):.{digits}g}"


def write_report(
    campaign: Mapping[str, Any], rows: list[dict[str, Any]], summary: list[dict[str, Any]],
    bridges: list[dict[str, Any]], output: Path,
) -> None:
    counts = Counter(row["status"] for row in rows)
    controls = campaign["campaign_config"]
    lines = [
        "# W5 external semantic-baseline validation report", "",
        "## Outcome", "",
        f"The formal local campaign contains **{len(rows)}** cells: 216 certified matched representations "
        f"times 8 frozen native/unified baseline configurations. Certified completion is "
        f"**{counts['completed']}/{len(rows)}**. Every cell remains in the Parquet artifact; only `completed` "
        "cells enter numerical summaries.", "",
        "The campaign includes a local/standard baseline (Qiskit level 3), two independently implemented "
        "semantic-capable baselines (TKET `PauliSimp` and PyZX `full_reduce`), and the authors' exact "
        "constructive phase-table reference. Conclusions below are class-aware; native semantic-object counts "
        "are not silently mixed with target-basis physical gates.", "",
        "## Frozen controls and certificate", "",
        f"All cells use basis `{controls['target_basis']}`, hardware `{controls['hardware']}`, timeout "
        f"`{controls['timeout_s']} s`, memory cap `{controls['memory_cap_bytes']} bytes`, exact total error "
        f"budget `{controls['total_error_budget']}`, and common certificate `{controls['certificate_kind']}` "
        "up to global phase. Each row freezes tool version/available commit metadata, pass sequence, bridge, "
        "seed, configuration digest, RSS peak, and event log.", "",
        "Installed wheel distributions normally contain no VCS commit identifier. In those cases the manifest "
        "records an explicit unavailable commit plus the installed package version; it does not invent a commit.", "",
        "| tool | installed version / repository revision | commit metadata | configurations |",
        "|---|---|---|---|",
    ]
    for tool in sorted({config["tool"] for config in campaign["baseline_configs"]}):
        group = [config for config in campaign["baseline_configs"] if config["tool"] == tool]
        first = group[0]
        commit = first.get("tool_commit") or "unavailable"
        ids = ", ".join(f"`{config['id']}`" for config in group)
        lines.append(
            f"| {tool} | `{first['tool_version']}` | `{commit}` "
            f"({first['tool_commit_source']}) | {ids} |"
        )
    lines.extend([
        "", "The exact pass sequence, output basis, bridge format, and configuration SHA-256 for each row "
        "are frozen in the YAML configurations and copied into the campaign manifest. The representation "
        "seeds are `20260811` and `20260812`; compiler seed equals the representation seed.", "",
        "## Status accounting", "", "| status | cells |", "|---|---:|",
    ])
    for status in sorted(VALID_STATUSES):
        lines.append(f"| `{status}` | {counts[status]} |")
    lines.extend([
        "", "`unsupported` means the bridge/tool could not represent the input. `predicate_error` means the "
        "configured common certificate was inconclusive or a declared predicate was unavailable. "
        "`correctness_failure` requires an explicit inequality in the exact CNOT-Rz phase-table domain. "
        "Neither unsupported nor predicate outcomes are numerical wins or losses.", "",
        "## Baseline results by frozen configuration", "",
        "| class | configuration | mode | completed | median native IR B | median certified gates | median CX | gate ratio vs input | median runtime s |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ])
    for row in summary:
        lines.append(
            f"| {row['category']} | `{row['baseline_id']}` | {row['config_mode']} | "
            f"{row['completed']}/{row['cells']} | {_fmt(row['median_native_output_ir_bytes'])} | "
            f"{_fmt(row['median_certificate_output_gates'])} | {_fmt(row['median_certificate_output_cx'])} | "
            f"{_fmt(row['median_certificate_gate_ratio'])} | {_fmt(row['median_compiler_runtime_s'])} |"
        )
    lines.extend([
        "", "For recommended-native configurations, `native_output_ir_bytes` is the literal native artifact: "
        "Qiskit literal OpenQASM in a charged external-output envelope when matrix instructions are present, "
        "TKET command JSON, PyZX graph JSON, or the authors' exact phase table. "
        "`certificate_output_gates` is the separate common-certificate circuit. "
        "For unified configurations it is also the physical `{cx,rz,h}` comparison circuit.", "",
        "### Class-fair interpretation", "",
    ])
    for category in ("local", "semantic-capable", "authors-reference"):
        group = [row for row in summary if row["category"] == category]
        completed = sum(row["completed"] for row in group)
        cells = sum(row["cells"] for row in group)
        names = ", ".join(f"`{row['baseline_id']}`" for row in group)
        lines.append(f"- **{category}:** {completed}/{cells} certified completions across {names}.")
    lines.extend([
        "", "This class accounting directly tests whether the finding survives semantic recovery; it does not "
        "base the conclusion on defeating only a local optimizer. The authors-reference rows are retained as "
        "constructive attainability evidence, not pooled with external-tool rankings.", "",
        "## Bridge loss audit", "",
        "Bridge measurements are de-duplicated across native/unified modes before aggregation. The full "
        "tool-by-representation table is frozen in `data/frozen/external_bridge_loss.csv`.", "",
        "| tool | certified bridges | max abs(delta gates) | max abs(delta depth) | max abs(delta CX) | median delta IR B |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for tool in sorted({row["tool"] for row in bridges}):
        group = [row for row in bridges if row["tool"] == tool]
        lines.append(
            f"| {tool} | {sum(row['bridge_certified'] for row in group)}/{sum(row['cells'] for row in group)} | "
            f"{max(row['max_abs_bridge_delta_gates'] for row in group):.3g} | "
            f"{max(row['max_abs_bridge_delta_depth'] for row in group):.3g} | "
            f"{max(row['max_abs_bridge_delta_cx'] for row in group):.3g} | "
            f"{_fmt(statistics.median(row['median_bridge_delta_ir_bytes'] for row in group))} |"
        )
    lines.extend(["", "Bridge gate/depth/CX losses are reported independently from optimization. Serialized "
                  "IR byte deltas may be nonzero because the native bridge codec and provenance are charged; "
                  "they are never interpreted as gate improvement.", "",
                  "## Anomalies and failures", ""])
    failures = [row for row in rows if row["status"] != "completed"]
    if failures:
        grouped = Counter(
            (row["status"], row["category"], row["baseline_id"], row["representation"],
             row.get("status_stage", "unknown"), row.get("output_certificate_status", "not_run"))
            for row in failures
        )
        lines.extend([
            "| status | class | configuration | representation | stage | certificate | cells |",
            "|---|---|---|---|---|---|---:|",
        ])
        for key, count in sorted(grouped.items()):
            status, category, baseline_id, representation, stage, certificate = key
            lines.append(
                f"| `{status}` | {category} | `{baseline_id}` | {representation} | {stage} | {certificate} | {count} |"
            )
    else:
        lines.append("No non-completed cell was observed.")
    zero_rss = sum(int(row.get("rss_peak_bytes") or 0) <= 0 for row in rows)
    lines.extend([
        "", f"RSS instrumentation anomaly check: **{zero_rss}** cell(s) have missing/non-positive peak RSS.", "",
        "Any observed certificate or theorem-model mismatch is retained in the table above. No point was "
        "deleted because it was inconvenient, and no timeout, unsupported input, or predicate error was "
        "converted to a favorable numeric result.", "",
        "## Reproduction", "",
        "Run `./.venv/bin/python scripts/run_external_baselines.py --formal-local` to create the immutable "
        "cell manifests and logs, then `./.venv/bin/python scripts/audit_bridge_loss.py` to re-hash every "
        "input/cell artifact, audit bridge loss, round-trip the Parquet file, and regenerate this report.", "",
        f"Raw campaign rows SHA-256: `{campaign['rows_sha256']}`. Registry SHA-256: "
        f"`{campaign['registry_sha256']}`.", "",
    ])
    output.write_text("\n".join(lines), encoding="utf-8")


def freeze_manifest(paths: Iterable[Path], campaign: Mapping[str, Any], output: Path) -> None:
    records = {
        _relative(path): {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for path in paths
    }
    versions = {
        name: importlib.metadata.version(name)
        for name in ("pandas", "pyarrow", "qiskit", "pytket", "pyzx", "psutil")
    }
    payload = {
        "schema": "ucc.external-baseline-freeze.v1", "campaign": campaign["campaign"],
        "matrix_complete": campaign["matrix_complete"], "status_counts": campaign["status_counts"],
        "files": records, "analysis_tool_versions": versions,
        "parquet_validation": "PAR1 magic and pandas/pyarrow cell_id round trip",
        "numeric_status_policy": "only certified completed rows enter numeric optimization summaries",
        "bridge_policy": "bridge losses de-duplicated by representation_id and tool",
    }
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def audit(
    campaign_root: Path, parquet: Path, freeze_dir: Path, report: Path,
) -> None:
    campaign, rows = verify_campaign(campaign_root)
    summary = baseline_summary(rows)
    bridges = bridge_summary(rows)
    freeze_dir.mkdir(parents=True, exist_ok=True)
    write_parquet(rows, parquet)
    raw_csv = freeze_dir / "external_baselines.csv"
    summary_csv = freeze_dir / "external_baseline_summary.csv"
    bridge_csv = freeze_dir / "external_bridge_loss.csv"
    _write_csv(raw_csv, rows)
    _write_csv(summary_csv, summary)
    _write_csv(bridge_csv, bridges)
    write_report(campaign, rows, summary, bridges, report)
    campaign_copy = freeze_dir / "external_campaign_manifest.json"
    shutil.copyfile(campaign_root / "campaign_manifest.json", campaign_copy)
    freeze_path = freeze_dir / "external_baseline_freeze_manifest.json"
    frozen_paths = [
        parquet, raw_csv, summary_csv, bridge_csv, report, campaign_copy,
        campaign_root / "external_baseline_cells.jsonl", ROOT / "baselines/BASELINE_REGISTRY.md",
        *(ROOT / "baselines/configs" / name for name in (
            "campaign.yaml", "qiskit_local.yaml", "tket_paulisimp.yaml",
            "pyzx_full_reduce.yaml", "authors_reference.yaml",
        )),
        ROOT / "scripts/run_external_baselines.py", ROOT / "scripts/audit_bridge_loss.py",
    ]
    freeze_manifest(frozen_paths, campaign, freeze_path)
    frozen = json.loads(freeze_path.read_text(encoding="utf-8"))
    for relative, record in frozen["files"].items():
        _verify_artifact({"path": relative, **record})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--campaign-root", type=Path,
        default=ROOT / "data/runs/w5-external-baselines-20260803",
    )
    parser.add_argument(
        "--parquet", type=Path, default=ROOT / "data/frozen/external_baselines.parquet",
    )
    parser.add_argument("--freeze-dir", type=Path, default=ROOT / "data/frozen")
    parser.add_argument("--report", type=Path, default=ROOT / "EXTERNAL_BASELINE_REPORT.md")
    args = parser.parse_args()
    audit(args.campaign_root, args.parquet, args.freeze_dir, args.report)
    print(json.dumps({"parquet": str(args.parquet), "report": str(args.report)}, sort_keys=True))


if __name__ == "__main__":
    main()

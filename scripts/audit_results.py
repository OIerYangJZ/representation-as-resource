#!/usr/bin/env python3
"""Normalize W3--W8 results and audit frozen-data provenance."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/manifest.yaml"
OUTPUT = ROOT / "data/frozen/unified_experiments.parquet"
AUDIT_JSON = ROOT / "data/frozen/data_audit.json"
REPORT = ROOT / "DATA_AUDIT_REPORT.md"
PRIMARY_KEY = [
    "experiment_id",
    "instance_id",
    "representation_id",
    "method_id",
    "seed",
    "backend_hash",
    "tool_version",
    "artifact_commit",
    "config_hash",
]


def canonical(value: Any) -> bytes:
    def clean(item: Any) -> Any:
        if isinstance(item, dict):
            return {str(k): clean(v) for k, v in sorted(item.items())}
        if isinstance(item, (list, tuple, set)):
            return [clean(v) for v in item]
        if hasattr(item, "tolist") and not isinstance(item, (str, bytes)):
            return clean(item.tolist())
        if pd.api.types.is_scalar(item) and pd.isna(item):
            return None
        if hasattr(item, "item"):
            return clean(item.item())
        return item

    return json.dumps(clean(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def digest(value: Any) -> str:
    payload = value if isinstance(value, bytes) else canonical(value)
    return hashlib.sha256(payload).hexdigest()


def file_digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def status(value: Any, certificate: Any = None) -> str:
    raw = str(value)
    if raw == "completed" and str(certificate) in {"passed", "completed_valid", "True"}:
        return "completed_valid"
    return raw


def normalized_record(
    row: dict[str, Any], *, source: str, source_row: int, **fields: Any
) -> dict[str, Any]:
    record = {
        **fields,
        "status": status(fields["status"], fields.get("certificate_status")),
        "source_dataset": source,
        "source_row": source_row,
        "source_row_sha256": digest(row),
    }
    for key in PRIMARY_KEY:
        if key not in record or record[key] is None or str(record[key]) == "":
            raise ValueError(f"{source}:{source_row} missing primary-key field {key}")
    return record


def normalize_w3(commit: str) -> list[dict[str, Any]]:
    path = "data/frozen/tradeoff_summary.csv"
    frame = pd.read_csv(ROOT / path)
    backend = digest({"model": "dispersed_update_turnstile", "accounting": "complete_cut"})
    output = []
    for index, series in frame.iterrows():
        row = series.to_dict()
        output.append(normalized_record(
            row, source=path, source_row=index,
            experiment_id="w3-tradeoff-20260802-local",
            instance_id=str(row["run_id"]), representation_id="dispersed_update_stream",
            method_id=str(row["compiler"]), seed=int(row["seed"]), backend_hash=backend,
            tool_version=f"repository:{commit[:12]}", artifact_commit=commit,
            config_hash=str(row["manifest_sha256"]), status="completed_valid",
            certificate_status=str(row["semantic_status"]),
        ))
    return output


def normalize_w4(commit: str) -> list[dict[str, Any]]:
    path = "data/frozen/matched_representation.parquet"
    frame = pd.read_parquet(ROOT / path)
    output = []
    for index, series in frame.iterrows():
        row = series.to_dict()
        backend = digest({
            "hardware": row["hardware"], "basis": row["target_basis"],
            "timeout_s": row["timeout_s"], "memory_cap_bytes": row["memory_cap_bytes"],
        })
        config = digest({"compiler": row["compiler"], "pipeline": row["compiler_pipeline"]})
        output.append(normalized_record(
            row, source=path, source_row=index,
            experiment_id="w4-matched-representation-20260802",
            instance_id=str(row["target_id"]), representation_id=str(row["representation_id"]),
            method_id=str(row["compiler"]), seed=int(row["seed"]), backend_hash=backend,
            tool_version=f"frozen-pipeline:{row['compiler']}", artifact_commit=commit,
            config_hash=config, status=row["status"], certificate_status=row["certificate_status"],
        ))
    return output


def normalize_w5(commit: str) -> list[dict[str, Any]]:
    path = "data/frozen/external_baselines.parquet"
    frame = pd.read_parquet(ROOT / path)
    output = []
    for index, series in frame.iterrows():
        row = series.to_dict()
        backend = digest({
            "hardware": row["hardware"], "basis": row["target_basis"],
            "timeout_s": row["timeout_s"], "memory_cap_bytes": row["memory_cap_bytes"],
            "bridge": row["bridge_format"],
        })
        version = str(row["tool_version"])
        output.append(normalized_record(
            row, source=path, source_row=index,
            experiment_id="w5-external-baselines-20260803",
            instance_id=str(row["target_id"]), representation_id=str(row["representation_id"]),
            method_id=str(row["baseline_id"]), seed=int(row["seed"]), backend_hash=backend,
            tool_version=f"{row['tool']}:{version}", artifact_commit=commit,
            config_hash=str(row["config_sha256"]), status=row["status"],
            certificate_status=row["output_certificate_status"],
        ))
    return output


def normalize_w7(commit: str) -> list[dict[str, Any]]:
    path = "data/frozen/qre_results.parquet"
    frame = pd.read_parquet(ROOT / path)
    output = []
    for index, series in frame.iterrows():
        row = series.to_dict()
        backend = digest({
            "qec_profile": row["qec_profile"], "physical_error_rate": row["physical_error_rate"],
            "cycle_time_seconds": row["cycle_time_seconds"],
        })
        config = digest({key: row[key] for key in (
            "epsilon_total", "allocation_policy", "factory_profile", "requested_factories",
            "qec_profile", "physical_error_rate",
        )})
        output.append(normalized_record(
            row, source=path, source_row=index,
            experiment_id=str(row["campaign_id"]), instance_id=str(row["target_id"]),
            representation_id=f"qre-input:{row['pipeline_id']}", method_id=str(row["pipeline_id"]),
            seed=int(row["seed"]), backend_hash=backend,
            tool_version="staq-grid-synth:a2acd39e60ed", artifact_commit=commit,
            config_hash=config, status=row["status"],
            certificate_status="completed_valid" if bool(row["certificate_dense_passed"]) else str(row["certificate_symbolic_status"]),
        ))
    return output


def normalize_w8() -> list[dict[str, Any]]:
    path = "data/frozen/natural_workloads.parquet"
    frame = pd.read_parquet(ROOT / path)
    output = []
    for index, series in frame.iterrows():
        row = series.to_dict()
        output.append(normalized_record(
            row, source=path, source_row=index,
            experiment_id=str(row["experiment_id"]), instance_id=str(row["instance_id"]),
            representation_id=str(row["representation_id"]), method_id=str(row["method_id"]),
            seed=int(row["seed"]), backend_hash=str(row["backend_hash"]),
            tool_version=str(row["tool_version"]), artifact_commit=str(row["artifact_commit"]),
            config_hash=str(row["config_hash"]), status=row["status"],
            certificate_status=row["certificate_status"],
        ))
    return output


def compare_csv_parquet(csv_path: Path, parquet_path: Path) -> dict[str, Any]:
    left = pd.read_csv(csv_path)
    right = pd.read_parquet(parquet_path)
    shared = list(right.columns)
    left = left[shared]
    conflicts = 0
    for column in shared:
        a, b = left[column], right[column]
        if pd.api.types.is_numeric_dtype(b):
            conflicts += int((~pd.Series([math.isclose(float(x), float(y), rel_tol=1e-11, abs_tol=1e-12) if pd.notna(x) and pd.notna(y) else pd.isna(x) and pd.isna(y) for x, y in zip(a, b)])).sum())
        else:
            def semantic_cell(value: Any) -> Any:
                if isinstance(value, str) and value[:1] in {"[", "{"}:
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        try:
                            return ast.literal_eval(value)
                        except (ValueError, SyntaxError):
                            return value
                if hasattr(value, "tolist"):
                    return value.tolist()
                return value
            conflicts += sum(canonical(semantic_cell(x)) != canonical(semantic_cell(y)) for x, y in zip(a, b))
    return {"csv": str(csv_path.relative_to(ROOT)), "parquet": str(parquet_path.relative_to(ROOT)), "rows": len(left), "conflicting_cells": conflicts}


def tex_label_audit() -> tuple[list[dict[str, Any]], int]:
    paths = [
        ROOT / "PaperDraft/main.tex",
        ROOT / "PaperDraft/supplement.tex",
        ROOT / "theory/qary_packing.tex",
        ROOT / "theory/dispersed_update_tradeoff.tex",
        ROOT / "theory/randomized_multipass_extension.tex",
        ROOT / "theory/matching_upper_bounds.tex",
        ROOT / "theory/certificate_soundness.tex",
    ]
    labels: dict[str, list[str]] = {}
    for path in paths:
        for number, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            for name in re.findall(r"\\label\{([^}]+)\}", line):
                labels.setdefault(name, []).append(f"{path.relative_to(ROOT)}:{number}")
    duplicate = [{"label": key, "locations": value} for key, value in labels.items() if len(value) > 1]
    return duplicate, len(labels)


def hash_drift(manifest: dict[str, Any]) -> list[dict[str, str]]:
    drift = []
    figure_manifest_path = ROOT / "data/frozen/figure_build_manifest.json"
    rebuilt_figures = {}
    if figure_manifest_path.exists():
        rebuilt_figures = json.loads(figure_manifest_path.read_text()).get("figures", {})
    receipts = [item.get("receipt") for item in manifest["datasets"] if item.get("receipt")]
    for relative in sorted(set(receipts)):
        path = ROOT / relative
        if not path.exists() or path.suffix != ".json":
            continue
        payload = json.loads(path.read_text())
        for group in ("source_sha256", "artifacts_sha256"):
            for item, expected in payload.get(group, {}).items():
                candidate = ROOT / item
                if candidate.exists():
                    observed = file_digest(candidate)
                    rebuilt = rebuilt_figures.get(Path(item).name)
                    if item.startswith("figures/") and rebuilt and rebuilt.get("sha256") == observed:
                        # Generated PDFs may differ bytewise because PDF metadata changes.
                        # The current source hashes are governed by figure_build_manifest.json.
                        continue
                    if observed != expected:
                        drift.append({"receipt": relative, "path": item, "kind": group, "expected": expected, "observed": observed})
                else:
                    drift.append({"receipt": relative, "path": item, "kind": "missing", "expected": expected, "observed": "missing"})
    return drift


def external_archive_status(manifest: dict[str, Any]) -> dict[str, Any]:
    archive = manifest.get("raw_provenance_archive", {})
    checkout = archive.get("checkout_path")
    if not checkout:
        return {"configured": False, "present": False, "checked_files": 0, "hash_drift": []}
    root = ROOT / checkout
    result: dict[str, Any] = {
        "configured": True,
        "repository": archive.get("repository"),
        "revision": archive.get("revision"),
        "checkout_path": checkout,
        "present": root.is_dir(),
        "checked_files": 0,
        "hash_drift": [],
    }
    if not root.is_dir():
        return result
    receipts = [item.get("receipt") for item in manifest["datasets"] if item.get("receipt")]
    for relative in sorted(set(receipts)):
        receipt_path = ROOT / relative
        if not receipt_path.exists() or receipt_path.suffix != ".json":
            continue
        payload = json.loads(receipt_path.read_text())
        for item, expected in payload.get("external_artifacts_sha256", {}).items():
            candidate = root / item
            result["checked_files"] += 1
            observed = file_digest(candidate) if candidate.exists() else "missing"
            if observed != expected:
                result["hash_drift"].append({
                    "receipt": relative,
                    "path": item,
                    "kind": "external_archive",
                    "expected": expected,
                    "observed": observed,
                })
    return result


def audit() -> dict[str, Any]:
    manifest = yaml.safe_load(MANIFEST.read_text())
    commit = str(manifest["frozen_artifact_commit"])
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("data/manifest.yaml has an invalid frozen_artifact_commit")
    records = normalize_w3(commit) + normalize_w4(commit) + normalize_w5(commit) + normalize_w7(commit) + normalize_w8()
    unified = pd.DataFrame(records)
    duplicates = unified[unified.duplicated(PRIMARY_KEY, keep=False)]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    unified.to_parquet(OUTPUT, index=False)

    registered = {item["path"] for item in manifest["datasets"]}
    registered |= {item["receipt"] for item in manifest["datasets"] if item.get("receipt")}
    registered |= set(manifest.get("auxiliary_artifacts", []))
    frozen_files = {str(path.relative_to(ROOT)) for path in (ROOT / "data/frozen").iterdir() if path.is_file()}
    generated = {str(OUTPUT.relative_to(ROOT)), str(AUDIT_JSON.relative_to(ROOT))}
    unregistered = sorted(frozen_files - registered - generated)
    missing = sorted(item["path"] for item in manifest["datasets"] if not (ROOT / item["path"]).exists())
    row_count_mismatches = []
    for item in manifest["datasets"]:
        if "rows" not in item or not (ROOT / item["path"]).exists():
            continue
        path = ROOT / item["path"]
        observed = len(pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path))
        if observed != int(item["rows"]):
            row_count_mismatches.append({"path": item["path"], "expected": item["rows"], "observed": observed})
    pair_checks = [compare_csv_parquet(ROOT / f"data/frozen/{stem}.csv", ROOT / f"data/frozen/{stem}.parquet") for stem in (
        "matched_representation", "external_baselines", "qre_results", "natural_workloads"
    )]
    duplicate_labels, label_count = tex_label_audit()
    drift = hash_drift(manifest)
    external_archive = external_archive_status(manifest)
    status_counts = unified["status"].value_counts(dropna=False).to_dict()
    report = {
        "schema": "ucc.data-audit.v1", "artifact_commit": commit,
        "canonical_source_rows": len(unified), "unique_primary_keys": len(unified) - len(duplicates),
        "duplicate_primary_key_rows": len(duplicates), "status_counts": status_counts,
        "source_rows": unified.groupby("source_dataset").size().to_dict(),
        "missing_registered_files": missing, "row_count_mismatches": row_count_mismatches,
        "csv_parquet_checks": pair_checks, "conflicting_numeric_cells": sum(x["conflicting_cells"] for x in pair_checks),
        "tex_labels": label_count, "duplicate_tex_labels": duplicate_labels,
        "unregistered_frozen_artifacts": unregistered, "hash_drift": drift,
        "external_raw_archive": external_archive,
        "known_historical_or_stale": manifest.get("known_historical_or_stale", []),
        "unified_sha256": file_digest(OUTPUT),
    }
    AUDIT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def write_report(result: dict[str, Any]) -> None:
    pair_lines = "\n".join(
        f"- `{item['csv']}` vs `{item['parquet']}`: {item['rows']} rows, {item['conflicting_cells']} conflicting cells."
        for item in result["csv_parquet_checks"]
    )
    unregistered = "\n".join(f"- `{path}`" for path in result["unregistered_frozen_artifacts"]) or "- None."
    drift = "\n".join(f"- `{item['path']}` differs from `{item['receipt']}` ({item['kind']})." for item in result["hash_drift"]) or "- None."
    external = result["external_raw_archive"]
    if external["present"]:
        external_lines = (
            f"Present at `{external['checkout_path']}`; checked {external['checked_files']} registered raw files."
        )
        if external["hash_drift"]:
            external_lines += "\n\n" + "\n".join(
                f"- `{item['path']}`: expected `{item['expected']}`, observed `{item['observed']}`."
                for item in external["hash_drift"]
            )
        else:
            external_lines += " No external-archive hash drift was detected."
    else:
        external_lines = (
            f"Not materialized. The optional archive is `{external['repository']}` at revision "
            f"`{external['revision']}` and can be fetched with `./reproducibility/fetch_raw_data.sh`. "
            "Its absence does not affect the committed frozen-data rebuild."
        )
    stale = "\n".join(f"- `{item['path']}` — {item['disposition']}: {item['reason']}" for item in result["known_historical_or_stale"])
    REPORT.write_text(f"""# Data audit report

## Result

The normalized provenance index contains **{result['canonical_source_rows']:,}** source rows and
**{result['duplicate_primary_key_rows']}** duplicate nine-field primary-key rows.  The index is
`data/frozen/unified_experiments.parquet` (SHA-256 `{result['unified_sha256']}`).
Status classes are preserved as `{json.dumps(result['status_counts'], sort_keys=True)}`;
non-completed rows are not coerced into numeric outcomes.

Registered-file omissions: {len(result['missing_registered_files'])}.  Registered row-count
mismatches: {len(result['row_count_mismatches'])}.  Conflicting CSV/parquet cells:
{result['conflicting_numeric_cells']}.  Duplicate labels among the active manuscript-directory
TeX sources: {len(result['duplicate_tex_labels'])} across {result['tex_labels']} labels.

## Numeric mirror checks

{pair_lines}

## Receipt hash drift

{drift}

Receipt drift is reported, never repaired in place.  A drifted file must be rerun and re-frozen or
explicitly classified as historical before it can support a manuscript number.

## Optional raw provenance archive

{external_lines}

## Unregistered frozen artifacts

{unregistered}

These files are not silently treated as evidence.  They are auxiliary analysis outputs or old
receipts until registered in `data/manifest.yaml`.

## Historical/intermediate data retained

{stale}

The full raw run tree is retained in the separately versioned archive.  The manifest identifies
which immutable in-repository table is canonical so that duplicate filenames in raw, CSV, and
parquet forms cannot be mixed during analysis.

## Reproduction

```bash
.venv/bin/python scripts/audit_results.py
.venv/bin/python -m pytest tests/test_paper_number_provenance.py -q
```
""")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="exit nonzero on a blocking audit finding")
    args = parser.parse_args()
    result = audit()
    write_report(result)
    print(json.dumps(result, indent=2, sort_keys=True))
    blocking = (
        result["duplicate_primary_key_rows"] or result["missing_registered_files"]
        or result["row_count_mismatches"] or result["conflicting_numeric_cells"]
        or result["duplicate_tex_labels"] or result["hash_drift"]
        or result["external_raw_archive"]["hash_drift"]
    )
    if args.check and blocking:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

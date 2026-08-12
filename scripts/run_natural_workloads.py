#!/usr/bin/env python3
"""Run the W8 natural-workload authors/external matched baseline campaign."""

from __future__ import annotations

import argparse
import importlib.metadata
import itertools
import json
import os
import platform
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workloads.natural import (  # noqa: E402
    FACTORS,
    QREContext,
    backend_hash,
    build_result_row,
    canonical_json,
    compile_authors,
    compile_external_tket,
    configuration_hash,
    dense_certificate,
    generate_instance,
    git_revision,
    load_yaml,
    raw_reference,
    row_id,
    sha256_bytes,
    sha256_path,
)


SCHEMA = "ucc.natural-workload-results.v1"
DEFAULT_OUTPUT = ROOT / "data/runs/w8-natural-20260803-local"


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unavailable"


def iter_instances(manifest: Mapping[str, Any]) -> Iterable[Any]:
    families = [item["id"] for item in manifest["families"]]
    for family, scale, seed, density, topology in itertools.product(
        families,
        manifest["scales"],
        manifest["seeds"],
        manifest["densities"],
        manifest["hardware_topologies"],
    ):
        yield generate_instance(family, scale, seed, float(density), topology)


def failure_row(
    instance: Any,
    method_id: str,
    config_hash: str,
    exc: Exception,
    factors: Mapping[str, int] | None,
) -> dict[str, Any]:
    return {
        "experiment_id": "w8-natural-factorial-20260803-local",
        "instance_id": instance.instance_id,
        "representation_id": instance.representation_id,
        "method_id": method_id,
        "seed": instance.seed,
        "backend_hash": backend_hash(instance.topology),
        "tool_version": "repository" if method_id.startswith("authors") else "pytket-runtime",
        "artifact_commit": git_revision(),
        "config_hash": config_hash,
        "row_id": row_id(instance, method_id, config_hash),
        "workload": instance.family,
        "workload_class": instance.workload_class,
        "scale": instance.scale,
        "density": instance.density,
        "hardware_topology": instance.topology,
        "status": "error",
        "certificate_status": "error",
        "qre_status": "unsupported",
        "error": f"{type(exc).__name__}: {exc}",
        "traceback": traceback.format_exc(limit=12),
        **{
            factor: None if factors is None else int(factors[factor])
            for factor in FACTORS
        },
    }


def run(output_dir: Path) -> dict[str, Any]:
    manifest_path = ROOT / "workloads/manifest.yaml"
    ablation_path = ROOT / "configs/ablation_matrix.yaml"
    manifest = load_yaml(manifest_path)
    ablation = load_yaml(ablation_path)
    factors = {name: int(ablation["default_all_on"][name]) for name in FACTORS}
    output_dir.mkdir(parents=True, exist_ok=True)
    output_root = output_dir / "outputs"
    qre = QREContext(float(manifest["epsilon_total"]), int(manifest["qre_factories"]))
    rows: list[dict[str, Any]] = []
    started_campaign = time.perf_counter()
    for instance in iter_instances(manifest):
        reference = raw_reference(instance)
        methods = (
            (
                "authors_all_on",
                lambda instance=instance: compile_authors(instance, factors),
                factors,
            ),
            (
                "external_tket_paulisimp",
                lambda instance=instance: compile_external_tket(instance),
                None,
            ),
        )
        for method_id, compiler, method_factors in methods:
            config_hash = configuration_hash(method_id, method_factors)
            try:
                circuit, compiler_record = compiler()
                certificate = dense_certificate(reference, circuit)
                qre_record = (
                    qre.measure(circuit)
                    if certificate["status"] == "completed_valid"
                    else {"qre_status": "unsupported"}
                )
                rows.append(
                    build_result_row(
                        instance,
                        method_id,
                        circuit,
                        compiler_record,
                        certificate,
                        qre_record,
                        config_hash,
                        output_root,
                        method_factors,
                    )
                )
            except Exception as exc:
                rows.append(failure_row(instance, method_id, config_hash, exc, method_factors))
    rows.sort(key=lambda row: (row["instance_id"], row["method_id"]))
    jsonl_path = output_dir / "natural_baselines.jsonl"
    jsonl_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    parquet_path = output_dir / "natural_baselines.parquet"
    pd.DataFrame(rows).to_parquet(parquet_path, index=False)
    result_manifest = {
        "schema": "ucc.natural-workload-run-manifest.v1",
        "campaign_id": manifest["campaign_id"],
        "runner": os.path.relpath(Path(__file__).resolve(), ROOT),
        "runner_sha256": sha256_path(Path(__file__).resolve()),
        "workload_manifest_sha256": sha256_path(manifest_path),
        "ablation_manifest_sha256": sha256_path(ablation_path),
        "artifact_commit": git_revision(),
        "host": platform.node(),
        "python": platform.python_version(),
        "packages": {
            name: package_version(name)
            for name in ("qiskit", "ucc", "pytket", "numpy", "pandas", "pyarrow")
        },
        "base_instances": len(rows) // 2,
        "rows": len(rows),
        "status_counts": pd.Series([row["status"] for row in rows]).value_counts().to_dict(),
        "elapsed_s": time.perf_counter() - started_campaign,
        "checked_grid_synth_angle_precision_pairs": len(qre.grid.records),
        "artifacts_sha256": {
            os.path.relpath(jsonl_path, ROOT): sha256_path(jsonl_path),
            os.path.relpath(parquet_path, ROOT): sha256_path(parquet_path),
        },
        "configuration_sha256": sha256_bytes(
            canonical_json({"manifest": manifest, "ablation": ablation, "factors": factors})
        ),
    }
    manifest_output = output_dir / "natural_baseline_manifest.json"
    manifest_output.write_text(
        json.dumps(result_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "rows": len(rows),
        "base_instances": len(rows) // 2,
        "status_counts": result_manifest["status_counts"],
        "grid_synth_pairs": len(qre.grid.records),
        "output": str(parquet_path),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run(args.output_dir.resolve())
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status_counts"] == {"completed_valid": summary["rows"]} else 1


if __name__ == "__main__":
    raise SystemExit(main())

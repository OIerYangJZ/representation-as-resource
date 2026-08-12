#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


THIS_FILE = Path(__file__).resolve()
OUTPUT_DIR = THIS_FILE.parent

REQUIRED_FIELDS = (
    "experiment_family",
    "instance_name",
    "n",
    "size",
    "r",
    "method_key",
    "paper_method_name",
    "timeout_s",
    "status",
    "wall_time_s",
    "gate_count",
    "depth",
    "cx_count",
    "rz_rotation_count",
    "notes",
    "source_command_or_script",
)
VALID_STATUSES = {"completed", "timeout", "error", "unavailable"}


def result_files(output_dir: Path) -> list[Path]:
    files = []
    for pattern in ("round3_*_results.json", "smoke_round3_*_results.json"):
        files.extend(sorted(output_dir.glob(pattern)))
    return sorted(set(files))


def validate_rows(path: Path, payload: Any) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(payload, list):
        return [f"{path.name}: top-level JSON is {type(payload).__name__}, expected list"], warnings
    for idx, row in enumerate(payload):
        label = f"{path.name}[{idx}]"
        if not isinstance(row, dict):
            errors.append(f"{label}: row is {type(row).__name__}, expected object")
            continue
        missing = [field for field in REQUIRED_FIELDS if field not in row]
        if missing:
            errors.append(f"{label}: missing required fields: {', '.join(missing)}")
        status = row.get("status")
        if status not in VALID_STATUSES:
            errors.append(f"{label}: malformed status {status!r}")
        timeout_s = row.get("timeout_s")
        if not isinstance(timeout_s, int) or timeout_s <= 0:
            errors.append(f"{label}: timeout_s must be a positive integer")
        if status == "completed":
            for metric in ("gate_count", "depth"):
                if not isinstance(row.get(metric), int):
                    errors.append(f"{label}: completed row has malformed {metric}")
            for optional_metric in ("cx_count", "rz_rotation_count"):
                value = row.get(optional_metric)
                if value is not None and not isinstance(value, int):
                    errors.append(f"{label}: malformed {optional_metric}")
        else:
            if row.get("gate_count") is not None or row.get("depth") is not None:
                warnings.append(f"{label}: non-completed row contains structural metrics")
        if not row.get("source_command_or_script"):
            errors.append(f"{label}: source_command_or_script is empty")
    return errors, warnings


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Round 3 repair JSON outputs.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()

    files = result_files(args.output_dir)
    if not files:
        print(f"No Round 3 result JSON files found in {args.output_dir}")
        raise SystemExit(1)

    any_errors = False
    for path in files:
        print(f"## {path.name}")
        try:
            payload = json.loads(path.read_text())
            print("- valid JSON: yes")
        except Exception as exc:
            print("- valid JSON: no")
            print(f"- invalid JSON error: {type(exc).__name__}: {exc}")
            any_errors = True
            continue

        rows = payload if isinstance(payload, list) else []
        methods = sorted({str(row.get("method_key")) for row in rows if isinstance(row, dict)})
        budgets = sorted({row.get("timeout_s") for row in rows if isinstance(row, dict)})
        print(f"- number of rows: {len(rows)}")
        print(f"- methods present: {', '.join(methods) if methods else '-'}")
        print(f"- timeout budgets present: {', '.join(str(b) for b in budgets) if budgets else '-'}")

        errors, warnings = validate_rows(path, payload)
        if errors:
            any_errors = True
            print("- malformed rows:")
            for error in errors:
                print(f"  - {error}")
        else:
            print("- malformed rows: none")
        if warnings:
            print("- warnings:")
            for warning in warnings:
                print(f"  - {warning}")
        print()

    raise SystemExit(1 if any_errors else 0)


if __name__ == "__main__":
    main()

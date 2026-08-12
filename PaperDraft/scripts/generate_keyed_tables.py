#!/usr/bin/env python3
"""Validate the full experiment key and generate the three hardware tables."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


PRIMARY_FIELDS = (
    "experiment",
    "instance",
    "representation",
    "method",
    "seed",
    "backend_hash",
    "tool_version",
    "config_hash",
)


def canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def tex_escape(value: str) -> str:
    return value.replace("_", r"\_")


def load_rows(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "ucc.experiment-registry.v1":
        raise ValueError("unexpected registry schema")
    backend_hash = canonical_hash(payload["backend"])
    expanded = []
    for source in payload["rows"]:
        campaign = payload["campaigns"][source["campaign"]]
        row = dict(source)
        row.update(
            experiment=campaign["experiment"],
            seed=campaign["seed"],
            backend_hash=backend_hash,
            config_hash=canonical_hash(campaign["config"]),
            runner=campaign["runner"],
        )
        row["primary_key"] = [row[field] for field in PRIMARY_FIELDS]
        row["reader_label"] = (
            f"{source['campaign']}-{source['instance'].replace('hw_mqt_', '').replace('_20', '')}"
            f"-s{row['seed']}-c{row['config_hash'][:8]}"
        )
        expanded.append(row)
    keys = [tuple(row["primary_key"]) for row in expanded]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate full primary key")
    return payload, expanded


def method_name(method: str) -> str:
    names = {
        "baseline_ucc": "baseline UCC",
        "semantic_ucc": "semantic UCC",
        "qiskit_opt3": r"\texttt{qiskit opt3}",
        "defaults_preinverse_only": r"\texttt{defaults\_preinverse\_only}",
        "defaults_reordered_only": r"\texttt{defaults\_reordered\_only}",
        "defaults_minimal_bundle": r"\texttt{defaults\_minimal\_bundle}",
    }
    return names[method]


def format_row(row: dict) -> str:
    return (
        f"  & {method_name(row['method'])} & {row['gates']:,} & {row['depth']:,} "
        f"& {row['cx']:,} & {row['runtime_s']:.3f} s \\\\"
    ).replace(",", r"{,}")


def write_reorder(rows: list[dict], path: Path) -> None:
    selected = [row for row in rows if row["campaign"] == "RP23"]
    blocks = []
    for instance in ("hw_mqt_qpeexact_20", "hw_mqt_qaoa_20"):
        local = [row for row in selected if row["instance"] == instance]
        label = tex_escape(local[0]["reader_label"])
        label_head, label_tail = label.rsplit("-s", 1)
        prefix = (
            rf"\multirow{{6}}{{*}}{{\shortstack{{\texttt{{{label_head}}}"
            rf"\\\texttt{{s{label_tail}}}}}}}"
        )
        lines = [prefix + format_row(local[0])]
        lines.extend(format_row(row) for row in local[1:])
        blocks.append("\n".join(lines))
    content = "\n\\midrule\n".join(blocks)
    row_terminator = " \\\\"
    if not content.endswith(row_terminator):
        raise AssertionError("generated reorder fragment has no final row terminator")
    # The parent closes the final row after \input.  This keeps LaTeX's
    # end-of-input hook inside that cell and avoids a spurious empty row before
    # the following \bottomrule.
    path.write_text(content[: -len(row_terminator)] + "\n", encoding="utf-8")


def write_hardware(rows: list[dict], instance: str, path: Path) -> None:
    order = {"qiskit_opt3": 0, "baseline_ucc": 1, "semantic_ucc": 2}
    local = sorted(
        (row for row in rows if row["campaign"] == "HW24" and row["instance"] == instance),
        key=lambda row: order[row["method"]],
    )
    content = "\n".join(format_row(row).lstrip("  & ") for row in local)
    row_terminator = " \\\\"
    if not content.endswith(row_terminator):
        raise AssertionError("generated hardware fragment has no final row terminator")
    path.write_text(content[: -len(row_terminator)] + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    payload, rows = load_rows(args.registry)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_reorder(rows, args.output_dir / "reorder_probe_rows.tex")
    write_hardware(rows, "hw_mqt_qpeexact_20", args.output_dir / "hardware_qpe_rows.tex")
    write_hardware(rows, "hw_mqt_qaoa_20", args.output_dir / "hardware_qaoa_rows.tex")
    expanded_path = args.output_dir / "expanded_primary_keys.json"
    expanded_path.write_text(
        json.dumps(
            {
                "schema": payload["schema"],
                "primary_key_fields": list(PRIMARY_FIELDS),
                "rows": rows,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "rows": len(rows),
                "unique_primary_keys": len(rows),
                "backend_hash": rows[0]["backend_hash"],
                "campaign_config_hashes": {
                    campaign: next(row["config_hash"] for row in rows if row["campaign"] == campaign)
                    for campaign in sorted(payload["campaigns"])
                },
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

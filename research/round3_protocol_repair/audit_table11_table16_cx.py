#!/usr/bin/env python3
"""Audit Table 11/Table 16 CX counts for phase_estimation_real rows."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
MAIN_TEX = ROOT / "PaperDraft" / "ucc_paper_draft_latex.tex"
APPENDIX_C_TEX = ROOT / "PaperDraft" / "appendix" / "appendix_C.tex"
OUTPUT_JSON = ROOT / "research" / "round3_protocol_repair" / "table11_table16_cx_audit.json"
OUTPUT_MD = ROOT / "research" / "round3_protocol_repair" / "table11_table16_cx_audit.md"

SOURCE_JSONS = [
    ROOT / "research" / "real_instance_results.json",
    ROOT / "Graph Materials" / "baseline vs optimized vs qiskit opt3" / "real_instance_results.json",
]

SOURCE_MDS = [
    ROOT / "research" / "real_instance_results.md",
    ROOT / "research" / "real_instance_results_summary.md",
    ROOT / "Graph Materials" / "baseline vs optimized vs qiskit opt3" / "real_instance_results_summary.md",
    ROOT / "research" / "round3_protocol_repair" / "round3_table_provenance_map.md",
    ROOT
    / "research"
    / "round3_protocol_repair"
    / "ssh_full_run_20260706_165733"
    / "round3_table_provenance_map.md",
]

METHOD_KEY_BY_PAPER_NAME = {
    "translation only": "translation_only",
    "qiskit opt3": "qiskit_opt3",
    "upstream UCC v0.4.12 pre-semantic default": "baseline_ucc",
    "baseline UCC": "baseline_ucc",
    "semantic UCC": "optimized_ucc",
    "defaults_preinverse_only": "defaults_preinverse_only",
    "defaults_reordered_only": "defaults_reordered_only",
    "defaults_minimal_bundle": "defaults_minimal_bundle",
}

PAPER_NAME_BY_METHOD_KEY = {
    "translation_only": "translation only",
    "qiskit_opt3": "qiskit opt3",
    "baseline_ucc": "upstream UCC v0.4.12 pre-semantic default",
    "optimized_ucc": "semantic UCC",
    "defaults_preinverse_only": "defaults_preinverse_only",
    "defaults_reordered_only": "defaults_reordered_only",
    "defaults_minimal_bundle": "defaults_minimal_bundle",
}

FIELDS_USED = [
    "output.total_gates",
    "output.depth",
    "output.cx_count",
    "output.multi_qubit_gates",
    "runtime_s",
]


def rel(path: Path | None) -> str | None:
    if path is None:
        return None
    return str(path.relative_to(ROOT))


def parse_int(value: str) -> int:
    text = re.sub(r"[^0-9-]", "", value)
    if not text:
        raise ValueError(f"cannot parse int from {value!r}")
    return int(text)


def parse_runtime(value: str) -> float | None:
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", value)
    if not match:
        return None
    return float(match.group(1))


def strip_latex(cell: str) -> str:
    text = cell.strip()
    text = re.sub(r"\\begin\{tabular\}(?:\[[^]]*\])?", "", text)
    text = text.replace("{@{}c@{}}", "")
    text = text.replace(r"\end{tabular}", "")
    text = re.sub(r"\\texttt\{([^{}]*)\}", r"\1", text)
    text = text.replace(r"\_", "_")
    text = text.replace(r"\\", " ")
    text = re.sub(r"[{}]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_table_environment(tex: str, label: str) -> str:
    label_pos = tex.index(label)
    begin_pos = tex.rfind(r"\begin{table", 0, label_pos)
    if begin_pos < 0:
        raise ValueError(f"could not find table environment for {label}")
    end_match = re.search(r"\\end\{table\*?\}", tex[label_pos:])
    if not end_match:
        raise ValueError(f"could not find table end for {label}")
    return tex[begin_pos : label_pos + end_match.end()]


def extract_phase_rows(table_text: str, table_name: str) -> list[dict[str, Any]]:
    phase_marker = r"\multirow"
    phase_pos = table_text.index(phase_marker)
    phase_text = table_text[phase_pos:]
    lines: list[str] = []
    seen_data = False
    for raw_line in phase_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if not seen_data:
            if r"\texttt{phase\_estimation\_real}" not in line:
                continue
            seen_data = True
        elif line.startswith(r"\midrule") or line.startswith(r"\bottomrule"):
            break
        if "&" in line and r"\\" in line:
            lines.append(line)

    rows: list[dict[str, Any]] = []
    for index, line in enumerate(lines, start=1):
        parts = [part.strip() for part in line.rsplit(r"\\", 1)[0].split("&")]
        if len(parts) < 6:
            raise ValueError(f"{table_name}: cannot parse row: {line}")
        method_cell = strip_latex(parts[1])
        method_key = METHOD_KEY_BY_PAPER_NAME.get(method_cell)
        if method_key is None:
            raise ValueError(f"{table_name}: unknown method cell {method_cell!r}")
        rows.append(
            {
                "table": table_name,
                "instance": "phase_estimation_real",
                "row_index_in_phase_block": index,
                "method_key": method_key,
                "paper_method_name": method_cell,
                "gate_count": parse_int(parts[2]),
                "depth": parse_int(parts[3]),
                "cx_count": parse_int(parts[4]),
                "runtime_s": parse_runtime(parts[5]),
                "tex_row": strip_latex(line),
            }
        )
    return rows


def selected_flag(row: dict[str, Any]) -> tuple[bool, Any]:
    for key in ("selected", "selected_candidate", "is_selected", "winner"):
        if key in row:
            return True, row[key]
    return False, None


def load_source_rows() -> dict[str, list[dict[str, Any]]]:
    source_rows: dict[str, list[dict[str, Any]]] = {}
    for path in SOURCE_JSONS:
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        phase_rows = data.get("phase_estimation_real", {})
        for method_key, row in phase_rows.items():
            output = row.get("output") or {}
            flag_present, flag = selected_flag(row)
            source_rows.setdefault(method_key, []).append(
                {
                    "method_key": method_key,
                    "paper_method_name": PAPER_NAME_BY_METHOD_KEY.get(method_key, method_key),
                    "gate_count": output.get("total_gates"),
                    "depth": output.get("depth"),
                    "cx_count": output.get("cx_count"),
                    "two_qubit_count": output.get("multi_qubit_gates"),
                    "runtime_s": row.get("runtime_s"),
                    "selected_candidate_flag_present": flag_present,
                    "selected_candidate": flag,
                    "source_json_path": rel(path),
                    "source_field_names_used": FIELDS_USED,
                    "status": row.get("status"),
                }
            )
    return source_rows


def runtime_matches(a: float | None, b: float | None) -> bool:
    if a is None or b is None:
        return False
    return abs(a - b) < 0.001


def find_source_match(row: dict[str, Any], source_rows: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    candidates = source_rows.get(row["method_key"], [])
    shape_matches = [
        candidate
        for candidate in candidates
        if candidate["gate_count"] == row["gate_count"] and candidate["depth"] == row["depth"]
    ]
    if not candidates:
        return {
            "match_status": "no_json_source_for_method",
            "source_json_path": None,
            "source_field_names_used": [],
        }
    if not shape_matches:
        return {
            "match_status": "method_present_but_gate_depth_do_not_match",
            "candidate_sources": candidates,
        }
    exact_runtime = [
        candidate
        for candidate in shape_matches
        if runtime_matches(row.get("runtime_s"), candidate.get("runtime_s"))
    ]
    selected = exact_runtime[0] if exact_runtime else shape_matches[0]
    return {
        "match_status": "matched_json_row",
        **selected,
        "runtime_match": bool(exact_runtime),
    }


def annotate_rows(rows: list[dict[str, Any]], source_rows: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    annotated = []
    for row in rows:
        source = find_source_match(row, source_rows)
        annotated.append(
            {
                **row,
                "selected_candidate_flag_present": source.get("selected_candidate_flag_present", False),
                "selected_candidate": source.get("selected_candidate"),
                "source_json_path": source.get("source_json_path"),
                "source_field_names_used": source.get("source_field_names_used", []),
                "source_match": source,
                "matches_source_cx": (
                    source.get("match_status") == "matched_json_row"
                    and row["cx_count"] == source.get("cx_count")
                ),
            }
        )
    return annotated


def compare_tables(table11: list[dict[str, Any]], table16: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_method_11 = {row["method_key"]: row for row in table11}
    by_method_16 = {row["method_key"]: row for row in table16}
    comparisons = []
    for method_key in sorted(set(by_method_11) & set(by_method_16)):
        row11 = by_method_11[method_key]
        row16 = by_method_16[method_key]
        same_gate_depth = row11["gate_count"] == row16["gate_count"] and row11["depth"] == row16["depth"]
        same_cx = row11["cx_count"] == row16["cx_count"]
        inconsistent_table = []
        if same_gate_depth and not same_cx:
            if row11.get("matches_source_cx") and not row16.get("matches_source_cx"):
                inconsistent_table.append("Appendix C Table 16")
            if row16.get("matches_source_cx") and not row11.get("matches_source_cx"):
                inconsistent_table.append("Table 11")
        comparisons.append(
            {
                "method_key": method_key,
                "paper_method_name": PAPER_NAME_BY_METHOD_KEY.get(method_key, method_key),
                "same_gate_depth": same_gate_depth,
                "same_cx": same_cx,
                "table11": {
                    "gate_count": row11["gate_count"],
                    "depth": row11["depth"],
                    "cx_count": row11["cx_count"],
                    "source_json_path": row11.get("source_json_path"),
                    "matches_source_cx": row11.get("matches_source_cx"),
                },
                "table16": {
                    "gate_count": row16["gate_count"],
                    "depth": row16["depth"],
                    "cx_count": row16["cx_count"],
                    "source_json_path": row16.get("source_json_path"),
                    "matches_source_cx": row16.get("matches_source_cx"),
                },
                "inconsistent_table": inconsistent_table,
            }
        )
    return comparisons


def kappa(gates: int, depth: int, multi_qubit: int) -> int:
    return gates + depth + 10 * multi_qubit


def write_md(audit: dict[str, Any]) -> None:
    lines = [
        "# Table 11 / Table 16 CX Audit",
        "",
        f"Generated: `{audit['generated_at']}`",
        "",
        "## Source Files Inspected",
        "",
    ]
    for item in audit["source_files_inspected"]:
        status = "present" if item["exists"] else "missing"
        lines.append(f"- `{item['path']}` ({item['kind']}, {status})")

    lines += [
        "",
        "## Extracted Table Rows",
        "",
        "| Table | Method key | Paper method | Gates | Depth | Table CX | Source CX | Source | Status |",
        "|---|---|---|---:|---:|---:|---:|---|---|",
    ]
    for row in audit["tables"]["table11_phase_estimation_real"] + audit["tables"]["table16_phase_estimation_real"]:
        source = row["source_match"]
        source_cx = source.get("cx_count")
        source_cx_text = "" if source_cx is None else f"{source_cx:,}"
        lines.append(
            "| {table} | `{method_key}` | {paper} | {gates:,} | {depth:,} | {cx:,} | {source_cx} | `{source_path}` | {status} |".format(
                table=row["table"],
                method_key=row["method_key"],
                paper=row["paper_method_name"],
                gates=row["gate_count"],
                depth=row["depth"],
                cx=row["cx_count"],
                source_cx=source_cx_text,
                source_path=row.get("source_json_path") or "",
                status=source.get("match_status"),
            )
        )

    lines += [
        "",
        "## Table 11 vs Table 16 Comparison",
        "",
        "| Method key | Same gates/depth | Table 11 CX | Table 16 CX | Inconsistent table |",
        "|---|---:|---:|---:|---|",
    ]
    for comparison in audit["comparisons"]:
        bad = ", ".join(comparison["inconsistent_table"]) or "none"
        lines.append(
            "| `{method}` | {same_gate_depth} | {cx11:,} | {cx16:,} | {bad} |".format(
                method=comparison["method_key"],
                same_gate_depth=comparison["same_gate_depth"],
                cx11=comparison["table11"]["cx_count"],
                cx16=comparison["table16"]["cx_count"],
                bad=bad,
            )
        )

    lines += [
        "",
        "## Verdict",
        "",
        audit["verdict"],
        "",
        "## Selector kappa Arithmetic",
        "",
        "The selector score is `kappa = gates + depth + 10 * multi_qubit`.",
        "",
        "| Method key | Gates | Depth | Multi-qubit/CX | kappa |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in audit["kappa_phase_estimation_real"]:
        lines.append(
            f"| `{row['method_key']}` | {row['gate_count']:,} | {row['depth']:,} | {row['multi_qubit_count']:,} | {row['kappa']:,} |"
        )

    OUTPUT_MD.write_text("\n".join(lines) + "\n")


def main() -> None:
    source_files = [
        *[{"path": rel(path), "kind": "json", "exists": path.exists()} for path in SOURCE_JSONS],
        *[{"path": rel(path), "kind": "md", "exists": path.exists()} for path in SOURCE_MDS],
        {"path": rel(MAIN_TEX), "kind": "tex", "exists": MAIN_TEX.exists()},
        {"path": rel(APPENDIX_C_TEX), "kind": "tex", "exists": APPENDIX_C_TEX.exists()},
    ]

    source_rows = load_source_rows()
    main_tex = MAIN_TEX.read_text()
    appendix_tex = APPENDIX_C_TEX.read_text()

    table11_env = extract_table_environment(main_tex, r"\label{tab:real-instances}")
    table16_env = extract_table_environment(appendix_tex, r"\label{tab:defaults-vs-full}")
    table11_rows = annotate_rows(extract_phase_rows(table11_env, "Table 11"), source_rows)
    table16_rows = annotate_rows(extract_phase_rows(table16_env, "Appendix C Table 16"), source_rows)
    comparisons = compare_tables(table11_rows, table16_rows)

    inconsistent_tables = sorted(
        {table for comparison in comparisons for table in comparison["inconsistent_table"]}
    )
    if inconsistent_tables:
        verdict = (
            "Appendix C Table 16 is inconsistent with the frozen real-instance JSON for "
            "overlapping phase_estimation_real rows; Table 11 matches the frozen JSON. "
            "No JSON source was found for the defaults_* reorder-probe rows."
        )
    else:
        verdict = (
            "Table 11 and Appendix C Table 16 are consistent for overlapping "
            "phase_estimation_real rows that have frozen JSON sources. No JSON source "
            "was found for the defaults_* reorder-probe rows."
        )

    kappa_rows = []
    for row in table11_rows:
        source = row["source_match"]
        multi_qubit = source.get("two_qubit_count")
        if source.get("match_status") == "matched_json_row" and multi_qubit is not None:
            kappa_rows.append(
                {
                    "method_key": row["method_key"],
                    "paper_method_name": row["paper_method_name"],
                    "gate_count": row["gate_count"],
                    "depth": row["depth"],
                    "multi_qubit_count": multi_qubit,
                    "kappa": kappa(row["gate_count"], row["depth"], multi_qubit),
                    "source_json_path": row["source_json_path"],
                }
            )

    audit = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_files_inspected": source_files,
        "tables": {
            "table11_phase_estimation_real": table11_rows,
            "table16_phase_estimation_real": table16_rows,
        },
        "comparisons": comparisons,
        "inconsistent_tables": inconsistent_tables,
        "verdict": verdict,
        "kappa_formula": "gates + depth + 10 * multi_qubit",
        "kappa_phase_estimation_real": kappa_rows,
    }

    OUTPUT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    write_md(audit)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Cross-check Round 6 certificates, results, frozen inputs, and manuscript."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import re
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FAMILIES = {"rational_cp", "unbounded_independent_pauli"}
METHODS = {
    "semantic_ucc",
    "qiskit_opt3",
    "pyzx_full_reduce",
    "tket_guided_paulisimp",
    "tket_paulisimp_unrebased",
    "tket_paulisimp_rebased",
    "staq_rotation_folding",
}
SIZES = {4000, 10000, 20000, 50000, 100000}
REQUIRED = {
    "family_key",
    "instance_name",
    "requested_gates",
    "actual_input_gates",
    "r",
    "n",
    "m",
    "support_rank_f2",
    "angle_specification",
    "method_key",
    "paper_method_name",
    "timeout_s",
    "status",
    "wall_time_s",
    "gate_count",
    "depth",
    "cx_count",
    "equivalence_checked",
    "equivalent_up_to_global_phase",
    "operator_max_abs_error",
    "log_path",
}

MANUSCRIPT_RELATIVE_PATHS = {
    "main TeX": Path("PaperDraft/ucc_paper_draft_latex.tex"),
    "Appendix A": Path("PaperDraft/appendix/appendix_A.tex"),
    "Appendix B": Path("PaperDraft/appendix/appendix_B.tex"),
    "Appendix C": Path("PaperDraft/appendix/appendix_C.tex"),
}

TARGET_NOUN_FAMILY = r"(?:pipeline|baseline|tool|method|compiler|optimizer)s?"
QUANTIFIED_TARGET_PHRASE = (
    rf"(?:[A-Za-z][A-Za-z-]*\s+){{0,4}}{TARGET_NOUN_FAMILY}"
)

UNIVERSAL_CLAIM_PATTERNS = (
    (
        "none-of recovery",
        re.compile(r"\bnone\s+of\b.{0,120}?\brecover(?:ed|s|ing)?\b", re.IGNORECASE),
    ),
    (
        "no-target recovery",
        re.compile(
            rf"\b(?:no|zero|neither|not\s+a\s+single)\s+"
            rf"{QUANTIFIED_TARGET_PHRASE}\b"
            r".{0,120}?\brecover(?:ed|s|ing)?\b",
            re.IGNORECASE,
        ),
    ),
    (
        "each-target recovery failure",
        re.compile(
            rf"\beach\s+{QUANTIFIED_TARGET_PHRASE}\b.{{0,120}}?"
            r"\b(?:fail(?:ed|s|ing)?|did\s+not|does\s+not)\b"
            r".{0,80}?\brecover(?:ed|s|ing)?\b",
            re.IGNORECASE,
        ),
    ),
    (
        "every-target recovery failure",
        re.compile(
            rf"\bevery\s+{QUANTIFIED_TARGET_PHRASE}\b.{{0,120}}?"
            r"\b(?:fail(?:ed|s|ing)?|did\s+not|does\s+not)\b"
            r".{0,80}?\brecover(?:ed|s|ing)?\b",
            re.IGNORECASE,
        ),
    ),
    (
        "all-target failure",
        re.compile(
            rf"\ball\s+{QUANTIFIED_TARGET_PHRASE}\b.{{0,120}}?"
            r"\b(?:fail(?:ed|s|ing)?|do\s+not|did\s+not)\b"
            r"(?:.{0,80}?\brecover(?:ed|s|ing)?\b)?",
            re.IGNORECASE,
        ),
    ),
    (
        "historical configured-pipeline recovery",
        re.compile(
            r"\b(?:the\s+)?configured\s+pipelines?\s+did\s+not\s+recover\b",
            re.IGNORECASE,
        ),
    ),
    (
        "historical those-tools recovery",
        re.compile(r"\bthose\s+tools\s+did\s+not\s+recover\b", re.IGNORECASE),
    ),
    (
        "historical post-lowering either/or",
        re.compile(
            r"\bpost-lowering\s+baselines?\s+either\b.{0,100}?"
            r"\b(?:grow|time\s+out|timeout)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "all-baseline failure",
        re.compile(
            r"\ball\b.{0,80}?\bbaselines?\b.{0,120}?"
            r"\b(?:fail(?:ed|s|ing)?|did\s+not|do\s+not|grow|time(?:d)?\s+out)\b",
            re.IGNORECASE,
        ),
    ),
)

UNIVERSAL_QUALIFIER_PATTERNS = (
    re.compile(rf"\bmost\s+{QUANTIFIED_TARGET_PHRASE}\b", re.IGNORECASE),
    re.compile(rf"\bnot\s+all\s+{QUANTIFIED_TARGET_PHRASE}\b", re.IGNORECASE),
    re.compile(
        r"\b(?:historical|superseded|quoted)\b.{0,80}"
        r"\b(?:claim|wording|statement|string)\b",
        re.IGNORECASE,
    ),
)

EXCEPTION_CLAUSE_PATTERNS = (
    re.compile(
        r"\bexcept(?:\s+for)?\s+(?P<target>.{1,120}?)"
        r"(?=\s+\b(?:fail(?:ed|s|ing)?|did\s+not|does\s+not|do\s+not|"
        r"recover(?:ed|s|ing)?)\b|[,;.!?]|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bwith\s+the\s+exception\s+of\s+"
        r"(?P<target>.{1,120}?)"
        r"(?=\s+\b(?:fail(?:ed|s|ing)?|did\s+not|does\s+not|do\s+not|"
        r"recover(?:ed|s|ing)?)\b|[,;.!?]|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bexceptions?\s+(?:are|is|being)\s+(?P<target>.{1,120}?)"
        r"(?=[,;.!?]|$)",
        re.IGNORECASE,
    ),
)

EMPTY_OR_NEGATED_EXCEPTION_TARGET = re.compile(
    r"^(?:(?:that|when)\s+)?(?:the\s+)?(?:none|nothing|nobody|no\s+one|"
    r"not\s+(?:one|a\s+single)|no|zero|neither)\b",
    re.IGNORECASE,
)
PROJECT_EXCEPTION_NAME_FAMILY = (
    r"(?:GuidedPauliSimp|PauliSimp|TKET|PyZX|Qiskit|staq|UCC|"
    r"route|configuration|reconstruction)"
)
NAMED_EXCEPTION_TARGET = re.compile(
    rf"\b(?:{TARGET_NOUN_FAMILY}|{PROJECT_EXCEPTION_NAME_FAMILY})\b",
    re.IGNORECASE,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_verifier():
    spec = importlib.util.spec_from_file_location(
        "verify_unbounded_witness", HERE / "verify_unbounded_witness.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def section_text(text: str, start: str, end: str, name: str) -> str:
    """Return a nonempty ordered section or raise with both semantic markers."""
    begin = text.find(start)
    if begin < 0:
        raise ValueError(f"{name}: start marker not found: {start!r}")
    finish = text.find(end, begin + len(start))
    if finish < 0:
        earlier = text.find(end)
        if 0 <= earlier <= begin:
            raise ValueError(
                f"{name}: reversed markers: end {end!r} occurs before start {start!r}"
            )
        raise ValueError(
            f"{name}: end marker not found after start: start={start!r}; end={end!r}"
        )
    body = text[begin + len(start) : finish]
    if finish <= begin or not body.strip():
        raise ValueError(
            f"{name}: empty or reversed range: start={start!r}; end={end!r}"
        )
    return text[begin:finish]


def normalize_reader_tex(text: str) -> str:
    """Remove non-reader TeX regions, comments, and layout-only whitespace."""
    if r"\begin{document}" in text:
        text = text.split(r"\begin{document}", 1)[1]
    for environment in ("verbatim", "verbatim*", "Verbatim", "lstlisting", "comment"):
        text = re.sub(
            rf"\\begin\{{{re.escape(environment)}\}}.*?"
            rf"\\end\{{{re.escape(environment)}\}}",
            " ",
            text,
            flags=re.DOTALL,
        )
    text = re.sub(
        r"\\begin\{minted\}(?:\[[^\]]*\])?\{[^}]*\}.*?\\end\{minted\}",
        " ",
        text,
        flags=re.DOTALL,
    )
    text = re.sub(r"\\verb\*?(?P<delimiter>[^\w\s]).*?(?P=delimiter)", " ", text)
    text = re.sub(r"(?m)(?<!\\)%.*$", " ", text)
    text = re.sub(
        r"(?m)^[ \t]*\\(?:newcommand|renewcommand|providecommand|def|"
        r"DeclareMathOperator|DeclareRobustCommand)\b.*$",
        " ",
        text,
    )
    return re.sub(r"\s+", " ", text).strip()


def reader_sentences(text: str) -> list[str]:
    """Retain sentence- and table-row-local context for reader-facing scans."""
    collapsed = normalize_reader_tex(text)
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+|\\item\s+|\\\\\s*", collapsed)
        if sentence.strip()
    ]


def has_genuine_exception(sentence: str) -> bool:
    """Accept a bounded positive exception from the closed target vocabulary."""
    for pattern in EXCEPTION_CLAUSE_PATTERNS:
        for match in pattern.finditer(sentence):
            target = re.sub(r"\s+", " ", match.group("target")).strip()
            if EMPTY_OR_NEGATED_EXCEPTION_TARGET.search(target):
                continue
            if NAMED_EXCEPTION_TARGET.search(target):
                return True
    return False


def has_universal_claim_qualifier(sentence: str) -> bool:
    """Return true only for bounded meta-language or a named positive exception."""
    return any(
        pattern.search(sentence) for pattern in UNIVERSAL_QUALIFIER_PATTERNS
    ) or has_genuine_exception(sentence)


def load_manuscript_sources(root: Path = ROOT) -> dict[str, str]:
    """Load the four active reader-facing TeX sources by stable logical name."""
    return {
        name: (root / relative).read_text(encoding="utf-8")
        for name, relative in MANUSCRIPT_RELATIVE_PATHS.items()
    }


def check_reader_facing_prose(sources: dict[str, str]) -> tuple[list[str], list[str]]:
    """Catch stale universal claims and ambiguous PauliSimp error language."""
    errors: list[str] = []
    checks: list[str] = []
    main_tex = sources["main TeX"]
    appendix_c = sources["Appendix C"]
    section_specs = {
        "rational-witness results": (
            r"\subsection{Rational CP",
            r"\subsection{Real-Task Panel}",
        ),
        "Discussion": (r"\section{Discussion}", r"\section{Conclusion}"),
        "Scope and Limitations": (
            r"\subsection{Scope and Limitations}",
            r"\section{Conclusion}",
        ),
        "Conclusion": (r"\section{Conclusion}", r"\section*{Reproducibility}"),
    }
    sections: dict[str, str] = {}
    for name, (start, end) in section_specs.items():
        try:
            sections[name] = section_text(main_tex, start, end, name)
        except ValueError as exc:
            errors.append(f"reader-facing section boundary error: {exc}")
            sections[name] = ""

    for source_name, text in sources.items():
        for sentence in reader_sentences(text):
            for family_name, pattern in UNIVERSAL_CLAIM_PATTERNS:
                if pattern.search(sentence) and not has_universal_claim_qualifier(sentence):
                    errors.append(
                        f"unqualified universal baseline claim ({family_name}) in "
                        f"{source_name}: {sentence[:220]}"
                    )
                    break
    checks.append(
        "scanned main TeX and Appendices A/B/C for bounded semantic families of "
        "universal baseline claims"
    )

    for source_name, text in sources.items():
        for sentence in reader_sentences(text):
            if not re.search(r"PauliSimp", sentence, re.IGNORECASE):
                continue
            if not re.search(
                r"predicate(?!-correct)|error|failure", sentence, re.IGNORECASE
            ):
                continue
            if not re.search(
                r"unrebased(?:\s+configuration)?", sentence, re.IGNORECASE
            ):
                errors.append(
                    f"ambiguous PauliSimp predicate/error sentence in {source_name}: "
                    f"{sentence[:220]}"
                )
    checks.append(
        "required local unrebased qualification for PauliSimp predicate/error "
        "language in main TeX and Appendices A/B/C"
    )

    discussion = sections["Discussion"]
    if not (
        re.search(r"rebased TKET PauliSimp", discussion, re.IGNORECASE)
        and re.search(r"did recover", discussion, re.IGNORECASE)
        and re.search(r"compact Pauli|aggregate representation", discussion, re.IGNORECASE)
    ):
        errors.append("Discussion lacks the rebased PauliSimp recovery exception")

    manuscript_for_formula = main_tex + "\n" + appendix_c
    criterion = re.compile(
        r"\\epsilon\s*\\leq\s*\\mathrm\{atol\}\s*\+\s*"
        r"\\mathrm\{rtol\}\s*\\max_\{i,j\}\s*\|U_\{ij\}\|"
    )
    if not criterion.search(manuscript_for_formula):
        errors.append("exact atol + rtol * max|U| criterion missing")

    try:
        pyzx_row = section_text(
            appendix_c,
            r"PyZX \texttt{full\_reduce}",
            r"TKET FullPeephole",
            "Appendix C PyZX full_reduce row",
        )
    except ValueError as exc:
        errors.append(f"reader-facing section boundary error: {exc}")
        pyzx_row = ""
    labelled_clauses = {
        "rational witness": re.compile(r"(?<!ir)\brational\s+witness\s*:", re.IGNORECASE),
        "irrational witness": re.compile(r"\birrational\s+witness\s*:", re.IGNORECASE),
    }
    for label, pattern in labelled_clauses.items():
        if not pattern.search(pyzx_row):
            errors.append(f"Appendix C PyZX row lacks independently labelled {label!r} clause")
    if "correctness failure" not in pyzx_row.lower():
        errors.append("Appendix C PyZX row lacks 'correctness failure'")

    try:
        headline = section_text(
            main_tex,
            "The headline comparison tables report",
            "The semantic artifact uses",
            "headline comparison method list",
        )
    except ValueError as exc:
        errors.append(f"reader-facing section boundary error: {exc}")
        headline = ""
    if headline and not all(
        token in headline
        for token in (
            "semantic UCC",
            r"\texttt{qiskit opt3}",
            r"\texttt{full\_reduce}",
            "rebased TKET PauliSimp",
            "public staq rotation folding",
            "GuidedPauliSimp",
            "TKET FullPeephole",
            "unrebased PauliSimp configuration",
            "artifact UCC with Fourier-layer IR",
            "phase-polynomial reference appear",
        )
    ):
        errors.append("distinct headline-table and appendix/ablation method lists are incomplete")
    checks.append(
        "asserted strict section markers, Discussion exception, exact tolerance, "
        "independent rational/irrational PyZX clauses, and scoped method lists"
    )
    return errors, checks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=HERE / "round6_all_results.json")
    parser.add_argument("--timeout-s", type=int, default=600)
    args = parser.parse_args()

    errors: list[str] = []
    checks: list[str] = []
    witness_spec = json.loads((HERE / "unbounded_witness_spec.json").read_text())
    witness_result = load_verifier().validate_metadata(witness_spec)
    if witness_result["rank_f2"] != 4:
        errors.append("unbounded witness exact rank is not 4")
    else:
        checks.append("exact F2 witness rank is 4=m")

    bad_rank = copy.deepcopy(witness_spec)
    bad_rank["support_vectors"][3]["bits"] = bad_rank["support_vectors"][0]["bits"][:]
    try:
        load_verifier().validate_metadata(bad_rank)
    except AssertionError:
        checks.append("verifier rejects a deliberately dependent support matrix")
    else:
        errors.append("verifier accepted a deliberately dependent support matrix")

    bad_angle = copy.deepcopy(witness_spec)
    bad_angle["certificate"].pop("irrational_angle_expression", None)
    try:
        load_verifier().validate_metadata(bad_angle)
    except AssertionError:
        checks.append("verifier rejects missing exact irrational-angle metadata")
    else:
        errors.append("verifier accepted missing irrational-angle metadata")

    baseline_hashes = json.loads((HERE / "prechange_frozen_hashes.json").read_text())
    for relative, expected in baseline_hashes.items():
        path = ROOT / relative
        if not path.exists():
            errors.append(f"pre-existing JSON disappeared: {relative}")
        elif sha256(path) != expected:
            errors.append(f"pre-existing JSON changed: {relative}")
    checks.append(f"checked {len(baseline_hashes)} pre-existing JSON hashes")

    rows = json.loads(args.results.read_text(encoding="utf-8"))
    if len(rows) != 70:
        errors.append(f"expected 70 full rows, got {len(rows)}")
    keys = [(r.get("family_key"), r.get("requested_gates"), r.get("method_key")) for r in rows]
    if len(set(keys)) != len(keys):
        errors.append("duplicate family/size/method rows")
    expected_keys = {(family, size, method) for family in FAMILIES for size in SIZES for method in METHODS}
    missing = expected_keys - set(keys)
    extra = set(keys) - expected_keys
    if missing:
        errors.append(f"missing rows: {sorted(missing)}")
    if extra:
        errors.append(f"unexpected rows: {sorted(extra)}")

    for index, row in enumerate(rows):
        missing_fields = REQUIRED - set(row)
        if missing_fields:
            errors.append(f"row {index} missing fields {sorted(missing_fields)}")
        if row.get("timeout_s") != args.timeout_s:
            errors.append(f"row {index} timeout {row.get('timeout_s')} != {args.timeout_s}")
        if row.get("actual_input_gates") != 8 + 10 * row.get("r", -1):
            errors.append(f"row {index} inconsistent actual size/r mapping")
        if row.get("status") == "completed":
            if row.get("equivalence_checked") is not True:
                errors.append(f"completed row {index} lacks equivalence check")
            if row.get("equivalent_up_to_global_phase") is not True:
                errors.append(f"completed row {index} failed equivalence")
            if any(row.get(field) is None for field in ("gate_count", "depth", "cx_count")):
                errors.append(f"completed row {index} lacks metrics")
        log_path = row.get("log_path")
        if log_path and not (ROOT / log_path).exists():
            errors.append(f"row {index} missing per-cell log {log_path}")
    checks.append("validated schema, unique keys, size mapping, budgets, metrics, and completed equivalence")

    unbounded = [r for r in rows if r["family_key"] == "unbounded_independent_pauli"]
    if any(r.get("support_rank_verified") is not True for r in unbounded):
        errors.append("unbounded rows do not all carry support_rank_verified=true")
    if any(r.get("unbounded_noncollision_by_proposition") is not True for r in unbounded):
        errors.append("unbounded rows do not all carry proposition certificate")

    for filename, predicate in (
        ("unbounded_witness_results.json", lambda r: r["family_key"] == "unbounded_independent_pauli"),
        ("rational_cp_round6_results.json", lambda r: r["family_key"] == "rational_cp"),
        ("public_phase_folding_results.json", lambda r: r["method_key"] == "staq_rotation_folding"),
        ("tket_paulisimp_results.json", lambda r: r["method_key"].startswith("tket_paulisimp")),
    ):
        derived = json.loads((HERE / filename).read_text(encoding="utf-8"))
        expected = [r for r in rows if predicate(r)]
        derived_keys = {(r["family_key"], r["requested_gates"], r["method_key"]) for r in derived}
        expected_subset = {(r["family_key"], r["requested_gates"], r["method_key"]) for r in expected}
        if derived_keys != expected_subset:
            errors.append(f"derived file mismatch: {filename}")
    checks.append("validated four derived result JSON subsets")

    manuscript_sources = load_manuscript_sources(ROOT)
    manuscript_parts = list(manuscript_sources.values())
    manuscript = "\n".join(manuscript_parts)
    prose_errors, prose_checks = check_reader_facing_prose(manuscript_sources)
    errors.extend(prose_errors)
    checks.extend(prose_checks)
    risky = {
        "finite-tail form gives this conclusion": "superseded finite-tail wording",
        "experiment verifies the lower bound": "external-tool lower-bound overclaim",
        "all practical compilers": "all-compiler overclaim",
        "unboundedly noncolliding rational CP": "rational witness overclaim",
    }
    for phrase, label in risky.items():
        if phrase.lower() in manuscript.lower():
            errors.append(f"{label}: {phrase!r}")
    if "TKET PauliSimp (rebased)" not in manuscript:
        errors.append("rebased PauliSimp canonical label missing")
    if "staq rotation folding" not in manuscript:
        errors.append("public staq method label missing")
    if "per-transducer tail bound" not in manuscript:
        errors.append("per-transducer finite-tail wording missing")
    if "& TKET PauliSimp &" in manuscript:
        errors.append("unqualified raw TKET PauliSimp remains in a table")
    checks.append("ran targeted manuscript claim and method-label scans")

    caption_lines = [line for line in manuscript.splitlines() if "\\caption" in line]
    for line in caption_lines:
        if "frozen JSON" in line or "Round 6" in line or "attack" in line or "repair" in line:
            errors.append(f"reader-facing caption contains workflow language: {line[:160]}")

    table_specs = (
        ("unbounded_independent_pauli", ROOT / "PaperDraft/round6_unbounded_table.tex"),
        ("rational_cp", ROOT / "PaperDraft/round6_rational_table.tex"),
    )
    table_methods = {
        "semantic_ucc",
        "qiskit_opt3",
        "pyzx_full_reduce",
        "tket_paulisimp_rebased",
        "staq_rotation_folding",
        "tket_guided_paulisimp",
    }
    for family, table_path in table_specs:
        if not table_path.exists():
            errors.append(f"generated manuscript table missing: {table_path.relative_to(ROOT)}")
            continue
        table_text = table_path.read_text(encoding="utf-8")
        for row in rows:
            if row["family_key"] != family or row["method_key"] not in table_methods:
                continue
            if row["status"] == "completed":
                token = f"{row['gate_count']}/{row['depth']}/{row['cx_count']}"
            else:
                token = row["status"].replace("_", " ")
            if token not in table_text:
                errors.append(
                    f"table {table_path.name} lacks JSON token {token} for "
                    f"{row['requested_gates']}/{row['method_key']}"
                )
    figure_paths = (
        ROOT / "PaperDraft/figures/unbounded_witness_scaling.pdf",
        ROOT / "PaperDraft/figures/fourier_separation.pdf",
        ROOT / "PaperDraft/figures/scaling_plot.png",
    )
    for figure_path in figure_paths:
        if not figure_path.exists() or figure_path.stat().st_size == 0:
            errors.append(f"missing or empty figure: {figure_path.relative_to(ROOT)}")
    checks.append("checked generated table tokens against JSON and required figure files")

    statuses = Counter(row["status"] for row in rows)
    report = {
        "status": "passed" if not errors else "failed",
        "row_count": len(rows),
        "status_counts": dict(sorted(statuses.items())),
        "checks": checks,
        "errors": errors,
    }
    (HERE / "round6_validation_results.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# Round 6 Validation Results",
        "",
        f"Status: **{report['status']}**",
        f"Rows: `{len(rows)}`",
        f"Status counts: `{dict(sorted(statuses.items()))}`",
        "",
        "## Checks",
        "",
    ]
    lines.extend(f"- {item}" for item in checks)
    lines.extend(["", "## Errors", ""])
    lines.extend(f"- {item}" for item in errors) if errors else lines.append("- None")
    (HERE / "round6_validation_results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Adversarial Round 6.2.3 prose-validator tests on disposable TeX copies."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import validate_round6_outputs as validator


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class Round62ValidatorTamperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="round6_2_3_tamper_")
        self.fixture_root = Path(self.temporary.name)
        self.original_hashes = {}
        for relative in validator.MANUSCRIPT_RELATIVE_PATHS.values():
            source = REPOSITORY_ROOT / relative
            self.original_hashes[relative] = validator.sha256(source)
            target = self.fixture_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    def tearDown(self) -> None:
        changed_originals = [
            str(relative)
            for relative, digest in self.original_hashes.items()
            if validator.sha256(REPOSITORY_ROOT / relative) != digest
        ]
        self.temporary.cleanup()
        self.assertFalse(self.fixture_root.exists(), "temporary tamper fixture was not removed")
        self.assertEqual(
            changed_originals,
            [],
            f"tamper test modified original manuscript sources: {changed_originals}",
        )

    def path(self, logical_name: str) -> Path:
        return self.fixture_root / validator.MANUSCRIPT_RELATIVE_PATHS[logical_name]

    def inject(self, logical_name: str, sentence: str) -> None:
        path = self.path(logical_name)
        text = path.read_text(encoding="utf-8")
        self.assertEqual(
            text.count(sentence),
            0,
            f"tamper sentence already occurs in {logical_name}: {sentence}",
        )
        path.write_text(text + "\n" + sentence + "\n", encoding="utf-8")
        self.assertEqual(
            path.read_text(encoding="utf-8").count(sentence),
            1,
            f"tamper sentence was not injected exactly once in {logical_name}: {sentence}",
        )

    def replace_once(self, logical_name: str, pattern: str, replacement: str) -> None:
        path = self.path(logical_name)
        text = path.read_text(encoding="utf-8")
        changed, count = re.subn(
            pattern, lambda _match: replacement, text, count=1, flags=re.DOTALL
        )
        self.assertEqual(count, 1, f"tamper pattern did not match in {logical_name}: {pattern}")
        path.write_text(changed, encoding="utf-8")

    def assert_rejected(self, expected: str) -> None:
        sources = validator.load_manuscript_sources(self.fixture_root)
        errors, _ = validator.check_reader_facing_prose(sources)
        self.assertTrue(errors, "tampered fixture passed the validator prose checks")
        self.assertTrue(
            any(expected.lower() in error.lower() for error in errors),
            f"expected {expected!r} in validator errors, got: {errors}",
        )
        self.assert_full_cli_rejected(expected)

    def assert_accepted(self) -> None:
        sources = validator.load_manuscript_sources(self.fixture_root)
        errors, _ = validator.check_reader_facing_prose(sources)
        self.assertEqual(errors, [], f"qualified fixture produced false positives: {errors}")
        completed = self.run_full_cli()
        diagnostic = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, diagnostic)
        print("full_validator_cli_exit=0; qualified_prose_accepted=true")

    def copy_project_file(self, relative: Path | str) -> None:
        relative = Path(relative)
        source = REPOSITORY_ROOT / relative
        self.assertTrue(source.is_file(), f"required CLI fixture file is missing: {relative}")
        self.original_hashes.setdefault(relative, validator.sha256(source))
        target = self.fixture_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    def prepare_full_cli_fixture(self) -> Path:
        round6 = Path("research/round6_major_revision")
        for name in (
            "validate_round6_outputs.py",
            "verify_unbounded_witness.py",
            "prechange_frozen_hashes.json",
            "unbounded_witness_spec.json",
            "round6_all_results.json",
            "unbounded_witness_results.json",
            "rational_cp_round6_results.json",
            "public_phase_folding_results.json",
            "tket_paulisimp_results.json",
        ):
            self.copy_project_file(round6 / name)

        baseline = json.loads(
            (REPOSITORY_ROOT / round6 / "prechange_frozen_hashes.json").read_text(
                encoding="utf-8"
            )
        )
        for relative in baseline:
            self.copy_project_file(relative)

        rows = json.loads(
            (REPOSITORY_ROOT / round6 / "round6_all_results.json").read_text(
                encoding="utf-8"
            )
        )
        for relative in sorted({row["log_path"] for row in rows if row.get("log_path")}):
            self.copy_project_file(relative)

        for relative in (
            "PaperDraft/round6_unbounded_table.tex",
            "PaperDraft/round6_rational_table.tex",
            "PaperDraft/figures/unbounded_witness_scaling.pdf",
            "PaperDraft/figures/fourier_separation.pdf",
            "PaperDraft/figures/scaling_plot.png",
        ):
            self.copy_project_file(relative)
        return self.fixture_root / round6 / "validate_round6_outputs.py"

    def run_prepared_cli(self, cli: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(cli)],
            cwd=self.fixture_root,
            text=True,
            capture_output=True,
            check=False,
        )

    def run_full_cli(self) -> subprocess.CompletedProcess[str]:
        return self.run_prepared_cli(self.prepare_full_cli_fixture())

    def assert_prepared_cli_rejected(self, cli: Path, expected: str) -> None:
        completed = self.run_prepared_cli(cli)
        diagnostic = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 1, diagnostic)
        self.assertIn(expected.lower(), diagnostic.lower(), diagnostic)
        print(
            f"full_validator_cli_exit={completed.returncode}; "
            f"diagnostic_family={expected}"
        )

    def assert_full_cli_rejected(self, expected: str) -> None:
        completed = self.run_full_cli()
        diagnostic = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 1, diagnostic)
        self.assertIn(expected.lower(), diagnostic.lower(), diagnostic)
        print(
            f"full_validator_cli_exit={completed.returncode}; "
            f"diagnostic_family={expected}"
        )

    def test_a_none_of_external_pipelines(self) -> None:
        self.inject("Appendix A", "None of the external pipelines recovered the bounded form.")
        self.assert_rejected("none-of recovery")

    def test_b_no_configured_pipeline_singular(self) -> None:
        self.inject("Appendix A", "No configured pipeline recovered the bounded form.")
        self.assert_rejected("no-target recovery")

    def test_c_every_configured_pipeline(self) -> None:
        self.inject(
            "Appendix A", "Every configured pipeline failed to recover the bounded form."
        )
        self.assert_rejected("every-target recovery failure")

    def test_d_rational_clause_deleted(self) -> None:
        self.replace_once(
            "Appendix C",
            r"rational witness:.*?(?=Irrational witness:)",
            "",
        )
        self.assert_rejected("independently labelled 'rational witness' clause")

    def test_e_irrational_clause_deleted(self) -> None:
        self.replace_once(
            "Appendix C",
            r"Irrational witness:.*?(?=\n& strong small-scale simplification)",
            "",
        )
        self.assert_rejected("independently labelled 'irrational witness' clause")

    def test_f_real_task_end_marker_missing(self) -> None:
        self.replace_once(
            "main TeX",
            re.escape(r"\subsection{Real-Task Panel}"),
            r"\subsection{Real Task Panel}",
        )
        self.assert_rejected("rational-witness results: end marker not found")
        errors, _ = validator.check_reader_facing_prose(
            validator.load_manuscript_sources(self.fixture_root)
        )
        self.assertTrue(any("Real-Task Panel" in error for error in errors))

    def test_g_appendix_b_unqualified_paulisimp_predicate_error(self) -> None:
        self.inject("Appendix B", "PauliSimp reports a predicate error.")
        self.assert_rejected("ambiguous PauliSimp predicate/error sentence in Appendix B")

    def test_h_all_pipeline_failure_family(self) -> None:
        self.inject("Appendix A", "All external pipelines failed.")
        self.assert_rejected("all-target failure")

    def test_i_without_exception_does_not_qualify(self) -> None:
        sentence = (
            "Every configured pipeline failed to recover the bounded form, without exception."
        )
        self.inject("Appendix A", sentence)
        self.assert_rejected("every-target recovery failure")

    def test_j_no_external_baseline(self) -> None:
        self.inject("Appendix A", "No external baseline recovered the bounded form.")
        self.assert_rejected("no-target recovery")

    def test_k_no_configured_tool(self) -> None:
        self.inject("Appendix A", "No configured tool recovered the bounded form.")
        self.assert_rejected("no-target recovery")

    def test_l_no_method(self) -> None:
        self.inject("Appendix A", "No method recovered the bounded form.")
        self.assert_rejected("no-target recovery")

    def test_m_no_compiler(self) -> None:
        self.inject("Appendix A", "No compiler recovered the bounded form.")
        self.assert_rejected("no-target recovery")

    def test_n_legitimate_qualified_prose_is_accepted(self) -> None:
        self.inject(
            "Appendix A", "Most configured pipelines did not recover the bounded form."
        )
        self.inject(
            "Appendix A",
            "All configured pipelines except for the rebased TKET PauliSimp pipeline "
            "failed to recover the bounded form.",
        )
        self.assert_accepted()

    def test_o_bare_exception_does_not_qualify(self) -> None:
        self.inject(
            "Appendix A",
            "Every configured pipeline failed to recover the bounded form; "
            "an exception was discussed.",
        )
        self.assert_rejected("every-target recovery failure")

    def test_p_every_compiler_family(self) -> None:
        self.inject("Appendix A", "Every compiler failed to recover the bounded form.")
        self.assert_rejected("every-target recovery failure")

    def test_q_all_tools_family(self) -> None:
        self.inject("Appendix A", "All configured tools failed.")
        self.assert_rejected("all-target failure")

    def test_r6_2_2_x1_not_a_single(self) -> None:
        self.inject(
            "Appendix A",
            "Not a single configured pipeline recovered the bounded form.",
        )
        self.assert_rejected("no-target recovery")

    def test_r6_2_2_x2_each(self) -> None:
        self.inject(
            "Appendix A", "Each configured pipeline failed to recover the bounded form."
        )
        self.assert_rejected("each-target recovery failure")

    def test_r6_2_2_x3_optimizer(self) -> None:
        self.inject("Appendix A", "No optimizer recovered the bounded form.")
        self.assert_rejected("no-target recovery")

    def test_r6_2_2_x4_neither_without_terminal_punctuation(self) -> None:
        self.inject("Appendix A", "Neither external pipeline recovered the bounded form")
        self.assert_rejected("no-target recovery")

    def test_r6_2_2_x5_zero_hard_wrapping(self) -> None:
        self.inject(
            "Appendix A", "Zero configured\npipelines recovered the bounded form."
        )
        self.assert_rejected("no-target recovery")

    def test_r6_2_2_w1_without_exception_being_noted(self) -> None:
        self.inject(
            "Appendix A",
            "Every configured pipeline failed to recover the bounded form, "
            "without exception being noted.",
        )
        self.assert_rejected("every-target recovery failure")

    def test_r6_2_2_w2_exceptions_are_none(self) -> None:
        self.inject(
            "Appendix A",
            "Every configured pipeline failed to recover the bounded form; "
            "the exceptions are none.",
        )
        self.assert_rejected("every-target recovery failure")

    def test_r6_2_2_w3_except_that_none_succeeded(self) -> None:
        self.inject(
            "Appendix A",
            "Every configured pipeline failed to recover the bounded form, "
            "except that none succeeded.",
        )
        self.assert_rejected("every-target recovery failure")

    def test_r6_2_2_w4_with_no_exceptions(self) -> None:
        self.inject(
            "Appendix A",
            "Every external baseline failed to recover the bounded form, "
            "with no exceptions.",
        )
        self.assert_rejected("every-target recovery failure")

    def test_r6_2_2_w5_there_were_no_exceptions(self) -> None:
        self.inject(
            "Appendix A",
            "Every external baseline failed to recover the bounded form; "
            "there were no exceptions.",
        )
        self.assert_rejected("every-target recovery failure")

    def test_r6_2_2_n1_through_n5_legitimate_controls(self) -> None:
        controls = (
            "All configured pipelines except the rebased TKET PauliSimp pipeline "
            "failed to recover the bounded form.",
            "Every configured pipeline except for the rebased TKET PauliSimp pipeline "
            "failed to recover the bounded form.",
            "All configured pipelines, with the exception of the rebased TKET "
            "PauliSimp pipeline, failed to recover the bounded form.",
            "Most configured pipelines did not recover the bounded form.",
            "Not all configured pipelines recovered the bounded form.",
        )
        for sentence in controls:
            self.inject("Appendix A", sentence)
        self.assert_accepted()

    def test_r6_2_2_case_comment_and_modifier_variants(self) -> None:
        sentence = (
            "EACH heavily rebased external % interposed TeX comment\n"
            "PIPELINE FAILED TO RECOVER THE BOUNDED FORM."
        )
        self.inject("Appendix A", sentence)
        self.assert_rejected("each-target recovery failure")

    def test_r6_2_2_lower_case_plural_punctuation_variant(self) -> None:
        self.inject(
            "Appendix A",
            "not a single configured optimizers, after lowering, recovered the bounded form!",
        )
        self.assert_rejected("no-target recovery")

    def test_r6_2_2_historical_discussion_exception_loss(self) -> None:
        self.replace_once(
            "main TeX",
            r"The rebased TKET PauliSimp pipeline did recover it on\s+"
            r"both witnesses by reconstructing a compact Pauli representation through a\s+"
            r"generic predicate-correct preamble\.",
            "The corresponding diagnostic is omitted.",
        )
        self.assert_rejected("Discussion lacks the rebased PauliSimp recovery exception")

    def test_r6_2_2_historical_tolerance_criterion_deletion(self) -> None:
        self.replace_once(
            "main TeX",
            r"\\epsilon\s*\\leq\s*\\mathrm\{atol\}\s*\+\s*"
            r"\\mathrm\{rtol\}\s*\\max_\{i,j\}\s*\|U_\{ij\}\|",
            r"\\epsilon \\text{ was checked}",
        )
        self.assert_rejected("exact atol + rtol * max|U| criterion missing")

    def test_r6_2_2_historical_witness_support_rank_corruption(self) -> None:
        cli = self.prepare_full_cli_fixture()
        path = self.fixture_root / "research/round6_major_revision/unbounded_witness_spec.json"
        spec = json.loads(path.read_text(encoding="utf-8"))
        self.assertNotEqual(
            spec["support_vectors"][3]["bits"], spec["support_vectors"][0]["bits"]
        )
        spec["support_vectors"][3]["bits"] = spec["support_vectors"][0]["bits"][:]
        path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
        self.assertEqual(
            json.loads(path.read_text(encoding="utf-8"))["support_vectors"][3]["bits"],
            spec["support_vectors"][0]["bits"],
        )
        self.assert_prepared_cli_rejected(cli, "support rank")

    def test_r6_2_2_historical_missing_irrational_angle(self) -> None:
        cli = self.prepare_full_cli_fixture()
        path = self.fixture_root / "research/round6_major_revision/unbounded_witness_spec.json"
        spec = json.loads(path.read_text(encoding="utf-8"))
        removed = spec["certificate"].pop("irrational_angle_expression", None)
        self.assertIsNotNone(removed, "irrational-angle declaration was not removed once")
        path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
        self.assertNotIn(
            "irrational_angle_expression",
            json.loads(path.read_text(encoding="utf-8"))["certificate"],
        )
        self.assert_prepared_cli_rejected(cli, "missing exact irrational-angle declaration")

    def test_r6_2_2_historical_generated_table_token_mismatch(self) -> None:
        cli = self.prepare_full_cli_fixture()
        path = self.fixture_root / "PaperDraft/round6_rational_table.tex"
        text = path.read_text(encoding="utf-8")
        old = "9588/5593/4788"
        self.assertEqual(text.count(old), 1, "table token fixture is not unique")
        path.write_text(text.replace(old, "9589/5593/4788"), encoding="utf-8")
        self.assertEqual(path.read_text(encoding="utf-8").count(old), 0)
        self.assert_prepared_cli_rejected(cli, "lacks JSON token 9588/5593/4788")

    def test_r6_2_2_historical_frozen_json_hash_mismatch(self) -> None:
        cli = self.prepare_full_cli_fixture()
        relative = Path("research/ablation_results_10k.json")
        path = self.fixture_root / relative
        text = path.read_text(encoding="utf-8")
        path.write_text(text + "\n", encoding="utf-8")
        self.assertEqual(path.read_text(encoding="utf-8"), text + "\n")
        self.assert_prepared_cli_rejected(cli, "pre-existing JSON changed")

    def test_r6_2_2_clean_tree_full_cli_control(self) -> None:
        completed = self.run_full_cli()
        diagnostic = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, diagnostic)
        self.assertIn('"status": "passed"', diagnostic)
        self.assertIn('"errors": []', diagnostic)
        print("full_validator_cli_exit=0; clean_tree_control=true")

    def test_r6_2_3_a1_zero_pipelines_is_not_an_exception(self) -> None:
        self.inject(
            "Appendix A",
            "Every configured pipeline failed to recover the bounded form, "
            "except for zero pipelines.",
        )
        self.assert_rejected("every-target recovery failure")

    def test_r6_2_3_a2_neither_pipeline_is_not_an_exception(self) -> None:
        self.inject(
            "Appendix A",
            "Every configured pipeline failed to recover the bounded form, "
            "except that neither pipeline succeeded.",
        )
        self.assert_rejected("every-target recovery failure")

    def test_r6_2_3_a3_zero_methods_is_not_an_exception(self) -> None:
        self.inject(
            "Appendix A",
            "Every configured pipeline failed to recover the bounded form; "
            "the exception is zero methods.",
        )
        self.assert_rejected("every-target recovery failure")

    def test_r6_2_3_zero_configured_pipelines_variant(self) -> None:
        self.inject(
            "Appendix A",
            "EVERY configured pipeline failed to recover the bounded form, "
            "EXCEPT FOR ZERO configured PIPELINES!",
        )
        self.assert_rejected("every-target recovery failure")

    def test_r6_2_3_neither_tested_method_missing_punctuation(self) -> None:
        self.inject(
            "Appendix A",
            "Every configured pipeline failed to recover the bounded form, "
            "except that neither tested method succeeded",
        )
        self.assert_rejected("every-target recovery failure")

    def test_r6_2_3_zero_optimizers_variant(self) -> None:
        self.inject(
            "Appendix A",
            "Every configured pipeline failed to recover the bounded form; "
            "the exception is zero optimizers.",
        )
        self.assert_rejected("every-target recovery failure")

    def test_r6_2_3_four_modifiers_wrap_comment_and_hyphen_variant(self) -> None:
        self.inject(
            "Appendix A",
            "Every configured pipeline failed to recover the bounded form, except for "
            "ZERO strongly guided highly-rebased % interposed TeX comment\n"
            "external optimizers.",
        )
        self.assert_rejected("every-target recovery failure")

    def test_r6_2_3_two_modifier_zero_target_variant(self) -> None:
        self.inject(
            "Appendix A",
            "Every configured pipeline failed to recover the bounded form, "
            "except for zero tested external methods.",
        )
        self.assert_rejected("every-target recovery failure")

    def test_r6_2_3_three_modifier_neither_target_variant(self) -> None:
        self.inject(
            "Appendix A",
            "Every configured pipeline failed to recover the bounded form, "
            "except that neither newly rebased external tool succeeded.",
        )
        self.assert_rejected("every-target recovery failure")

    def test_r6_2_3_negated_named_exception_is_rejected(self) -> None:
        self.inject(
            "Appendix A",
            "Every configured pipeline failed to recover the bounded form, "
            "except that no rebased TKET PauliSimp pipeline succeeded.",
        )
        self.assert_rejected("every-target recovery failure")

    def test_r6_2_3_neither_named_exception_is_rejected(self) -> None:
        self.inject(
            "Appendix A",
            "Every configured pipeline failed to recover the bounded form, "
            "except that neither PyZX nor Qiskit succeeded.",
        )
        self.assert_rejected("every-target recovery failure")

    def test_r6_2_3_no_method_is_not_an_exception(self) -> None:
        self.inject(
            "Appendix A",
            "Every configured pipeline failed to recover the bounded form, "
            "except for no method.",
        )
        self.assert_rejected("every-target recovery failure")

    def test_r6_2_3_nobody_is_not_an_exception(self) -> None:
        self.inject(
            "Appendix A",
            "Every configured pipeline failed to recover the bounded form, except nobody.",
        )
        self.assert_rejected("every-target recovery failure")

    def test_r6_2_3_nothing_is_not_an_exception(self) -> None:
        self.inject(
            "Appendix A",
            "Every configured pipeline failed to recover the bounded form, except nothing.",
        )
        self.assert_rejected("every-target recovery failure")

    def test_r6_2_3_no_one_is_not_an_exception(self) -> None:
        self.inject(
            "Appendix A",
            "Every configured pipeline failed to recover the bounded form, except no one.",
        )
        self.assert_rejected("every-target recovery failure")

    def test_r6_2_3_not_one_is_not_an_exception(self) -> None:
        self.inject(
            "Appendix A",
            "Every configured pipeline failed to recover the bounded form, except not one.",
        )
        self.assert_rejected("every-target recovery failure")

    def test_r6_2_3_not_a_single_tool_is_not_an_exception(self) -> None:
        self.inject(
            "Appendix A",
            "Every configured pipeline failed to recover the bounded form, "
            "except for not a single tool.",
        )
        self.assert_rejected("every-target recovery failure")

    def test_r6_2_3_b1_named_pipeline_is_accepted(self) -> None:
        self.inject(
            "Appendix A",
            "All configured pipelines except the rebased TKET PauliSimp pipeline "
            "failed to recover the bounded form.",
        )
        self.assert_accepted()

    def test_r6_2_3_b2_bare_paulisimp_name_is_accepted(self) -> None:
        self.inject(
            "Appendix A",
            "All tested baselines, with the exception of rebased PauliSimp, "
            "failed to recover the bounded form.",
        )
        self.assert_accepted()

    def test_r6_2_3_b3_compact_pauli_route_is_accepted(self) -> None:
        self.inject(
            "Appendix A",
            "All configured methods except the compact-Pauli reconstruction route "
            "failed to recover the bounded form.",
        )
        self.assert_accepted()

    def test_r6_2_3_b4_every_external_tool_named_exception_is_accepted(self) -> None:
        self.inject(
            "Appendix A",
            "Every external tool except the rebased TKET PauliSimp pipeline "
            "failed to recover the bounded form.",
        )
        self.assert_accepted()

    def test_r6_2_3_named_configuration_and_route_controls(self) -> None:
        self.inject(
            "Appendix A",
            "All configured pipelines except the rebased PauliSimp configuration "
            "failed to recover the bounded form.",
        )
        self.inject(
            "Appendix A",
            "All tested baselines, with the exception of the compact-Pauli "
            "reconstruction route, failed to recover the bounded form.",
        )
        self.assert_accepted()

    def test_r6_2_3_historical_qualifier_forms_remain_accepted(self) -> None:
        controls = (
            "Most configured pipelines did not recover the bounded form.",
            "Not all configured pipelines recovered the bounded form.",
            "Every configured pipeline failed to recover the bounded form, except for "
            "the rebased TKET PauliSimp pipeline.",
            "Every configured pipeline failed to recover the bounded form, except that "
            "the rebased TKET PauliSimp pipeline succeeded.",
            "Every configured pipeline failed to recover the bounded form, except when "
            "the rebased TKET PauliSimp pipeline succeeded.",
            "Every configured pipeline failed to recover the bounded form; with the "
            "exception of rebased PauliSimp, the recovery was absent.",
            "Every configured pipeline failed to recover the bounded form; the exception "
            "is rebased PauliSimp.",
            "Every configured pipeline failed to recover the bounded form; the exceptions "
            "are TKET and PyZX.",
            "Every configured pipeline failed to recover the bounded form; the exception "
            "being the compact-Pauli reconstruction route.",
        )
        for sentence in controls:
            self.inject("Appendix A", sentence)
        self.assert_accepted()

    def test_r6_2_3_closed_project_name_vocabulary_is_accepted(self) -> None:
        names = (
            "PauliSimp",
            "GuidedPauliSimp",
            "TKET",
            "PyZX",
            "Qiskit",
            "staq",
            "UCC",
            "the reconstruction",
        )
        for name in names:
            self.inject(
                "Appendix A",
                f"All configured pipelines except {name} failed to recover the bounded form.",
            )
        self.assert_accepted()

    def test_r6_2_3_legitimate_exception_then_unrelated_sentence(self) -> None:
        self.inject(
            "Appendix A",
            "All configured pipelines except rebased PauliSimp failed to recover the "
            "bounded form. The zero vector is neither an exception nor a pipeline.",
        )
        self.assert_accepted()

    def test_r6_2_3_unrelated_math_terms_do_not_trigger(self) -> None:
        self.inject(
            "Appendix A",
            "Zero is the additive identity; neither basis vector is an exception to "
            "this algebraic rule.",
        )
        self.assert_accepted()

    def test_r6_2_3_arbitrary_exception_text_is_not_whitelisted(self) -> None:
        self.inject(
            "Appendix A",
            "All configured pipelines except the lunar detour failed to recover the "
            "bounded form.",
        )
        self.assert_rejected("all-target failure")


if __name__ == "__main__":
    unittest.main(verbosity=2)

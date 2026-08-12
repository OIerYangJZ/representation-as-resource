from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from compiler.reference_streaming.compilers import COMPILER_NAMES
from compiler.reference_streaming.model import RunConfig, build_dispersed_instance
from compiler.reference_streaming.runner import run_reference_compiler
from encoding.codec import decode_exact
from instrumentation.event_trace import verify_trace_run


FRACTIONS = {
    "echo": 0.0,
    "full_aggregation": 1.0,
    "hybrid_25": 0.25,
    "hybrid_50": 0.50,
    "hybrid_75": 0.75,
    "ir_materializing": 1.0,
}


class ReferenceCompilerTests(unittest.TestCase):
    def config(self, compiler: str, *, passes: int = 2, schedule: str = "round_major") -> RunConfig:
        return RunConfig(compiler, 4, 3, 4, 0.5, passes, FRACTIONS[compiler], schedule, 1729)

    def test_all_compilers_emit_exactly_equivalent_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for compiler in COMPILER_NAMES:
                with self.subTest(compiler=compiler):
                    manifest_path = run_reference_compiler(self.config(compiler), directory)
                    manifest = verify_trace_run(manifest_path, verify_slices=True)
                    self.assertEqual(manifest["extra"]["input_equivalence"]["status"], "pass")
                    self.assertEqual(manifest["extra"]["output_certificate"]["status"], "pass")
                    crossings = []
                    with (manifest_path.parent / "events.jsonl").open("r", encoding="utf-8") as stream:
                        for line in stream:
                            row = json.loads(line)
                            if row["crossing"]:
                                crossings.append(row["crossing"])
                    self.assertEqual(crossings.count("A_to_B"), 2)
                    self.assertEqual(crossings.count("B_to_A"), 1)

    def test_permuted_within_round_schedule_preserves_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = run_reference_compiler(
                self.config("hybrid_25", passes=4, schedule="permuted_within_round"), directory
            )
            self.assertEqual(verify_trace_run(manifest)["extra"]["output_certificate"]["projective_error"], 0.0)

    def test_flat_token_schema_contains_a_share_not_x(self) -> None:
        config = self.config("echo")
        x, _, flat = build_dispersed_instance(config)
        self.assertEqual(len(flat.records), config.m * config.r)
        for record in flat.records:
            self.assertEqual(set(record.to_payload()), {"round", "generator", "support", "parameter"})
        totals = [0] * config.m
        for record in flat.records:
            totals[record.generator] = (totals[record.generator] + record.parameter.constant.numerator) % config.Q
        self.assertEqual(tuple(totals), x)

    def test_actual_crossing_frames_are_decodable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = run_reference_compiler(self.config("full_aggregation", passes=1), directory)
            event = None
            for line in (manifest_path.parent / "events.jsonl").read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                if row["crossing"] == "A_to_B":
                    event = row
                    break
            self.assertIsNotNone(event)
            for name in ("control", "store", "window", "parameter", "ir"):
                record = event["slices"][name]
                data = (manifest_path.parent / record["path"]).read_bytes()
                payload = data[record["offset"] : record["offset"] + record["bytes"]]
                self.assertIsNotNone(decode_exact(payload))


class EventTraceTamperTests(unittest.TestCase):
    def test_verifier_rejects_edited_frame_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = run_reference_compiler(
                RunConfig("echo", 2, 2, 2, 0.5, 1, 0.0, "round_major", 7), directory
            )
            control = manifest.parent / "control.frames"
            payload = bytearray(control.read_bytes())
            payload[-1] ^= 1
            control.write_bytes(payload)
            with self.assertRaises(ValueError):
                verify_trace_run(manifest)


if __name__ == "__main__":
    unittest.main()

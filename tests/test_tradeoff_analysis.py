from __future__ import annotations

import csv
import gzip
import json
import tempfile
import unittest
from pathlib import Path

from compiler.reference_streaming.model import RunConfig
from compiler.reference_streaming.runner import run_reference_compiler
from scripts.analyze_tradeoff import analyze


class TradeoffAnalysisTests(unittest.TestCase):
    def test_analysis_uses_verified_event_traces_and_keeps_residuals(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            campaign = root / "campaign"
            campaign.mkdir()
            configs = (
                RunConfig("echo", 4, 2, 8, 0.5, 1, 0.0, "round_major", 20260801),
                RunConfig("full_aggregation", 4, 2, 8, 0.5, 1, 1.0, "round_major", 20260801),
                RunConfig("hybrid_50", 4, 2, 8, 0.5, 1, 0.5, "round_major", 20260801),
            )
            for config in configs:
                run_reference_compiler(config, campaign)
            (campaign / "campaign_manifest.json").write_text(
                json.dumps({"selected_runs": len(configs)}) + "\n", encoding="utf-8"
            )
            frozen = root / "frozen"
            figure = root / "frontier.pdf"
            manifest = analyze(campaign, frozen, figure, verify_slices=True)
            self.assertTrue(manifest["campaign_complete"])
            self.assertTrue(manifest["all_verified_points_in_allowed_region"])
            self.assertTrue(figure.is_file())
            with (frozen / "tradeoff_summary.csv").open("r", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), len(configs))
            self.assertTrue(all(float(row["cap_envelope_residual_bits"]) >= 0 for row in rows))
            with gzip.open(frozen / "tradeoff_events.jsonl.gz", "rt", encoding="utf-8") as stream:
                first = json.loads(next(stream))
            self.assertIn("B_cross_bits", first)
            self.assertIn("run_id", first)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
KEY = [
    "experiment_id", "instance_id", "representation_id", "method_id", "seed",
    "backend_hash", "tool_version", "artifact_commit", "config_hash",
]


def test_unified_experiment_index_has_complete_unique_primary_key() -> None:
    frame = pd.read_parquet(ROOT / "data/frozen/unified_experiments.parquet")
    assert len(frame) == 24_748
    assert frame[KEY].notna().all().all()
    assert not frame.duplicated(KEY).any()
    assert frame.backend_hash.str.fullmatch(r"[0-9a-f]{64}").all()
    assert frame.config_hash.str.fullmatch(r"[0-9a-f]{64}").all()
    assert set(frame.status) == {"completed_valid", "predicate_error"}
    assert (frame.status == "predicate_error").sum() == 48


def test_every_generated_paper_number_has_a_live_provenance_entry() -> None:
    mapping = yaml.safe_load((ROOT / "data/provenance_map.yaml").read_text())
    ids = {item["id"] for item in mapping["entries"]}
    macros = {item["macro"] for item in mapping["entries"]}
    assert len(ids) == len(mapping["entries"])
    assert len(macros) == len(mapping["entries"])
    generated = (ROOT / "PaperDraft/generated/paper_numbers.tex").read_text()
    generated_ids = set(re.findall(r"\\DataNumber\{([^}]+)\}", generated))
    generated_macros = set(re.findall(r"\\newcommand\{\\([^}]+)\}", generated))
    assert generated_ids == ids
    assert generated_macros == macros
    for entry in mapping["entries"]:
        assert (ROOT / entry["source"]).exists()


def test_frozen_paper_numbers_match_the_declared_expected_values() -> None:
    mapping = {
        item["id"]: item for item in yaml.safe_load(
            (ROOT / "data/provenance_map.yaml").read_text()
        )["entries"]
    }
    frozen = json.loads((ROOT / "data/frozen/paper_numbers.json").read_text())
    assert {item["id"] for item in frozen} == set(mapping)
    for item in frozen:
        expected = mapping[item["id"]]["expected"]
        observed = item["observed"]
        if isinstance(expected, float):
            assert abs(float(observed) - expected) <= max(1e-10, abs(expected) * 1e-10)
        else:
            assert int(observed) == int(expected)


def test_data_audit_is_clean_and_preserves_status_classes() -> None:
    audit = json.loads((ROOT / "data/frozen/data_audit.json").read_text())
    assert audit["duplicate_primary_key_rows"] == 0
    assert audit["missing_registered_files"] == []
    assert audit["row_count_mismatches"] == []
    assert audit["conflicting_numeric_cells"] == 0
    assert audit["duplicate_tex_labels"] == []
    assert audit["hash_drift"] == []
    assert audit["unregistered_frozen_artifacts"] == []
    assert audit["status_counts"] == {"completed_valid": 24_700, "predicate_error": 48}


def test_seed_and_bootstrap_statistics_are_frozen() -> None:
    natural = yaml.safe_load((ROOT / "workloads/manifest.yaml").read_text())
    analysis = json.loads((ROOT / "data/frozen/natural_workload_analysis.json").read_text())
    assert len(natural["seeds"]) == 3
    assert analysis["bootstrap_replicates"] == 4_000
    assert analysis["bootstrap_seed"] == 20_260_830
    effects = pd.read_csv(ROOT / "data/frozen/natural_ablation_effects.csv")
    assert effects[["ci95_low", "ci95_high"]].notna().all().all()
    assert (effects.ci95_low <= effects["mean"]).all()
    assert (effects["mean"] <= effects.ci95_high).all()

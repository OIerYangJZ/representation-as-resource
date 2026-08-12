from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "data/frozen/natural_workloads.parquet"
KEY = [
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


def test_manifest_covers_required_workload_classes_and_grid() -> None:
    manifest = yaml.safe_load((ROOT / "workloads/manifest.yaml").read_text())
    families = {item["id"] for item in manifest["families"]}
    required = {
        "qaoa_ising",
        "diagonal_hamiltonian",
        "trotter_commuting_blocks",
        "qpe_controlled_powers",
        "qft_arithmetic",
        "controlled_power_ladder",
        "phase_polynomial_blocks",
        "negative_random_clifford_rz",
        "negative_routing_dominated",
    }
    assert families == required
    assert manifest["scales"] == [1, 2, 4]
    assert len(manifest["seeds"]) == 3
    assert set(manifest["hardware_topologies"]) == {"all_to_all", "line"}


def test_full_factorial_frozen_table_is_complete_and_unique() -> None:
    frame = pd.read_parquet(FROZEN)
    assert len(frame) == 21_060
    assert frame[KEY].notna().all().all()
    assert not frame.duplicated(KEY).any()
    authors = frame[frame.method_id == "authors_factorial"]
    external = frame[frame.method_id == "external_tket_paulisimp"]
    assert len(authors) == 20_736
    assert len(external) == 324
    assert set(frame.status) == {"completed_valid"}
    assert set(frame.certificate_status) == {"completed_valid"}
    assert set(frame.qre_status) == {"completed_valid"}


def test_every_instance_has_all_64_factorial_cells_and_external_match() -> None:
    frame = pd.read_parquet(FROZEN)
    authors = frame[frame.method_id == "authors_factorial"]
    external = frame[frame.method_id == "external_tket_paulisimp"]
    assert set(authors.groupby("instance_id").size()) == {64}
    assert set(external.groupby("instance_id").size()) == {1}
    assert set(authors.instance_id) == set(external.instance_id)


def test_predeclared_success_and_negative_control_results_are_not_cherry_picked() -> None:
    analysis = json.loads(
        (ROOT / "data/frozen/natural_workload_analysis.json").read_text()
    )
    assert analysis["successful_positive_families"] == [
        "controlled_power_ladder",
        "diagonal_hamiltonian",
        "qaoa_ising",
        "qpe_controlled_powers",
        "trotter_commuting_blocks",
    ]
    assert analysis["negative_systematic_regressions"] == 0
    summary = pd.read_csv(ROOT / "data/frozen/natural_workload_summary.csv")
    assert len(summary) == 9
    assert set(summary.workload_class) == {"natural_positive", "negative_control"}
    negative = pd.read_csv(ROOT / "data/frozen/natural_negative_controls.csv")
    assert len(negative) == 10
    assert not negative.systematic_regression.any()


def test_all_six_main_effects_and_pairwise_interactions_are_reported() -> None:
    effects = pd.read_csv(ROOT / "data/frozen/natural_ablation_effects.csv")
    interactions = pd.read_csv(
        ROOT / "data/frozen/natural_ablation_interactions.csv"
    )
    factors = {
        "semantic_lift",
        "aggregation",
        "selector",
        "cache_reuse",
        "preset_recognizer",
        "projected_block_selection",
    }
    assert set(effects.factor) == factors
    assert len({tuple(sorted(pair)) for pair in zip(interactions.factor_a, interactions.factor_b)}) == 15
    assert set(interactions.metric) == {"gates", "cx", "runtime_s"}


def test_qre_is_end_to_end_not_a_t_count_alias() -> None:
    frame = pd.read_parquet(FROZEN)
    required = {
        "logical_t_states",
        "qre_physical_qubits",
        "qre_factory_physical_qubits",
        "qre_factories",
        "qre_cycles",
        "qre_runtime_seconds",
        "spacetime_qubit_seconds",
        "qre_epsilon_total",
    }
    assert required.issubset(frame.columns)
    assert (frame.qre_epsilon_total == 1.0e-6).all()
    assert (frame.qre_physical_qubits > 0).all()
    assert (frame.qre_factory_physical_qubits > 0).all()
    assert (frame.spacetime_qubit_seconds > 0).all()

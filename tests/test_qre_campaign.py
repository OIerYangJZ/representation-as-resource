from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from scripts.allocate_synthesis_error import (
    equal_decimal_allocation,
    split_error_budget,
    t_cost_greedy_allocation,
)
from scripts.analyze_qre_campaign import validate
from scripts.run_qre_campaign import schedule_qre


ROOT = Path(__file__).resolve().parents[1]


def test_total_error_split_is_additive_and_shared() -> None:
    budget = split_error_budget(
        1e-6,
        {"algorithmic": 0.1, "synthesis": 0.45, "logical": 0.45},
    )
    assert budget.epsilon_algorithmic == pytest.approx(1e-7)
    assert budget.epsilon_synthesis == pytest.approx(4.5e-7)
    assert budget.epsilon_logical == pytest.approx(4.5e-7)
    assert budget.allocated_total == pytest.approx(budget.epsilon_total)
    with pytest.raises(ValueError, match="sum to one"):
        split_error_budget(
            1e-6,
            {"algorithmic": 0.1, "synthesis": 0.5, "logical": 0.5},
        )


def test_equal_and_measured_cost_allocations_never_exceed_budget() -> None:
    multiplicities = {"a": 90, "b": 10}
    epsilon = 4.5e-4
    equal = equal_decimal_allocation(multiplicities, epsilon)
    precision = equal["groups"]["a"]["decimal_precision"]
    costs = {
        "a": {precision: 100, precision - 1: 90},
        "b": {precision: 100, precision - 1: 40},
    }
    greedy = t_cost_greedy_allocation(multiplicities, epsilon, costs)
    assert equal["allocated_total"] <= epsilon
    assert greedy["allocated_total"] <= epsilon
    assert greedy["steps"]
    equal_t = sum(
        item["multiplicity"] * costs[key][item["decimal_precision"]]
        for key, item in equal["groups"].items()
    )
    greedy_t = sum(
        item["multiplicity"] * costs[key][item["decimal_precision"]]
        for key, item in greedy["groups"].items()
    )
    assert greedy_t < equal_t


def test_surface_code_schedule_meets_logical_budget() -> None:
    profile = yaml.safe_load(
        (ROOT / "qre/configs/surface_code_conservative.yaml").read_text()
    )
    factory = {"id": "parallel_16", "requested_factories": 16}
    qre = schedule_qre(
        {"logical_qubits": 4, "output_depth": 24},
        logical_t_states=1800,
        logical_error_budget=4.5e-7,
        profile=profile,
        factory_profile=factory,
    )
    assert qre["logical_failure_bound"] <= 4.5e-7
    assert qre["physical_qubits"] == (
        qre["data_physical_qubits"] + qre["factory_physical_qubits"]
    )
    assert qre["spacetime_qubit_seconds"] == pytest.approx(
        qre["physical_qubits"] * qre["runtime_seconds"]
    )


def test_error_schema_and_campaign_use_required_total_error_grid() -> None:
    schema = json.loads((ROOT / "qre/error_budget_schema.json").read_text())
    campaign = yaml.safe_load((ROOT / "qre/configs/campaign.yaml").read_text())
    assert schema["properties"]["composition"]["const"] == "additive_union_bound"
    assert campaign["error_budget"]["epsilon_totals"] == [1e-3, 1e-6, 1e-9]
    assert set(campaign["error_budget"]["synthesis_allocation_policies"]) == {
        "equal_decimal",
        "t_cost_greedy",
    }


def test_frozen_qre_matrix_is_complete_certified_and_within_budget() -> None:
    frame = pd.read_parquet(ROOT / "data/frozen/qre_results.parquet")
    audit = validate(frame)
    assert audit["observed_rows"] == 288
    assert audit["total_error_violations"] == 0
    assert audit["certificate_missing"] == 0
    assert audit["dense_certificate_failures"] == 0
    assert set(frame["pipeline_category"]) == {
        "semantic-first",
        "materialize-first",
        "external-semantic-capable",
    }


def test_materialize_conclusion_is_stable_but_semantic_tools_are_not_conflated() -> None:
    frame = pd.read_parquet(ROOT / "data/frozen/qre_results.parquet")
    index = [
        "target_id",
        "epsilon_total",
        "allocation_policy",
        "qec_profile",
        "requested_factories",
    ]
    pivot = frame.pivot(
        index=index, columns="pipeline_id", values="spacetime_qubit_seconds"
    )
    assert (pivot["materialize_first"] > pivot["semantic_first"]).all()
    assert (pivot["materialize_first"] > pivot["external_tket_paulisimp"]).all()
    # The external path remains separately classified even when it recovers a
    # more compact form than the authors' semantic-first implementation.
    assert (pivot["external_tket_paulisimp"] < pivot["semantic_first"]).all()

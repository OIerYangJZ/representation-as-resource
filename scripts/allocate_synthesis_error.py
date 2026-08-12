#!/usr/bin/env python3
"""Allocate one fixed synthesis-error budget across logical rotations.

The public CLI is intentionally independent of the QRE runner.  The equal
policy rounds *down* to a decimal error radius understood by staq grid_synth.
The optional discrete policy uses a measured T-cost table and spends the
remaining decimal slack greedily without exceeding the same total budget.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


SCHEMA = "ucc.qre.synthesis-allocation.v1"


@dataclass(frozen=True)
class ErrorBudget:
    epsilon_total: float
    epsilon_algorithmic: float
    epsilon_synthesis: float
    epsilon_logical: float

    @property
    def allocated_total(self) -> float:
        return self.epsilon_algorithmic + self.epsilon_synthesis + self.epsilon_logical

    def as_dict(self) -> dict[str, float]:
        return {
            "epsilon_total": self.epsilon_total,
            "epsilon_algorithmic": self.epsilon_algorithmic,
            "epsilon_synthesis": self.epsilon_synthesis,
            "epsilon_logical": self.epsilon_logical,
            "allocated_total": self.allocated_total,
        }


def split_error_budget(
    epsilon_total: float,
    fractions: Mapping[str, float],
    *,
    tolerance: float = 1e-12,
) -> ErrorBudget:
    """Validate and split an additive total-error budget."""

    if not math.isfinite(epsilon_total) or not 0.0 < epsilon_total <= 1.0:
        raise ValueError("epsilon_total must lie in (0, 1]")
    required = {"algorithmic", "synthesis", "logical"}
    if set(fractions) != required:
        raise ValueError(f"fractions must have exactly {sorted(required)}")
    values = {key: float(fractions[key]) for key in required}
    if any(not math.isfinite(value) or value < 0.0 for value in values.values()):
        raise ValueError("error-budget fractions must be finite and nonnegative")
    if values["synthesis"] <= 0.0 or values["logical"] <= 0.0:
        raise ValueError("synthesis and logical fractions must be positive")
    if not math.isclose(sum(values.values()), 1.0, rel_tol=0.0, abs_tol=tolerance):
        raise ValueError("error-budget fractions must sum to one")
    return ErrorBudget(
        epsilon_total=epsilon_total,
        epsilon_algorithmic=epsilon_total * values["algorithmic"],
        epsilon_synthesis=epsilon_total * values["synthesis"],
        epsilon_logical=epsilon_total * values["logical"],
    )


def _validate_multiplicities(multiplicities: Mapping[str, int]) -> dict[str, int]:
    result = {str(key): int(value) for key, value in multiplicities.items()}
    if not result or any(value <= 0 for value in result.values()):
        raise ValueError("multiplicities must be a nonempty map of positive integers")
    return dict(sorted(result.items()))


def equal_decimal_allocation(
    multiplicities: Mapping[str, int],
    epsilon_synthesis: float,
) -> dict[str, Any]:
    """Give every rotation one common decimal radius with a certified sum."""

    groups = _validate_multiplicities(multiplicities)
    if not math.isfinite(epsilon_synthesis) or epsilon_synthesis <= 0.0:
        raise ValueError("epsilon_synthesis must be positive and finite")
    rotation_count = sum(groups.values())
    precision = max(1, int(math.ceil(math.log10(rotation_count / epsilon_synthesis))))
    per_rotation = 10.0 ** (-precision)
    allocated = rotation_count * per_rotation
    if allocated > epsilon_synthesis * (1.0 + 1e-12):
        raise AssertionError("decimal allocation exceeded synthesis budget")
    return {
        "schema": SCHEMA,
        "policy": "equal_decimal",
        "rotation_count": rotation_count,
        "epsilon_synthesis": epsilon_synthesis,
        "allocated_total": allocated,
        "unused_budget": epsilon_synthesis - allocated,
        "groups": {
            key: {
                "multiplicity": multiplicity,
                "decimal_precision": precision,
                "epsilon_per_rotation": per_rotation,
            }
            for key, multiplicity in groups.items()
        },
    }


def t_cost_greedy_allocation(
    multiplicities: Mapping[str, int],
    epsilon_synthesis: float,
    t_costs: Mapping[str, Mapping[int, int]],
    *,
    minimum_precision: int = 1,
) -> dict[str, Any]:
    """Spend equal-policy slack using measured discrete T costs.

    Starting at the safe equal decimal precision, a group may move to the next
    looser measured precision only when the additive allocation still fits.
    Each step maximizes T-state savings per added error.  This is a documented
    greedy upper construction, not a proof of globally optimal allocation.
    """

    equal = equal_decimal_allocation(multiplicities, epsilon_synthesis)
    groups = _validate_multiplicities(multiplicities)
    current = {
        key: int(equal["groups"][key]["decimal_precision"])
        for key in groups
    }
    allocated = float(equal["allocated_total"])
    steps: list[dict[str, Any]] = []
    while True:
        candidates: list[tuple[float, int, str, int, float, int]] = []
        for key, multiplicity in groups.items():
            old_precision = current[key]
            new_precision = old_precision - 1
            if new_precision < minimum_precision:
                continue
            table = t_costs.get(key, {})
            if old_precision not in table or new_precision not in table:
                continue
            old_t = int(table[old_precision]) * multiplicity
            new_t = int(table[new_precision]) * multiplicity
            saving = old_t - new_t
            added_error = multiplicity * (
                10.0 ** (-new_precision) - 10.0 ** (-old_precision)
            )
            if saving <= 0 or allocated + added_error > epsilon_synthesis * (1.0 + 1e-12):
                continue
            ratio = saving / added_error
            candidates.append((ratio, saving, key, new_precision, added_error, new_t))
        if not candidates:
            break
        _, saving, key, new_precision, added_error, _ = max(
            candidates, key=lambda item: (item[0], item[1], item[2])
        )
        old_precision = current[key]
        current[key] = new_precision
        allocated += added_error
        steps.append(
            {
                "group": key,
                "from_precision": old_precision,
                "to_precision": new_precision,
                "added_error": added_error,
                "t_saving": saving,
            }
        )
    result_groups = {
        key: {
            "multiplicity": multiplicity,
            "decimal_precision": current[key],
            "epsilon_per_rotation": 10.0 ** (-current[key]),
        }
        for key, multiplicity in groups.items()
    }
    recomputed = sum(
        item["multiplicity"] * item["epsilon_per_rotation"]
        for item in result_groups.values()
    )
    if not math.isclose(recomputed, allocated, rel_tol=1e-12, abs_tol=1e-30):
        raise AssertionError("allocation bookkeeping mismatch")
    if allocated > epsilon_synthesis * (1.0 + 1e-12):
        raise AssertionError("cost-greedy allocation exceeded synthesis budget")
    return {
        "schema": SCHEMA,
        "policy": "t_cost_greedy",
        "optimization_claim": "greedy measured-cost upper construction; not globally optimal",
        "rotation_count": sum(groups.values()),
        "epsilon_synthesis": epsilon_synthesis,
        "allocated_total": allocated,
        "unused_budget": epsilon_synthesis - allocated,
        "equal_decimal_precision": next(
            iter(equal["groups"].values())
        )["decimal_precision"],
        "steps": steps,
        "groups": result_groups,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epsilon-total", type=float, required=True)
    parser.add_argument("--algorithmic-fraction", type=float, default=0.0)
    parser.add_argument("--synthesis-fraction", type=float, default=0.5)
    parser.add_argument("--logical-fraction", type=float, default=0.5)
    parser.add_argument("--rotation-count", type=int, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    budget = split_error_budget(
        args.epsilon_total,
        {
            "algorithmic": args.algorithmic_fraction,
            "synthesis": args.synthesis_fraction,
            "logical": args.logical_fraction,
        },
    )
    allocation = equal_decimal_allocation(
        {"all_rotations": args.rotation_count}, budget.epsilon_synthesis
    )
    print(json.dumps({"budget": budget.as_dict(), "allocation": allocation}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

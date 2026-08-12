#!/usr/bin/env python3
"""Fail-loud verifier for the unbounded independent-Pauli witness metadata."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


HERE = Path(__file__).resolve().parent


def rank_f2(rows: list[list[int]]) -> tuple[int, list[int]]:
    matrix = [row[:] for row in rows]
    if not matrix:
        return 0, []
    width = len(matrix[0])
    pivot_row = 0
    pivots: list[int] = []
    for column in range(width):
        pivot = next(
            (index for index in range(pivot_row, len(matrix)) if matrix[index][column]),
            None,
        )
        if pivot is None:
            continue
        matrix[pivot_row], matrix[pivot] = matrix[pivot], matrix[pivot_row]
        for index in range(len(matrix)):
            if index != pivot_row and matrix[index][column]:
                matrix[index] = [
                    left ^ right
                    for left, right in zip(matrix[index], matrix[pivot_row])
                ]
        pivots.append(column)
        pivot_row += 1
        if pivot_row == len(matrix):
            break
    return pivot_row, pivots


def validate_metadata(spec: dict) -> dict:
    n = spec.get("n")
    m = spec.get("m")
    supports = spec.get("support_vectors")
    if not isinstance(n, int) or not isinstance(m, int) or not isinstance(supports, list):
        raise AssertionError("n, m, and support_vectors must be declared")
    if len(supports) != m:
        raise AssertionError(f"support row count {len(supports)} != m={m}")
    rows = [entry.get("bits") for entry in supports]
    if any(not isinstance(row, list) or len(row) != n for row in rows):
        raise AssertionError("every support row must be a declared n-bit list")
    if any(bit not in (0, 1) for row in rows for bit in row):
        raise AssertionError("support matrix must contain only exact bits 0 or 1")
    rank, pivots = rank_f2(rows)
    if rank != m:
        raise AssertionError(f"support rank {rank} != m={m}; rows are not independent")
    if spec.get("declared_support_rank_f2") != rank:
        raise AssertionError("declared_support_rank_f2 disagrees with exact elimination")

    certificate = spec.get("certificate", {})
    expression = certificate.get("irrational_angle_expression")
    if not isinstance(expression, str) or "sqrt(2)" not in expression:
        raise AssertionError("missing exact irrational-angle declaration")
    if not any(entry.get("irrational") is True for entry in supports):
        raise AssertionError("no support term is explicitly declared irrational")
    if certificate.get("proposition_label") != "prop:fooling-set":
        raise AssertionError("wrong or missing Proposition 1 label")
    if certificate.get("lemma_label") != "lem:pauli-uniqueness":
        raise AssertionError("wrong or missing coefficient-uniqueness lemma label")
    if certificate.get("unbounded_noncollision_by_proposition") is not True:
        raise AssertionError("unbounded proposition certificate is not asserted")
    if certificate.get("support_rank_verified") is not True:
        raise AssertionError("support_rank_verified is not true")
    return {"rank_f2": rank, "pivots": pivots, "irrational_expression": expression}


def verify_lowering_identity(atol: float = 1e-12) -> float:
    import numpy as np
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Operator, Pauli

    theta = math.pi * math.sqrt(2) / 11
    lowered = QuantumCircuit(2)
    lowered.rz(theta, 0)
    lowered.rz(theta, 1)
    lowered.cp(-2 * theta, 0, 1)
    z_z = Pauli("ZZ").to_matrix()
    target = math.e ** (-0.5j * theta) * (
        np.cos(theta / 2) * np.eye(4) - 1j * np.sin(theta / 2) * z_z
    )
    error = float(np.max(np.abs(Operator(lowered).data - target)))
    if error > atol:
        raise AssertionError(f"RZ/RZ/CP lowering error {error} exceeds {atol}")
    return error


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, default=HERE / "unbounded_witness_spec.json")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    result = validate_metadata(spec)
    result["lowering_max_abs_error"] = verify_lowering_identity()
    result.update(
        {
            "support_rank_verified": True,
            "unbounded_noncollision_by_proposition": True,
            "certificate_kind": "symbolic proposition application",
            "status": "passed",
        }
    )
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()

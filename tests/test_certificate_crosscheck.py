from __future__ import annotations

import hashlib
import json
import unittest
from fractions import Fraction

from certificates.audit import equivalent_pair
from certificates.canonicalize import (
    ExactCircuit,
    ExactOperation,
    PauliAxis,
    SymbolicAngle,
    canonicalize,
)
from certificates.symbolic_checker import (
    certified_quality_mean,
    check_equivalence,
    dense_check,
)


class CertificateCrosscheckTests(unittest.TestCase):
    def test_modulo_two_pi_global_phase_and_order_canonicalization(self):
        first = PauliAxis(3, 0, (1 << 0) | (1 << 1))
        second = PauliAxis(3, 0, 1 << 2)
        reference = ExactCircuit.of(3, [
            ExactOperation.rotation(first, Fraction(1, 8)),
            ExactOperation.rotation(second, Fraction(3, 16)),
        ])
        candidate = ExactCircuit.of(3, [
            ExactOperation.rotation(second, Fraction(35, 16)),
            ExactOperation.rotation(first, Fraction(1, 16)),
            ExactOperation.rotation(first, Fraction(1, 16)),
            ExactOperation.global_phase(Fraction(5, 7)),
        ], global_phase_over_pi=Fraction(9, 11))
        result = check_equivalence(reference, candidate)
        self.assertEqual(result["status"], "completed_valid")
        self.assertEqual(canonicalize(reference).to_bytes(), canonicalize(candidate).to_bytes())

    def test_clifford_frame_conjugation_is_canonical(self):
        reference = ExactCircuit.of(2, [
            ExactOperation.clifford("h", 0),
            ExactOperation.clifford("cx", 0, 1),
            ExactOperation.rz(1, Fraction(3, 16)),
            ExactOperation.clifford("cx", 0, 1),
            ExactOperation.clifford("h", 0),
        ])
        candidate = ExactCircuit.of(2, [
            ExactOperation.rotation(PauliAxis(2, 1 << 0, 1 << 1), Fraction(3, 16)),
        ])
        self.assertEqual(check_equivalence(reference, candidate)["status"], "completed_valid")
        dense = dense_check(reference, candidate)
        self.assertEqual(dense["status"], "completed_valid")
        self.assertLess(dense["projective_distance"], 1e-12)

    def test_pauli_sign_is_moved_exactly_into_coefficient(self):
        negative_axis = PauliAxis(2, 1 << 0, 1 << 1, -1)
        positive_axis = PauliAxis(2, 1 << 0, 1 << 1, 1)
        reference = ExactCircuit.of(2, [
            ExactOperation.rotation(negative_axis, Fraction(5, 32)),
        ])
        candidate = ExactCircuit.of(2, [
            ExactOperation.rotation(positive_axis, Fraction(-5, 32)),
        ])
        self.assertEqual(check_equivalence(reference, candidate)["status"], "completed_valid")
        self.assertEqual(dense_check(reference, candidate)["status"], "completed_valid")

    def test_width_one_through_six_symbolic_and_dense_agree(self):
        for width in range(1, 7):
            with self.subTest(width=width):
                reference, candidate = equivalent_pair(width)
                symbolic = check_equivalence(reference, candidate)
                dense = dense_check(reference, candidate)
                self.assertEqual(symbolic["status"], "completed_valid")
                self.assertEqual(dense["status"], symbolic["status"])
                self.assertLess(dense["projective_distance"], 1e-12)

    def test_each_supported_clifford_conjugation_matches_dense_semantics(self):
        cases = (
            ("h", (0,), "h"), ("s", (0,), "sdg"), ("sdg", (0,), "s"),
            ("x", (0,), "x"), ("y", (0,), "y"), ("z", (0,), "z"),
            ("cx", (0, 1), "cx"), ("cz", (0, 1), "cz"),
            ("swap", (0, 1), "swap"),
        )
        for gate, qubits, inverse in cases:
            for rotation_qubit in range(2):
                with self.subTest(gate=gate, rotation_qubit=rotation_qubit):
                    source = ExactCircuit.of(2, [
                        ExactOperation.clifford(gate, *qubits),
                        ExactOperation.rz(rotation_qubit, Fraction(3, 16)),
                        ExactOperation.clifford(inverse, *qubits),
                    ])
                    form = canonicalize(source)
                    self.assertEqual(len(form.rotations), 1)
                    rotation = form.rotations[0]
                    candidate = ExactCircuit.of(2, [
                        ExactOperation.rotation(rotation.axis, rotation.coefficient),
                    ])
                    self.assertEqual(check_equivalence(source, candidate)["status"], "completed_valid")
                    dense = dense_check(source, candidate)
                    self.assertEqual(dense["status"], "completed_valid")
                    self.assertLess(dense["projective_distance"], 1e-12)

    def test_completed_valid_always_has_content_addressed_certificate(self):
        reference, candidate = equivalent_pair(4)
        result = check_equivalence(reference, candidate)
        self.assertEqual(result["status"], "completed_valid")
        certificate = dict(result["independent_certificate"])
        digest = certificate.pop("certificate_sha256")
        payload = (json.dumps(certificate, sort_keys=True, separators=(",", ":")) + "\n").encode()
        self.assertEqual(hashlib.sha256(payload).hexdigest(), digest)
        self.assertTrue(certificate["accepted"])
        self.assertTrue(all(certificate["proof_obligations"].values()))

    def test_formal_symbol_coefficients_split_and_compare_exactly(self):
        axis = PauliAxis(2, 0, (1 << 0) | (1 << 1))
        angle = SymbolicAngle.make(Fraction(1, 8), {"theta": Fraction(3, 5)})
        half = SymbolicAngle.make(Fraction(1, 16), {"theta": Fraction(3, 10)})
        reference = ExactCircuit.of(2, [ExactOperation.rotation(axis, angle)])
        candidate = ExactCircuit.of(2, [
            ExactOperation.rotation(axis, half), ExactOperation.rotation(axis, half),
        ])
        changed = ExactCircuit.of(2, [
            ExactOperation.rotation(
                axis, SymbolicAngle.make(Fraction(1, 8), {"theta": Fraction(3, 5), "eta": 1})
            )
        ])
        self.assertEqual(check_equivalence(reference, candidate)["status"], "completed_valid")
        self.assertEqual(check_equivalence(reference, changed)["status"], "completed_invalid")
        self.assertEqual(dense_check(reference, candidate)["status"], "numerical_inconclusive")

    def test_five_statuses_and_quality_exclusion_policy(self):
        identity = ExactCircuit.of(1, [])
        valid = check_equivalence(identity, identity)
        invalid = check_equivalence(identity, ExactCircuit.of(2, []))
        unsupported = check_equivalence(identity, ExactCircuit.of(1, [ExactOperation("t", (0,))]))
        predicate = check_equivalence(identity, ExactCircuit.of(1, [
            ExactOperation.rotation(PauliAxis(1, 1, 0), Fraction(1, 8)),
            ExactOperation.rotation(PauliAxis(1, 0, 1), Fraction(1, 8)),
        ]))
        numerical = check_equivalence(identity, ExactCircuit.of(1, [ExactOperation.rz(0, 0.125)]))
        self.assertEqual(
            {row["status"] for row in (valid, invalid, unsupported, predicate, numerical)},
            {"completed_valid", "completed_invalid", "unsupported", "predicate_error", "numerical_inconclusive"},
        )
        rows = [
            {"status": "completed_valid", "quality": 2.0},
            {"status": "completed_valid", "quality": 4.0},
            {"status": "unsupported", "quality": -1000.0},
            {"status": "predicate_error", "quality": 0.0},
        ]
        summary = certified_quality_mean(rows, "quality")
        self.assertEqual(summary["mean_completed_valid"], 3.0)
        self.assertEqual(summary["included_completed_valid"], 2)
        self.assertEqual(summary["excluded_status_counts"]["unsupported"], 1)

    def test_dense_width_limit_is_explicit(self):
        circuit = ExactCircuit.of(7, [])
        self.assertEqual(dense_check(circuit, circuit)["status"], "unsupported")


if __name__ == "__main__":
    unittest.main()

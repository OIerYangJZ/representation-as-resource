from __future__ import annotations

import unittest

from certificates.audit import MUTATION_KINDS, mutate, mutation_reference
from certificates.symbolic_checker import check_equivalence, dense_check


class CertificateMutationTests(unittest.TestCase):
    def test_all_adversarial_mutations_are_rejected_without_dense_disagreement(self):
        false_accepts = []
        disagreements = []
        observed = set()
        for variant in range(8):
            reference = mutation_reference(variant)
            for kind in MUTATION_KINDS:
                with self.subTest(variant=variant, mutation=kind):
                    observed.add(kind)
                    candidate = mutate(reference, kind)
                    symbolic = check_equivalence(reference, candidate)
                    dense = dense_check(reference, candidate)
                    if symbolic["status"] == "completed_valid":
                        false_accepts.append((variant, kind))
                    if symbolic["status"] != dense["status"]:
                        disagreements.append((variant, kind, symbolic["status"], dense["status"]))
                    self.assertEqual(symbolic["status"], "completed_invalid")
                    self.assertEqual(dense["status"], "completed_invalid")
                    self.assertGreater(dense["projective_distance"], dense["reject_tolerance"])
        self.assertEqual(observed, set(MUTATION_KINDS))
        self.assertEqual(false_accepts, [])
        self.assertEqual(disagreements, [])


if __name__ == "__main__":
    unittest.main()

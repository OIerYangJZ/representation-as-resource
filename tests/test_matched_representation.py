from __future__ import annotations

import unittest
from pathlib import Path

from benchmarks.representation_generators import (
    REPRESENTATIONS,
    canonical_target,
    generate_representation,
    make_target,
    pyzx_certificate,
    qasm_bytes,
    validate_representation_set,
)
from scripts.run_matched_matrix import COMPILERS, expand_cells, load_plan, phase_table_aggregate


ROOT = Path(__file__).resolve().parents[1]


class MatchedRepresentationTests(unittest.TestCase):
    def target(self):
        return make_target({
            "target_id": "unit-test-target", "m": 6, "r": 4, "K": 8,
            "density": 0.5, "target_seed": 4101,
        })

    def test_all_representations_share_one_certificate(self):
        target = self.target()
        generated = validate_representation_set(target, 20260811)
        self.assertEqual([item.representation for item in generated], list(REPRESENTATIONS))
        reference = qasm_bytes(canonical_target(target))
        self.assertTrue(all(pyzx_certificate(reference, item.qasm)["passed"] for item in generated))
        self.assertEqual(len({item.representation_id for item in generated}), len(REPRESENTATIONS))

    def test_masked_shares_are_nontrivial_and_sum_modulo_wraparound(self):
        target = self.target()
        generated = generate_representation(target, "masked_share_update", 20260812)
        modulus = 8 * target.K
        by_generator = {}
        for token in generated.tokens:
            share = int(token.angle_over_pi * 4 * target.K)
            self.assertNotIn(share % modulus, {0, target.x[token.generator] % modulus})
            by_generator.setdefault(token.generator, []).append(share)
        for generator, shares in by_generator.items():
            self.assertEqual(sum(shares) % modulus, target.x[generator] % modulus)
            self.assertEqual(len(shares), target.r)

    def test_target_is_fixed_across_representation_seed_and_not_all_ones(self):
        target = self.target()
        first = generate_representation(target, "random_commuting_order", 20260811)
        second = generate_representation(target, "random_commuting_order", 20260812)
        self.assertEqual(first.target.x, second.target.x)
        self.assertLess(len(target.active_support), target.m)
        self.assertNotEqual(first.representation_id, second.representation_id)

    def test_full_aggregator_reads_input_semantics(self):
        target = self.target()
        represented = generate_representation(target, "masked_share_update", 20260811)
        candidate = phase_table_aggregate(represented.circuit)
        certificate = pyzx_certificate(qasm_bytes(canonical_target(target)), qasm_bytes(candidate))
        self.assertTrue(certificate["passed"])

    def test_manifest_expands_to_complete_cartesian_product(self):
        plan = load_plan(ROOT / "benchmarks/matched_manifest.yaml")
        index = []
        for target in plan["targets"]:
            for seed in plan["seeds"]:
                for representation in plan["representations"]:
                    index.append({
                        "target_id": target["target_id"], "seed": seed, "representation": representation,
                        "representation_id": f"rep-{target['target_id']}-{seed}-{representation}",
                        "manifest_path": "unused", "manifest_sha256": "0" * 64,
                    })
        cells = expand_cells(index, plan)
        expected = len(plan["targets"]) * len(REPRESENTATIONS) * len(COMPILERS) * len(plan["seeds"])
        self.assertEqual(len(cells), expected)
        self.assertEqual(len({cell["cell_id"] for cell in cells}), expected)
        keys = {(cell["target_id"], cell["representation"], cell["compiler"], cell["seed"]) for cell in cells}
        self.assertEqual(len(keys), expected)


if __name__ == "__main__":
    unittest.main()

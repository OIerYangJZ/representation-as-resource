from __future__ import annotations

import unittest

from benchmarks.representation_generators import (
    canonical_target,
    make_target,
    pyzx_certificate,
    qasm_bytes,
)
from scripts.run_external_baselines import (
    _classify_certificate,
    bridge_input,
    compile_baseline,
    expand_specs,
    load_baseline_configs,
    load_campaign_config,
)


class ExternalBaselineTests(unittest.TestCase):
    def target(self):
        return make_target({
            "target_id": "w5-test", "m": 4, "r": 2, "K": 8,
            "density": 0.5, "target_seed": 501,
        })

    def test_registry_has_three_classes_and_native_unified_pairs(self):
        configs = load_baseline_configs()
        self.assertEqual(len(configs), 8)
        self.assertEqual({row["category"] for row in configs}, {
            "local", "semantic-capable", "authors-reference",
        })
        for tool in {row["tool"] for row in configs}:
            self.assertEqual(
                {row["mode"] for row in configs if row["tool"] == tool},
                {"recommended_native", "unified_target_basis"},
            )

    def test_campaign_expands_complete_representation_baseline_matrix(self):
        specs = expand_specs(load_campaign_config(), load_baseline_configs())
        self.assertEqual(len(specs), 216 * 8)
        self.assertEqual(len({row["cell_id"] for row in specs}), 216 * 8)
        keys = {(row["representation_id"], row["baseline_id"]) for row in specs}
        self.assertEqual(len(keys), 216 * 8)

    def test_all_bridges_and_compilers_use_common_certificate(self):
        reference = canonical_target(self.target())
        source_qasm = qasm_bytes(reference)
        for config in load_baseline_configs():
            with self.subTest(config=config["id"]):
                _, post, _, post_qasm, _ = bridge_input(source_qasm, config["tool"])
                self.assertTrue(pyzx_certificate(source_qasm, qasm_bytes(post))["passed"])
                candidate, _, certificate_qasm, _, _ = compile_baseline(
                    post_qasm, config, seed=502, target_basis=["cx", "rz", "h"],
                )
                self.assertTrue(pyzx_certificate(source_qasm, certificate_qasm)["passed"])
                if config["mode"] == "unified_target_basis":
                    gate_types = {item.operation.name for item in candidate.data}
                    self.assertFalse(gate_types - {"cx", "rz", "h", "barrier", "id"})

    def test_inconclusive_and_exact_inequality_have_distinct_statuses(self):
        from qiskit import QuantumCircuit

        identity = QuantumCircuit(2)
        phase = QuantumCircuit(2)
        phase.cx(0, 1)
        phase.rz(0.25, 1)
        phase.cx(0, 1)
        false_certificate = {"passed": False, "status": "inconclusive"}
        self.assertEqual(_classify_certificate(identity, identity, false_certificate), "predicate_error")
        self.assertEqual(_classify_certificate(identity, phase, false_certificate), "correctness_failure")


if __name__ == "__main__":
    unittest.main()

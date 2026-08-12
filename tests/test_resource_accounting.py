from __future__ import annotations

import json
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

from encoding.codec import (
    CircuitDAG,
    CommittedOutput,
    ControlState,
    IRField,
    IREdge,
    IRNode,
    Instruction,
    LiveWindow,
    ParameterEntry,
    ParameterLedger,
    PauliSupport,
    StoreState,
    SymbolicParameter,
    decode_exact,
    encode,
)
from instrumentation.resource_accounting import (
    ResourceAccountant,
    ResourceSnapshot,
    assert_rows_file_backed,
    build_example_trace,
    load_measurement,
    verify_manifest,
)


def snapshot(address: int = 8) -> ResourceSnapshot:
    parameter = SymbolicParameter(Fraction(5, 17), ((address, Fraction(-2, 9)),))
    instruction = Instruction(
        "rzz",
        (0, address),
        PauliSupport(((0, "Z"), (address, "Z"))),
        (parameter,),
    )
    dag = CircuitDAG(
        address + 1,
        (IRNode(0, Instruction("id", (0,))), IRNode(address, instruction)),
        (IREdge(0, address, 1),) if address else (),
    )
    committed = encode(CommittedOutput("target-basis", b"rzz"))
    return ResourceSnapshot(
        ControlState({"head": address, "pass_count": 3}),
        StoreState({"aggregate_keys": [address]}),
        LiveWindow((instruction,)),
        ParameterLedger((ParameterEntry((0, address, 0), parameter),)),
        IRField((dag,)),
        committed,
        pass_count=3,
        pass_index=1,
    )


class ResourceAccountingTests(unittest.TestCase):
    def test_all_formal_components_come_from_actual_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            row = ResourceAccountant(directory, "run").measure("cut-001", snapshot())
            self.assertEqual(row["p"], 3)
            self.assertEqual(
                row["B_cut_bytes"],
                sum(row[f"B_{name}_bytes"] for name in ("control", "store", "window", "parameter", "ir")),
            )
            self.assertEqual(row["B_cut_bits"], 8 * row["B_cut_bytes"])
            self.assertEqual(row["B_com_bits"], 8 * row["B_com_bytes"])
            for name in ("control", "store", "window", "parameter", "ir", "committed"):
                path = Path(row[f"{name}_artifact_path"])
                self.assertTrue(path.is_file())
                self.assertEqual(path.stat().st_size, row[f"{name}_bytes"])
            self.assertEqual(load_measurement(row["artifact_manifest_path"])["B_cut_bits"], row["B_cut_bits"])
            assert_rows_file_backed([row])

    def test_digest_verifier_detects_edited_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            row = ResourceAccountant(directory, "run").measure("cut", snapshot())
            store_path = Path(row["store_artifact_path"])
            store_path.write_bytes(store_path.read_bytes() + b"x")
            with self.assertRaises(ValueError):
                verify_manifest(row["artifact_manifest_path"])

    def test_growing_width_addresses_and_ir_edges_are_charged(self) -> None:
        small_instruction = Instruction("x", (127,))
        large_instruction = Instruction("x", (128,))
        self.assertGreater(len(encode(large_instruction)), len(encode(small_instruction)))

        one_small_node = CircuitDAG(2, (IRNode(1, Instruction("x", (1,))),), ())
        one_large_node = CircuitDAG(16385, (IRNode(16384, Instruction("x", (16384,))),), ())
        self.assertEqual(len(one_small_node.nodes), len(one_large_node.nodes))
        self.assertGreater(len(encode(one_large_node)), len(encode(one_small_node)))

        no_edge = CircuitDAG(2, (IRNode(0, Instruction("x", (0,))), IRNode(1, Instruction("x", (1,)))), ())
        with_edge = CircuitDAG(
            2,
            no_edge.nodes,
            (IREdge(0, 1, 0),),
        )
        self.assertGreater(len(encode(with_edge)), len(encode(no_edge)))

    def test_conditional_dictionary_is_explicit_not_silently_free(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = snapshot()
            conditional = ResourceSnapshot(
                base.control,
                base.store,
                base.window,
                base.parameter,
                base.ir,
                base.committed_prefix,
                base.pass_count,
                base.pass_index,
                "conditional",
                "b" * 64,
                4096,
            )
            row = ResourceAccountant(directory, "conditional").measure("cut", conditional)
            manifest = json.loads(Path(row["artifact_manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["description"]["dictionary_bytes"], 4096)
            self.assertFalse(manifest["description"]["dictionary_charged_in_cut"])

    def test_deterministic_example_trace_is_fully_verifiable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rows = build_example_trace(Path(directory))
            self.assertEqual(len(rows), 3)
            assert_rows_file_backed(rows)
            final = Path(rows[-1]["committed_artifact_path"]).read_bytes()
            self.assertIsInstance(decode_exact(final), CommittedOutput)
            self.assertGreater(rows[-1]["B_com_bytes"], rows[0]["B_com_bytes"])


if __name__ == "__main__":
    unittest.main()

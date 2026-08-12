from __future__ import annotations

import hashlib
import unittest
from fractions import Fraction

from encoding.codec import (
    AggregateRecord,
    CertificateInput,
    CircuitDAG,
    CommittedOutput,
    ControlState,
    ExternalToolOutput,
    FlatUpdateStream,
    IRField,
    IREdge,
    IRNode,
    Instruction,
    LiveWindow,
    ParameterEntry,
    ParameterLedger,
    PauliSupport,
    SemanticStream,
    StoreState,
    SymbolicParameter,
    UpdateRecord,
    decode_exact,
    encode,
    semantic_signature,
)


class CodecRoundTripTests(unittest.TestCase):
    def setUp(self) -> None:
        self.support = PauliSupport(((130, "z"), (0, "Z")))
        self.parameter = SymbolicParameter(
            Fraction(-7, 19), ((128, Fraction(2, 3)), (4, Fraction(-5, 11)))
        )
        self.instruction = Instruction(
            "pauli_rotation", (0, 130), self.support, (self.parameter,), {"generator": 129}
        )
        self.dag = CircuitDAG(
            131,
            (
                IRNode(1, Instruction("h", (0,))),
                IRNode(130, self.instruction),
            ),
            (IREdge(1, 130, 0),),
            {"name": "roundtrip"},
        )

    def test_all_public_artifact_types_round_trip_canonically(self) -> None:
        output_payload = b"OPENQASM 2.0;\n"
        output_digest = hashlib.sha256(encode(ExternalToolOutput("tool", "qasm2", output_payload))).hexdigest()
        corpus = (
            self.parameter,
            self.support,
            self.instruction,
            SemanticStream(131, (AggregateRecord(129, self.support, self.parameter, 3),)),
            FlatUpdateStream(
                131,
                2,
                (
                    UpdateRecord(0, 129, self.support, SymbolicParameter(Fraction(5, 19))),
                    UpdateRecord(1, 129, self.support, SymbolicParameter(Fraction(-12, 19), self.parameter.terms)),
                ),
            ),
            self.dag,
            ExternalToolOutput("tool", "qasm2", output_payload),
            CertificateInput("exact", output_digest, b"certificate-sidecar"),
            ControlState({"pass": 2, "heads": [3, 8], "halted": False}),
            StoreState({"keys": [1, 130], "layout": "sorted"}),
            LiveWindow((self.instruction,)),
            ParameterLedger((ParameterEntry((2, 130, 0), self.parameter),)),
            IRField((self.dag,)),
            CommittedOutput("qasm2", output_payload),
            {"canonical": [1, -2, Fraction(3, 5), b"x"], "z": None},
        )
        for value in corpus:
            with self.subTest(type=type(value).__name__):
                encoded = encode(value)
                decoded = decode_exact(encoded)
                self.assertEqual(decoded, value)
                self.assertEqual(encode(decoded), encoded)

    def test_semantic_and_dispersed_streams_have_identical_signature(self) -> None:
        support = PauliSupport(((2, "Z"), (9, "Z")))
        semantic = SemanticStream(
            10,
            (AggregateRecord(7, support, SymbolicParameter(Fraction(3, 13))),),
        )
        flat = FlatUpdateStream(
            10,
            3,
            (
                UpdateRecord(0, 7, support, SymbolicParameter(Fraction(11, 13))),
                UpdateRecord(1, 7, support, SymbolicParameter(Fraction(-4, 13))),
                UpdateRecord(2, 7, support, SymbolicParameter(Fraction(-4, 13))),
            ),
        )
        self.assertEqual(semantic_signature(semantic), semantic_signature(flat))
        self.assertEqual(semantic_signature(decode_exact(encode(semantic))), semantic_signature(decode_exact(encode(flat))))

        repeated = SemanticStream(
            10,
            (AggregateRecord(7, support, SymbolicParameter(Fraction(1, 13)), 3),),
        )
        self.assertEqual(semantic_signature(repeated), semantic_signature(semantic))

    def test_declared_width_and_round_bounds_are_enforced(self) -> None:
        support = PauliSupport(((3, "Z"),))
        with self.assertRaises(ValueError):
            SemanticStream(3, (AggregateRecord(2, support, SymbolicParameter(1)),))
        with self.assertRaises(ValueError):
            FlatUpdateStream(4, 1, (UpdateRecord(1, 2, support, SymbolicParameter(1)),))

    def test_conditional_description_requires_dictionary_digest(self) -> None:
        digest = "a" * 64
        value = SemanticStream(1, (), "conditional", digest)
        self.assertEqual(decode_exact(encode(value)), value)
        with self.assertRaises(ValueError):
            SemanticStream(1, (), "conditional", None)
        with self.assertRaises(ValueError):
            FlatUpdateStream(1, 0, (), "self_contained", digest)


if __name__ == "__main__":
    unittest.main()

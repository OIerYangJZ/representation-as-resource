from __future__ import annotations

import unittest
from fractions import Fraction

from encoding.codec import (
    MAGIC,
    CodecError,
    CommittedOutput,
    ControlState,
    ExternalToolOutput,
    PauliSupport,
    SymbolicParameter,
    decode_all,
    decode_exact,
    decode_from,
    encode,
)


class PrefixFreeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.values = (
            None,
            b"",
            b"x",
            {"x": 1},
            {"x": 1, "y": [2, 3]},
            SymbolicParameter(Fraction(-17, 257), ((128, Fraction(1, 3)),)),
            PauliSupport(((0, "X"), (16384, "Z"))),
            ControlState({"head": 16384, "pass": 3}),
            ExternalToolOutput("qiskit", "openqasm2", b"OPENQASM 2.0;"),
            CommittedOutput("target", b"abc"),
        )

    def test_no_complete_codeword_is_a_proper_prefix(self) -> None:
        frames = [encode(value) for value in self.values]
        for i, left in enumerate(frames):
            for j, right in enumerate(frames):
                if i != j:
                    self.assertFalse(right.startswith(left), (i, j))

    def test_concatenated_frames_decode_without_out_of_band_lengths(self) -> None:
        stream = b"".join(encode(value) for value in self.values)
        self.assertEqual(decode_all(stream), list(self.values))
        offset = 0
        for expected in self.values:
            actual, offset = decode_from(stream, offset)
            self.assertEqual(actual, expected)
        self.assertEqual(offset, len(stream))

    def test_every_truncated_frame_is_rejected(self) -> None:
        frame = encode(ExternalToolOutput("tool", "binary", bytes(range(32))))
        for length in range(len(frame)):
            with self.subTest(length=length):
                with self.assertRaises(CodecError):
                    decode_exact(frame[:length])

    def test_noncanonical_varint_and_trailing_data_are_rejected(self) -> None:
        frame = encode({"x": 1})
        self.assertEqual(frame[: len(MAGIC)], MAGIC)
        noncanonical_version = MAGIC + b"\x81\x00" + frame[len(MAGIC) + 1 :]
        with self.assertRaises(CodecError):
            decode_exact(noncanonical_version)
        with self.assertRaises(CodecError):
            decode_exact(frame + b"junk")


if __name__ == "__main__":
    unittest.main()


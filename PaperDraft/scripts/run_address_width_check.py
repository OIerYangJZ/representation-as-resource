#!/usr/bin/env python3
"""E8 Arm B: does committed output pay address width in third-party tools?

Preregistered at PaperDraft/research/E8_preregistration.md (P5), committed
before this script was run.

This is a portability CHECK, not the mechanism of P1.  P1 says the
irreducible commitment toll is schedule entropy, which does not grow with
address width.  Arm B asks the separate, weaker question of whether real
toolchains -- ones the authors do not control -- also spend committed bytes
on addresses, i.e. whether the codec slack measured in Arm A is idiosyncratic
to the authors' serializer or generic.

Design: rotation content is held byte-identical while address width varies.
M_ROT rotations are placed on the first M_ROT qubits of an n-qubit register,
n in N_VALUES.  Gate count, gate order, and angle text do not change with n
by construction; only the addresses do.  Bytes per rotation record is
measured as (bytes with M_ROT rotations - bytes with 0 rotations) / M_ROT, so
that register declarations and preambles are differenced away.

Outputs the frozen artifact PaperDraft/generated/e8_address_width.json.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
GENERATED = THIS_FILE.parent.parent / "generated"

M_ROT = 64
N_VALUES = (64, 512, 4096, 65536)
ANGLE = 0.37  # one fixed angle: its text is identical in every cell


def targets(n: int, rotations: int, spread: bool) -> list[int]:
    """Which qubits carry the rotations.

    spread=False is the preregistered P5 design: the first `rotations`
    qubits.  NOTE that this holds the *used* addresses at 0..rotations-1 no
    matter how wide the register is, so it does not in fact vary address
    width -- see the post-hoc arm below.

    spread=True spreads the rotations across the whole register so that the
    emitted addresses actually widen with n.
    """
    if not spread:
        return list(range(rotations))
    return [min(n - 1, (j * n) // rotations) for j in range(rotations)]


def qiskit_sizes(n: int, rotations: int, spread: bool = False) -> dict[str, int]:
    from qiskit import QuantumCircuit
    from qiskit import qasm3

    circuit = QuantumCircuit(n)
    for j in targets(n, rotations, spread):
        circuit.rz(ANGLE, j)
    return {"qasm3_bytes": len(qasm3.dumps(circuit).encode())}


def pytket_sizes(n: int, rotations: int, spread: bool = False) -> dict[str, int]:
    from pytket import Circuit
    from pytket.qasm import circuit_to_qasm_str

    circuit = Circuit(n)
    for j in targets(n, rotations, spread):
        circuit.Rz(ANGLE, j)
    return {
        "qasm_bytes": len(circuit_to_qasm_str(circuit).encode()),
        "json_bytes": len(json.dumps(circuit.to_dict()).encode()),
    }


def run(spread: bool) -> list[dict[str, object]]:
    rows = []
    for n in N_VALUES:
        row: dict[str, object] = {"n": n, "rotations": M_ROT, "spread": spread}
        for tool, fn in (("qiskit", qiskit_sizes), ("pytket", pytket_sizes)):
            loaded = fn(n, M_ROT, spread)
            empty = fn(n, 0, spread)
            entry = {}
            for metric, value in loaded.items():
                delta = value - empty[metric]
                entry[metric] = {
                    "total": value,
                    "empty": empty[metric],
                    "bytes_per_rotation": delta / M_ROT,
                }
            row[tool] = entry
            print(f"  n={n} spread={spread} {tool} ok", file=sys.stderr)
        rows.append(row)
    return rows


def evaluate(rows: list[dict[str, object]]) -> dict[str, object]:
    """P5, verbatim: monotone nondecreasing in n, and >= 3 bytes growth."""
    series = {}
    for row in rows:
        for tool in ("qiskit", "pytket"):
            for metric, entry in row[tool].items():
                series.setdefault(f"{tool}.{metric}", []).append(
                    (row["n"], entry["bytes_per_rotation"])
                )

    checks = {}
    for name, points in series.items():
        points.sort()
        values = [v for _, v in points]
        monotone = all(b >= a - 1e-9 for a, b in zip(values, values[1:]))
        growth = values[-1] - values[0]
        checks[name] = {
            "points": points,
            "monotone_nondecreasing": monotone,
            "growth_bytes_per_rotation": growth,
            "growth_at_least_3": growth >= 3.0,
        }
    passed = all(c["monotone_nondecreasing"] and c["growth_at_least_3"]
                 for c in checks.values())
    return {"per_series": checks, "verdicts": {"P5_address_width_paid": passed}}


def main() -> int:
    rows = run(spread=False)
    decision = evaluate(rows)

    # Post-hoc, NOT preregistered.  P5 as written placed every rotation on the
    # first M_ROT qubits, so the emitted addresses were 0..63 at every n and
    # the arm did not vary its own explanatory variable.  P5 is reported
    # failed exactly as preregistered; this second arm is exploratory and
    # carries no verdict.
    posthoc_rows = run(spread=True)
    posthoc = evaluate(posthoc_rows)

    payload = {
        "design": {
            "preregistration": "PaperDraft/research/E8_preregistration.md",
            "rotations": M_ROT,
            "n_values": list(N_VALUES),
            "angle": ANGLE,
            "metric": "(bytes with rotations - bytes with none) / rotations",
            "note": "portability check only; not the mechanism of P1",
        },
        "rows": rows,
        "decision": decision,
        "posthoc_spread_addresses": {
            "status": "EXPLORATORY -- not preregistered, no verdict claimed",
            "reason": "the preregistered P5 design placed all rotations on "
                      "qubits 0..63 regardless of n, so address width was "
                      "never varied; P5 is reported failed as preregistered "
                      "and this arm is a corrected diagnostic only",
            "rows": posthoc_rows,
            "analysis": posthoc,
        },
    }
    GENERATED.mkdir(parents=True, exist_ok=True)
    with open(GENERATED / "e8_address_width.json", "w") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    print(json.dumps(decision["verdicts"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

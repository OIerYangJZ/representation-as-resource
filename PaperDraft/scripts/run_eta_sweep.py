#!/usr/bin/env python3
"""E6: noise-vs-memory Pareto sweep over twirl strength eta.

Execution-plan task E6.  Device model (matches Proposition
`prop:eta-pareto`): each generator independently with probability eta
enters the two-round stream in dispersed twirled form (masked share mod
Q=3 with a uniform twirl sign per round, tracked presentation); otherwise
its aggregate is exposed as a single round-2 token.  Binary aggregates
x_j in {0,1} (the masked-share device of thm:main-tradeoff).

Two executable compilers, both restart-verified at the inter-round cut
(the snapshot alone plus the round-2 suffix must reproduce the correct
output; no Python object is free state):

  * deferred  -- compact output; pays the cut in STATE: retains one trit
                 (first share) and one sign bit per twirled generator.
                 Predicted crossing slope: m*(log2 3 + 1)/8 bytes per
                 unit eta (residue trits + frame bits, the zero-error
                 floor of thm:w1-one-pass-mask + eq:frame-lower).
  * streaming -- commits first-round share records immediately; pays the
                 cut in COMMITTED OUTPUT: A_pre grows linearly in eta,
                 crossing state stays O(log m).

Outputs: frozen JSON PaperDraft/generated/eta_sweep_pareto.json and
figure PaperDraft/figures/eta_sweep_pareto.pdf.
"""

from __future__ import annotations

import json
import math
import random
import statistics
import sys
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
GENERATED = THIS_FILE.parent.parent / "generated"
FIGURES = THIS_FILE.parent.parent / "figures"

M_VALUES = (32, 64, 128)
ETAS = (0.0, 0.25, 0.5, 0.75, 1.0)
SEEDS = (1, 2, 3)
Q = 3
MAGIC = b"ETA1"

TRIT_BITS = math.log2(3)


# ------------------------------------------------------------- encoding ---

def varint(value: int) -> bytes:
    out = bytearray()
    while True:
        chunk = value & 0x7F
        value >>= 7
        out.append(chunk | (0x80 if value else 0))
        if not value:
            return bytes(out)


def read_varint(buf: bytes, pos: int) -> tuple[int, int]:
    shift = value = 0
    while True:
        byte = buf[pos]
        pos += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, pos
        shift += 7


def pack_trits(trits: list[int]) -> bytes:
    value = 0
    for trit in reversed(trits):
        value = value * 3 + trit
    length = max(1, (len(trits) * 2 + 7) // 8) if trits else 0
    # exact byte length of base-3 packing
    if trits:
        length = (int(math.ceil(len(trits) * TRIT_BITS)) + 7) // 8
        length = max(length, (value.bit_length() + 7) // 8, 1)
    return value.to_bytes(length, "big") if trits else b""


def unpack_trits(payload: bytes, count: int) -> list[int]:
    value = int.from_bytes(payload, "big")
    trits = []
    for _ in range(count):
        trits.append(value % 3)
        value //= 3
    return trits


def pack_bits(bits: list[int]) -> bytes:
    out = bytearray((len(bits) + 7) // 8)
    for index, bit in enumerate(bits):
        if bit:
            out[index // 8] |= 1 << (index % 8)
    return bytes(out)


def unpack_bits(payload: bytes, count: int) -> list[int]:
    return [(payload[i // 8] >> (i % 8)) & 1 for i in range(count)]


# -------------------------------------------------------------- instance ---

def make_instance(m: int, eta: float, seed: int) -> dict[str, object]:
    rng = random.Random(f"e6-{m}-{eta}-{seed}")
    x = [rng.randrange(2) for _ in range(m)]
    twirled = [j for j in range(m) if rng.random() < eta]
    shares = {}
    for j in twirled:
        u = rng.randrange(Q)
        s1 = rng.choice((1, -1))
        s2 = rng.choice((1, -1))
        v = (s2 * (x[j] - s1 * u)) % Q
        assert (s1 * u + s2 * v) % Q == x[j]
        shares[j] = (u, s1, v, s2)
    return {"m": m, "x": x, "twirled": twirled, "shares": shares}


def round2_records(instance: dict[str, object]) -> list[tuple]:
    m = instance["m"]
    shares = instance["shares"]
    twirled = set(instance["twirled"])
    records = []
    for j in range(m):
        if j in twirled:
            _, _, v, s2 = shares[j]
            records.append(("U2", j, v, s2))
        else:
            records.append(("AGG", j, instance["x"][j]))
    return records


def encode_output(m: int, aggregates: list[int]) -> bytes:
    return MAGIC + varint(m) + pack_bits(aggregates)


# ----------------------------------------------------- deferred compiler ---

def deferred_snapshot(instance: dict[str, object]) -> bytes:
    us = [instance["shares"][j][0] for j in instance["twirled"]]
    s1bits = [1 if instance["shares"][j][1] == 1 else 0
              for j in instance["twirled"]]
    trit_payload = pack_trits(us)
    return (
        MAGIC
        + varint(instance["m"])
        + varint(len(us))
        + varint(len(trit_payload))
        + trit_payload
        + pack_bits(s1bits)
    )


def deferred_resume(snapshot: bytes, records: list[tuple]) -> bytes:
    assert snapshot[:4] == MAGIC
    pos = 4
    m, pos = read_varint(snapshot, pos)
    count, pos = read_varint(snapshot, pos)
    trit_len, pos = read_varint(snapshot, pos)
    us = unpack_trits(snapshot[pos:pos + trit_len], count)
    pos += trit_len
    s1bits = unpack_bits(snapshot[pos:], count)
    aggregates = [0] * m
    cursor = 0
    for record in records:
        if record[0] == "U2":
            _, j, v, s2 = record
            s1 = 1 if s1bits[cursor] else -1
            aggregates[j] = (s1 * us[cursor] + s2 * v) % Q
            cursor += 1
        else:
            _, j, value = record
            aggregates[j] = value
    assert cursor == count
    return encode_output(m, aggregates)


# ---------------------------------------------------- streaming compiler ---

def streaming_prefix(instance: dict[str, object]) -> bytes:
    committed = bytearray(MAGIC + varint(instance["m"]))
    for j in instance["twirled"]:
        u, s1, _, _ = instance["shares"][j]
        committed += varint(j) + bytes([u | (0x80 if s1 == 1 else 0)])
    return bytes(committed)


def streaming_snapshot(instance: dict[str, object]) -> bytes:
    return MAGIC + varint(instance["m"]) + varint(len(instance["twirled"]))


def streaming_resume(prefix: bytes, snapshot: bytes,
                     records: list[tuple]) -> bytes:
    suffix = bytearray()
    for record in records:
        if record[0] == "U2":
            _, j, v, s2 = record
            suffix += varint(j) + bytes([v | (0x80 if s2 == 1 else 0)])
        else:
            _, j, value = record
            suffix += varint(j) + bytes([0x40 | value])
    return varint(len(prefix)) + prefix + bytes(suffix)


def streaming_decode(output: bytes, twirled_count: int) -> list[int]:
    prefix_len, start = read_varint(output, 0)
    prefix = output[start:start + prefix_len]
    suffix = output[start + prefix_len:]
    assert prefix[:4] == MAGIC
    pos = 4
    m, pos = read_varint(prefix, pos)
    first = {}
    while pos < len(prefix):
        j, pos = read_varint(prefix, pos)
        byte = prefix[pos]
        pos += 1
        first[j] = (byte & 0x3F, 1 if byte & 0x80 else -1)
    assert len(first) == twirled_count
    aggregates = [0] * m
    pos = 0
    while pos < len(suffix):
        j, pos = read_varint(suffix, pos)
        byte = suffix[pos]
        pos += 1
        if byte & 0x40:
            aggregates[j] = byte & 0x3F
        else:
            u, s1 = first[j]
            v, s2 = byte & 0x3F, (1 if byte & 0x80 else -1)
            aggregates[j] = (s1 * u + s2 * v) % Q
    return aggregates


# ------------------------------------------------------------------ main ---

def run() -> dict[str, object]:
    rows = []
    for m in M_VALUES:
        for eta in ETAS:
            for seed in SEEDS:
                instance = make_instance(m, eta, seed)
                records = round2_records(instance)
                truth = encode_output(m, list(instance["x"]))

                snap_d = deferred_snapshot(instance)
                out_d = deferred_resume(snap_d, records)
                assert out_d == truth, "deferred restart failed"

                prefix_s = streaming_prefix(instance)
                snap_s = streaming_snapshot(instance)
                out_s = streaming_resume(prefix_s, snap_s, records)
                decoded = streaming_decode(out_s, len(instance["twirled"]))
                assert decoded == instance["x"], "streaming restart failed"

                rows.append(
                    {
                        "m": m,
                        "eta": eta,
                        "seed": seed,
                        "twirled": len(instance["twirled"]),
                        "deferred_B_cross_bytes": len(snap_d),
                        "deferred_A_pre_bytes": 0,
                        "streaming_B_cross_bytes": len(snap_s),
                        "streaming_A_pre_bytes": len(prefix_s),
                        "resume_verified": True,
                    }
                )
    return {"rows": rows}


def analyze(rows: list[dict[str, object]]) -> dict[str, object]:
    def mean_series(metric: str, m: int) -> list[tuple[float, float]]:
        return [
            (
                eta,
                statistics.mean(
                    float(r[metric]) for r in rows
                    if r["m"] == m and r["eta"] == eta
                ),
            )
            for eta in ETAS
        ]

    def ols_slope(points: list[tuple[float, float]]) -> float:
        n = len(points)
        mx = sum(p[0] for p in points) / n
        my = sum(p[1] for p in points) / n
        num = sum((p[0] - mx) * (p[1] - my) for p in points)
        den = sum((p[0] - mx) ** 2 for p in points)
        return num / den

    result = {}
    for m in M_VALUES:
        measured = ols_slope(mean_series("deferred_B_cross_bytes", m))
        predicted = m * (TRIT_BITS + 1) / 8
        result[str(m)] = {
            "deferred_slope_bytes_per_eta_measured": measured,
            "deferred_slope_bytes_per_eta_predicted_floor": predicted,
            "measured_over_predicted": measured / predicted,
            "streaming_Apre_slope_bytes_per_eta": ols_slope(
                mean_series("streaming_A_pre_bytes", m)
            ),
            "streaming_B_cross_max_bytes": max(
                float(r["streaming_B_cross_bytes"]) for r in rows
                if r["m"] == m
            ),
        }
    return result


def figure(rows: list[dict[str, object]],
           out_path: Path | None = None) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = {32: "#0072B2", 64: "#E69F00", 128: "#009E73"}
    fig, axes = plt.subplots(1, 2, figsize=(5.8, 2.6), sharex=True)

    for m in M_VALUES:
        for ax, metric in (
            (axes[0], "deferred_B_cross_bytes"),
            (axes[1], "streaming_A_pre_bytes"),
        ):
            means = [
                statistics.mean(
                    float(r[metric]) for r in rows
                    if r["m"] == m and r["eta"] == eta
                )
                for eta in ETAS
            ]
            ax.plot(ETAS, means, "o-", color=colors[m], linewidth=2,
                    markersize=4, label=f"$m={m}$")
        predicted = [m * (TRIT_BITS + 1) / 8 * eta for eta in ETAS]
        axes[0].plot(ETAS, predicted, "--", color=colors[m], linewidth=1,
                     alpha=0.6)

    axes[0].set_ylabel("crossing state $S$ (bytes)")
    axes[0].set_title("deferred: pay in state", fontsize=9)
    axes[1].set_ylabel(r"committed prefix $A_{\mathrm{pre}}$ (bytes)")
    axes[1].set_title("streaming: pay in output", fontsize=9)
    for ax in axes:
        ax.set_xlabel(r"dispersal fraction $\eta$")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(True, linewidth=0.3, alpha=0.4)
    axes[0].legend(frameon=False, fontsize=7, loc="upper left")
    fig.text(
        0.5, -0.04,
        "dashed: zero-error floor $\\eta m(\\log_2 3 + 1)/8$ bytes",
        ha="center", fontsize=7,
    )
    fig.tight_layout()
    if out_path is None:
        FIGURES.mkdir(parents=True, exist_ok=True)
        out_path = FIGURES / "eta_sweep_pareto.pdf"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    payload = run()
    payload["design"] = {
        "m_values": list(M_VALUES),
        "etas": list(ETAS),
        "seeds": list(SEEDS),
        "Q": Q,
        "rounds": 2,
        "aggregates": "binary",
        "presentation": "tracked (sign bits alongside residues)",
        "verification": "snapshot-only restart reproduces exact output",
    }
    payload["analysis"] = analyze(payload["rows"])
    GENERATED.mkdir(parents=True, exist_ok=True)
    with open(GENERATED / "eta_sweep_pareto.json", "w") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
    figure(payload["rows"])
    print(json.dumps(payload["analysis"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

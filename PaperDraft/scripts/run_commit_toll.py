#!/usr/bin/env python3
"""E8 Arm A: the commitment toll.

Preregistered at PaperDraft/research/E8_preregistration.md (committed before
this script was run; git commit order is the timestamp).

Question.  fig:eta-sweep shows the two admissible payment channels of
thm:w1-unified-frontier exchanging at ~6:1 rather than 1:1.  The frontier
charges them at par.  Where does the asymmetry come from?

Decomposition under test:

    committed bits/generator = payload + identity + codec slack
    state     bits/generator = payload

The preregistered claim is that the irreducible part -- `identity` -- is the
entropy of the commitment schedule, log2 C(m,k) bits over k committed
generators, and NOT the address width conjectured by the review note.  A
compiler that defers pays no identity at all: the round-2 records disclose
the mask for free.  A compiler that commits early must self-identify, because
committed records are immediately executable (rem:streaming-grounding:
append-only first exposure, real-time control stack).

Four encoders on the same two-round masked-share device (Q=3, binary
aggregates, tracked signs), every cell restart-verified:

  deferred                 state channel; positions implicit in round-2 order
  stream_varint            the existing encoder: varint(j) + payload byte
  stream_opt_selfid        identity-optimal, prefix parseable on its own
  stream_opt_maskdeferred  control: mask recovered from the suffix instead

Outputs the frozen artifact PaperDraft/generated/e8_commit_toll.json.
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

Q = 3
TRIT_BITS = math.log2(3)
MAGIC = b"TOLL"

M_ALL = (128, 512, 2048, 8192, 32768)
M_OPT = (128, 512, 2048)
ETAS = (0.125, 0.25, 0.5, 1.0)
SEEDS = (1, 2, 3)
K_MIN = 16


# ------------------------------------------------------------- primitives ---

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


def varint_len(value: int) -> int:
    return len(varint(value))


def bits_for(alphabet: int) -> int:
    """Exact bit length of an index into an alphabet of the given size."""
    return max(1, (alphabet - 1).bit_length())


# --------------------------------------------------- combinatorial ranking ---

def mask_rank(m: int, selected: list[int]) -> int:
    """Lexicographic rank of a k-subset of [m].  Inverse of mask_unrank."""
    rank = 0
    pos = 0
    k = len(selected)
    for index, chosen in enumerate(selected):
        remaining = k - index
        for value in range(pos, chosen):
            rank += math.comb(m - 1 - value, remaining - 1)
        pos = chosen + 1
    return rank


def mask_unrank(m: int, k: int, rank: int) -> list[int]:
    selected = []
    pos = 0
    for index in range(k):
        remaining = k - index
        value = pos
        while True:
            block = math.comb(m - 1 - value, remaining - 1)
            if rank < block:
                break
            rank -= block
            value += 1
        selected.append(value)
        pos = value + 1
    return selected


# ---------------------------------------------------------------- instance ---

def make_instance(m: int, eta: float, seed: int) -> dict[str, object]:
    """Same device as run_eta_sweep.make_instance, seeded for E8."""
    rng = random.Random(f"e8-{m}-{eta}-{seed}")
    x = [rng.randrange(2) for _ in range(m)]
    dispersed = [j for j in range(m) if rng.random() < eta]
    shares = {}
    for j in dispersed:
        u = rng.randrange(Q)
        s1 = rng.choice((1, -1))
        s2 = rng.choice((1, -1))
        v = (s2 * (x[j] - s1 * u)) % Q
        assert (s1 * u + s2 * v) % Q == x[j]
        shares[j] = (u, s1, v, s2)
    return {"m": m, "x": x, "dispersed": dispersed, "shares": shares}


def round2_records(instance: dict[str, object]) -> list[tuple]:
    """Round-major suffix.  Identical across all four encoders."""
    dispersed = set(instance["dispersed"])
    records = []
    for j in range(instance["m"]):
        if j in dispersed:
            _, _, v, s2 = instance["shares"][j]
            records.append(("U2", j, v, s2))
        else:
            records.append(("AGG", j, instance["x"][j]))
    return records


# ------------------------------------------------------- packed body codec ---

def pack_body(m: int, instance: dict[str, object], with_mask: bool) -> tuple[int, int]:
    """Concatenate mask rank / residues / signs into one integer.

    Field alphabets are exact -- C(m,k) for the mask, 3^k for the residues,
    2^k for the signs -- and the whole body is rounded to bytes once, at the
    end (Amendment 1).  Returns (value, alphabet_size).
    """
    dispersed = instance["dispersed"]
    k = len(dispersed)
    trit_value = 0
    for j in reversed(dispersed):
        trit_value = trit_value * Q + instance["shares"][j][0]
    sign_value = 0
    for index, j in enumerate(dispersed):
        if instance["shares"][j][1] == 1:
            sign_value |= 1 << index

    alphabet = (Q ** k) * (2 ** k)
    value = trit_value * (2 ** k) + sign_value
    if with_mask:
        rank = mask_rank(m, dispersed)
        value = rank * alphabet + value
        alphabet *= math.comb(m, k)
    return value, alphabet


def unpack_body(m: int, k: int, value: int, with_mask: bool) -> tuple[list[int] | None, list[int], list[int]]:
    sign_value = value % (2 ** k)
    value //= 2 ** k
    trit_value = value % (Q ** k)
    value //= Q ** k
    mask = mask_unrank(m, k, value) if with_mask else None
    residues = []
    for _ in range(k):
        residues.append(trit_value % Q)
        trit_value //= Q
    signs = [1 if (sign_value >> i) & 1 else -1 for i in range(k)]
    return mask, residues, signs


def header_bytes(m: int, k: int) -> bytes:
    """Identical across all four encoders (Amendment 1)."""
    return MAGIC + varint(m) + varint(k)


# ---------------------------------------------------------------- encoders ---

def encode_packed(instance: dict[str, object], with_mask: bool) -> dict[str, object]:
    m = instance["m"]
    k = len(instance["dispersed"])
    value, alphabet = pack_body(m, instance, with_mask)
    body_bits = bits_for(alphabet) if k else 0
    body_len = (body_bits + 7) // 8
    blob = header_bytes(m, k) + value.to_bytes(body_len, "big")
    return {
        "blob": blob,
        "header_len": len(header_bytes(m, k)),
        "body_bits": body_bits,
        "body_bytes": body_len,
    }


def encode_stream_varint(instance: dict[str, object]) -> dict[str, object]:
    m = instance["m"]
    k = len(instance["dispersed"])
    body = bytearray()
    for j in instance["dispersed"]:
        u, s1, _, _ = instance["shares"][j]
        body += varint(j) + bytes([u | (0x80 if s1 == 1 else 0)])
    return {
        "blob": header_bytes(m, k) + bytes(body),
        "header_len": len(header_bytes(m, k)),
        "body_bits": len(body) * 8,
        "body_bytes": len(body),
    }


# ------------------------------------------------------------- decoders -----

def decode_packed(blob: bytes, records: list[tuple], with_mask: bool) -> list[int]:
    """Reconstruct the aggregates from the serialized blob plus the suffix."""
    assert blob[:4] == MAGIC
    pos = 4
    m, pos = read_varint(blob, pos)
    k, pos = read_varint(blob, pos)
    value = int.from_bytes(blob[pos:], "big") if k else 0
    mask, residues, signs = unpack_body(m, k, value, with_mask)
    if mask is None:
        # Control arm: the prefix is not independently parseable.  The mask is
        # recovered from the suffix, which addresses every record anyway.
        mask = [record[1] for record in records if record[0] == "U2"]
    assert len(mask) == k
    slot = {j: i for i, j in enumerate(mask)}
    aggregates = [0] * m
    for record in records:
        if record[0] == "U2":
            _, j, v, s2 = record
            i = slot[j]
            aggregates[j] = (signs[i] * residues[i] + s2 * v) % Q
        else:
            _, j, value_agg = record
            aggregates[j] = value_agg
    return aggregates


def decode_stream_varint(blob: bytes, records: list[tuple]) -> list[int]:
    assert blob[:4] == MAGIC
    pos = 4
    m, pos = read_varint(blob, pos)
    k, pos = read_varint(blob, pos)
    first = {}
    while pos < len(blob):
        j, pos = read_varint(blob, pos)
        byte = blob[pos]
        pos += 1
        first[j] = (byte & 0x3F, 1 if byte & 0x80 else -1)
    assert len(first) == k
    aggregates = [0] * m
    for record in records:
        if record[0] == "U2":
            _, j, v, s2 = record
            u, s1 = first[j]
            aggregates[j] = (s1 * u + s2 * v) % Q
        else:
            _, j, value_agg = record
            aggregates[j] = value_agg
    return aggregates


# -------------------------------------------------------------------- run ---

def run_cell(m: int, eta: float, seed: int, with_optimal: bool) -> dict[str, object]:
    instance = make_instance(m, eta, seed)
    records = round2_records(instance)
    truth = list(instance["x"])
    k = len(instance["dispersed"])

    row: dict[str, object] = {"m": m, "eta": eta, "seed": seed, "k": k}

    deferred = encode_packed(instance, with_mask=False)
    assert decode_packed(deferred["blob"], records, with_mask=False) == truth, \
        f"deferred restart failed at m={m} eta={eta} seed={seed}"
    row["deferred"] = {kk: vv for kk, vv in deferred.items() if kk != "blob"}

    varint_arm = encode_stream_varint(instance)
    assert decode_stream_varint(varint_arm["blob"], records) == truth, \
        f"stream_varint restart failed at m={m} eta={eta} seed={seed}"
    row["stream_varint"] = {kk: vv for kk, vv in varint_arm.items() if kk != "blob"}

    if with_optimal:
        selfid = encode_packed(instance, with_mask=True)
        assert decode_packed(selfid["blob"], records, with_mask=True) == truth, \
            f"stream_opt_selfid restart failed at m={m} eta={eta} seed={seed}"
        row["stream_opt_selfid"] = {kk: vv for kk, vv in selfid.items()
                                    if kk != "blob"}

        maskdef = encode_packed(instance, with_mask=False)
        assert decode_packed(maskdef["blob"], records, with_mask=False) == truth, \
            f"stream_opt_maskdeferred restart failed at m={m} eta={eta} seed={seed}"
        row["stream_opt_maskdeferred"] = {kk: vv for kk, vv in maskdef.items()
                                          if kk != "blob"}

    row["restart_verified"] = True
    row["predicted_toll_bits_per_gen"] = (
        math.log2(math.comb(m, k)) / k if 0 < k < m else 0.0
    )
    return row


def run() -> list[dict[str, object]]:
    rows = []
    for m in M_ALL:
        for eta in ETAS:
            for seed in SEEDS:
                rows.append(run_cell(m, eta, seed, with_optimal=(m in M_OPT)))
                print(f"  cell m={m} eta={eta} seed={seed} ok", file=sys.stderr)
    return rows


# --------------------------------------------------------------- analysis ---

def bits_per_gen(row: dict[str, object], arm: str, exact: bool) -> float | None:
    if arm not in row or not row["k"]:
        return None
    entry = row[arm]
    numerator = entry["body_bits"] if exact else 8 * entry["body_bytes"]
    return numerator / row["k"]


def analyze(rows: list[dict[str, object]]) -> dict[str, object]:
    cells = {}
    for row in rows:
        key = f"m={row['m']},eta={row['eta']}"
        cells.setdefault(key, []).append(row)

    summary = {}
    for key, group in sorted(cells.items()):
        entry: dict[str, object] = {
            "m": group[0]["m"],
            "eta": group[0]["eta"],
            "k_mean": statistics.mean(r["k"] for r in group),
            "predicted_toll_bits_per_gen":
                statistics.mean(r["predicted_toll_bits_per_gen"] for r in group),
        }
        for arm in ("deferred", "stream_varint", "stream_opt_selfid",
                    "stream_opt_maskdeferred"):
            values = [bits_per_gen(r, arm, exact=False) for r in group]
            exacts = [bits_per_gen(r, arm, exact=True) for r in group]
            if any(v is None for v in values):
                continue
            entry[arm] = {
                "bits_per_gen_bytegranular": statistics.mean(values),
                "bits_per_gen_exact": statistics.mean(exacts),
            }
        if "stream_opt_selfid" in entry:
            for label, arm in (("toll", "stream_opt_selfid"),
                               ("toll_control", "stream_opt_maskdeferred")):
                for suffix in ("bytegranular", "exact"):
                    entry[f"{label}_{suffix}"] = (
                        entry[arm][f"bits_per_gen_{suffix}"]
                        - entry["deferred"][f"bits_per_gen_{suffix}"]
                    )
        summary[key] = entry
    return summary


def evaluate(summary: dict[str, object]) -> dict[str, object]:
    """Evaluate the frozen decision rule verbatim.  No metric substitution."""
    def mean_varint_bits(m: int) -> float:
        return 8 * (sum(varint_len(j) for j in range(m)) / m + 1)

    c1, p1, p2, p3, p4 = [], [], [], [], []

    for key, entry in summary.items():
        m, eta, k = entry["m"], entry["eta"], entry["k_mean"]

        measured = entry["stream_varint"]["bits_per_gen_bytegranular"]
        predicted = mean_varint_bits(m)
        c1.append({"cell": key, "measured": measured, "predicted": predicted,
                   "within_2pct": abs(measured - predicted) <= 0.02 * predicted})

        if "toll_bytegranular" not in entry:
            continue
        toll = entry["toll_bytegranular"]
        toll_exact = entry["toll_exact"]
        target = entry["predicted_toll_bits_per_gen"]

        if k >= K_MIN:
            tolerance = max(0.05 * target, 0.5)
            p1.append({"cell": key, "toll": toll, "toll_exact": toll_exact,
                       "predicted": target, "tolerance": tolerance,
                       "pass": abs(toll - target) <= tolerance})
        if eta == 1.0:
            p2.append({"cell": key, "toll": toll, "pass": abs(toll) <= 0.2})
        p3.append({"cell": key, "toll_control": entry["toll_control_bytegranular"],
                   "pass": abs(entry["toll_control_bytegranular"]) <= 0.2})

    # P4: toll is flat in m at fixed eta while the varint arm is not.
    at_half = {entry["m"]: entry for entry in summary.values()
               if entry["eta"] == 0.5 and "toll_bytegranular" in entry}
    if 128 in at_half and 2048 in at_half:
        toll_drift = abs(at_half[2048]["toll_bytegranular"]
                         - at_half[128]["toll_bytegranular"])
        varint_drift = (at_half[2048]["stream_varint"]["bits_per_gen_bytegranular"]
                        - at_half[128]["stream_varint"]["bits_per_gen_bytegranular"])
        p4 = {"toll_drift_128_to_2048": toll_drift,
              "varint_drift_128_to_2048": varint_drift,
              "pass": toll_drift < 0.2 and varint_drift > 7.0}
    else:
        p4 = {"pass": False, "reason": "missing cells"}

    verdicts = {
        "C1_calibration": all(item["within_2pct"] for item in c1),
        "P1_toll_is_schedule_entropy": bool(p1) and all(i["pass"] for i in p1),
        "P2_par_tight_at_eta1": bool(p2) and all(i["pass"] for i in p2),
        "P3_selfid_is_the_mechanism": bool(p3) and all(i["pass"] for i in p3),
        "P4_not_address_width": p4["pass"],
    }
    return {"C1": c1, "P1": p1, "P2": p2, "P3": p3, "P4": p4,
            "verdicts": verdicts}


def main() -> int:
    rows = run()
    summary = analyze(rows)
    decision = evaluate(summary)
    payload = {
        "design": {
            "preregistration": "PaperDraft/research/E8_preregistration.md",
            "m_all": list(M_ALL),
            "m_optimal_arms": list(M_OPT),
            "etas": list(ETAS),
            "seeds": list(SEEDS),
            "Q": Q,
            "rounds": 2,
            "aggregates": "binary",
            "presentation": "tracked (sign bits alongside residues)",
            "k_min_for_analysis": K_MIN,
            "verification": "snapshot/prefix plus round-2 suffix reproduces "
                            "the exact output in every cell",
        },
        "rows": rows,
        "summary": summary,
        "decision": decision,
    }
    GENERATED.mkdir(parents=True, exist_ok=True)
    with open(GENERATED / "e8_commit_toll.json", "w") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    print(json.dumps(decision["verdicts"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

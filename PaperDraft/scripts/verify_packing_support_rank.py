#!/usr/bin/env python3
"""Exact GF(2) rank verifier for the packing-family chain supports."""

from __future__ import annotations

import json
from pathlib import Path


SWEEP = (4, 8, 16, 32, 64)


def gf2_rank(rows: list[int], width: int) -> int:
    """Return the exact row rank of bit-packed rows over GF(2)."""

    work = list(rows)
    rank = 0
    for column in range(width):
        pivot = next(
            (index for index in range(rank, len(work)) if work[index] & (1 << column)),
            None,
        )
        if pivot is None:
            continue
        work[rank], work[pivot] = work[pivot], work[rank]
        for index in range(len(work)):
            if index != rank and work[index] & (1 << column):
                work[index] ^= work[rank]
        rank += 1
    return rank


def verify_sweep() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for m in SWEEP:
        n = m + 1
        supports = [(1 << j) | (1 << (j + 1)) for j in range(m)]
        rank = gf2_rank(supports, n)
        record = {
            "m": m,
            "n": n,
            "support_masks_hex": [hex(mask) for mask in supports],
            "rank_F2": rank,
            "rank_equals_m": rank == m,
        }
        if rank != m:
            raise AssertionError(f"packing support rank {rank} != m={m}")
        records.append(record)
    return records


def main() -> int:
    records = verify_sweep()
    payload = {
        "verifier": Path(__file__).name,
        "construction": "a_j = e_j + e_{j+1}, j=1..m, n=m+1",
        "arithmetic": "exact bit-packed Gaussian elimination over GF(2)",
        "sweep": list(SWEEP),
        "records": records,
        "all_passed": all(bool(row["rank_equals_m"]) for row in records),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

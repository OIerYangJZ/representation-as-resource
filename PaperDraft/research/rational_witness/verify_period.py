#!/usr/bin/env python3
"""Exact integer certificate for the canonical four-qubit RZ/CP period."""

from __future__ import annotations

import argparse
import hashlib
from fractions import Fraction
from functools import reduce
from itertools import product
from math import gcd
from pathlib import Path


RZ_ANGLES = (("rz_q0", 0, 7), ("rz_q1", 1, 8),
             ("rz_q2", 2, 9), ("rz_q3", 3, 10))
CP_ANGLES = (("cp_q0_q1", 0, 1, 12), ("cp_q0_q2", 0, 2, 13),
             ("cp_q0_q3", 0, 3, 14), ("cp_q1_q2", 1, 2, 14),
             ("cp_q1_q3", 1, 3, 15), ("cp_q2_q3", 2, 3, 16))
EXPECTED_PERIOD = 131_040


def lcm(a: int, b: int) -> int:
    return a // gcd(a, b) * b


def lcm_many(values: list[int]) -> int:
    return reduce(lcm, values, 1)


def mod_two(value: Fraction) -> Fraction:
    return value - 2 * (value // 2)


def order_mod_two(value: Fraction) -> int:
    """Least positive k for which k*value is zero modulo 2."""

    value = mod_two(value)
    if value == 0:
        return 1
    return 2 * value.denominator // gcd(abs(value.numerator),
                                        2 * value.denominator)


def phase_over_pi(bits: tuple[int, ...]) -> Fraction:
    total = Fraction(0, 1)
    for _, qubit, denominator in RZ_ANGLES:
        total += Fraction(2 * bits[qubit] - 1, 2 * denominator)
    for _, control, target, denominator in CP_ANGLES:
        total += Fraction(bits[control] * bits[target], denominator)
    return mod_two(total)


def frac_fields(value: Fraction) -> str:
    return f"numerator={value.numerator} denominator={value.denominator}"


def render_certificate() -> str:
    lines = [
        "certificate_version=1",
        "arithmetic=fractions.Fraction",
        "phase_modulus_over_pi=2",
        "term_orders:",
    ]
    term_orders: list[int] = []
    for name, _, denominator in RZ_ANGLES:
        angle = Fraction(1, denominator)
        order = order_mod_two(angle)
        term_orders.append(order)
        lines.append(f"  name={name} angle_p=1 angle_q={denominator} order={order}")
    for name, _, _, denominator in CP_ANGLES:
        angle = Fraction(1, denominator)
        order = order_mod_two(angle)
        term_orders.append(order)
        lines.append(f"  name={name} angle_p=1 angle_q={denominator} order={order}")
    term_lcm = lcm_many(term_orders)
    lines.append("term_order_vector=" + ",".join(map(str, term_orders)))
    lines.append(f"term_order_lcm={term_lcm}")

    states = list(product((0, 1), repeat=4))
    phases = {state: phase_over_pi(state) for state in states}
    base = phases[(0, 0, 0, 0)]
    relative_orders: list[int] = []
    lines.append("relative_phase_constraints:")
    for state in states:
        relative = mod_two(phases[state] - base)
        order = order_mod_two(relative)
        relative_orders.append(order)
        label = "".join(map(str, state))
        lines.append(
            f"  state={label} {frac_fields(relative)} order={order}"
        )
    relative_lcm = lcm_many(relative_orders)
    lines.append("relative_order_vector=" + ",".join(map(str, relative_orders)))
    lines.append(f"relative_order_lcm={relative_lcm}")
    lines.append(f"minimality_state_1011_order={relative_orders[11]}")
    lines.append(f"exact_global_phase_period_T={relative_lcm}")

    assert term_lcm == EXPECTED_PERIOD
    assert relative_lcm == EXPECTED_PERIOD
    assert relative_orders[11] == EXPECTED_PERIOD
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", type=Path,
                        help="compare the generated certificate byte-for-byte")
    args = parser.parse_args()
    generated = render_certificate()
    if args.check is None:
        print(generated, end="")
        return 0
    frozen = args.check.read_text(encoding="utf-8")
    if frozen != generated:
        raise SystemExit("certificate_check=FAILED")
    digest = hashlib.sha256(frozen.encode("utf-8")).hexdigest()
    print(f"certificate_check=PASSED sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

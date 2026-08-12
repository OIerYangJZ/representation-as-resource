# Exact commuting-Pauli/Clifford correctness certificate

## Claim and non-claim

`exact_commuting_pauli_clifford_canonical_v1` is a sound acceptance
certificate for exact circuits in the domain below. If it returns
`completed_valid`, the two inputs implement the same unitary up to global
phase. The checker is deliberately incomplete: a rejected pair may still be
equivalent by an identity outside this normal form. The implementation never
turns a rejection, unsupported construct, failed predicate, or floating-point
guess into an equivalence claim.

## Canonical input language

An input is an `ExactCircuit(width, operations, global_phase_over_pi)`. Its
operations are ordered in execution order. A coefficient is an exact element
of `Q*pi + direct_sum_s Q*theta_s`, stored as a reduced rational `pi` part and
a sorted sparse map of declared formal-symbol coefficients. A plain
`fractions.Fraction` is the shorthand with an empty symbol map.

Supported Clifford generators are:

- single-qubit `h`, `s`, `sdg`, `x`, `y`, and `z`;
- two-qubit `cx`, `cz`, and `swap`;
- structural `id` and `barrier` records.

Supported non-Clifford records are:

- `rz(q, a)`, with exact symbolic angle `a` and semantics
  `exp(-i a Z_q / 2)` (the stored rational `pi` part is multiplied by pi);
- `pauli(P, a)`, where `P` is an address-complete signed Hermitian Pauli
  support `(width, x_mask, z_mask, sign)` and the semantics is
  `exp(-i pi a P / 2)`;
- `global_phase(a)`, plus the circuit-level exact global phase. Both are
  accepted but omitted from projective canonical equality.

A Python float without an exact rational-pi sidecar is not silently rounded.
It returns `numerical_inconclusive`. Unknown gates and malformed addresses are
`unsupported`. After Clifford extraction, all Pauli rotations must commute
pairwise; failure of that declared predicate is `predicate_error`.

## Clifford-frame convention

For the Clifford prefix product `F`, the canonicalizer stores the signed
images

```
F^dagger X_j F,  F^dagger Z_j F,  j = 0,...,n-1.
```

Each image is a signed Hermitian Pauli. This signed inverse-conjugation tableau
determines `F` up to global phase. Clifford global phase is therefore
normalized without choosing an arbitrary matrix phase.

While scanning a circuit, the implementation maintains

```
U_prefix = F R(P_t,a_t) ... R(P_1,a_1)
```

up to global phase. Appending a Clifford updates the tableau. Appending a
physical rotation `R(Q,a)` records `F^dagger Q F` in the rotation list.

## Coefficient and support canonicalization

1. A negative Pauli sign is moved into its coefficient:
   `R(-P,a) = R(P,-a)`.
2. Identity-axis rotations are discarded because they are global phases.
3. The pairwise-commutation predicate is checked exactly with the binary
   symplectic product.
4. Coefficients of identical unsigned supports are added exactly, including
   every named formal-symbol component.
5. Only the rational-pi component is reduced to the unique representative in
   `[0,2)` because
   `R(P,(a+2k)pi) = (-1)^k R(P,a pi)`.
   Formal-symbol components are never reduced or numerically sampled.
6. Zero coefficients are removed and remaining records are ordered
   lexicographically by `(x_mask,z_mask)`.

The canonical JSON uses sorted keys, reduced numerator/positive-denominator
pairs, literal support masks, and the complete signed Clifford tableau. Its
SHA-256 is deterministic.

## Acceptance and independent certificate

The checker accepts exactly when the reference and candidate canonical byte
records are equal. Every `completed_valid` result contains an
`independent_certificate` with:

- hashes of both input records and both canonical records;
- the common soundness-domain identifier;
- the coefficient period and global-phase policy;
- separate comparison bits for width, rotation table, and Clifford frame;
- all discharged proof obligations;
- a SHA-256 over the certificate payload itself.

No other status is accepted. In particular, a row called `completed_valid`
without this independent certificate is malformed and must not enter an
analysis.

## Status contract

| status | meaning | enters quality means? |
|---|---|---:|
| `completed_valid` | symbolic equality accepted and independent certificate present | yes |
| `completed_invalid` | canonical certificate rejected in-domain | no |
| `unsupported` | syntax, gate, address, or dense width is outside the checker language | no |
| `predicate_error` | supported syntax failed a domain predicate or checker execution predicate | no |
| `numerical_inconclusive` | exact coefficient sidecar is absent or dense distance lies in its guard band | no |

`completed_invalid` is a certificate rejection, not a completeness theorem for
unitary inequivalence. For the adversarial audit suite, every rejection is
independently confirmed by the dense checker.

The helper `certified_quality_mean` includes only `completed_valid` rows and
reports all excluded statuses separately. Legacy W4/W5 `completed` labels are
not retroactively relabeled; they used their frozen PyZX certificate policy.

## Dense crosscheck

For `n <= 6` and fully numerical coefficients, the independent checker constructs dense operators using
Qiskit's matrix semantics and evaluates

```
min_phi ||U - exp(i phi) V||_F / sqrt(2^n).
```

The minimizing phase is obtained from `Tr(U^dagger V)`. Distances at most
`1e-9` are `completed_valid`, distances at least `1e-7` are
`completed_invalid`, and the open guard band is `numerical_inconclusive`.
Dense results are evidence for the implementation, not part of the arbitrary
width soundness proof.

## Reproduction

Run:

```bash
./.venv/bin/python -m pytest -q \
  tests/test_certificate_crosscheck.py tests/test_certificate_mutations.py
./.venv/bin/python -m certificates.audit
```

Formal-symbol inputs remain soundly checkable by the symbolic layer, while the
dense layer returns `numerical_inconclusive` until assignments are supplied.
The formal local audit is frozen at `data/frozen/certificate_audit.json`.

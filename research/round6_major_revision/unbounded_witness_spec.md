# Unbounded Independent-Pauli Witness Specification

## Family

The new family is separate from the rational ten-term CP witness:

\[
C_r=H^{\otimes 4}D^rH^{\otimes 4},\qquad
D=\exp\!\left[-\frac{i}{2}\sum_{j=1}^{4}\theta_j Z^{a_j}\right].
\]

Rows below are supports in column order `(q0,q1,q2,q3)`:

| Term | Support | Exact angle |
|---|---|---|
| `Z0 Z1` | `1100` | `pi*sqrt(2)/11` |
| `Z1 Z2` | `0110` | `pi/13` |
| `Z2 Z3` | `0011` | `pi/17` |
| `Z0` | `1000` | `pi/19` |

Gaussian elimination over `F2` gives pivots in all four columns, so
`rank_F2(A)=4=m`. Three of the four generators are nontrivial two-qubit
characters; the single-qubit fourth row closes the even-parity rank deficit.
This support system is not the dependent ten-term support system used by the
rational CP witness.

## Unbounded certificate

The first angle obeys

\[
\theta_1/\pi=\sqrt{2}/11\notin\mathbb{Q}.
\]

This is a symbolic declaration based on the irrationality of `sqrt(2)`, not a
floating-point test. The independent-support coefficient-uniqueness lemma
`lem:pauli-uniqueness`, followed by Proposition `prop:fooling-set`, therefore
implies pairwise noncollision for every distinct pair of repetition counts.
Thus `support_rank_verified=true` and
`unbounded_noncollision_by_proposition=true` are mathematical certificates.

## Gate convention and lowering

The experiment uses the repository's Qiskit conventions

\[
RZ(\theta)=e^{-i\theta Z/2},\qquad
CP(\phi)=\operatorname{diag}(1,1,1,e^{i\phi}).
\]

Every two-body term is lowered generically as

\[
RZ_i(\theta)RZ_j(\theta)CP_{ij}(-2\theta)
=e^{-i\theta/2}e^{-i\theta Z_iZ_j/2}.
\]

The displayed scalar is a global phase. The `Z0` term is one `RZ_0(theta)`.
One declared diagonal block therefore contains ten input gates, and the two
Hadamard boundaries contain eight. For a requested size `s`, the deterministic
mapping is `r=max(1,floor((s-8)/10))`, with actual size `8+10r`. Consequently
the standard requests 4k, 10k, 20k, 50k, and 100k map to `r=399,999,1999,4999,9999`
and actual sizes 3998, 9998, 19998, 49998, and 99998.

## Binding and implementation checks

Qiskit receives a binary double obtained from `math.pi` and `math.sqrt(2)`.
That binding is solely an executable approximation of the symbolically defined
family; it is not used to certify irrationality. Completed experimental cells
are checked numerically up to global phase with `atol=rtol=1e-9`. The verifier
also checks the lowering identity on a one-block unitary. These numerical
checks certify implementation consistency only.

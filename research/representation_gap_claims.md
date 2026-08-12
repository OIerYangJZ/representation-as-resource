# Representation Gap and Recoverability Gap

## Stronger Theoretical Framing

The strongest defensible PRX-style theoretical claim is not:

- our current branch is a universally better compiler

and not:

- every useful optimization must be moved before basis lowering.

The stronger claim that *is* defensible is:

> for structured circuit families, there can exist a representation-dependent
> recoverability gap between bounded compilation in a flat basis-lowered
> instruction stream and bounded compilation in a semantic term algebra that
> preserves repeated, conjugated, Fourier-like, or mirrored structure.

This claim is stronger than a pure systems narrative because it states that the
problem is not merely bad engineering or poor pass ordering. It is a mismatch
between the representation in which opportunities are visible and the
representation in which bounded compilers are asked to search.

## Setup

Let:

- `C` be a high-level circuit
- `L_B(C)` be its lowering into target basis `B`
- `kappa` be a conservative structural cost
- `Phi_K(C)` be the bounded semantic lift of `C` into the branch's term algebra
- `T_K(C)` be the bounded set of semantic candidates reachable under that lift

Let `A_w` denote a class of bounded post-lowering compilers that operate only
on fully materialized basis-level circuits and whose rewrites/comparisons are
restricted to bounded local structure or bounded candidate generation after
lowering.

For the sharper family theorem below, we replace the earlier informal
boundary-oblivious shorthand by a more explicit restricted class. Let
`F_{w,b,rho}^{lc}` denote the class of **locally certifying bounded flat
compilers** with:

- local observation radius at most `w`,
- candidate budget at most `b`,
- access only to invariants computed from the fully materialized
  basis-lowered stream,
- a semantic-unit recovery rule that may only fuse across boundaries admitting
  a **local certificate** built from at most `rho` radius-`w` witness windows.

Write `cert(partial, L_B(C))` for the certificate profile attached to a
candidate boundary `partial`, and let

- `mult(cert(partial, L_B(C)))`

denote the number of boundaries in the lowered circuit with the same
certificate profile.

We additionally impose a **collision-respecting certification rule**:

- if `mult(cert(partial, L_B(C))) = Theta(r)`, the compiler is not allowed to
  treat `partial` as a uniquely recoverable semantic boundary;
- only boundaries whose certificate multiplicity is `O(1)` may be singled out
  as certified high-level block boundaries.

Interpretation:

- a compiler in `F_{w,b,rho}^{lc}` is allowed to recover a high-level block
  only when its boundaries are locally certifiable by a bounded amount of
  exceptional evidence and that evidence does not collide on `Theta(r)`
  repeated boundaries,
- repeated boundaries whose certificate profiles recur `Theta(r)` times do not
  satisfy this certification rule.

This is the flat compiler class that the sharpened separation theorems compare
against.

For lower-bound-style statements below, we also use the following regularity
assumption on certification:

- the certificate map of a compiler in `F_{w,b,rho}^{lc}` factors through a
  finite witness alphabet determined only by the at-most-`rho` radius-`w`
  witness windows and a bounded internal state;
- away from an `O(1)` prefix/suffix anomaly zone, this certification rule is
  translation-invariant on the lowered repeated body.

## Definition: Representation Gap

Define the `K,w`-representation gap of `C` by

- `Gap_rep^{K,w}(C) = inf_{A in A_w} kappa(A(L_B(C))) - inf_{T in T_K(C)} kappa(L_B(T))`

Interpretation:

- the first term is the best structural cost achievable by a bounded flat
  post-lowering compiler class
- the second term is the best structural cost achievable after bounded semantic
  lifting and bounded term-level candidate generation

If `Gap_rep^{K,w}(C) > 0`, then the semantic representation strictly enlarges
the set of cheaply recoverable opportunities for that bounded compilation
regime.

## Definition: Recoverability Gap

Define the `K,w`-recoverability gap of `C` by

- `Gap_rec^{K,w}(C) = kappa(C_flat^*) - kappa(C_term^*)`

where

- `C_flat^*` is the best candidate recovered from the flat basis-lowered
  representation by the bounded class `A_w`
- `C_term^*` is the best candidate recovered from the bounded semantic term
  representation

This is the operational version used in our experiments: it measures how much
quality is lost because the flat representation does not preserve cheaply
recoverable structure.

## Proposition 1: Repetition Amplifies Representation Gap

Consider a repeated family

- `C_r = P ∘ B^r ∘ S`

and suppose there exists a semantic block candidate `B*` such that

- `kappa(P ∘ (B*)^r ∘ S) <= kappa(P ∘ B^r ∘ S) - r delta + beta`

for some `delta > 0` and boundary term `beta >= 0`.

Then, whenever the bounded flat class `A_w` cannot recover `B*` from
`L_B(C_r)` within its search regime, the recoverability gap satisfies

- `Gap_rec^{K,w}(C_r) >= r delta - beta`

Interpretation:

- a per-block semantic advantage is amplified linearly by repetition count
- this is why repeated families can show very large structural gaps even when
  the semantic lift itself is bounded

This proposition captures the behavior of repeated QFT/QPE-style families and
gives a principled explanation for why the strongest gains often appear on
large repeated circuits.

## Proposition 2: Term-Level Selection Reduces Materialization Complexity

Suppose

- `C_r = P ∘ B^r ∘ S`

and a bounded semantic controller builds block candidates

- `B_1, ..., B_q`

with projected structural costs computable from term-level metrics.

If the flat strategy materializes every full candidate

- `P ∘ B_i^r ∘ S`

before comparison, while the semantic strategy compares projected term costs
first and materializes only the winning candidate, then full-circuit
materialization cost is reduced from

- `Theta(q * M_r)`

to

- `Theta(M_r) +` bounded block-level comparison cost

where `M_r` is the size of the fully materialized repeated circuit.

Interpretation:

- this is not just a coding trick
- it is a consequence of treating the semantic term as the primary comparison
  object

This proposition explains why repeated-run term-level selection can improve
runtime materially on large repeated families such as `qpe_style` and
`hw_mqt_grover_20`.

## Proposition 3: Recoverability Is Representation-Dependent

Suppose a lowering map `L_B` transforms a structured high-level object

- repeated block
- conjugation shell
- Fourier ladder
- mirrored/self-inverse shell

into a basis-level instruction stream whose block boundaries are no longer
distinguished by the local invariants used by the bounded flat class `A_w`.

Then `A_w` cannot, in general, guarantee recovery of that object as a single
semantic unit after lowering, even though semantics are preserved exactly.

Interpretation:

- semantics may survive lowering
- but cheap recoverability of the optimization opportunity may not

This is the core reason the current branch should be framed as a
representation-aware compilation method rather than only as a better pass
ordering.

## Lemma 4: Certificate-Collision Lower Bound

Let `C_r` be a repeated family with `Theta(r)` interior semantic boundaries.
Suppose that:

1. every compiler in `F_{w,b,rho}^{lc}` uses a certificate map drawn from the
   finite witness alphabet above,
2. away from an `O(1)` anomaly zone, certification is translation-invariant on
   the lowered repeated body,
3. every interior boundary `partial` satisfies
   `mult(cert(partial, L_B(C_r))) = Theta(r)`.

Then every compiler in `F_{w,b,rho}^{lc}` can certify at most `O(1)`
boundaries of `L_B(C_r)`.

Interpretation:

- this is a genuine lower-bound-style bottleneck hidden inside the family
  theorems,
- the flat compiler does not fail because semantics are lost,
- it fails because all interior boundaries are locally ambiguous and the class
  is forbidden to break that ambiguity by a bounded, translation-invariant
  local certification rule.

## Primary Theorem: Fourier-Layer Recoverability Separation

The sharpest current PRX-style target is not inverse cancellation. It is a
non-inverse Fourier-layer separation in which the exploitable structure is
Abelian phase aggregation. This is the primary theorem: it gives a clean
witness that semantic pre-basis compilation and bounded flat post-lowering
recovery can have different asymptotic power on the same unitary family.

- `C_{m,r} = H_Lambda D_m(theta)^r H_Lambda`

where

- `D_m(theta) = product_{j=1}^m exp(-i theta_j P_j / 2)`,
- each `P_j` is a diagonal Pauli-`Z` string or a bounded-arity diagonal phase
  interaction,
- all `P_j` commute.

This family has no adjacent `U U^\dagger` cancellation. The exploitable
identity is Abelian coefficient aggregation:

- `D_m(theta)^r = product_{j=1}^m exp(-i r theta_j P_j / 2)`.

Write `pg_B(C)` for the number of nontrivial bounded-arity phase-gadget atoms
retained after lowering to the fixed target basis `B`. Under a fixed
bounded-arity lowering convention, each retained nontrivial phase gadget
contributes at least constant target-basis structure, so lower bounds on
`pg_B` imply corresponding asymptotic lower bounds for gate count and two-qubit
count up to constants.

### Semantic upper bound

A pre-basis Fourier-layer semantic compiler stores one coefficient per
diagonal term and aggregates

- `(P_j, theta_j) -> (P_j, r theta_j)`

before lowering. Under bounded-arity lowering, each aggregated term lowers to
`O(1)` target-basis structure, so the semantic output size is

- `O(m)`,

and in the fixed-width construction where `m = O(1)`, the output size is

- `O(1)`.

### Restricted flat compiler class

Let `F_{w,b,rho}^{fl}` be the class of basis-local flat compilers that:

- receive only the fully basis-lowered stream `L_B(C_{m,r})`,
- use at most `b` bounded candidate-generation rounds,
- can fuse a repeated phase term or a bounded cluster of phase terms only when
  the fusion is justified by at most `rho` radius-`w` witness windows,
- require the certificate to authorize the specific local fusion or bounded
  cluster being rewritten,
- cannot use a repeated local certificate profile by itself to authorize a bulk
  global aggregation over all copies,
- are finite-alphabet, translation-invariant away from an `O(1)` anomaly zone,
- are collision-respecting,
- and are not allowed to first reconstruct a global phase-polynomial or
  commuting-diagonal IR from the whole circuit.

This last exclusion is important. A compiler that globally reconstructs the
diagonal phase-polynomial representation belongs on the semantic side of the
separation, not the basis-local side.

### Theorem

Fix constants `w,b,rho` and a fixed bounded-arity target-basis lowering scheme
`L_B`. Consider `C_{m,r}` with `m > w`. Assume:

1. **bounded arity**:
   every `P_j` has support bounded independently of `m` and `r`;
2. **non-resonance**:
   for the repetition range under consideration, `r theta_j != 0 mod 2*pi` for
   every non-removable term `P_j`; asymptotically this can be enforced by
   choosing `theta_j / pi` irrational;
3. **periodic separated lowering**:
   in the interior of `L_B(C_{m,r})`, two consecutive occurrences of the same
   semantic phase term `P_j` are separated by one full period containing
   `Theta(m)` other lowered phase gadgets, and the radius-`w` witness
   neighborhoods around interior occurrences of the same `P_j` are identical up
   to translation;
4. **bounded local recovery**:
   the compiler is in `F_{w,b,rho}^{fl}`, so fusing repeated phase terms
   requires a finite-alphabet local certificate built from at most `rho`
   radius-`w` windows, the certification rule is translation-invariant away
   from `O(1)` prefix/suffix anomalies, and collision-respecting certificates
   cannot select one copy, one distant partner, or a bulk aggregation set from
   `Theta(r)` locally indistinguishable copies;
5. **no global diagonal lift**:
   the flat compiler class cannot first recover the full commuting diagonal
   phase-polynomial representation.

Then there is a constant `c > 0`, independent of `m` and `r`, such that every
compiler `A` in `F_{w,b,rho}^{fl}` satisfies

- `pg_B(A(L_B(C_{m,r}))) >= c r m - O(m)`.

By contrast, there is a Fourier-layer semantic compiler `S` and a constant
`C > 0` such that

- `pg_B(L_B(S(C_{m,r}))) <= C m`.

Therefore `C_{m,r}` gives an `Omega(r)` representation-dependent separation
between bounded basis-local flat recovery and pre-basis semantic phase
aggregation. In the fixed-width regime `m = m0 > w`, this becomes `Omega(r)`
versus `O(1)`.

### Fixed-width corollary

If `m = m0 > w` is fixed and the non-resonance condition holds for the tested
repetition range, then the theorem gives the direct fixed-width separation

- `Omega(r)` versus `O(1)`.

Every compiler in `F_{w,b,rho}^{fl}` retains `Omega(r)` nontrivial basis-level
phase-gadget structure, while a pre-basis Fourier-layer semantic compiler emits
a constant-size target-basis circuit.

This is the asymptotic interpretation of the `fourier_phase_sandwich`
experiment: optimized UCC emits 42 gates, depth 24, and 12 `cx` gates at every
tested scale.

### Proof

The semantic upper bound and the flat lower bound are separate.

For the upper bound, define `S` to be the compiler that stores the diagonal
layer as a commuting list of term-coefficient pairs before target-basis
lowering. Commutativity gives

- `(product_j exp(-i theta_j P_j / 2))^r = product_j exp(-i r theta_j P_j / 2)`.

A Fourier-layer semantic compiler stores the layer as term-coefficient pairs
`(P_j, theta_j)`, replaces each coefficient by `r theta_j` under the chosen
parameter-normalization convention, and lowers each bounded-arity term once.
Since every `P_j` has bounded support, there is a constant `C` such that the
lowered form of all `m` aggregated terms contains at most `C m` nontrivial
phase-gadget atoms. Hence `pg_B(L_B(S(C_{m,r}))) <= C m`, and this is `O(1)`
when `m` is fixed.

For the lower bound, fix any compiler `A` in `F_{w,b,rho}^{fl}`. Index the
occurrences of the `j`th diagonal term across the repeated layer by
`G_{j,1}, G_{j,2}, ..., G_{j,r}`. By non-resonance, each `G_{j,t}` is a
nontrivial phase-gadget occurrence unless it is explicitly removed by a
certified fusion with other occurrences of the same semantic term. By term
separation, for fixed `w` and `m > w`, no radius-`w` witness window contains
two consecutive occurrences `G_{j,t}` and `G_{j,t+1}`. Thus a valid fusion
across copies cannot be justified by directly observing both occurrences in one
bounded local view.

Remove the `O(1)` prefix/suffix anomaly zone from the repeated body. On the
remaining interior occurrences, the certification rule factors through a finite
witness alphabet, uses at most `rho` bounded windows, and is
translation-invariant. Periodic separated lowering implies that, for each fixed
`j`, all interior occurrences `G_{j,t}` have the same radius-`w` witness data up
to translation. Therefore the local certificate profile attached to those
occurrences has multiplicity `Theta(r)`. Because the class is
collision-respecting, such a repeated certificate profile cannot choose a unique
long-range fusion partner, a unique period boundary, or a unique subset of
interior copies to aggregate. Hence `A` can certify only `O(1)` fusions
involving the anomaly zone for a fixed term `P_j`; for all sufficiently large
`r`, a constant fraction of the `r` occurrences of that term remains
represented by nontrivial lowered phase-gadget structure.

This holds independently for each of the `m` non-resonant diagonal terms.
Summing the retained interior occurrences over all `m` terms gives a constant
`c > 0`, independent of `m` and `r`, such that

- `pg_B(A(L_B(C_{m,r}))) >= c r m - O(m)`.

This proves the lower bound and completes the separation.

The proof has two logically distinct parts. The upper bound is a semantic
coefficient-aggregation identity. The lower bound is a recoverability
obstruction: after periodic basis lowering, all interior copies of a phase term
look identical to the bounded local certificate rule, so the flat compiler
cannot certify the nonlocal aggregation without leaving the restricted class.
This is why the theorem is about representation-dependent recoverability rather
than about unitary equivalence.

### Natural algorithmic source of the witness

The `H · D^r · H` family is synthetic only in the controlled-experiment sense.
It is the minimal fixed-width extraction of a structure that appears naturally
in Fourier-based quantum algorithms. QFT can be written, up to swaps and
ordering conventions, as alternating Hadamard boundaries and controlled phase
rotations. Within each phase stage, the controlled rotations are diagonal in
the computational basis and commute. AQFT keeps the same representation but
truncates small-angle diagonal interactions. QPE adds repeated controlled
powers before an inverse QFT; on an eigenstate of the simulated unitary, these
controlled powers contribute coherent phase factors on the phase register, and
the inverse-QFT stage again exposes a Fourier diagonal layer.

Thus QFT, AQFT, and QPE all contain the same semantic object used by the
witness: a bounded collection of commuting diagonal phase terms whose repeated
use should be aggregated by coefficient addition before basis materialization.
The `fourier_phase_sandwich` family isolates this object so that inverse
cancellation, routing, and unrelated algorithmic structure cannot explain the
result. The QFT/AQFT and QPE-style controls then test whether the same
recoverability issue appears in natural algorithm-source circuits rather than
only in the minimal separation witness.

### Why the restricted flat class is meaningful

`F_{w,b,rho}^{fl}` is not intended to describe every possible compiler. It
intentionally excludes compilers that first lift the entire lowered circuit
into a global diagonal phase-polynomial, ZX-diagram, or commuting-Hamiltonian
representation and then aggregate coefficients. Such compilers instantiate the
semantic side of the separation.

The restricted class captures a common post-lowering engineering regime:

- the compiler sees a flat target-basis instruction stream,
- it applies bounded peephole, commutation, cancellation, or candidate
  generation steps,
- and any fusion must be justified by bounded local evidence.

This connects directly to the current multi-compiler evidence:

- Qiskit preset optimization and UCCDefaults-style flows improve local
  target-basis structure but do not reconstruct the global commuting diagonal
  layer on `H D^r H`;
- TKET FullPeephole probes a strong peephole-oriented regime and times out on
  this family before recovering the constant semantic form;
- PyZX is a stress test for the boundary. PyZX has algebraic rewriting power in
  principle, so the result is not a theorem that PyZX cannot solve the family.
  The narrower claim is that, in the tested QASM/Qiskit-to-PyZX-to-Qiskit
  pipeline and fixed target-basis protocol, PyZX did not recover the global
  diagonal phase-polynomial aggregation.

Thus the theorem and experiments have different roles. The theorem explains
why bounded local post-lowering optimization should not be expected to close
the gap. The Qiskit/TKET/PyZX results show that several strong practical
pipelines, as configured in the artifact, behave consistently with that
barrier. If a future tool explicitly reconstructs and aggregates the global
phase-polynomial, that supports the semantic side of the theorem rather than
refuting the representation-gap claim.

### Experimental role

This theorem is the correct mathematical reading of the
`fourier_phase_sandwich` experiments:

- optimized UCC behaves like the pre-basis semantic compiler and outputs 42
  gates across all tested scales,
- Qiskit opt3, Qiskit commutative inverse cancellation, PyZX in the tested
  pipeline, and TKET FullPeephole do not recover the same global diagonal
  aggregation on this family,
- if a future tool does recover it by building a global phase-polynomial or
  diagonal IR, that supports the semantic side of the theorem rather than
  refuting the representation-gap framing.

## Phase-Ladder Family Separation Theorem

We can sharpen the abstract gap claim into a more separation-style statement
for a concrete QPE/QFT-style family.

Consider a phase-ladder family

- `Q_r = P ∘ F^r ∘ S`

where each repeated block `F` is a bounded Fourier-like ladder consisting of
stages

- `F = F_1 ∘ ... ∘ F_ell`

and each stage `F_j` is built from:

- a bounded Hadamard boundary,
- a commuting diagonal phase layer,
- an optional bounded permutation or terminal swap pattern.

Assume:

1. **bounded semantic recoverability**:
   the semantic lift preserves each copy of `F` as a Fourier-layer term and can
   construct a repeated semantic candidate `T_r^*` such that
   `kappa(L_B(T_r^*)) <= kappa(L_B(Q_r)) - r delta + beta`
   for constants `delta > 0` and `beta >= 0`,
2. **uniform local periodicity after lowering**:
   away from an `O(1)` prefix/suffix zone, every lowered copy of `F` presents
   the same finite family of radius-`w` neighborhoods, so local observations do
   not reveal which repeated copy a window belongs to,
3. **certificate multiplicity growth**:
   every interior ladder boundary `partial` admits only certificate profiles
   with
   `mult(cert(partial, L_B(Q_r))) = Theta(r)`,
   while only the `O(1)` prefix/suffix anomalies have certificate multiplicity
   `O(1)`.

Then, for all sufficiently large `r`,

- `inf_{A in F_{w,b,rho}^{lc}} kappa(A(L_B(Q_r))) - kappa(L_B(T_r^*)) >= (r-c) delta - beta`

and therefore

- `Gap_rec^{K,w}(Q_r) = Omega(r)`.

Interpretation:

- the separation is now stated against an explicit restricted class of flat
  compilers rather than against an informal bounded post-lowering regime
- by Lemma 4, the flat class can certify only the `O(1)` anomalous
  boundaries and cannot uniquely recover the `Theta(r)` interior ladders
- the lower bound is therefore linear because the semantic path can recover all
  `r` ladders while the flat class can recover only `O(1)` of them
- this is a family-level separation in recoverable structure, not just a claim
  about one benchmark or one implementation trick

The theorem is still conditional, but the conditions are now explicit:

- a repeated Fourier-like family,
- a compiler class whose block recovery must be justified by bounded local
  certificates after lowering,
- and a semantic lift that preserves one ladder per repetition.

## Corollary: Phase-Ladder Materialization Separation

Under the same setup, suppose the semantic controller compares `q` block-level
phase-ladder candidates before full reconstruction.

If a flat strategy materializes all full repeated candidates before comparison,
its materialization cost is

- `Theta(q * M_r)`

where `M_r = Theta(r * m_F)` is the size of the fully materialized repeated
phase-ladder circuit and `m_F` is the materialized size of one ladder block.

If the semantic controller compares projected term costs first and materializes
only the winning repeated ladder, then its materialization cost becomes

- `Theta(M_r) + O(q * m_F)`

Interpretation:

- the semantic advantage on phase-ladder families is not only structural
- it also changes the materialization complexity of bounded candidate control

This is the strongest concrete family theorem currently supported by the branch.
It is stronger than the earlier operational theorem because it compares two
explicit compilation classes:

- a locally certifying bounded flat class `F_{w,b,rho}^{lc}`
- a bounded semantic term compiler that preserves repeated ladders

The theorem is therefore better described as a **conditional family
separation theorem** than as a generic recoverability heuristic.

## Mirrored / Conjugation Family Separation Theorem

An analogous separation statement can be written for a second family based on
conjugation or mirrored shells.

Consider a mirrored-shell family

- `G_r = P ∘ C^r ∘ S`

where each repeated block `C` is a bounded shell built from stages

- `C = C_1 ∘ ... ∘ C_m`

and each stage `C_j` has one of the semantic forms

- `Conj(U_j,M_j) = U_j M_j U_j^\dagger`, where `U_j` is a bounded shell and
  `M_j` is a bounded core or marker layer, or
- `Mirror(D_j,S_j)`, where `D_j` is a bounded diagonal prefix and `S_j` is a
  bounded mirrored or self-inverse shell.

Assume:

1. **bounded semantic recoverability**:
   the semantic lift preserves each copy of `C` as a mirrored/conjugation term
   and constructs a repeated semantic candidate `R_r^*` with
   `kappa(L_B(R_r^*)) <= kappa(L_B(G_r)) - r delta + beta`,
2. **uniform local shell periodicity after lowering**:
   away from an `O(1)` prefix/suffix zone, every lowered copy of `C` presents
   the same finite family of radius-`w` neighborhoods, so local observations do
   not reveal which repeated copy an entry or exit shell boundary belongs to,
3. **certificate multiplicity growth**:
   every interior shell entry or exit boundary `partial` admits only certificate
   profiles
   with
   `mult(cert(partial, L_B(G_r))) = Theta(r)`,
   while only `O(1)` prefix/suffix anomalies have certificate multiplicity
   `O(1)`.

Then, for all sufficiently large `r`,

- `inf_{A in F_{w,b,rho}^{lc}} kappa(A(L_B(G_r))) - kappa(L_B(R_r^*)) >= (r-c) delta - beta`

and therefore

- `Gap_rec^{K,w}(G_r) = Omega(r)`.

Interpretation:

- the same recoverability-gap mechanism is not unique to phase ladders,
- it also applies to families whose high-level structure is carried by repeated
  conjugation shells or mirrored/self-inverse shells,
- by Lemma 4, this again becomes a collision-respecting local
  certification barrier rather than just an informal “flat compiler misses the
  boundary” story,
- this is the most natural second theorem line for Grover-like and
  amplitude-amplification-style workloads.

## Corollary: Mirrored-Shell Materialization Separation

Under the same setup, suppose the semantic controller compares `q` block-level
mirrored/conjugation candidates before full reconstruction.

If a flat strategy materializes all full repeated shell candidates before
comparison, its materialization cost is

- `Theta(q * N_r)`

where `N_r = Theta(r * m_C)` is the size of the fully materialized repeated
shell circuit and `m_C` is the materialized size of one shell block.

If the semantic controller compares projected term costs first and materializes
only the winning repeated shell, then its materialization cost becomes

- `Theta(N_r) + O(q * m_C)`

Interpretation:

- the second family is now symmetric with the phase-ladder line not only at the
  recoverability-gap level,
- it also induces the same compressed-domain-vs-flat materialization
  separation.

This second theorem is currently less experimentally mature than the
phase-ladder theorem, but it is the clearest route to a two-family
representation-aware theory.

## Strongest Safe PRX-Style Claim

The strongest safe high-level claim is therefore:

> structured quantum circuit compilation exhibits a representation-dependent
> recoverability gap: for some families, bounded compilation over a flat
> basis-lowered representation is provably weaker, in operational terms, than
> bounded compilation over a semantic term algebra that preserves repeated,
> conjugated, Fourier-like, and mirrored structure.

This claim is stronger than the current systems-only framing because it says:

- the issue is not merely a bad default pipeline
- the issue is not merely one missing pass
- the issue is a mismatch between optimization opportunity and representation

## What This Would Need for a Full PRX-Level Version

To make this into a genuinely strong PRX-style theoretical section, we would
still need one of the following:

1. a sharper class theorem proving Lemma 4 from even weaker assumptions
   than collision-respecting local certification
2. stronger experimental and structural support for the mirrored/conjugation
   family theorem, rather than only the phase-ladder line
3. a more formal semantic-to-flat separation theorem that abstracts both
   repeated phase ladders and mirrored repeated shells

Right now the propositions above are the strongest safe conditional version of
the theory.

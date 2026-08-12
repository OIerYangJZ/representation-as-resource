# Representation-Dependent Recoverability in Structured Quantum Circuit Compilation

## Abstract

Quantum circuit lowering preserves unitary semantics, but it need not preserve
the structural evidence needed for efficient resource reduction. We study this
phenomenon as a representation-dependent recoverability gap: after a circuit is
materialized into a flat target-basis stream, globally meaningful phase,
repetition, or conjugation structure may become locally indistinguishable to a
bounded compiler, whereas a semantic term representation can preserve the same
structure until after aggregation and candidate selection.

The main result is a Fourier-layer recoverability separation. For
`C_{m,r}=H_Lambda D_m(theta)^r H_Lambda`, where `D_m` is a commuting diagonal
phase layer, a restricted bounded flat compiler that cannot reconstruct a
global phase-polynomial representation must retain `Omega(rm)` nontrivial
lowered phase-gadget structure. A pre-basis semantic compiler aggregates the
commuting coefficients and emits `O(m)` structure; in the fixed-width case this
becomes an `Omega(r)` versus `O(1)` separation. The theorem does not claim that
all compilers fail. It identifies the boundary between flat post-lowering
recovery and semantic global lifting.

We instantiate the principle in UCC as an experimental artifact through a
bounded semantic term controller with Fourier-layer, repeated, inverse,
mirrored, and conjugation terms. The empirical role split is deliberate:
Fourier-layer circuits provide the primary separation witness, while
mirrored/conjugation circuits provide secondary anti-regression evidence,
showing how semantic lifting restores UCC to parity with strong flat optimizers
on Grover-like structures. On the fixed-width `H · D^r · H` witness, optimized
UCC reduces inputs of approximately `4k`, `10k`, `20k`, `50k`, and `100k` gates
to `42` gates, depth `24`, and `12` `cx` gates, while `qiskit opt3` grows to
`9,588`, `23,988`, and `47,988` gates at the first three sizes and times out at
`50k` and `100k`. Across official Qiskit instances and public `MQT
Bench`/`SupermarQ` cases, the same mechanism fixes severe UCC regressions
without claiming universal dominance over external compilers. A
resource-consequence experiment further shows that, under a rotation-count
Clifford+T proxy at precision `1e-10`, semantic-first compilation keeps a
constant T-proxy of `2,200`, whereas materialize-first `qiskit opt3` grows from
`479,300` to `2,399,300` before timing out.

## 1. Introduction

Quantum circuit compilation is representation-sensitive. The usual
lower-then-optimize pipeline first decomposes high-level algorithmic structure
into a target basis and then optimizes the resulting instruction stream. This
lowering map is semantically exact, but it is not necessarily
opportunity-preserving: repeated phase ladders, commuting diagonal layers,
inverse shells, and mirrored conjugations can become distributed across a large
basis-level materialization in which their original boundaries are no longer
locally evident.

The bottleneck studied here is not the computational power of an unrestricted
optimizer, but the recoverability of structure under the representation
available to a bounded compiler. A flat basis-level compiler with bounded local
evidence observes only small neighborhoods of the materialized stream. When a
structured family contains many repeated interior positions with identical
local certificate profiles, such a compiler cannot safely select the globally
meaningful aggregation or cancellation boundaries without extra semantic
information. A semantic compiler avoids this ambiguity by keeping the relevant
terms explicit before basis materialization.

We distinguish two empirical regimes of this recoverability gap. The first is
structural separation: a semantic representation exposes a global aggregation,
such as coefficient addition in a commuting Fourier layer, that a restricted
flat compiler cannot recover without reconstructing a global diagonal
representation. Our main theorem proves this regime for
`C_{m,r}=H_Lambda D_m(theta)^r H_Lambda`, giving an `Omega(r)` versus `O(1)`
fixed-width separation in retained phase-gadget structure. The second regime is
recoverability parity: semantic lifting does not beat the strongest external
compiler, but it prevents catastrophic regression by preserving high-level
identities such as mirrored or conjugation shells.

UCC is used as the artifact and diagnostic testbed for this principle, not as
the object of a universal optimizer-dominance claim. Its default flow is
composable across frontends and backends, but that composability also makes it
vulnerable to structured-circuit regressions. The optimized branch adds a
bounded semantic term algebra, dispatch-driven candidate control, projected
block selection, late materialization, and cache-aware reuse. On the primary
Fourier-layer witness, the semantic branch produces the predicted constant
output while tested flat pipelines grow or time out. On mirrored/conjugation
families, it restores UCC to `qiskit opt3`-level quality rather than claiming a
new external-baseline separation.

## 2. Contributions

The paper makes six theory-driven claims.

1. We formalize representation-dependent recoverability: basis lowering
   preserves unitary semantics but can erase the bounded local evidence needed
   to recover repeated, inverse, Fourier-layer, and mirrored/conjugation
   structure.
2. We define a restricted class of locally certifying bounded flat compilers
   and prove a certificate-collision lower-bound lemma explaining why repeated
   semantic positions can become locally indistinguishable after lowering.
3. We prove the primary Fourier-layer recoverability separation: under explicit
   bounded-local recovery assumptions,
   `H_Lambda D_m(theta)^r H_Lambda` requires `Omega(rm)` retained lowered
   phase-gadget structure for restricted flat recovery but only `O(m)`
   structure for pre-basis semantic phase aggregation, with an `Omega(r)`
   versus `O(1)` fixed-width corollary.
4. We identify mirrored/conjugation shells as a secondary recoverability
   regime: semantic lifting prevents severe UCC regressions and restores parity
   with strong flat baselines on Grover-like and mirrored-shell workloads, but
   is not presented as the main external-baseline separation.
5. We instantiate the principle in UCC through a bounded semantic term algebra
   with Fourier-layer, repeated, inverse, mirrored, and conjugation terms;
   projected cost comparison; late materialization; cache-aware subterm reuse;
   and conservative backend-aware dispatch.
6. We evaluate the implementation across theorem-witness families,
   algorithmic-source controls, official real instances, public benchmark
   suites, and hardware-aware cases. The results include a systematic
   fixed-width `H · D^r · H` separation from `qiskit opt3`, broad
   `qiskit opt3`-level quality recovery, mirrored/conjugation anti-regression
   evidence, and a stable five-seed hardware-aware win on `hw_mqt_qaoa_20`.

## 3. Method

### 3.1 From implementation detail to compilation principle

The current branch should not be described only as an implementation that
happens to use semantic terms. A more accurate statement is:

> if exploitable structure is easier to preserve, compare, or reuse before
> basis lowering than after it, then compilation should first move that circuit
> into a bounded semantic term algebra and postpone flat materialization until
> after candidate selection.

This principle is motivated by a representation-dependent notion of
recoverability. Basis lowering preserves semantics, but it does not necessarily
preserve the cheap detectability of repeated blocks, inverse blocks, Fourier
layers, or mirrored/self-inverse shells. In that sense, lowering is
semantics-preserving but not automatically opportunity-preserving.

### 3.2 Representation gap and recoverability gap

The stronger theoretical claim behind the branch is not universal dominance but
representation-dependent recoverability. Let:

- `L_B(C)` be lowering into target basis `B`
- `kappa` be a conservative structural cost
- `T_K(C)` be the bounded set of semantic candidates produced by the semantic
  lift under budget `K`
- `A_w` be a bounded post-lowering compiler class restricted to flat
  basis-level candidate generation or local rewrite regimes

For the sharper family statements below, we replace the earlier informal
boundary-oblivious shorthand by a more explicit restricted class
`F_{w,b,rho}^{lc}` of locally certifying bounded flat compilers. These
compilers operate only on fully materialized basis-level circuits, use local
observations of radius at most `w`, generate at most `b` bounded candidates,
and may recover a semantic unit only across boundaries admitting a local
certificate built from at most `rho` radius-`w` witness windows. Write
`cert(partial, L_B(C))` for the certificate profile of a candidate boundary and
`mult(cert(partial, L_B(C)))` for the number of boundaries with that same
certificate profile. The class is collision-respecting: if
`mult(cert(partial, L_B(C))) = Theta(r)`, the compiler may not use that
certificate to single out one repeated interior boundary as a uniquely
recoverable semantic boundary. Only `O(1)`-multiplicity certificate profiles
may justify singling out a boundary.

For the sharper lower-bound-style statements below, we also assume that the
certificate map factors through a finite witness alphabet induced by the
at-most-`rho` radius-`w` windows and a bounded internal state, and that away
from an `O(1)` anomaly zone the certification rule is translation-invariant on
the lowered repeated body.

Define the `K,w` representation gap of `C` by

- `Gap_rep^{K,w}(C) = inf_{A in A_w} kappa(A(L_B(C))) - inf_{T in T_K(C)} kappa(L_B(T))`

and the operational recoverability gap by

- `Gap_rec^{K,w}(C) = kappa(C_flat^*) - kappa(C_term^*)`

where `C_flat^*` is the best candidate recovered from the flat basis-lowered
representation and `C_term^*` is the best candidate recovered from the bounded
semantic term representation.

The meaning is simple: semantics may survive lowering, while cheap
recoverability of the opportunity may not. This is the sense in which the
branch should be viewed as representation-aware rather than only as a better
default pass schedule.

### 3.2.1 A certificate-collision lower bound

Let `C_r` be a repeated family with `Theta(r)` interior semantic boundaries.
If

1. every compiler in `F_{w,b,rho}^{lc}` uses the finite-alphabet,
   translation-invariant certification rule above, and
2. every interior boundary `partial` satisfies
   `mult(cert(partial, L_B(C_r))) = Theta(r)`,

then every compiler in `F_{w,b,rho}^{lc}` can certify at most `O(1)`
boundaries of `L_B(C_r)`.

This is the lower-bound-style bottleneck used by the family theorems: the flat
compiler is blocked not because semantics disappear, but because all interior
boundaries are locally ambiguous and the class is forbidden to break that
ambiguity by bounded, translation-invariant local evidence.

### 3.3 Primary theorem: Fourier-layer recoverability separation

The central formal statement is not about inverse cancellation. It is a
non-inverse Fourier-layer separation in which the exploitable structure is
Abelian phase aggregation. This is the paper's primary theorem: it provides a
clean witness that semantic pre-basis compilation and bounded flat
post-lowering recovery can have different asymptotic power on the same unitary
family.

- `C_{m,r} = H_Lambda D_m(theta)^r H_Lambda`,

where

- `D_m(theta) = product_{j=1}^m exp(-i theta_j P_j / 2)`,
- each `P_j` is a diagonal Pauli-`Z` string or bounded-arity diagonal phase
  interaction,
- all `P_j` commute.

This family has no adjacent `U U^\dagger` cancellation. The useful algebraic
identity is coefficient aggregation in a commuting diagonal representation:

- `D_m(theta)^r = product_{j=1}^m exp(-i r theta_j P_j / 2)`.

For the separation statement, write `pg_B(C)` for the number of nontrivial
bounded-arity phase-gadget atoms retained after lowering to the fixed target
basis `B`. This is a structural measure rather than a claim about one specific
syntactic gate sequence. Under any fixed bounded-arity lowering convention,
each retained nontrivial phase gadget contributes at least a constant amount of
target-basis structure, so lower bounds on `pg_B` imply asymptotic lower bounds
for gate count and two-qubit count up to constant factors.

A pre-basis Fourier-layer semantic compiler can therefore store one coefficient
per diagonal term, replace `(P_j, theta_j)` by `(P_j, r theta_j)`, and lower
each bounded-arity term once. Its output size is `O(m)`, or `O(1)` in the
fixed-width construction where `m` is constant.

Now define `F_{w,b,rho}^{fl}` as a restricted basis-local flat compiler class.
It receives only `L_B(C_{m,r})`, not the semantic provenance of the repeated
diagonal terms. It may apply arbitrary unitarity-preserving local basis
identities, bounded commutations, bounded peephole rewrites, and at most `b`
bounded candidate-generation rounds. However, any rewrite whose effect is to
fuse repeated occurrences of a phase term, or a bounded cluster of phase terms,
must be justified by at most `rho` radius-`w` witness windows. The certificate
must authorize the specific local fusion or bounded cluster being rewritten; a
repeated local certificate profile cannot by itself authorize a bulk global
aggregation over all copies. The compiler cannot construct an auxiliary
representation keyed by global Pauli strings, global phase-polynomial terms,
or commuting-diagonal Hamiltonian terms before performing the fusion. The
certification rule is finite-alphabet, translation-invariant away from an
`O(1)` anomaly zone, and collision-respecting.

The theorem is therefore a restricted-class separation. It is not a lower bound
against compilers that first reconstruct a global phase-polynomial, ZX, or
diagonal-Hamiltonian representation; such compilers belong to the semantic side
of the separation.

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
   the flat compiler cannot first recover the full commuting diagonal
   phase-polynomial representation.

Then there is a constant `c > 0`, independent of `m` and `r`, such that every
compiler `A` in `F_{w,b,rho}^{fl}` satisfies

- `pg_B(A(L_B(C_{m,r}))) >= c r m - O(m)`.

By contrast, there is a Fourier-layer semantic compiler `S` and a constant
`C > 0` such that

- `pg_B(L_B(S(C_{m,r}))) <= C m`.

Thus the family gives an `Omega(r)` representation-dependent separation
between bounded basis-local flat recovery and pre-basis semantic phase
aggregation. In the fixed-width regime `m = m0 > w`, the separation becomes
`Omega(r)` versus `O(1)`.

Proof. The semantic upper bound and the flat lower bound are separate.

For the upper bound, define `S` to be the compiler that stores the diagonal
layer as a commuting list of term-coefficient pairs before target-basis
lowering. Commutativity gives

- `(product_j exp(-i theta_j P_j / 2))^r`
- `= product_j exp(-i r theta_j P_j / 2)`.

A Fourier-layer semantic compiler stores the layer as term-coefficient pairs
`(P_j, theta_j)`, replaces each coefficient by `r theta_j` under the chosen
parameter-normalization convention, and lowers each bounded-arity term once.
Since each `P_j` has bounded support, there is a constant `C` such that the
lowered form of all `m` aggregated terms contains at most `C m` nontrivial
phase-gadget atoms. Hence `pg_B(L_B(S(C_{m,r}))) <= C m`, and this is `O(1)`
when `m` is fixed.

For the lower bound, fix any compiler `A` in `F_{w,b,rho}^{fl}`. Index the
occurrences of the `j`th diagonal term across the repeated layer by
`G_{j,1}, G_{j,2}, ..., G_{j,r}`. By non-resonance, each `G_{j,t}` represents a
nontrivial phase-gadget occurrence unless it is explicitly removed by a
certified fusion with other occurrences of the same semantic term. By term
separation, for fixed `w` and `m > w`, no radius-`w` witness window contains
two consecutive occurrences `G_{j,t}` and `G_{j,t+1}` of the same semantic
term. Thus a valid fusion across copies cannot be justified by directly
observing both occurrences inside one bounded local view.

Remove the `O(1)` prefix/suffix anomaly zone from the repeated body. On the
remaining interior occurrences, the certification rule factors through a finite
witness alphabet, uses at most `rho` bounded windows, and is
translation-invariant. Periodic separated lowering implies that, for each fixed
`j`, all interior occurrences `G_{j,t}` have the same radius-`w` witness data up
to translation. Therefore the local certificate profile attached to those
occurrences has multiplicity `Theta(r)`. Because the class is
collision-respecting, such a repeated certificate profile cannot choose a unique
long-range fusion partner, a unique period boundary, or a unique subset of
interior copies to aggregate. Therefore `A` can certify only `O(1)` fusions
involving the anomaly zone for a fixed term `P_j`; for all sufficiently large
`r`, a constant fraction of the `r` occurrences of that term remains
represented by nontrivial lowered phase-gadget structure.

This excludes a symmetric operation that aggregates all copies at once, because
such an operation would require exactly the global semantic object indexed by
the repeated Pauli term `P_j`. That operation belongs on the semantic side of
the separation, not the restricted flat-recovery side.

This argument holds independently for each of the `m` non-resonant diagonal
terms. Summing the retained interior occurrences over all `m` terms gives a
constant `c > 0`, independent of `m` and `r`, such that

- `pg_B(A(L_B(C_{m,r}))) >= c r m - O(m)`.

This proves the lower bound and completes the separation.

The proof has two logically distinct parts. The upper bound is a semantic
coefficient-aggregation identity. The lower bound is a recoverability
obstruction: after periodic basis lowering, all interior copies of a phase term
look identical to the bounded local certificate rule, so the flat compiler
cannot certify the nonlocal aggregation without leaving the restricted class.
This is why the theorem is about representation-dependent recoverability rather
than about unitary equivalence.

This theorem is intentionally conditional. A compiler that reconstructs a
global phase-polynomial or diagonal IR belongs on the semantic side of the
separation. Thus a future tool that closes this gap by building such an IR
would support, not refute, the representation-gap framing.

#### Claim boundary of the separation

The positive claim is:

- there exists a family of quantum circuits where the compiler representation
  changes the asymptotic recoverability of an optimization opportunity;
- bounded flat recovery retains `Omega(rm)` phase-gadget structure;
- pre-basis semantic coefficient aggregation retains only `O(m)` structure,
  or `O(1)` in the fixed-width case.

The claim is not:

- a lower bound against all possible quantum compilers;
- a proof that Qiskit, TKET, or PyZX are intrinsically unable to solve the
  family;
- a claim that optimized UCC is universally better than external compilers.

A compiler that globally reconstructs a phase-polynomial, ZX,
stabilizer-phase, or commuting-diagonal Hamiltonian representation has crossed
from the flat-recovery side to the semantic side of the separation. If such a
compiler recovers the same constant-size output, that supports the
representation-gap framing because it identifies the missing semantic
representation.

The external baselines therefore play a diagnostic role. Their failure to
recover the constant form on the configured `H D^r H` pipeline is evidence that
these practical configurations did not reconstruct the required global
diagonal representation under the fixed protocol. The empirical claim is a
regime split, not universal optimizer dominance.

This also makes the claim falsifiable in the right way. A direct flat-stream
pipeline that recovered the constant form without constructing any global
phase-polynomial, ZX, stabilizer-phase, or commuting-diagonal representation
would challenge the adequacy of `F_{w,b,rho}^{fl}` as a model of bounded flat
recovery. A pipeline that succeeds by constructing such a representation would
not challenge the theorem; it would provide an independent implementation of
the semantic side. This distinction prevents the restricted class from being
tuned post hoc to named software outcomes.

#### Fixed-width corollary

If the Fourier-layer width is fixed to a constant `m0 > w` and the
non-resonance condition holds for the tested repetition range, then `C_{m0,r}`
gives a direct

- `Omega(r)` versus `O(1)`

separation. Every compiler in `F_{w,b,rho}^{fl}` retains `Omega(r)` nontrivial
basis-level phase-gadget structure, while the pre-basis Fourier-layer semantic
compiler emits a constant-size target-basis circuit.

This is the asymptotic form of the fixed-width `fourier_phase_sandwich`
experiment: optimized UCC emits 42 gates, depth 24, and 12 `cx` gates at every
tested scale.

#### Natural algorithmic source of the witness

The `H · D^r · H` family is synthetic only in the controlled-experiment sense.
It is the minimal fixed-width extraction of a structure that appears naturally
in Fourier-based quantum algorithms. The quantum Fourier transform can be
written, up to swaps and ordering conventions, as stages of the form

- `H_a · product_{b>a} CP_{a,b}(pi / 2^{b-a})`.

The controlled-phase gates in a stage are diagonal in the computational basis
and commute with one another. Thus each stage contains a commuting diagonal
layer `D_m(theta)` adjacent to a Hadamard or Fourier basis-change boundary.
Approximate QFT deletes sufficiently small-angle controlled phases from the
same diagonal layer, so it preserves the relevant diagonality and
commutativity.

Phase estimation also contains the same object. Standard QPE applies
controlled powers `CU^{2^k}` on a phase register and then applies an inverse
QFT. If `U |psi> = exp(2 pi i phi) |psi>`, phase kickback maps a computational
basis state `|x>` of the phase register to
`exp(2 pi i phi x) |x>`, which is a diagonal phase-gradient operator on that
register. When `U` is itself diagonal, the same conclusion holds directly at
the controlled-power level. The subsequent inverse-QFT block supplies the
Fourier basis-change context around these diagonal phase terms.

Thus QFT, AQFT, and QPE all contain the same semantic object used by the
witness: a bounded collection of commuting diagonal phase terms whose repeated
use should be aggregated by coefficient addition before basis materialization.
The experimental `fourier_phase_sandwich` family isolates this object as
`H_Lambda D_m(theta)^r H_Lambda` so that inverse cancellation, routing,
terminal swaps, non-Abelian subroutines, and approximation thresholds cannot
explain the result.

The natural algorithmic instances and the witness have different roles.
QFT, AQFT, QPE, amplitude-estimation, and QFT-arithmetic benchmarks show that
the semantic object is not invented solely for the experiment. The fixed-width
`H D^r H` witness proves that once this object is repeated, a compiler
restricted to bounded local recovery after lowering can be asymptotically
separated from a compiler that preserves the object semantically. We do not
claim that every full QFT or QPE instance must exhibit the same `Omega(r)` gap
in practice; full algorithms may contain additional structure, frontend
shortcuts, or routing effects. The claim is narrower and stronger: the Fourier
diagonal layer is a natural algorithmic object, and there exists a controlled
family built from that object on which representation alone creates the
recoverability separation.

Natural-source control matrix:

| Source | Semantic object | Experimental control | Observed role |
|---|---|---|---|
| QFT | Hadamard stages plus commuting controlled-phase layers | `algorithmic_qft`, `qft_forward_repeat` | no-worse quality across all five sizes; smaller-size runtime/scalability wins |
| AQFT | truncated QFT diagonal layer with the same commuting structure | `algorithmic_aqft` | no-worse quality across all five sizes; confirms the object is not tied to exact full QFT |
| QPE | controlled phase accumulation and inverse-QFT context | `phase_estimation_real`, `mqt_qpeexact_32`, `mqt_qpeinexact_24`, `qpe_style` | parity/recovery on real and public instances; mixed `qpe_style` scaling, so not the main separation witness |
| QFT arithmetic / amplitude estimation | Fourier-style phase accumulation in arithmetic or estimation routines | `mqt_draper_qft_adder_32`, `mqt_ae_8` | parity with `qiskit opt3` and large baseline-UCC regression repair |
| Minimal witness | fixed-width commuting diagonal phase layer between basis-change boundaries | `fourier_phase_sandwich = H D^r H` | formal separation witness: constant `42`-gate semantic output versus flat-pipeline growth or timeout |

### 3.4 Why the restricted flat class is meaningful

The restricted class `F_{w,b,rho}^{fl}` is not meant to describe all possible
quantum compilers. It deliberately excludes compilers that first lift the whole
lowered circuit into a global phase-polynomial, ZX-diagram, or
commuting-Hamiltonian representation and then aggregate coefficients. Such
compilers belong on the semantic side of the separation.

The class instead abstracts a common engineering regime: after basis lowering,
the compiler works on a flat target-basis instruction stream using bounded
peephole rewrites, bounded commutation/cancellation, bounded candidate
generation, and local certificates for when pieces of the stream may be fused.

This is meaningful for the current experiment:

- Qiskit preset optimization and the UCCDefaults-style pipeline improve local
  target-basis structure but do not reconstruct the global commuting diagonal
  phase layer on `H D^r H`.
- TKET FullPeephole probes a strong local/peephole-oriented regime and times
  out on the Fourier-layer family before recovering the constant semantic form.
- PyZX is a deliberate stress test. PyZX has algebraic rewriting power in
  principle, so its result should not be read as a theorem that PyZX cannot
  solve the family. The narrower claim is that, in the tested
  QASM/Qiskit-to-PyZX-to-Qiskit pipeline and fixed target-basis protocol, PyZX
  did not recover the global diagonal phase-polynomial aggregation.

The theorem and the multi-compiler experiment therefore play different roles.
The theorem explains why bounded local post-lowering optimization should not be
expected to close the gap. The Qiskit, TKET, and PyZX experiments show that
several strong practical pipelines, as configured in the artifact, behave
consistently with that barrier. A future compiler that explicitly reconstructs
and aggregates the global phase-polynomial would not contradict the theorem; it
would instantiate the semantic compiler side.

The class should therefore be read as a representation boundary, not as a
performance ranking. The empirical question is whether practical pipelines, as
configured in the artifact, behave on the flat-recovery side or the
semantic-lifting side for this family. The theoretical question is why the
flat-recovery side cannot use repeated local evidence alone to justify a
global diagonal aggregation.

Operational classification boundary:

For the Fourier-layer family, any pipeline that recovers the constant
fixed-width output must do at least one of the following:

- reconstruct a global semantic representation equivalent to a
  phase-polynomial, ZX, stabilizer-phase, or commuting-diagonal Hamiltonian
  object;
- use nonlocal provenance information from before basis lowering;
- violate the bounded local certification assumptions defining
  `F_{w,b,rho}^{fl}`.

Thus a successful future flat-looking implementation would not by itself
refute the theorem. It would classify the implementation by identifying which
global semantic or nonlocal mechanism it uses.

### 3.5 A phase-ladder family separation theorem

The abstract gap claim can be sharpened into a more separation-style statement
for a QPE/QFT-style family. Consider

- `Q_r = P ∘ F^r ∘ S`

where `F` is a bounded Fourier-like phase ladder built from repeated stages
`F1, ..., Fℓ`, and each stage consists of a bounded Hadamard boundary, a
commuting diagonal phase layer, and an optional bounded permutation or terminal
swap pattern.

Assume:

1. **bounded semantic recoverability**:
   the semantic lift preserves each copy of `F` as a Fourier-layer term and can
   construct a repeated semantic candidate `T_r^*` such that
   `kappa(L_B(T_r^*)) <= kappa(L_B(Q_r)) - r delta + beta`
   for constants `delta > 0` and `beta >= 0`,
2. **uniform local periodicity after lowering**:
   away from an `O(1)` prefix/suffix zone, each lowered copy of `F` induces the
   same finite family of radius-`w` neighborhoods, so local views do not reveal
   which repeated copy a window belongs to,
3. **certificate multiplicity growth**:
   every interior ladder boundary `partial` admits only certificate profiles
   with `mult(cert(partial, L_B(Q_r))) = Theta(r)`, while only the `O(1)`
   prefix/suffix anomalies have certificate multiplicity `O(1)`.

Then, for all sufficiently large `r`,

- `inf_{A in F_{w,b,rho}^{lc}} kappa(A(L_B(Q_r))) - kappa(L_B(T_r^*)) >= (r-c) delta - beta`

and therefore

- `Gap_rec^{K,w}(Q_r) = Omega(r)`.

The meaning is sharper than before. The statement is no longer only that
repetition amplifies recoverability effects. It now says that, under an
explicit restricted class of flat compilers whose block recovery must be
locally certified after lowering, bounded semantic compilation and bounded flat
compilation are linearly separated on this family. The lower-bound-style step
is that interior ladder boundaries collide on `Theta(r)` certificate profiles,
so by the certificate-collision lower bound a collision-respecting flat
compiler can certify only the `O(1)` anomalous prefix/suffix boundaries.

The same family also sharpens the runtime story. If a flat strategy
materializes all `q` full repeated candidates before comparison, its
materialization cost is `Theta(q * M_r)`, where `M_r` is the size of the fully
materialized repeated ladder circuit. If the semantic controller compares
projected term costs first and materializes only the winner, that cost becomes
`Theta(M_r) + O(q * m_F)`, where `m_F` is the materialized size of one ladder
block. This is a materialization separation between the flat and semantic
controllers, not just an implementation detail, and it explains why repeated
phase-heavy workloads such as `qpe_style` are the current branch's strongest
regime.

### 3.6 A mirrored/conjugation family separation theorem

An analogous separation statement can be written for a second family based on
conjugation or mirrored shells. Consider

- `G_r = P ∘ C^r ∘ S`

where each repeated block `C` is a bounded shell built from stages
`C = C_1 ∘ ... ∘ C_m`, and each stage has one of the semantic forms

- `Conj(U_j, M_j) = U_j M_j U_j^\dagger`, where `U_j` is a bounded shell and
  `M_j` is a bounded core or marker layer, or
- `Mirror(D_j, S_j)`, where `D_j` is a bounded diagonal prefix and `S_j` is a
  bounded mirrored or self-inverse shell.

Assume:

1. **bounded semantic recoverability**:
   the semantic lift preserves each repeated shell as a mirrored/conjugation
   term and constructs a repeated semantic candidate `R_r^*` with
   `kappa(L_B(R_r^*)) <= kappa(L_B(G_r)) - r delta + beta`,
2. **uniform local shell periodicity after lowering**:
   away from an `O(1)` prefix/suffix zone, each lowered copy of `C` induces the
   same finite family of radius-`w` neighborhoods, so local views do not reveal
   which repeated copy an entry or exit shell boundary belongs to,
3. **certificate multiplicity growth**:
   every interior shell entry or exit boundary `partial` admits only
   certificate profiles
   with `mult(cert(partial, L_B(G_r))) = Theta(r)`, while only `O(1)`
   prefix/suffix anomalies have certificate multiplicity `O(1)`.

Then, for all sufficiently large `r`,

- `inf_{A in F_{w,b,rho}^{lc}} kappa(A(L_B(G_r))) - kappa(L_B(R_r^*)) >= (r-c) delta - beta`

and therefore

- `Gap_rec^{K,w}(G_r) = Omega(r)`.

This second theorem is currently less experimentally mature than the
phase-ladder line, but it captures the branch's intended second theory route:
Grover-like and amplitude-amplification-like workloads should be understood as
repeated conjugation or mirrored-shell families rather than as isolated timeout
recovery cases. As in the phase-ladder line, the obstruction is now phrased as
a certificate-collision barrier rather than a vague inability to see the
boundary.

Under the same setup, the runtime side is also symmetric with the first family:
if a flat strategy materializes all `q` full repeated shell candidates before
comparison, the materialization cost is `Theta(q * N_r)`, where
`N_r = Theta(r * m_C)` is the size of the fully materialized repeated shell and
`m_C` is the materialized size of one shell block. If the semantic controller
compares projected term costs first and materializes only the winner, the cost
becomes `Theta(N_r) + O(q * m_C)`.

### 3.7 Bounded semantic lift and term algebra

The current branch therefore applies a bounded semantic lift

- `Phi(C) = T(C)`

where `T(C)` is a compositional term in a small hierarchical circuit algebra:

- `Prim(s)`
- `T1 ∘ T2`
- `T^r`
- `Conj(U, M)`
- `Fourier(F1, ..., Fℓ)`
- `Mirror(D, S)`

The intended meaning is:

- `Prim(s)` for primitive or already compiled spans
- `T1 ∘ T2` for sequential composition
- `T^r` for repeated blocks or repeated runs
- `Conj(U, M)` for `U M U^{-1}` structure
- `Fourier(F1, ..., Fℓ)` for phase-ladder or Fourier-type layers broken into
  bounded stages
- `Mirror(D, S)` for a short diagonal prefix followed by a mirrored or
  self-inverse shell

The goal is not to introduce a universal IR. The goal is to preserve exactly
the classes of structure that the branch can exploit reliably before basis
lowering destroys them.

### 3.8 Pre-basis preprocessing

For a bounded number of outer iterations, the method applies:

1. repeated-prefix detection and reuse
2. repeated-run detection and reuse
3. adjacent exact inverse-block cancellation
4. commutative inverse cancellation
5. adjacent parameterized-gate merging when legal
6. bounded semantic lifting into Fourier-layer and mirrored/self-inverse terms

If one full outer iteration does not shrink the circuit, preprocessing stops.

### 3.9 Candidate-selection policy

The method does not trust a single optimization path. Instead, it compares a
small set of candidates depending on the compilation regime:

- pure basis translation
- the default UCC path
- source-level or pre-simplified `qiskit opt3` references where justified
- semantic references derived from Fourier-layer, conjugation, or
  mirrored/self-inverse terms
- limited backend-aware portfolio candidates when routing instability is known
  to matter

The output with the lowest conservative structural cost is returned.

For repeated-run families, the current controller follows a stronger rule than
"compile several full circuits and compare them." It performs one extra level
of selection before rebuilding the full circuit. If

- `C = P · B^r · S`

with repeated block `B`, then the branch builds a bounded set of block-level
candidates `B1, ..., Bq`, evaluates the projected structural costs of the
semantic repeated-run terms

- `P ∘ B1^r ∘ S`
- `...`
- `P ∘ Bq^r ∘ S`

without first materializing all full circuits, picks the best one, and only
then rebuilds the full repeated circuit. This projected term-level selection is
now a key runtime component on `qpe_style` and `hw_mqt_grover_20`.

This leads to a second theoretical point: on repeated families the semantic
controller compares in a compressed domain first and only materializes the
winning candidate. The method is therefore not only representation-aware in
quality terms; it also changes the asymptotic materialization pattern of the
search procedure.

If

- `C = P ∘ B^r ∘ S`

and the semantic controller compares block candidates `B1, ..., Bq` at the
term level before materialization, then the branch avoids rebuilding `q`
different giant circuits just to compare them. In that operational sense,
repetition amplifies both structural quality gaps and the benefit of term-level
selection.

### 3.10 Late materialization, reuse, and fallback

The semantic path is not authoritative. It is advisory. The branch therefore
follows three additional rules:

1. semantic terms should be lowered late, not immediately;
2. semantic subterms should be compiled once and reused aggressively;
3. semantic candidates should lose to flat references whenever they do not
   clearly improve conservative structural cost.

This explains why the current implementation includes:

- semantic term caches
- compiled semantic subterm caches
- repeated-run block caches

and why the branch still falls back to translation, default UCC, or strong
Qiskit references when semantic candidates are not clearly beneficial.

### 3.11 Positioning

This is not a claim that exact inverse cancellation is novel. Nor is it a claim
that the branch already dominates strong external baselines on every workload.
The intended claim is narrower but more principled: bounded structure-aware
preprocessing plus semantic term-level candidate control can materially improve
UCC's default behavior on structured circuits because recoverability of
structural opportunities depends on representation. The strongest safe
high-level claim is therefore:

> structured quantum circuit compilation can exhibit a
> representation-dependent recoverability gap: for some structured families,
> bounded compilation over a flat basis-lowered representation is operationally
> weaker than bounded compilation over a semantic term algebra that preserves
> repeated, conjugated, Fourier-like, and mirrored structure.

## 4. Experimental Setup

### 4.1 Controlled fixed-basis studies

We use a fixed target basis

- `['cx', 'rx', 'ry', 'rz', 'h']`

for all all-to-all comparisons. This isolates structural effects from arbitrary
gateset differences.

The controlled Fourier-layer family is a theorem witness, not an arbitrary toy
benchmark. Its purpose is the same as a separation construction in classical
complexity or compiler lower-bound work: isolate one mechanism under which two
representations expose provably different recoverability. The family uses
standard quantum-circuit ingredients:

- Hadamard basis changes,
- commuting diagonal phase interactions,
- repeated Fourier/QPE-style phase layers.

The width is fixed so that the semantic representation has a constant number
of terms while the flat materialized representation grows with the repetition
count. This fixed-width choice is what makes the `Omega(r)` versus `O(1)`
corollary experimentally visible as the constant `42`-gate output in the
`fourier_phase_sandwich` table.

The witness family validates the theorem; it is not used to claim that all
workloads have the same structure. To connect the construction back to natural
algorithm sources, the evaluation also includes official Qiskit library
instances, `MQT Bench` cases, `SupermarQ` cases, and algorithmic QFT/AQFT
controls. These additional cases test whether the same representation principle
appears in realistic pipelines, but they are not required for the formal
separation.

### 4.2 Real and public benchmarks

We evaluate on:

- official Qiskit circuit-library instances:
  - `phase_estimation_real`
  - `grover_real`
  - `qaoa_real`
- `MQT Bench`:
  - `mqt_qpeexact_32`
  - `mqt_qaoa_32`
  - `mqt_grover_20`
- `SupermarQ`:
  - `supermarq_mermin_bell_8`
  - `supermarq_qaoa_vanilla_12`
  - `supermarq_hamiltonian_sim_8`

### 4.3 Hardware-aware setup

We also evaluate a routed setting using a fixed 20-qubit bidirectional line
backend with native operations:

- `u`
- `sx`
- `p`
- `cx`
- `measure`
- `id`

The main backend-aware cases are:

- `hw_mqt_qpeexact_20`
- `hw_mqt_qaoa_20`

### 4.4 Metrics

We report:

- total gate count
- depth
- `cx` count
- runtime

We also include repeated-run and fixed-seed stability measurements.

## 5. Results

### 5.0 Evidence map

The experiments are organized by the role they play in the recoverability-gap
argument, not by the software package being improved.

1. **Primary theorem witness**:
   the fixed-width `H · D^r · H` family tests the Fourier-layer recoverability
   separation directly.
2. **External flat-pipeline behavior**:
   `qiskit opt3`, TKET, and PyZX comparisons test whether practical pipelines
   in the artifact recover the same global diagonal representation.
3. **Causal ablation**:
   disabling the Fourier-layer semantic path should remove the constant-output
   behavior if semantic aggregation is the operative mechanism.
4. **Resource consequence**:
   semantic-first versus materialize-first resource estimates test whether the
   same representation gap inflates rotation and Clifford+T proxy costs.
5. **Natural-source controls**:
   QFT, AQFT, QPE, amplitude-estimation, and QFT-arithmetic cases test whether
   the witness extracts structure that appears in algorithmic circuits.
6. **Secondary recoverability evidence**:
   mirrored/conjugation families test anti-regression and parity recovery
   rather than the main external-baseline separation.

The current tables now cover the theorem witness, external-pipeline behavior,
causal ablation, resource consequence, natural-source controls, and secondary recoverability
evidence. The Fourier ablation closes the mechanism check: when the
Fourier-layer semantic path is disabled, the no-Fourier variant times out at
every tested scale; Fourier-enabled UCC modes return the canonical `42`-gate
circuit whenever they complete.

### 5.1 Controlled fixed-basis structural results

#### Repeated `QFT + QFT^-1` (100k gates)

| Method | Output Gates | Output Depth |
|---|---:|---:|
| translation only | 400,000 | 142,500 |
| baseline UCC | 968,784 | 276,266 |
| optimized branch | 0 | 0 |

#### Repeated `QFT + QFT` control (100k gates)

| Method | Output Gates | Output Depth |
|---|---:|---:|
| translation only | 400,000 | 140,000 |
| baseline UCC | 1,207,504 | 317,501 |
| optimized branch | 347,500 | 125,000 |

These results show that after controlling for the final target basis, a strong
simplification opportunity remains before basis lowering.

### 5.2 Fixed-basis external baselines at 100k gates

The most important canonical observations are:

- repeated `QFT + QFT^-1`
  - `Qiskit CommutativeInverseCancellation`: `0`
  - optimized UCC: `0`
- repeated `QFT + QFT`
  - `qiskit opt3`: `347,500`
  - optimized UCC: `347,500`
- `qpe_style`
  - baseline UCC: `456,013`
  - optimized UCC: `164,400`
  - `qiskit opt3`: timeout at `> 120s`
- `qaoa_ring`
  - baseline UCC: `300,055`
  - optimized UCC: `100,000`
  - strong fixed-basis baselines: `100,000`
- `grover_mirrored`
  - baseline UCC: `4,122,006`
  - optimized UCC: `1,158,011`
  - `qiskit opt3`: `1,158,011`

The fixed-basis study supports three points:

1. exact inverse cancellation by itself is not novel;
2. baseline UCC can be dramatically worse than strong external baselines;
3. the optimized branch often recovers the strongest fixed-basis quality and in
   `qpe_style` remains stronger than the timed-out `qiskit opt3` reference.

#### Systematic `QFT + QFT^-1` external scaling

The strongest family-level external-baseline win is a runtime/scalability win
under equal optimal output quality. On repeated `QFT + QFT^-1`, optimized UCC
returns the zero-gate circuit at every tested size, is faster than `qiskit opt3`
where `qiskit opt3` completes, and avoids the `qiskit opt3` timeouts at `50k`
and `100k`.

| Input Gates | qiskit opt3 Gates | qiskit opt3 Runtime | qiskit commutative inverse Gates | qiskit commutative inverse Runtime | optimized UCC Gates | optimized UCC Runtime |
|---:|---:|---:|---:|---:|---:|---:|
| `4,000` | `0` | `1.052s` | `0` | `0.082s` | `0` | `0.063s` |
| `10,000` | `0` | `6.090s` | `0` | `0.182s` | `0` | `0.124s` |
| `20,000` | `0` | `24.596s` | `0` | `0.341s` | `0` | `0.279s` |
| `50,000` | timeout | `>90s` | `0` | `0.979s` | `0` | `0.829s` |
| `100,000` | timeout | `>90s` | `0` | `2.271s` | `0` | `1.651s` |

This result should be stated carefully. It is not a strict gate-count win at
the smaller sizes, because `qiskit opt3` also finds the zero-gate circuit there.
The systematic win is that optimized UCC keeps the same optimal output while
scaling better in runtime; as an additional control, it also matches
`qiskit_commutative_inverse` in output quality and is faster at every tested
size.

#### Non-inverse Fourier-layer scaling

To separate the phase-ladder claim from inverse cancellation, we also evaluate
a non-inverse Fourier/phase-polynomial family

- `fourier_phase_sandwich = H · D^r · H`

where `D` is a repeated commuting diagonal phase-polynomial layer. This family
has no `U U^\dagger` structure; the recoverability question is whether the
compiler can aggregate the diagonal phase polynomial before basis lowering.

| Requested Gates | Actual Input Gates | qiskit opt3 | optimized UCC |
|---:|---:|---:|---:|
| `4,000` | `3,998` | `9,588` gates, depth `5,593`, cx `4,788`, `1.898s` | `42` gates, depth `24`, cx `12`, `3.164s` |
| `10,000` | `9,998` | `23,988` gates, depth `13,993`, cx `11,988`, `11.805s` | `42` gates, depth `24`, cx `12`, `14.621s` |
| `20,000` | `19,998` | `47,988` gates, depth `27,993`, cx `23,988`, `46.009s` | `42` gates, depth `24`, cx `12`, `55.843s` |
| `50,000` | `49,998` | timeout `>90s` | `42` gates, depth `24`, cx `12`, `20.129s` |
| `100,000` | `99,998` | timeout `>120s` | `42` gates, depth `24`, cx `12`, `27.064s` |

This is the strongest current phase-ladder result: optimized UCC gives a `5/5`
strict structural-quality win over `qiskit opt3` on a non-inverse family. The
large-scale points also become scalability wins because `qiskit opt3` times
out while optimized UCC finishes with the same constant-size output.

This table is the fixed-width experimental counterpart of the theorem above.
The semantic branch aggregates the repeated commuting diagonal layer and emits
a constant-size circuit, while the post-lowering baselines either grow with
input size or time out under the fixed protocol. The PyZX and TKET rows in the
full result file should be read as empirical pipeline evidence rather than
formal lower bounds on those tools: in this artifact configuration, they did
not recover the global diagonal representation that the semantic theorem says
is needed to close the gap.

External-pipeline failure matrix:

| Pipeline | Representation tested | Observed behavior on `H D^r H` | Interpretation |
|---|---|---|---|
| optimized UCC semantic path | pre-basis Fourier-layer term | `42` gates, depth `24`, `12` cx at every tested scale | implements the semantic side of the theorem |
| `qiskit opt3` | preset target-basis pipeline | `9,588`, `23,988`, `47,988` gates at 4k, 10k, 20k; timeout at 50k and 100k | grows as a materialize-first pipeline that did not recover the global diagonal layer |
| Qiskit commutative inverse cancellation | targeted inverse/commutation control | `13,574`, `33,974` gates at 4k, 10k; timeout from 20k | confirms that inverse-oriented cancellation is not the missing mechanism |
| PyZX pipeline | Qiskit--QASM--PyZX--Qiskit algebraic stress test | `13,574`, `33,974`, `67,974` gates at 4k, 10k, 20k; timeout at larger sizes | did not recover global phase-polynomial aggregation in this configured pipeline |
| TKET FullPeephole | strong peephole-oriented external baseline | timeout from 4k under the fixed protocol | probes the bounded local/peephole side rather than a global semantic lift |
| no-Fourier UCC ablation | same artifact with Fourier-layer semantic path disabled | timeout at every tested scale in the ablation run | causal check that constant output depends on Fourier-layer semantic lifting |

#### Fourier-layer semantic-path ablation

To check whether the `42`-gate output is caused by the Fourier-layer semantic
representation rather than ordinary downstream pass ordering, we disable the
Fourier-layer IR path and rerun the fixed-width `H · D^r · H` witness.

This is a mechanism ablation, not an optimized-versus-baseline ranking. The
relevant comparison is between Fourier-enabled UCC modes and the no-Fourier
semantic-path variant.

| Requested Gates | qiskit opt3 | baseline UCC | optimized UCC | no Fourier-layer IR |
|---:|---:|---:|---:|---:|
| `4,000` | `9,588 / 3.800s` | `42 / 7.862s` | `42 / 7.593s` | timeout `>60s` |
| `10,000` | `23,988 / 24.168s` | `42 / 33.269s` | `42 / 32.363s` | timeout `>60s` |
| `20,000` | timeout `>60s` | timeout `>60s` | timeout `>60s` | timeout `>60s` |
| `50,000` | timeout `>120s` | `42 / 76.554s` | `42 / 80.594s` | timeout `>120s` |
| `100,000` | timeout `>120s` | `42 / 110.383s` | `42 / 110.816s` | timeout `>120s` |

The ablation strengthens the causal interpretation of the Fourier-layer
result. In the no-Fourier variant, the compiler never recovers a completed
constant-size circuit under the timeout budget. In contrast, Fourier-enabled
UCC paths recover the same `42`-gate canonical circuit whenever they finish.
The `20k` row timed out for every method in this ablation run and should be
read as a runtime caveat rather than a quality comparison.

Therefore the constant form is tied to semantic Fourier-layer lifting and
coefficient aggregation, not merely to a favorable ordering of flat
post-lowering passes.

#### Resource-consequence experiment

The Fourier-layer separation is not only a gate-count phenomenon. To test
whether the same representation gap affects resource estimation, we compare a
semantic-first path against materialize-first paths on the
`fourier_phase_sandwich` family. The semantic-first path performs Fourier-layer
aggregation before target-basis materialization. The materialize-first paths
first lower or optimize the expanded circuit using `qiskit opt3` or a
no-Fourier-IR UCC path.

The resource proxy is:

- `T_epsilon(R) = ceil(3 log2(1/epsilon)) R`,

where `R` is the number of arbitrary `rx`/`ry`/`rz` rotations. This is a
reproducible synthesis-cost proxy, not an exact optimal T-count.

Each non-timeout cell below reports:

- `gates / cx / rotations / T_proxy(1e-10)`.

| Requested Gates | semantic first | materialize-first qiskit opt3 | materialize-first no-Fourier UCC |
|---:|---:|---:|---:|
| `4,000` | `42 / 12 / 22 / 2,200` | `9,588 / 4,788 / 4,793 / 479,300` | `9,588 / 4,788 / 4,793 / 479,300` |
| `10,000` | `42 / 12 / 22 / 2,200` | `23,988 / 11,988 / 11,993 / 1,199,300` | timeout `>120s` |
| `20,000` | `42 / 12 / 22 / 2,200` | `47,988 / 23,988 / 23,993 / 2,399,300` | timeout `>600s` |
| `50,000` | `42 / 12 / 22 / 2,200` | timeout `>600s` | timeout `>600s` |
| `100,000` | `42 / 12 / 22 / 2,200` | timeout `>600s` | timeout `>600s` |

At precision `1e-6` and `1e-12`, semantic-first remains constant at T-proxy
values `1,320` and `2,640`, respectively. Materialize-first `qiskit opt3`
reaches `1,439,580` and `2,879,160` at `20k` before timing out at larger sizes.

This connects the recoverability theorem to a fault-tolerant compilation
concern: if coefficient aggregation is delayed until after basis
materialization, resource estimates can be inflated by the unrecovered rotation
multiplicity.

The physical point is the ordering of semantic aggregation relative to
synthesis. In a fault-tolerant pipeline, arbitrary rotations are eventually
approximated by discrete resources such as Clifford+T sequences. If the
compiler first materializes `r` separate rotations and only later estimates or
synthesizes them, the resource estimator sees `r` independent approximation
tasks. A semantic-first pipeline instead combines the coefficients first and
presents one aggregated rotation per phase term.

The proxy above deliberately does not model optimal number-theoretic synthesis
or cancellation inside a synthesized Clifford+T sequence. It isolates the
representation-level multiplicity that enters any resource estimator before
backend-specific synthesis optimizations. Therefore the resource-consequence
result is an FTQC relevance argument for pre-synthesis semantic aggregation,
not an exact optimal T-count claim.

### 5.3 Official real instances

| Instance | baseline UCC | optimized UCC | qiskit opt3 |
|---|---:|---:|---:|
| `phase_estimation_real` | `471,819` gates, `80.923s` | `166,805` gates, `1.364s` | `166,805` gates, `1.298s` |
| `grover_real` | `287,047` gates, `1.915s` | `79,029` gates, `0.556s` | `79,029` gates, `0.552s` |
| `qaoa_real` | `167,833` gates, `1.010s` | `36,512` gates, `0.273s` | `36,512` gates, `0.272s` |

Interpretation:

- optimized UCC strongly improves over baseline UCC on all three official
  instances;
- on all three, output quality matches `qiskit opt3` exactly;
- runtime is now within a small constant factor of `qiskit opt3`.

### 5.4 Public benchmark suites

#### `MQT Bench`

Representative canonical results:

- `mqt_qpeexact_32`
  - baseline UCC: `5,494`
  - optimized UCC: `1,891`
  - `qiskit opt3`: `1,891`
- `mqt_qaoa_32`
  - baseline UCC: `6,310`
  - optimized UCC: `1,422`
  - `qiskit opt3`: `1,422`
- `mqt_grover_20`
  - baseline UCC: timeout `> 120s`
  - optimized UCC: `3,848,810`
  - `qiskit opt3`: `3,848,810`

Additional phase-ladder positive cases:

- `mqt_qpeinexact_24`
  - baseline UCC: `3,682`
  - optimized UCC: `1,206`
  - `qiskit opt3`: `1,206`
- `mqt_ae_8`
  - baseline UCC: `542`
  - optimized UCC: `207`
  - `qiskit opt3`: `207`
- `mqt_draper_qft_adder_32`
  - baseline UCC: `5,278`
  - optimized UCC: `1,630`
  - `qiskit opt3`: `1,630`

#### `SupermarQ`

Representative canonical results:

- `supermarq_mermin_bell_8`
  - baseline UCC: `386` gates, depth `135`
  - optimized UCC: `76` gates, depth `44`
  - `qiskit opt3`: `76` gates, depth `44`
- `supermarq_qaoa_vanilla_12`
  - baseline UCC: `947` gates, depth `225`
  - optimized UCC: `222` gates, depth `80`
  - `qiskit opt3`: `222` gates, depth `80`
- `supermarq_hamiltonian_sim_8`
  - baseline UCC: `71` gates, depth `36`
  - optimized UCC: `71` gates, depth `36`
  - `qiskit opt3`: `51` gates, depth `24`

Interpretation:

- the quality-recovery story generalizes beyond official Qiskit-library
  instances;
- the current `phase-ladder / Fourier-layer` line is additionally supported by
  `qpeinexact`, amplitude estimation, and QFT-based arithmetic;
- the branch is clearly useful on multiple public benchmark families;
- but the method is not uniformly superior on every family.

Additional mirrored/conjugation positive cases:

- `grover_real`
  - baseline UCC: `287,047`
  - optimized UCC: `79,029`
  - `qiskit opt3`: `79,029`
- `mqt_grover_8`
  - baseline UCC: `18,992`
  - optimized UCC: `5,170`
  - `qiskit opt3`: `5,170`
- `mqt_grover_12`
  - baseline UCC: `259,797`
  - optimized UCC: `71,706`
  - `qiskit opt3`: `71,706`
- `mqt_grover_16`
  - baseline UCC: `2,112,285`
  - optimized UCC: `581,098`
  - `qiskit opt3`: `581,098`
- `grover_mirrored_100k`
  - baseline UCC: `4,122,006`
  - optimized UCC: `1,158,011`
  - `qiskit opt3`: `1,158,011`

These cases matter because they make the second theory line less dependent on
the routed timeout-recovery interpretation of `hw_mqt_grover_20`. The current
mirrored/conjugation story is now supported not only by a hard routed Grover
case, but also by clean all-to-all and fixed-basis positive cases spanning an
official Grover real instance, multiple MQT Grover sizes, and a large repeated
mirrored-shell benchmark.

A second scaling sweep makes this support more systematic. On public
`MQT Bench` Grover instances, optimized UCC exactly matches `qiskit opt3` at
sizes 8, 12, and 16:

- `mqt_grover_8`: baseline UCC `18,992`, optimized UCC `5,170`,
  `qiskit opt3` `5,170`
- `mqt_grover_12`: baseline UCC `259,797`, optimized UCC `71,706`,
  `qiskit opt3` `71,706`
- `mqt_grover_16`: baseline UCC `2,112,285`, optimized UCC `581,098`,
  `qiskit opt3` `581,098`

On fixed-basis `grover_mirrored` repeated-shell scaling, the same pattern holds
from 10k to 100k input gates:

- `10k`: baseline UCC `412,206`, optimized UCC `115,811`, `qiskit opt3`
  `115,811`
- `20k`: baseline UCC `824,406`, optimized UCC `231,611`, `qiskit opt3`
  `231,611`
- `50k`: baseline UCC `2,061,006`, optimized UCC `579,011`, `qiskit opt3`
  `579,011`
- `100k`: baseline UCC `4,122,006`, optimized UCC `1,158,011`, `qiskit opt3`
  `1,158,011`

This scaling sweep is important because it makes the second theory line less
dependent on one large structured point. The mirrored/conjugation family now
has both public benchmark scaling and repeated-shell fixed-basis scaling.

### 5.5 Hardware-aware results

#### Canonical fixed-seed results (`seed_transpiler = 12345`)

| Instance | qiskit opt3 | baseline UCC | optimized UCC |
|---|---:|---:|---:|
| `hw_mqt_qpeexact_20` | `1572 / depth 407 / cx 812 / 0.056s` | `1976 / depth 648 / cx 1350 / 0.174s` | `1572 / depth 407 / cx 812 / 0.235s` |
| `hw_mqt_qaoa_20` | `2091 / depth 532 / cx 1530 / 0.078s` | `2057 / depth 513 / cx 1503 / 0.141s` | `2050 / depth 487 / cx 1458 / 0.112s` |

Interpretation:

- `hw_mqt_qpeexact_20` is now a clean fixed-seed parity case: optimized UCC
  matches `qiskit opt3` on total gates, depth, and `cx`, while remaining much
  stronger than baseline UCC.
- `hw_mqt_qaoa_20` is the clearest hardware-aware win: optimized UCC improves
  over both `qiskit opt3` and baseline UCC in total gates, depth, and `cx`.
- `hw_mqt_grover_20` remains too large to use as a main routed-quality table,
  but optimized UCC now returns in `1.999s`, while both baseline UCC and
  `qiskit opt3` still time out under the current setting; the stronger
  mirrored/self-inverse repeated-run candidate lowers total gates to
  `6,467,857`, depth to `4,094,196`, and `cx` to `3,045,048`.

#### Five-seed sweep

Across seeds `0`, `1`, `42`, `12345`, and `54321`, the `hw_mqt_qaoa_20`
external-baseline win persists. Representative pairs are:

- seed `0`
  - `qiskit opt3`: `2107 / depth 536 / cx 1468`
  - optimized UCC: `2046 / depth 457 / cx 1430`
- seed `42`
  - `qiskit opt3`: `2085 / depth 513 / cx 1487`
  - optimized UCC: `2061 / depth 466 / cx 1438`
- seed `54321`
  - `qiskit opt3`: `2127 / depth 523 / cx 1442`
  - optimized UCC: `1992 / depth 425 / cx 1387`

So the hardware-aware QAOA result is not a single-seed artifact.

### 5.6 Scaling and ablation

The scaling study covers `4k`, `10k`, `20k`, `50k`, and `100k` input sizes for:

- `qft_inverse`
- `qpe_style`
- `qaoa_ring`
- `grover_mirrored`

The most important scaling conclusions are:

- `qft_inverse` is solved maximally strongly at every tested size (`0` gates)
- `qpe_style` remains one of the strongest wins; on the latest branch, direct
  spot checks give `82,200` gates at `50k` in `2.504s`, and `164,400` gates at
  `100k` in `4.636s`
- `qaoa_ring` consistently avoids baseline-UCC inflation; at `100k`, output
  remains `100,000`, and the refreshed full-suite scaling run now reports
  `1.901s` at `100k`
- `grover_mirrored` improves strongly over baseline UCC but remains runtime
  heavy at scale

The ablation study shows that the current branch is now concentrated around a
semantic representation and dispatch-controller contribution rather than a
single rewrite rule. At the canonical `10k` point, the main output metrics are
largely preserved across the individual ablations, indicating that the present
branch behavior is dominated by bounded semantic representation, dispatch
structure, and conservative fast paths more than by any one local rewrite in
isolation.

## 6. Discussion

The current evidence supports five main conclusions.

First, the main scientific claim is a representation claim. Basis lowering can
preserve unitary semantics while destroying the bounded local evidence needed
to recover global Fourier-layer structure. The `H · D^r · H` family is the
primary witness: semantic phase aggregation gives a fixed-width `Omega(r)`
versus `O(1)` separation, and the corresponding experiment gives a strict
structural-quality win over the tested external pipelines.

Second, mirrored/conjugation workloads play a different role. They do not
currently provide the main external-baseline separation, because strong flat
pipelines such as `qiskit opt3` can often recover the same output quality.
Their value is as secondary evidence for recoverability-aware compilation:
semantic lifting prevents severe baseline-UCC regressions and restores parity
on Grover-like and mirrored-shell workloads.

Third, simple pass-ordering fixes are not sufficient to explain the full
behavior. They explain part of the UCCDefault story, but the strongest
Fourier-layer result requires preserving and aggregating the semantic diagonal
representation before flat materialization.

Fourth, the empirical story goes beyond the theorem witness without claiming
universality. Official Qiskit instances, `MQT Bench`, and `SupermarQ` show
broad anti-regression and quality-recovery behavior, while mixed cases such as
`supermarq_hamiltonian_sim_8` show that the semantic branch is selective rather
than uniformly dominant.

Fifth, the resource-consequence experiment shows that the recoverability gap
can propagate into synthesis-oriented resource estimates. Under a simple
precision-dependent Clifford+T proxy, semantic-first compilation keeps the
Fourier witness at constant rotation and T-proxy cost, while materialize-first
pipelines grow by orders of magnitude or time out. This is the main evidence
connecting the compilation theorem to FTQC resource estimation.

Sixth, runtime remains a real systems constraint. The method helps on
repeat-heavy and Fourier-like circuits and now behaves much better on the
official real instances, but backend-aware Grover-style routing remains
difficult and some public-suite families reduce only to parity with strong
Qiskit baselines.

## 7. Limitations

This study has several limitations.

1. The theorem is a restricted-class separation, not a lower bound against all
   possible quantum compilers. A compiler that reconstructs a global
   phase-polynomial, ZX, or commuting-diagonal IR belongs to the semantic side
   of the separation.
2. The fixed-width `H · D^r · H` family is intentionally structured. It is a
   minimal theorem witness, not a claim that all QFT or QPE instances exhibit
   the same `Omega(r)` gap.
3. The external-baseline evidence is pipeline-specific. PyZX and TKET are
   evaluated through the artifact's QASM/Qiskit conversion and fixed-basis
   protocol, so their failure to recover the constant form is evidence about
   this configured pipeline rather than a theorem about those tools in all
   modes.
4. The evaluation is centered on UCC and Qiskit-flavored workflows.
5. The method is bounded and heuristic rather than globally optimal.
6. Strong external baselines still match or exceed the method on some families,
   for example `supermarq_hamiltonian_sim_8`; mirrored/conjugation cases are
   therefore framed as parity recovery rather than primary separation evidence.
7. The Fourier ablation is a mechanism check for semantic Fourier lifting.
   Disabling the Fourier-layer IR path times out at every tested scale, while
   Fourier-enabled UCC modes recover the `42`-gate form whenever they complete.
   Since both baseline and optimized Fourier-enabled modes can return the same
   canonical output, the conclusion is about semantic Fourier recognition
   broadly rather than one specific optimized branch shortcut.
8. The resource-consequence experiment uses a precision-dependent
   rotation-count proxy for Clifford+T synthesis cost rather than exact optimal
   synthesis. It supports the scaling consequence of delayed semantic
   aggregation, not a claim about optimal T-counts for every synthesis backend.

## 8. Reproducibility

The frozen research directory includes a standardized artifact entry point:

- `run_frozen_artifact.py`

plus supporting documentation:

- `artifact_environment_snapshot.md`
- `artifact_output_manifest.md`
- `artifact_reproducibility_guide.md`

These provide:

- the local environment and package snapshot
- canonical output files for each experiment family
- one-command reproduction of the frozen suite

## 9. Conclusion

This work supports a representation-aware compilation claim rather than a
sweeping optimizer-dominance claim. Basis lowering can preserve unitary
semantics while destroying the bounded local evidence needed to recover global
Fourier-layer and conjugation structure. The primary result is the Fourier-layer
recoverability separation: bounded flat recovery retains `Omega(rm)`
phase-gadget structure on `H_Lambda D_m^r H_Lambda`, whereas semantic
coefficient aggregation emits `O(m)` structure and `O(1)` structure in the
fixed-width case. The UCC implementation serves as the artifact showing that
this distinction is operational: the Fourier witness gives a strict separation
from tested flat pipelines, and the Fourier ablation shows that disabling the
semantic Fourier path removes the completed constant-output recovery under the
tested timeout budgets. The resource-consequence experiment shows that the
same representation choice can inflate rotation and Clifford+T proxy estimates
when aggregation is delayed until after materialization. Mirrored/conjugation families show the secondary
anti-regression role of semantic lifting by restoring parity on Grover-like
workloads. The remaining challenge is to broaden these
recoverability gains beyond the present workload families and to characterize
more precisely which practical pipelines belong on the flat-recovery side or
the semantic-lifting side of the separation.

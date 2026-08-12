# Term Algebra as a Compilation Principle

## Goal

The current branch should no longer be described only as an implementation that
happens to use semantic terms. A more accurate statement is that it follows a
representation-aware compilation principle:

> structured quantum circuits should be compiled through a bounded semantic term
> algebra whenever structural opportunities are easier to compare, preserve, or
> reuse before basis lowering than after it.

The point is not to claim a universal new IR. The point is to state clearly why
the branch works, what class of opportunities it targets, and why term-level
selection is preferable to flat gate-stream compilation on the targeted
families.

## Principle 1: Recoverability Depends on Representation

Let `C` be a high-level circuit, `L_B(C)` its lowering into target basis `B`,
and `kappa` a structural cost measure on basis-lowered circuits.

The branch is motivated by the observation that structural opportunities are
not representation-invariant in operational terms. A cancellation or reuse
opportunity may be easily visible in `C` but not cheaply recoverable from
`L_B(C)`.

This gives the core systems claim:

- basis lowering is semantics-preserving
- but it is not necessarily opportunity-preserving

In particular, repeated blocks, inverse blocks, Fourier-like phase ladders, and
mirrored/self-inverse shells may survive semantically while becoming much more
expensive to detect or exploit after lowering.

## Principle 2: Lift Only Bounded, Semantically Stable Structure

The branch therefore applies a bounded semantic lift

- `Phi(C) = T(C)`

where `T(C)` is built only from a small family of semantically stable
constructors:

- `Prim(s)`
- `T1 ∘ T2`
- `T^r`
- `Conj(U, M)`
- `Fourier(F1, ..., Fℓ)`
- `Mirror(D, S)`

This is not intended as a universal algebra over all circuits. It is a bounded
semantic lift that targets exactly the structures for which the branch can
offer:

- exact semantics preservation
- cheap projected comparison
- block/stage reuse

The boundedness requirement is part of the principle, not an implementation
detail. If the lift is not bounded, the compilation controller becomes too
expensive and loses its systems value.

## Principle 3: Compare in the Compressed Domain Before Materializing

For repeated or semantic families, the branch should not rebuild several full
candidate circuits and then compare them. That would destroy most of the
runtime benefit of semantic lifting.

Instead, the principle is:

> when a candidate family admits a compressed semantic term representation,
> selection should be performed on projected term-level cost before full-circuit
> materialization.

This is exactly what the repeated-run controller now does. If

- `C = P ∘ B^r ∘ S`

and `B1, ..., Bq` are block-level semantic candidates, then the branch first
compares projected costs of

- `P ∘ B1^r ∘ S`
- ...
- `P ∘ Bq^r ∘ S`

at the term level, chooses one, and only then materializes the final circuit.

This principle explains why the method can improve runtime on large repeated
families without sacrificing structural quality.

## Principle 4: Materialize Late, Reuse Aggressively

Once semantic terms exist, repeated blocks, Fourier stages, mirrored shells,
and conjugation parts should be compiled once and reused many times.

So the branch follows a late-materialization policy:

- build semantic terms first
- compile semantic subterms once
- reuse compiled fragments across candidates and repeated calls
- materialize the full instruction stream only after controller selection

This principle explains:

- semantic reference caches
- compiled semantic term caches
- repeated-run block caches

These are not accidental runtime optimizations. They are consequences of the
fact that the semantic object is the primary unit of comparison and reuse.

## Principle 5: Semantic Terms Are Advisory, Not Authoritative

The branch does not assume that the semantic term path always dominates flat
compilation. That would be too strong and empirically false on some families.

The actual principle is conservative:

> semantic lifting introduces an additional candidate space, not an obligation
> to trust semantic candidates unconditionally.

This is why the branch still performs conservative candidate control against:

- basis translation
- default UCC
- preset/Qiskit references
- backend-aware portfolio references when needed

The semantic path is therefore best understood as a representation-aware
anti-regression layer.

## Resulting Compilation Principle

Putting the five points together, the current branch can be described as
follows:

> a structured circuit should be lifted into a bounded semantic term algebra
> whenever that lift preserves exploitable structure more cheaply than direct
> lowering; candidate selection should then occur on semantic terms before full
> circuit materialization, with late lowering, aggressive reuse, and
> conservative fallback to flat compilation when semantic candidates are not
> clearly beneficial.

This is the sense in which the term algebra is no longer just an implementation
framework. It is the current branch's compilation principle.

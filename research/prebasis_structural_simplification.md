# Pre-Basis Structural Simplification

## Goal

The experimental result on repeated `QFT + inverse-QFT` circuits suggests
that some compilation failures are not caused by missing local identities,
but by *when* simplification is applied in the pipeline.

Once a structured circuit is lowered too early into a basis gate set, much of
 the high-level cancellation structure is obscured. The purpose of this note is
to generalize the current QFT observation into a reusable algorithmic framing.

## Problem Setting

Let a quantum circuit be represented as a sequence of higher-level operations
before basis lowering:

- parameterized single-qubit gates
- multi-qubit controlled operations
- swaps / permutations
- structured subroutines such as QFT, QPE fragments, ansatz layers, or Grover
  iterates

We are interested in circuits that contain at least one of the following
patterns:

1. exact inverse blocks: `U U†`
2. repeated exact blocks: `U U U ...`
3. mirrored blocks: `U M U†`
4. commuting inverse chains that become visible only before decomposition

The core hypothesis is:

> For structured circuits, a bounded structural simplification pass applied
> before basis lowering can prevent catastrophic expansion that downstream local
> synthesis cannot recover from.

## General Algorithm

We define a bounded pre-basis pass over a circuit `C`.

### Input

- a circuit in high-level IR
- a maximum structural block size `B`
- a minimum repetition threshold `R`
- a bounded number of outer iterations `T`

### Output

- a structurally simplified circuit `C'`

### Stable Instruction Signature

For each instruction, compute a stable signature:

- operation name
- normalized parameters
- qubit indices
- classical bit indices

This allows repeated-block and inverse-block detection to be performed over the
instruction stream without immediately decomposing the circuit into basis gates.

### Pass Loop

For up to `T` iterations:

1. Repeated-prefix detection
   - Detect the largest repeated exact prefix block.
   - Simplify one copy of the block.
   - Reuse the simplified block across all repeats if this reduces size.

2. Repeated-run detection
   - Detect the largest repeated exact block anywhere in the circuit.
   - Simplify one instance and reuse it across the run if beneficial.

3. Adjacent inverse-block cancellation
   - Detect a block immediately followed by its inverse.
   - Remove the pair as a whole unit.

4. Commutative inverse cancellation
   - Apply a local commutation-aware inverse-cancellation pass to expose
     additional reductions.

5. Stop criterion
   - If an outer iteration does not reduce instruction count, terminate.

### Pseudocode

```text
Input: circuit C, block bound B, repetition threshold R, iteration bound T
Output: simplified circuit C'

C' <- C
for t in 1..T:
    changed <- false

    C1 <- simplify_largest_repeated_prefix(C', B, R)
    if size(C1) < size(C'):
        C' <- C1
        changed <- true

    C2 <- simplify_largest_repeated_run(C', B, R)
    if size(C2) < size(C'):
        C' <- C2
        changed <- true

    C3 <- cancel_adjacent_inverse_blocks(C', B)
    if size(C3) < size(C'):
        C' <- C3
        changed <- true

    C4 <- commutative_inverse_cancellation(C')
    if size(C4) < size(C'):
        C' <- C4
        changed <- true

    if not changed:
        break

return C'
```

## Simplification Rule for Candidate Blocks

When a candidate block is extracted, simplification can use a hierarchy:

1. exact identity check for bounded-size blocks
2. inverse-pair cancellation
3. commutative inverse cancellation
4. optional exact or symbolic verification for small blocks

The important point is that all of this happens *before* basis lowering.

## Why This Is Not Just a QFT Trick

The QFT example is only one instance of a broader class of structured circuits.
The same pre-basis logic should be evaluated on at least the following four
families:

1. QFT / inverse-QFT
   - canonical exact inverse structure
   - strong test for catastrophic expansion versus structural cancellation

2. QPE-style circuits
   - repeated controlled phase ladders plus inverse QFT style structure
   - useful to test whether the approach generalizes to phase-estimation
     subroutines rather than isolated QFT blocks

3. QAOA / repeated ansatz layers
   - ring entanglers and repeated cost/mixer layers
   - useful to test repeated-block reuse even when exact cancellation is weak

4. Grover-style mirrored iterates
   - oracle / diffusion / mirrored-or-inverse structure
   - useful to test symmetry and mirrored-block detection beyond Fourier-based
     circuits

## Complexity Discussion

With block size bounded by `B` and iteration count bounded by `T`, the pass is
intended to be near-linear in circuit size up to a moderate constant factor.

The expensive part is structural scanning over bounded windows, not global
search for an optimal rewriting.

This is a deliberate design choice:

- we are not solving global quantum circuit optimization
- we are cheaply removing obvious high-level structural redundancy before a
  generic compiler destroys it

## Central Research Question

The paper-level question is not merely:

> "Can PopQC or another pass improve QFT?"

Instead, it is:

> "Can a bounded pre-basis structural simplification stage systematically
> improve compilation for structured quantum circuits by preserving and
> exploiting cancellation opportunities that are otherwise lost after basis
> lowering?"

## Immediate Experimental Plan

The next stage should compare at least:

- baseline compiler
- post-transpilation optional pass
- pre-basis structural simplification

for the four circuit families listed above, tracking:

- total gate count
- depth
- 2-qubit gate count
- runtime
- whether the final result preserves target constraints

This would establish whether the key improvement comes from:

- the rewrite rules themselves, or
- the placement of those rules in the compilation pipeline

## Benchmark Instantiation For The First Study

For the first round of experiments, the four structured circuit families can be
instantiated with exact `100,000`-gate workloads as follows:

1. QFT / inverse-QFT
   - 8 qubits
   - block size: 80 gates
   - exact repeats: 1,250

2. QPE-style phase-kickback roundtrip
   - 4 evaluation qubits + 1 phase qubit
   - includes the inverse-QFT swap layer so the block size is exactly 50 gates
   - exact repeats: 2,000

3. QAOA ring layer
   - 20 qubits
   - block size: 100 gates
   - exact repeats: 1,000

4. Grover mirrored iterate
   - 8 qubits
   - block size: 50 gates
   - exact repeats: 2,000

These four cases are intentionally chosen to cover:

- exact inverse structure
- phase-estimation style ladders
- repeated ansatz layers without strong exact cancellation
- mirrored / symmetric iterates

## First 100k-Gate Comparison

Using the four benchmark families above, the first comparison was run across
three modes:

1. baseline UCC
2. UCC + PopQC as an optional post-transpilation custom pass
3. experimental pre-basis structural simplification

### Summary Table

| Family | Mode | Output Gates | Output Depth | 2Q Gates | Runtime |
|---|---|---:|---:|---:|---:|
| QFT / inverse-QFT | baseline | 968,784 | 276,266 | 135,004 | 6.514 s |
| QFT / inverse-QFT | post-pass | 896,288 | 272,516 | 135,004 | 23.885 s |
| QFT / inverse-QFT | pre-basis | 0 | 0 | 0 | 1.627 s |
| QPE-style | baseline | 456,013 | 236,011 | 60,002 | 3.762 s |
| QPE-style | post-pass | 428,007 | 234,011 | 60,002 | 10.695 s |
| QPE-style | pre-basis | 212,006 | 140,002 | 60,002 | 226.131 s |
| QAOA ring | baseline | 300,055 | 163,055 | 40,000 | 2.440 s |
| QAOA ring | post-pass | 262,127 | 145,091 | 40,000 | 6.326 s |
| QAOA ring | pre-basis | 100,000 | 62,000 | 40,000 | 5.042 s |
| Grover mirrored | baseline | 4,122,006 | 2,166,021 | 468,000 | 24.305 s |
| Grover mirrored | post-pass | 3,762,014 | 2,076,018 | 468,000 | 111.706 s |
| Grover mirrored | pre-basis | 1,158,011 | 762,010 | 468,000 | 60.556 s |

### Family-Level Interpretation

#### QFT / inverse-QFT

This is the clearest success case for pre-basis structural simplification.

- baseline UCC catastrophically expands the circuit
- the optional post-pass reduces the blow-up slightly, but does not change the
  qualitative failure mode
- the pre-basis method removes the entire repeated inverse structure and
  returns the empty circuit

This strongly supports the claim that placement in the pipeline matters more
than merely adding a post-pass.

#### QPE-style

The QPE-style benchmark also benefits substantially from pre-basis
simplification in output size:

- baseline: `456,013`
- post-pass: `428,007`
- pre-basis: `212,006`

However, the runtime cost is currently prohibitive:

- baseline: `3.762 s`
- post-pass: `10.695 s`
- pre-basis: `226.131 s`

So the method generalizes beyond QFT in circuit quality, but not yet in
practical runtime.

#### QAOA ring

For the repeated-layer ansatz case, pre-basis simplification is best understood
as an anti-regression result rather than a strong optimizer:

- baseline and post-pass both inflate the circuit substantially
- the pre-basis method preserves the input scale exactly

This indicates that the current structural rules are useful as a guard against
destructive rewriting, even when they do not produce large positive
compression.

#### Grover mirrored

The mirrored Grover-style benchmark shows that the method is not only a Fourier
special case:

- baseline and post-pass both explode badly
- pre-basis simplification reduces the blow-up by a large margin

The result is still far from ideal, but it is a strong sign that mirrored and
inverse-aware structure should be treated before basis lowering.

## Initial Conclusion

The first 100k-gate study supports four claims.

1. Placement matters.
   Pre-basis simplification can be dramatically stronger than a post-pass on
   structured inverse workloads.

2. The idea generalizes beyond QFT.
   It also helps on QPE-style and Grover-style circuits, though with different
   quality/runtime tradeoffs.

3. The current method is not yet universal.
   On QAOA-like layered ansatz circuits it mostly acts as an anti-regression
   guard, not a strong compressor.

4. Runtime is now the main research bottleneck.
   The current implementation proves the value of the approach, but still needs
   better bounded scanning, block selection, and family-aware heuristics before
   it is a practical compiler stage.

This means the next paper-level step is not to ask whether the idea works at
all, but to ask how to make pre-basis structural simplification both:

- general enough to cover several structured circuit families
- and efficient enough to compete with standard compilation pipelines in wall
  clock time

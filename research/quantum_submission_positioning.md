# Quantum Submission Positioning

## One-sentence positioning

This paper is a reproducible compiler-systems study showing that bounded
pre-basis structural preprocessing plus conservative candidate control can act
as an anti-regression and quality-recovery layer for UCC on structured quantum
circuits.

## What we claim

1. baseline UCC has real regressions on structured workloads
2. these regressions are not fully explained by simple pass-ordering fixes
3. the optimized branch recovers `qiskit opt3`-level output quality on official
   real instances and multiple public benchmark families
4. the optimized branch exceeds `qiskit opt3` on at least one stable
   hardware-aware public benchmark (`hw_mqt_qaoa_20`)

## What we do not claim

1. that we built a universally superior compiler
2. that exact inverse cancellation itself is novel
3. that the method dominates strong Qiskit baselines on every workload family

## Reviewer-facing framing

The most important point is that the contribution is not a single rewrite rule.
It is a bounded redesign of the UCC decision flow:

- pre-basis structural preprocessing
- conservative candidate selection
- source-level short-circuiting
- limited backend-aware portfolio search only where instability matters

## Strongest evidence to emphasize

- official real instances:
  - `phase_estimation_real`
  - `grover_real`
  - `qaoa_real`
- public benchmark sources:
  - `MQT Bench`
  - `SupermarQ`
- hardware-aware evidence:
  - stable win on `hw_mqt_qaoa_20`
  - fixed-seed parity on `hw_mqt_qpeexact_20`
- stability:
  - five-seed win on `hw_mqt_qaoa_20`

## Weak points to acknowledge explicitly

- some families still only reach parity with `qiskit opt3`
- `supermarq_hamiltonian_sim_8` is a mixed case
- the method is bounded and heuristic, not globally optimal
- `hw_mqt_grover_20` is still best framed as a timeout-recovery / robustness
  case rather than a main competitive routed-quality result, even though the
  stronger mirrored/self-inverse repeated-run IR now lowers its total gates,
  depth, and `cx` versus the earlier fallback

## Recommended paper-level claim

> bounded pre-basis structural preprocessing is a meaningful optimization
> opportunity for UCC: it repairs strong default-pipeline regressions, recovers
> Qiskit-level quality on real and public benchmark instances, and can exceed
> `qiskit opt3` on stable hardware-aware public cases while also improving
> robustness on harder routed workloads.

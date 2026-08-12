# Quantum Submission Checklist

## Goal

This checklist tracks the current UCC optimization line against the realistic
requirements for **Quantum (Journal)**.

The paper should be framed as a **compiler-systems study**, not as a claim that
we built a universally stronger compiler than Qiskit.

The strongest defensible claim is now:

> bounded pre-basis structural preprocessing plus conservative candidate control
> materially improves UCC's default behavior on structured workloads, recovers
> `qiskit opt3`-level output quality on real and public benchmark instances,
> and yields a stable hardware-aware win on `hw_mqt_qaoa_20`.

## Current Status

Core experimental requirements are satisfied.

Already in place:

- official Qiskit real instances
  - `PhaseEstimation`
  - `GroverOperator`
  - `QAOAAnsatz`
- strong baselines
  - baseline UCC
  - `qiskit opt3`
  - `qiskit_commutative_inverse`
- scaling and ablation
- two public benchmark sources
  - `MQT Bench`
  - `SupermarQ`
- hardware-aware evaluation on a 20-qubit line backend
- five-seed stability evidence for the hardware-aware QAOA win
- artifact packaging and one-command reproduction

## Canonical Strongest Results

### Real all-to-all instances

- `phase_estimation_real`
  - baseline UCC: `471,819`
  - optimized UCC: `166,805`
  - `qiskit opt3`: `166,805`
- `grover_real`
  - baseline UCC: `287,047`
  - optimized UCC: `79,029`
  - `qiskit opt3`: `79,029`
- `qaoa_real`
  - baseline UCC: `167,833`
  - optimized UCC: `36,512`
  - `qiskit opt3`: `36,512`

### Public benchmark suites

- `MQT Bench`
  - `mqt_qpeexact_32`: optimized UCC matches `qiskit opt3`
  - `mqt_qaoa_32`: optimized UCC matches `qiskit opt3`
  - `mqt_grover_20`: optimized UCC matches `qiskit opt3`, baseline UCC times out
- `SupermarQ`
  - `supermarq_mermin_bell_8`: optimized UCC matches `qiskit opt3`
  - `supermarq_qaoa_vanilla_12`: optimized UCC matches `qiskit opt3`
  - `supermarq_hamiltonian_sim_8`: mixed case; optimized UCC does not beat strong Qiskit baselines

### Hardware-aware canonical win

- `hw_mqt_qaoa_20`
  - `qiskit opt3`: `2091` gates, depth `532`, `cx = 1530`
  - optimized UCC: `2050` gates, depth `487`, `cx = 1458`
- this win remains stable across seeds `0`, `1`, `42`, `12345`, and `54321`

## Submission Consequences

The submission should **not** claim:

- a universally superior compiler
- novelty from exact inverse cancellation alone
- dominance over strong Qiskit baselines on every workload family

The submission **should** claim:

- baseline UCC has real structural regressions
- these regressions are not fully explained by simple pass-ordering fixes
- bounded pre-basis preprocessing plus candidate control consistently recovers
  strong output quality for UCC
- the method goes beyond parity in at least one stable hardware-aware public case

## Remaining Work

The remaining work is packaging rather than new core experiments:

- finalize the Quantum-oriented manuscript
- add the minimal figure set
- prepare submission-facing metadata and cover materials

## Readiness

Current readiness assessment:

- experiments: ready
- reproducibility: ready
- framing: ready after claim tightening
- manuscript packaging: in progress

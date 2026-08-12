# Unitary Foundation Microgrant Proposal

## Project Title

Pre-Basis Structural Simplification for the Unitary Compiler Collection (UCC)

## One-Sentence Summary

This project will turn a promising experimental optimization branch for UCC
into a reproducible, upstream-ready compiler optimization workflow that
prevents severe regressions on structured quantum circuits and recovers
`qiskit opt3`-level output quality on real algorithm-family instances.

## Project Summary

Quantum circuit compilers often lower circuits into basis gates before
exploiting higher-level structure. In UCC, this can lead to severe regression
on structured workloads: inverse structure, repeated blocks, and mirrored
subroutines may be obscured or destroyed before simplification has a chance to
act.

I have developed an experimental optimization branch for UCC that adds bounded
pre-basis structural preprocessing and conservative candidate selection. The
goal is not to claim a universally superior compiler, but to improve UCC's
default behavior on real structured circuits while keeping the optimization
bounded and reproducible.

The current prototype already demonstrates strong evidence on official Qiskit
circuit-library instances and large structured benchmarks. The proposed
microgrant project would turn this prototype into a polished open-source
contribution with a benchmark harness, artifact-quality reproducibility, and
an upstream proposal aligned with UCC's contribution process.

## Why This Project Matters

UCC is an important open-source effort for making quantum compilation more
composable across frameworks and backends. A practical weakness of the current
pipeline is that structure can be lost before useful simplifications happen.

This project matters for three reasons:

1. It addresses a real systems problem inside an existing open-source quantum
   compiler, rather than building a disconnected research prototype.
2. It improves compiler robustness on structured workloads that occur in
   algorithmic families such as phase estimation, Grover-style search, and
   QAOA.
3. It produces reusable open-source assets: benchmark scripts, reproducible
   evaluation, and an upstream-compatible optimization proposal.

## Existing Evidence

The current prototype has already been evaluated on both synthetic structured
families and official Qiskit circuit-library instances.

### Official Real Instances

All results below use a fixed final target basis:

- `["cx", "rx", "ry", "rz", "h"]`

#### `phase_estimation_real`

| Method | Output Gates | Runtime |
|---|---:|---:|
| baseline UCC | `471,819` | `76.706 s` |
| optimized UCC | `166,805` | `2.007 s` |
| qiskit opt3 | `166,805` | `1.306 s` |

#### `grover_real`

| Method | Output Gates | Runtime |
|---|---:|---:|
| baseline UCC | `287,047` | `1.735 s` |
| optimized UCC | `79,029` | `0.933 s` |
| qiskit opt3 | `79,029` | `0.499 s` |

#### `qaoa_real`

| Method | Output Gates | Runtime |
|---|---:|---:|
| baseline UCC | `167,833` | `0.931 s` |
| optimized UCC | `36,512` | `0.416 s` |
| qiskit opt3 | `36,512` | `0.251 s` |

These results support the following current claim:

> bounded pre-basis structural preprocessing plus source-level short-circuiting
> can act as an anti-regression and quality-recovery layer for UCC, reaching
> `qiskit opt3`-level output quality on official real instances while keeping
> runtime within a small constant factor of direct `qiskit opt3`.

### Large Structured Benchmarks

On fixed-basis `100,000`-gate structured circuits, the prototype also shows
strong gains over baseline UCC:

- repeated `QFT + QFT^-1`:
  - baseline UCC: `968,784` gates
  - optimized branch: `0` gates
- repeated `QFT + QFT`:
  - baseline UCC: `1,207,504` gates
  - optimized branch: `347,500` gates

These controlled experiments show that UCC's regressions are not only due to
gate-set translation overhead; there is a real optimization opportunity before
basis lowering.

## Proposed Work

I propose a 3-6 month project with four concrete work packages.

### 1. Upstream-Compatible Optimization Path

Refactor the current experimental branch into a cleaner, upstream-compatible
optimization path for UCC. This includes:

- isolating the structure-aware preprocessing logic
- clarifying which parts belong in default UCC behavior versus an optional pass
- aligning the implementation with UCC's compiler-pass contribution process

### 2. Real Benchmark Expansion

Extend the current evaluation from official Qiskit instances to broader public
benchmark sources, such as:

- additional Qiskit library algorithms
- MQT Bench
- SupermarQ

The goal is to demonstrate where the method helps, where it only avoids
regression, and where it does not add value.

### 3. Reproducible Artifact and Benchmark Harness

Package the benchmark workflow into an artifact-quality evaluation harness:

- benchmark generation scripts
- fixed-basis comparison scripts
- scaling and ablation studies
- saved JSON/Markdown result tables
- clear instructions to reproduce all main figures and tables

### 4. Upstream Proposal and Documentation

Prepare the final results in a form useful to the UCC maintainers:

- a focused proposal discussion
- code cleanup and documentation
- optional-pass or pipeline-optimization proposal
- user-facing explanation of when the optimization is expected to help

## Deliverables

By the end of the project, I expect to deliver:

1. A cleaned and documented optimization implementation in the UCC research
   branch.
2. A benchmark harness covering real algorithm-family circuits and public
   benchmark suites.
3. Reproducible result artifacts for fixed-basis comparisons, scaling, and
   ablation.
4. An upstream-facing proposal package for the UCC maintainers.
5. A paper-style technical report describing the optimization opportunity,
   algorithm, and empirical findings.

## Timeline

### Month 1

- clean the current prototype
- finalize benchmark harness for official Qiskit instances
- add at least one public benchmark-suite integration

### Month 2

- run expanded benchmark comparisons
- complete scaling and ablation refresh on the latest branch
- identify the final upstream-compatible decomposition of the optimization

### Month 3

- write documentation and artifact guide
- prepare upstream proposal discussion
- package the results into a report suitable for a paper or technical note

If the project extends toward 4-6 months, the additional time would go toward:

- broader benchmark coverage
- maintainer feedback and iteration
- optional upstream PR work after the discussion phase

## How the Funds Would Be Used

The grant would primarily support:

- developer/researcher time for implementation, benchmarking, and integration
- compute time and storage for large benchmark runs and artifact preparation
- documentation and publication-quality packaging of the results

This project is an especially good fit for microgrant support because it is:

- open-source
- scoped to a 3-6 month deliverable
- valuable to an existing community-maintained quantum software project
- unlikely to receive traditional funding at this stage despite having clear
  practical value

## Why Unitary Foundation

This project aligns directly with Unitary Foundation's goals:

- contributing to an existing open-source quantum project
- improving useful quantum software infrastructure
- creating artifacts that help other contributors and researchers build on the
  work

It is also well matched to the Foundation's funding model: this is exactly the
kind of focused, bottom-up open-source systems work that can materially improve
the ecosystem with a modest grant.

## Risks and Mitigation

The main technical risk is that the optimization may not consistently outperform
strong external baselines on every workload family.

The mitigation is that the project is not framed as "build a universally better
compiler." Instead, it is framed as:

- identifying a real optimization opportunity in UCC
- characterizing where it helps and where it does not
- delivering a reproducible artifact and upstream-ready proposal

That means the project remains valuable even if the final result is a bounded
optimization layer rather than a universally dominant pass.

## Short Applicant Statement

I want to use this microgrant to turn a promising experimental UCC optimization
branch into a reusable open-source contribution with strong reproducibility and
clear upstream value. The current prototype already shows large improvements on
official Qiskit algorithm-family circuits and on large structured workloads.
The next step is to package that work into something the community can inspect,
reuse, benchmark, and potentially integrate.

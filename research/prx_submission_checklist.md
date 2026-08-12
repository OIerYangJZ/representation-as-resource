# PRX Quantum Submission Checklist

## Goal

This checklist is for evaluating what would still be required to make the
current UCC optimization project plausibly competitive for **PRX Quantum**.

This is a much higher bar than the Quantum checklist. The relevant standard is
not simply "solid experiments" but rather:

- stronger novelty
- broader impact
- stronger external-baseline evidence
- a more general scientific conclusion

## Current Assessment

The current work is **not yet PRX-ready**.

At present, the strongest defensible interpretation is:

- a compiler systems optimization study for UCC
- a clear demonstration that pipeline placement matters
- a bounded preprocessing design that fixes severe UCC regressions and recovers
  strong baseline quality on real algorithm-family instances

That is already meaningful, but it is still closer to:

- a strong systems / software optimization paper

than to:

- a field-shaping, broadly general quantum-science result

## What PRX Would Need Beyond the Current State

### 1. A stronger scientific claim than "improves UCC"

Why:

- PRX-level work needs a conclusion that matters beyond one codebase

Needed upgrade:

- formulate the project as a more general principle of quantum compilation,
  for example:
  - when basis lowering destroys structure irreversibly
  - when pre-basis simplification is provably advantageous
  - which circuit families exhibit a gap between pre-lowering and post-lowering
    optimizability

Success condition:

- the central claim reads like a compiler principle, not a UCC patch study

### 2. Broader compiler comparison

Why:

- PRX-level empirical work cannot stop at "baseline UCC vs optimized UCC vs
  Qiskit"

Minimum target:

- `Qiskit`
- `TKET` if feasible and stable
- at least one more relevant compiler/synthesis baseline if available
  (for example a BQSKit-based reference where appropriate)

Success condition:

- a broad, fair cross-compiler comparison table exists for the key workloads

### 3. A significantly broader real benchmark corpus

Why:

- three official Qiskit-library instances are not enough for PRX

Needed expansion:

- public benchmark suites
  - `MQT Bench`
  - `SupermarQ`
  - possibly `QASMBench`
- more real algorithm families
  - additional phase-estimation variants
  - amplitude-estimation / amplification style circuits
  - more than one QAOA graph family
  - additional mirrored / structured search circuits

Success condition:

- the paper can show broad behavior across multiple public sources, not just
  curated internal examples

### 4. Clear wins against strong external baselines

Why:

- matching `qiskit opt3` is a strong result for a systems venue
- PRX usually needs more than parity

Needed result profile:

- multiple workload families where the method clearly beats strong baselines
  in at least one critical metric:
  - gate count
  - depth
  - 2Q gate count
  - runtime at matched quality

Success condition:

- the main results table shows repeated wins, not just parity and anti-regression

### 5. A backend-aware / architecture-aware study

Why:

- PRX-level evidence should connect more strongly to realistic hardware or
  realistic compilation settings

Needed:

- multiple hardware-aware targets
- coupling maps or native-gate backends
- comparison of routed circuits and 2Q metrics

Success condition:

- at least one section demonstrates relevance beyond abstract all-to-all
  fixed-basis compilation

### 6. Stronger scaling evidence

Why:

- current scaling evidence is useful, but PRX will likely expect stronger and
  cleaner scaling behavior

Needed:

- refreshed scaling study on the latest optimized branch
- ideally larger size coverage where feasible
- repeated timing / variance bars for key workloads

Success condition:

- scaling behavior is stable, reproducible, and clearly interpretable

### 7. A clearer theoretical component

Why:

- PRX papers often benefit from a more explicit theory contribution, even when
  experimentally grounded

Possible directions:

- a formal classification of circuit families where pre-basis simplification
  has a structural advantage
- sufficient conditions for recoverable vs irrecoverable structure loss after
  basis lowering
- formal bounds or complexity discussion for the preprocessing stage and the
  placement gap

Success condition:

- the paper offers something more general than empirical heuristics

## Concrete Experimental Tasks

### Must-do

1. Refresh all existing benchmark tables on the latest branch.
2. Add at least one public benchmark suite.
3. Add at least one additional compiler baseline beyond Qiskit/UCC.
4. Add hardware-aware experiments.
5. Demonstrate at least one real workload family with a genuine external-baseline win.

### Strongly recommended

6. Add repeated timing and variance for all headline results.
7. Expand the real-instance set beyond the three current Qiskit-library cases.
8. Add one explicitly theory-motivated experiment section tied to a general claim.

## Non-Goals For PRX Preparation

Do **not** mistake these for sufficient PRX upgrades:

- polishing prose only
- adding a few more synthetic stress tests
- making the UCC code cleaner without broadening the scientific result
- showing only that UCC no longer regresses badly

Those are useful, but they do not close the PRX gap.

## Final Readiness Check

The work becomes plausibly competitive for **PRX Quantum** only when most of
the following are true:

- the claim generalizes beyond UCC
- the benchmark corpus is broad and public
- strong external baselines are repeatedly beaten on real workloads
- hardware-aware evidence is included
- scaling and variance are thoroughly documented
- a meaningful theoretical principle accompanies the empirical study

Until then, the project is better viewed as a strong candidate for:

- ACM TQC
- IEEE TQE
- potentially Quantum, after the narrower checklist is completed

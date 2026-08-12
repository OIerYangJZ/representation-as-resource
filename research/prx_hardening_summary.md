# PRX Hardening Summary

This note records the four current PRX-facing hardening steps and where they
are now written in the paper package.

## 1. Main theorem hardening

Status: completed in the current draft.

Where:

- `PaperDraft/ucc_paper_draft_latex.tex`
- `ucc/research/quantum_paper_draft.md`
- `ucc/research/representation_gap_claims.md`

Content now included:

- explicit restricted flat compiler class `F^{fl}_{w,b,rho}`;
- finite-alphabet, translation-invariant local certificate rule;
- collision-respecting certificate condition;
- no-global-diagonal-lift condition;
- structural measure `pg_B`;
- formal Fourier-layer theorem for `C_{m,r}=H_Lambda D_m(theta)^r H_Lambda`;
- fixed-width `Omega(r)` versus `O(1)` corollary tied to the 42-gate output;
- operational classification boundary: a future compiler that succeeds must
  either reconstruct a global semantic representation, use pre-lowering
  provenance, or leave the restricted flat class.

## 2. Natural algorithmic source hardening

Status: completed in the current draft.

Where:

- `PaperDraft/ucc_paper_draft_latex.tex`, `Algorithmic Source of the Fourier-Layer Witness`
- `PaperDraft/ucc_paper_draft_latex.tex`, `Role of Controlled Witness Families`
- `ucc/research/quantum_paper_draft.md`, natural-source control matrix

Content now included:

- QFT source: Hadamard stages plus commuting controlled-phase layers;
- AQFT source: truncated version of the same diagonal phase-layer object;
- QPE source: controlled phase accumulation and inverse-QFT context;
- amplitude-estimation and QFT-arithmetic controls;
- explicit distinction between natural algorithmic source controls and the
  minimal theorem witness `fourier_phase_sandwich = H D^r H`.

## 3. Multi-compiler failure matrix

Status: completed in the current draft.

Where:

- `PaperDraft/ucc_paper_draft_latex.tex`, `External-pipeline failure matrix`
- `ucc/research/quantum_paper_draft.md`, `External-pipeline failure matrix`
- `Paper/Report.tex`, Chinese summary slide

Matrix entries:

- optimized UCC semantic path: constant 42 gates;
- `qiskit opt3`: grows to 9,588 / 23,988 / 47,988 gates and then times out;
- Qiskit commutative inverse control: not sufficient, times out from 20k;
- PyZX pipeline: grows to 13,574 / 33,974 / 67,974 gates and then times out;
- TKET FullPeephole: times out from 4k;
- no-Fourier UCC ablation: times out at every tested size.

Interpretation:

This is not a universal ranking of named compilers. It is a representation
diagnostic showing that the tested configured pipelines did not reconstruct the
global diagonal/phase-polynomial representation required by the semantic side
of the theorem.

## 4. Resource-consequence / FTQC meaning

Status: completed in the current draft.

Where:

- `PaperDraft/ucc_paper_draft_latex.tex`, `Resource-consequence experiment`
- `PaperDraft/ucc_paper_draft_latex.tex`, `Significance for Fault-Tolerant Synthesis`
- `ucc/research/quantum_paper_draft.md`, resource-consequence section
- `Paper/Report.tex`, Chinese FTQC/resource slides

Content now included:

- semantic-first path keeps the Fourier witness at 22 rotations and
  `T_proxy(1e-10)=2,200`;
- materialize-first `qiskit opt3` reaches 23,993 rotations and
  `T_proxy(1e-10)=2,399,300` at 20k before timing out at larger scales;
- the result is framed as an ordering effect:
  semantic aggregation before synthesis/resource estimation versus
  materialization before synthesis/resource estimation;
- explicit caveat: this is a reproducible rotation-count Clifford+T proxy, not
  an exact optimal T-count claim.

## Current PRX-facing conclusion

The current paper should be pitched as:

> A representation-dependent recoverability separation for Fourier-layer
> quantum circuits, experimentally instantiated in UCC, with a multi-compiler
> diagnostic showing that several strong configured flat pipelines fail to
> recover the same global diagonal representation, and a resource-consequence
> experiment showing that this representation gap can propagate into
> fault-tolerant synthesis-oriented estimates.

What remains is no longer primarily code or raw experiment generation. The
main remaining PRX risk is conceptual polish: making the restricted compiler
class feel natural, making the theorem statement concise enough for reviewers,
and avoiding overclaiming beyond the Fourier-layer separation.

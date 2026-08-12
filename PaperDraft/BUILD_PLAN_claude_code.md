# BUILD PLAN — Packing-Family Scaling Experiment and Final Assembly (v7.2 PRXQ)

> **2026-08-01 supersession.** The user explicitly authorized a local rerun for
> the current revision.  The executed packing configuration uses
> `Delta = pi/4` and per-token angle `pi/16`, with exact rational-pi
> certificates.  Issues 13--16 also add separate certificate, cut-trace, and
> fixed-total-error synthesis/QRE artifacts; the older scope notes below apply
> only to the original packing-only handoff.

> **Context for the implementation agent.** The manuscript `main.tex` (+ `appendix/`,
> `references.bib`) is the repaired PRXQ version. The formal layer has been rewritten:
> the old vacuous `B_int + B_out >= m` theorem is replaced by (a) an unconditional
> output-description counting theorem (`thm:output-counting`) and (b) a streaming
> commitment–memory tradeoff (`thm:main-tradeoff`) proved via a cut-reconstruction
> message argument, with bookkeeping in Appendix A (`app:lem:reconstruction`).
> The packing-separation constant is corrected to `eps0 = sin(1/4) ~ 0.247`.
> The tex compiles clean (0 errors, 0 undefined references) with red `\TBD{...}`
> placeholders in Sec. VII.B (Packing-Family Scaling) awaiting real-toolchain data.
>
> **Your job:** run the experiment, fill the placeholders, regenerate the figure,
> rebuild, and verify. **Do not edit the formal sections** (Secs. III–V, Appendix A).
> If you believe you have found a mathematical error, STOP and report it; do not fix it.

---

## 0. Honest-scope boundary (governs all prose you write)

- The external-toolchain rows are **configured-pipeline diagnostics**. They do NOT
  prove, test, or validate `thm:main-tradeoff` (commitment–memory split is not
  observable from gate counts) and are not members of the transducer class.
- Panel (b) bit curves are **deterministic encoding rules**, not measurements.
- FORBIDDEN in any text you write or fill: "proves", "validates the theorem",
  "independent evidence", "empirical confirmation", "verifies the bound",
  "confirms Theorem", or equivalents referring to the packing figure/table.
  Permitted framing: "links", "illustrates", "diagnoses", "reports the behavior of".
- Do not describe panel (b)'s tightness display as a "check" of the theorem;
  it displays stated encoding conventions against the counting line.

## 1. Instance construction (matches Sec. VII.B text — do not deviate)

- Characters: chain two-body Pauli-Z characters `a_j = e_j + e_{j+1}`,
  j = 1..m, on `n = m + 1` qubits. These are F2-independent for every m.
- **Rank certification (required):** for each m in the sweep, run an exact
  F2 Gaussian elimination over the support matrix (reuse/extend
  `witness_rank_audit/verify_support_rank.py`) and assert `rank == m`.
  Record the verifier output in the frozen JSON.
- Per-token lowering (same convention as the manuscript / prior witnesses):
  `RZ_i(theta) RZ_j(theta) CP_ij(-2*theta)` implements `exp(-i*theta*Z_i Z_j / 2)`
  up to global phase.
- Encoding: balanced round-robin (`def:streaming-encoding`),
  `sigma(i) = ((i-1) mod m) + 1`, dispersal `r = 4`, per-token angle
  `alpha/r = pi/16` (`alpha = pi/4`), input `x = (1,...,1)` (worst case,
  avoids zero-angle identity ambiguities). Stream = `r*m` two-body tokens
  = `3*r*m` gates. The round-robin interleaving on shared wires is the point:
  do NOT sort/group tokens by generator before handing to the toolchains.
- Sweep: `m ∈ {4, 8, 16, 32, 64}` → `n ∈ {5, 9, 17, 33, 65}`.

## 2. Pipelines and protocol

Run under the standard frozen protocol (Appendix B provenance map),
`timeout_s = 600` wall-clock per method per instance, pinned environment
(Python 3.10.12, Qiskit 2.5.0, PyZX 0.10.4, pytket 2.18.0, UCC 0.4.12):

1. `semantic_ucc` — Fourier-layer IR enabled (`UCC_DISABLE_FOURIER_LAYER_IR` unset)
2. `qiskit_opt3` — `optimization_level=3, layout_method="trivial", routing_method="none"`
3. `tket_paulisimp_rebased` — identical generic preamble as canonical protocol:
   DecomposeBoxes, AutoRebase({CX,Rz,Rx}), RemoveRedundancies, PauliSimp,
   RemoveRedundancies, target-basis cleanup
4. `staq_rotation_folding` — public `fold_rotations`, commit a2acd39, generic
   double-precision QASM2 patch, no family labels
5. `phase_poly_reference` — aggregate commuting rz/cp coefficients, lower once
   via Qiskit opt0. NOTE: the existing reference recognizes the HD^rH sandwich;
   the packing stream has NO Hadamard boundaries. Extend the recognizer to a
   plain commuting rz/cp layer, or add a `--no-boundary` mode; disclose the
   change in provenance.

Target basis `B = [cx, rx, ry, rz, h]` throughout.

**Correctness:** every completed cell must pass equivalence to `U_x`:
- `n <= 6` (m = 4, and only m = 4): exact global-phase-aligned numerical check,
  `eps <= atol + rtol*max|U_ij|`, `atol = rtol = 1e-9`.
- `n > 6` (m >= 8): symbolic phase-polynomial certificate (`def:certificate`):
  extract diagonal coefficients per character key from the output, compare to
  the aggregate `x_j * alpha` modulo 2*pi, with the Hadamard-free adjustment.
  Certificate generator and checker must remain independent implementations.
- Statuses `timeout / correctness failure / predicate error / unsupported`
  recorded separately, never scored as numerical results.

## 3. Deliverables

### 3a. `scripts/packing_scaling_real.py`
Parameter-free `__main__`; runs Sec. 1–2; writes:
- `figures/packing_scaling.csv` with columns:
  `m,n,path,status,gates,depth,cx,runtime_s,certificate,bits_repr`
- per-cell logs + environment snapshot into
  `research/packing_scaling/` (frozen-JSON style, SHA256SUMS updated).

### 3b. Panel-(b) representation rules (deterministic; state them verbatim in README)
- Semantic encoding bits: `bits_sem(m) = m + 2*ceil(log2(m+2)) + 8`
  (m-bit support mask + width field + fixed header).
- Echo encoding bits: `bits_echo(m) = (3*r*m) * (2*ceil(log2(n)) + 6)`
  (per-gate: two qubit indices + opcode/param tag).
- Counting line: `y = m` (Kraft-tight binary prefix-free lower bound).
- Assertions: `bits_sem(m) >= m` for all m; `bits_sem(m) - m <= 3*ceil(log2 m) + 10`;
  `bits_echo(m) / m` grows ~ `Theta(log m)` (monotone increasing ratio suffices).

### 3c. `figures/packing_scaling.pdf` — two panels
- (a) log–log completed output gates vs m, five pipelines, status cells omitted
  from curves (annotate statuses in caption-consistent style).
- (b) `bits_sem`, `bits_echo`, and the Kraft-tight line `m` vs m (log x, log y).
- Style-match the existing figures (matplotlib, same fonts/markers as
  `fourier_separation.pdf` generation scripts).

### 3d. Fill the manuscript placeholders
- Replace each `\pkcell` in `tab:packing-scaling` with `gates/depth/cx` for
  completed cells or the literal status word (`timeout`, etc.). 25 cells.
- Replace the `\pkResultsSummary` macro DEFINITION in the preamble with one
  factual paragraph (<= 6 sentences) written from the frozen CSV. Obey Sec. 0.
  Template shape: which paths completed at which m; how semantic UCC and the
  reference scale with m; how the external rows scale with the r*m stream;
  end with one sentence noting statuses are recorded separately.
- Restore `figures/scaling_plot.png` from the frozen figures directory
  (Appendix C has an `\IfFileExists` guard on it).
- After filling: `grep -n "TBD" main.tex appendix/*.tex` must return ONLY the
  `\newcommand{\TBD}` definition line (or delete the macro if unused).

## 4. Verification checklist (all must pass; stop on first failure)

1. Rank verifier: `rank_F2 = m` at every m; recorded in JSON.
2. All assertions of 3b pass.
3. Every completed cell's certificate passes; statuses distinct in CSV.
4. `figures/packing_scaling.csv` and `.pdf` exist; CSV values match the
   deterministic rules and the frozen per-cell logs.
5. LaTeX build `pdflatex; bibtex; pdflatex; pdflatex`:
   zero errors, zero undefined references, zero multiply-defined labels,
   `fig:packing-scaling` and `tab:packing-scaling` resolve.
6. Figure/table numbering audit: page through the compiled PDF; confirm
   `fig:packing-scaling` renders as a real figure (no TBD box), and that
   figure/table numbers cited in prose match the rendered numbers
   (cross-table consistency lesson from Round 3→4: any numerical fill can
   introduce a new mismatch — diff every number in prose against the CSV).
7. Forbidden-phrase scan over the diff of your prose edits (Sec. 0 list),
   including negated-quantifier variants ("zero pipelines", "neither pipeline",
   "not a single") — do not let scoped-universal claims through.
8. `PYTHONDONTWRITEBYTECODE=1` prefix on any `py_compile` sanity checks.
9. SHA256SUMS / FILE_MANIFEST.tsv updated for all new/changed artifacts.

## 5. Out of scope — do not do

- No edits to Secs. III–V, Appendix A, or any theorem/lemma/proof text.
- No pure-simulation substitute for the toolchain runs (the sweep is cheap:
  <= 768 gates at m = 64).
- No end-to-end QRE runs; no changes to the frozen fixed-width witness data.
- No claim upgrades anywhere (Sec. 0).

## 6. Execution order

1. Rank verifier extension + run.
2. `scripts/packing_scaling_real.py` (instance gen → 5 pipelines × 5 sizes →
   certificates → CSV → figure).
3. Fill `\pkcell`s and `\pkResultsSummary`; restore `scaling_plot.png`.
4. Full LaTeX build; checklist Sec. 4 top to bottom.
5. Freeze: logs, CSV, SHA256SUMS, manifest.

## 7. Open items for the humans (not for this agent)

- Math-collaborator review now covers THREE load-bearing proofs before freeze:
  (i) the per-pass pumpability induction (Appendix A, pre-existing),
  (ii) the corrected packing-separation lemma (`lem:packing-separation`),
  (iii) the streaming tradeoff message argument
       (`thm:main-tradeoff` + `app:lem:reconstruction`).
- Prof. Deng sign-off on the new abstract/contributions framing.
- AQIS-submitted version divergence: this manuscript now differs materially
  from the AQIS extended abstract; decide whether to notify.

# Quantum submission format

The manuscript was reformatted from **PRX Quantum** (`revtex4-2`) to
**Quantum** (`quantumarticle`, https://quantum-journal.org). The PRXQ sources
are frozen verbatim under [`prxquantum_format_backup/`](prxquantum_format_backup/).

## Active documents

`main.tex` is the shared manuscript body and defaults to the complete arXiv
content when compiled directly.  Use the two entry points below for release
builds so the intended version is explicit.

| Version | Entry point | Content policy | Build |
| --- | --- | --- | --- |
| arXiv | `main_arXiv.tex` | Complete current manuscript, including the classical-text provenance note in the acknowledgements. | `latexmk -pdf main_arXiv.tex` → 53 pp. |
| Quantum submission | `main_quantum.tex` | Same manuscript, except that the two `Yijing`/`Laozi` passages and their framing are omitted from the acknowledgements. | `latexmk -pdf main_quantum.tex` → 53 pp. |
| Supplement | `supplement.tex` | Shared by both versions. | `latexmk -pdf supplement.tex` → 5 pp. |

All three build clean from a wiped auxiliary state: exit 0, no undefined references
or citations, no BibTeX warnings.

Drop the `unpublished` class option and replace it with `accepted=YYYY-MM-DD`
once the paper is accepted; that switches on Quantum's branding and the
"Accepted in Quantum" page footer.

## What changed relative to the PRXQ source

Formatting only — no text, no numbers, no claims, no figures were touched.

- **Class.** `revtex4-2 [aps,prx,reprint,floatfix,superscriptaddress]` →
  `quantumarticle [a4paper,twocolumn,10pt,unpublished]`. Author/affiliation
  markup is unchanged: `quantumarticle` accepts the REVTeX
  `\author`/`\affiliation`/`\email` form and auto-detects repeated
  affiliations as superscript addresses.
- **`\pdfoutput=1`** added immediately after `\documentclass`. It must sit
  there and not before: `quantumarticle` sets `\pdfoutput=0` at the end of
  the class and then checks, at the first `\usepackage`, that the author put
  it back — the arXiv wants it in the first five lines either way.
- **`\maketitle` moved before the `abstract` environment** (REVTeX wants it
  after).
- **`\date{\today}` removed.** `quantumarticle` errors on `\today`, since the
  arXiv typesets on demand and the date would drift.
- **Bibliography** now `\bibliographystyle{quantum}` with
  `\usepackage[numbers]{natbib}`, and moved *before* `\appendix`, per the
  Quantum template. `quantum.bst` renders every entry's title as a DOI
  hyperlink, which Quantum requires as a Crossref member.
- **`acknowledgments` → `acknowledgements`.** In `quantumarticle` the former
  is a one-argument command, not an environment. The author-contribution
  paragraph that trailed it now carries its own
  `\section*{Author contributions}` heading instead of running on unlabelled
  under Acknowledgements.
- **`\counterwithout{equation}{section}` dropped.** It existed to undo
  REVTeX's per-appendix equation numbering; `quantumarticle` numbers
  equations continuously already, which is what the Quantum template
  prescribes.
- **`\let\switch@array\relax` retained.** `quantumarticle` pulls in REVTeX's
  `ltxgrid`/`ltxutil` for the two-column grid and `widetext`, so `ltxutil`'s
  legacy `array` patch — incompatible with `array` 2.6n on TeX Live 2026 —
  still has to be disabled, exactly as in the PRXQ build.
- **`references.bib`:** `kushilevitz1997communication` gained its Cambridge
  DOI (`10.1017/CBO9780511574948`, verified against Crossref);
  `sipser2012introduction` gained `nolink = {}`, `quantum.bst`'s marker for a
  work with no DOI, eprint, or URL. Without these two, `quantum.bst` aborts
  with a literal-stack error.
- **`supplement.tex`:** same class swap; the title's manual `\\` breaks were
  removed (`quantumarticle` typesets the title in LR mode and rejects them);
  and the four `\includegraphics{../../figures/...}` paths were corrected to
  `../figures/...`. That last one was a pre-existing bug, not a consequence
  of the reformat — the supplement could not build from `PaperDraft/` before.

## Content revision carried out alongside the reformat

Two changes that are *not* formatting, made on 2026-09-22 and recorded here
because they alter the submission package:

- **Retitled** to *Representation-Dependent Recoverability in Quantum
  Compilation*. The abstract and introduction were reweighted so the
  recoverability bounds and their measurement lead, and the fault-tolerant
  resource estimate reads as a downstream consequence. `supplement.tex`
  carries the new title. No section was moved or removed.
- **Proposition 7 (commitment toll) was reproved as a two-sided
  characterization.** The previous statement fixed a mask and then counted
  over all masks, and derived a bound on the committed prefix alone from a
  hypothesis that did not exclude the crossing state. It is now stated over
  a mask ensemble compiled by one mask-uniform algorithm, under an explicit
  *executed commitment* hypothesis (new Definition 18), proved by source
  coding, and paired with a converse clause showing that a buffered
  mask-deferred compiler pays no toll at all. The E8 control arm
  `stream_opt_maskdeferred` is that converse, measured. Scope caveats are in
  the new Remark 11 and in a new item in Sec. 12.2.

## Version policy and remaining submission work

The two release entry points are intentionally thin wrappers around
`main.tex`; do not copy the manuscript body into either wrapper.  The Quantum
switch controls only the classical-text block in the acknowledgements.  Grant
acknowledgements, the generative-AI disclosure, author contributions, and all
scientific content remain identical between the two versions.

`cover_letter/cover-letter.tex` is still addressed to *PRX Quantum* and argues
the paper's fit for that journal (lines 48, 58, 123); it also quotes the old
title (line 56). It is an `article`-class document, so it needs no format
change, but it does need an editorial rewrite for Quantum.

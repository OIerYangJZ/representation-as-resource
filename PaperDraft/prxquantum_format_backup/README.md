# PRX Quantum format backup

Frozen snapshot of the manuscript as it was submitted to **PRX Quantum**
(`revtex4-2`, options `aps,prx,reprint,floatfix,superscriptaddress`), taken
before the reformat for **Quantum**.

Contents:

| File | Note |
| --- | --- |
| `main.tex` | PRXQ manuscript source, verbatim |
| `main.bbl` | REVTeX (`apsrev4-2`) bibliography produced from `../references.bib` |
| `main.pdf` | Last compiled PRXQ PDF (48 pp.) |
| `appendix/` | Appendix sources as of the PRXQ submission |

## Rebuilding

`main.tex` resolves `\input` and `\includegraphics` paths **relative to
`PaperDraft/`**, not to this folder (it reaches out to `../theory/`,
`../figures/`, `generated/`, `figures/`, `appendix/`). To rebuild it, run
from `PaperDraft/`:

```sh
cp prxquantum_format_backup/main.tex ./main_prxq.tex
latexmk -pdf -interaction=nonstopmode main_prxq.tex
```

The live manuscript (`PaperDraft/main.tex`) is now in Quantum
(`quantumarticle`) format; see `PaperDraft/README_quantum_submission.md`.

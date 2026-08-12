#!/usr/bin/env bash
# Build a self-contained Overleaf upload bundle for the PRX Quantum submission
# (manuscript + cover letter).
#
# The working tree keeps the manuscript at PaperDraft/ but pulls \input and
# \includegraphics targets from ../theory/ and ../figures/.  Overleaf has no
# parent directory above the project root, so this script flattens those two
# escapes into theory/ and figures/ inside the bundle and rewrites the paths in
# main.tex accordingly.  Nothing else in the source is modified.
#
# Usage:  bash PaperDraft/scripts/make_overleaf_bundle.sh
# Output: PaperDraft/overleaf_bundle/  and  PaperDraft/overleaf_bundle.zip

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PAPER="$(dirname "$HERE")"          # .../PaperDraft
ROOT="$(dirname "$PAPER")"          # repository root
OUT="$PAPER/overleaf_bundle"
ZIP="$PAPER/overleaf_bundle.zip"

rm -rf "$OUT" "$ZIP"
mkdir -p "$OUT"/{figures,theory,appendix,generated,cover_letter}
mkdir -p "$OUT/research/claim_evidence" "$OUT/research/experiment_registry/generated"

# --- manuscript, with the two parent-relative prefixes flattened -------------
sed -e 's|\.\./theory/|theory/|g' \
    -e 's|\.\./figures/|figures/|g' \
    "$PAPER/main.tex" > "$OUT/main.tex"

cp "$PAPER/references.bib" "$OUT/references.bib"
cp "$PAPER/main.bbl"       "$OUT/main.bbl"        # so the bibliography renders on the first pass

# --- \input targets ----------------------------------------------------------
cp "$PAPER/appendix/"*.tex   "$OUT/appendix/"
cp "$PAPER/generated/"*.tex  "$OUT/generated/"
for f in model_implementation_mapping qary_packing dispersed_update_tradeoff \
         randomized_multipass_extension matching_upper_bounds certificate_soundness; do
  cp "$ROOT/theory/$f.tex" "$OUT/theory/$f.tex"
done
cp "$PAPER/research/claim_evidence/claim_evidence_rows.tex" \
   "$OUT/research/claim_evidence/"
cp "$PAPER/research/experiment_registry/generated/reorder_probe_rows.tex" \
   "$PAPER/research/experiment_registry/generated/hardware_qpe_rows.tex" \
   "$PAPER/research/experiment_registry/generated/hardware_qaoa_rows.tex" \
   "$OUT/research/experiment_registry/generated/"

# --- figures -----------------------------------------------------------------
# PaperDraft/figures first; then the six drawn from the repository-root figures/
# directory.  eta_sweep_pareto.pdf exists in both and differs -- main.tex cites
# the PaperDraft copy, so the root copy is deliberately not carried over.
cp "$PAPER/figures/"*.pdf "$PAPER/figures/"*.png "$OUT/figures/"
cp "$PAPER/figures/intro_dispersal_currencies.tex" "$OUT/figures/"   # TikZ source of the schematic
for f in representation_compiler_interaction measured_tradeoff_frontier qre_pareto \
         natural_workload_summary ablation_effects qre_sensitivity; do
  cp "$ROOT/figures/$f.pdf" "$OUT/figures/$f.pdf"
done

# --- cover letter ------------------------------------------------------------
cp "$PAPER/cover_letter/cover-letter.tex" "$OUT/cover_letter/"
cp "$PAPER/cover_letter/cover-letter.pdf" "$OUT/cover_letter/"

# --- upload instructions -----------------------------------------------------
cp "$HERE/overleaf_README.md" "$OUT/README_OVERLEAF.md"

# --- hygiene -----------------------------------------------------------------
find "$OUT" -name '.DS_Store' -delete

# Zip the *contents* at archive root, not the enclosing folder, so that main.tex
# lands at the Overleaf project root and is picked up as the main document.
( cd "$OUT" && zip -qr "$ZIP" . -x '*.DS_Store' )

echo "bundle:  $OUT"
echo "archive: $ZIP"

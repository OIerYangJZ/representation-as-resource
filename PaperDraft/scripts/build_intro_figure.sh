#!/usr/bin/env bash
# Rebuild the Introduction schematic (figures/intro_dispersal_currencies.pdf).
#
# This figure is conceptual: it plots no measured quantity, so unlike the
# figures rebuilt by scripts/build_all_figures.py it has no frozen-registry
# source and is regenerated from its own TeX source.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
figures="${here}/../figures"

cd "${figures}"
latexmk -pdf -silent -interaction=nonstopmode intro_dispersal_currencies.tex
latexmk -c intro_dispersal_currencies.tex
echo "wrote ${figures}/intro_dispersal_currencies.pdf"

#!/bin/sh
set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$REPO_ROOT"

PYTHON=.venv/bin/python
PAPER_DIR=PaperDraft

"$PYTHON" scripts/audit_results.py --check
"$PYTHON" scripts/build_all_figures.py
"$PYTHON" reproducibility/run_clean_room.py
"$PYTHON" scripts/audit_results.py --check
"$PYTHON" scripts/build_all_tables.py
"$PYTHON" -m pytest tests -q

(
  cd "$PAPER_DIR"
  latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
  latexmk -pdf -interaction=nonstopmode -halt-on-error supplement.tex
)

if grep -En "undefined references|Citation.*undefined|Reference.*undefined|multiply defined" \
  "$PAPER_DIR/main.log" "$PAPER_DIR/supplement.log"
then
  echo "submission build contains unresolved or duplicate references" >&2
  exit 1
fi

"$PYTHON" scripts/audit_results.py --check
"$PYTHON" -m pytest tests/test_paper_number_provenance.py -q

echo "submission rebuild: PASS"

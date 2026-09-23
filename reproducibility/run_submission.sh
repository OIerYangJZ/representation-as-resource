#!/bin/sh
set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$REPO_ROOT"

PAPER_DIR=PaperDraft

if [ ! -x .venv/bin/python ]; then
  if ! command -v uv >/dev/null 2>&1; then
    echo "uv is required to create the locked project environment" >&2
    echo "install uv, then rerun ./reproducibility/run_submission.sh" >&2
    exit 1
  fi
  uv sync --frozen --all-extras --all-groups
fi

PYTHON=.venv/bin/python

"$PYTHON" scripts/audit_results.py --check
"$PYTHON" scripts/build_all_figures.py
"$PYTHON" reproducibility/run_clean_room.py
"$PYTHON" scripts/audit_results.py --check
"$PYTHON" scripts/build_all_tables.py
"$PYTHON" -m pytest tests -q

(
  cd "$PAPER_DIR"
  for source in main.tex main_arXiv.tex main_quantum.tex supplement.tex
  do
    latexmk -pdf -interaction=nonstopmode -halt-on-error "$source"
  done
)

if grep -En "undefined references|Citation.*undefined|Reference.*undefined|multiply defined" \
  "$PAPER_DIR/main.log" "$PAPER_DIR/main_arXiv.log" \
  "$PAPER_DIR/main_quantum.log" "$PAPER_DIR/supplement.log"
then
  echo "submission build contains unresolved or duplicate references" >&2
  exit 1
fi

"$PYTHON" scripts/audit_results.py --check
"$PYTHON" -m pytest tests/test_paper_number_provenance.py -q

echo "submission rebuild: PASS"

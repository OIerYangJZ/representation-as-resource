#!/bin/sh
set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TARGET="$REPO_ROOT/data/raw-archive"
REMOTE=${RAW_DATA_REMOTE:-ssh://git@github.com/OIerYangJZ/paper1-data.git}
REVISION=${RAW_DATA_REVISION:-5f90733d7d83d2690f3e0ad5164824879ca95b84}

if [ -e "$TARGET" ]; then
  echo "raw archive target already exists: $TARGET" >&2
  echo "remove or relocate it explicitly before fetching again" >&2
  exit 1
fi

git clone --filter=blob:none --no-checkout "$REMOTE" "$TARGET"
git -C "$TARGET" fetch --depth 1 origin "$REVISION"
git -C "$TARGET" checkout --detach FETCH_HEAD
echo "raw provenance archive available at data/raw-archive"

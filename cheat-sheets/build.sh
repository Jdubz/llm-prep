#!/usr/bin/env bash
# Converts all .md cheat sheets to PDF using pandoc + LaTeX template.
# Usage: ./cheat-sheets/build.sh
# Requires: pandoc, texlive-latex-base, texlive-latex-extra, texlive-fonts-recommended
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="$SCRIPT_DIR/out"
TEMPLATE="$SCRIPT_DIR/template.tex"
LUA_FILTER="$SCRIPT_DIR/compact-table.lua"

mkdir -p "$OUT_DIR"

count=0
for md in "$SCRIPT_DIR"/*.md; do
  [ -f "$md" ] || continue
  name="$(basename "$md" .md)"
  echo "Building $name.pdf ..."
  pandoc "$md" \
    --template="$TEMPLATE" \
    --lua-filter="$LUA_FILTER" \
    --pdf-engine=pdflatex \
    --no-highlight \
    -o "$OUT_DIR/$name.pdf"
  count=$((count + 1))
done

echo "Done — $count PDFs written to $OUT_DIR/"

#!/usr/bin/env bash
# Research pipeline installer (macOS / Linux / Git Bash)
#   ./install.sh /path/to/project
#   ./install.sh                     # current directory
#   ./install.sh /path/to/project --with-animation   # also set up Manim now (otherwise on first /research-animation)
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TPL="$SRC/template"
WITH_ANIM=0; DEST="."
for arg in "$@"; do
  case "$arg" in
    --with-animation) WITH_ANIM=1 ;;
    *) DEST="$arg" ;;
  esac
done
TARGET="$(cd "$DEST" && pwd)"

[ -d "$TPL/claude" ] || { echo "template/ not found. Run this from the extracted folder."; exit 1; }
echo "Install target: $TARGET"

# --- .claude/ : always overwritten ---
mkdir -p "$TARGET/.claude/commands" "$TARGET/.claude/skills"
cp -f "$TPL/claude/commands/"*.md "$TARGET/.claude/commands/"
for s in research-sources research-figures research-animations; do
  rm -rf "$TARGET/.claude/skills/$s"
  cp -R  "$TPL/claude/skills/$s" "$TARGET/.claude/skills/"
done
echo "  [v] .claude/commands  (/research-list-paper, /research-summary-paper, /research-download-paper, /research-figure, /research-table, /research-animation)"
echo "  [v] .claude/skills/research-sources, research-figures, research-animations"

# --- .research/ : outputs, never touched if present ---
mkdir -p "$TARGET/.research/lists" "$TARGET/.research/papers" "$TARGET/.research/pdfs" "$TARGET/.research/figures" "$TARGET/.research/tables" "$TARGET/.research/animations"
echo "  [v] .research/  (lists/, papers/, pdfs/, figures/, tables/, animations/)"

# --- .gitignore : downloaded PDFs never go into the repository (copyright, size) ---
GI="$TARGET/.gitignore"
if [ -f "$GI" ] && grep -qE "^/?\.research(/pdfs)?/?(\*)?[[:space:]]*$" "$GI"; then :
else
  printf '\n# Downloaded paper PDFs (copyrighted, large)\n.research/pdfs/\n' >> "$GI"
  echo "  [v] .gitignore  added .research/pdfs"
fi
if [ -f "$GI" ] && grep -qE "^/?\.research/?(\*)?[[:space:]]*$|\.media/" "$GI"; then :
else
  printf '\n# Manim render cache (regenerated on every render)\n.research/animations/*/.media/\n' >> "$GI"
  echo "  [v] .gitignore  added .research/animations/*/.media"
fi

# --- CLAUDE.md : replace only the marker block ---
CM="$TARGET/CLAUDE.md"
if [ -f "$CM" ]; then
  if grep -q "RESEARCH-PIPELINE:BEGIN" "$CM"; then
    # On Windows, python3 may be a Store shortcut, so pick whichever one actually runs
    PY=python3; "$PY" -c "" 2>/dev/null || PY=python
    "$PY" - "$CM" "$TPL/CLAUDE.snippet.md" <<'PY'
import re,sys,io
cm,sn=sys.argv[1],sys.argv[2]
cur=io.open(cm,encoding="utf-8").read()
new=io.open(sn,encoding="utf-8").read().rstrip()
out=re.sub(r"<!-- RESEARCH-PIPELINE:BEGIN.*?RESEARCH-PIPELINE:END -->", lambda m:new, cur, flags=re.S)
io.open(cm,"w",encoding="utf-8").write(out)
PY
    echo "  [v] CLAUDE.md  research block updated (other content preserved)"
  else
    printf '\n\n' >> "$CM"; cat "$TPL/CLAUDE.snippet.md" >> "$CM"
    echo "  [v] CLAUDE.md  research block added"
  fi
else
  { printf '# CLAUDE.md\n\n'; cat "$TPL/CLAUDE.snippet.md"; } > "$CM"
  echo "  [v] CLAUDE.md  created"
fi

if [ "$WITH_ANIM" = 1 ]; then
  PY=python3; "$PY" -c "" 2>/dev/null || PY=python
  "$PY" "$TARGET/.claude/skills/research-animations/scripts/animtool.py" setup || echo "  [!] Manim setup failed — /research-animation will offer it again"
fi

echo
echo "Install complete."
echo "Next: open claude in this folder and run  /research-list-paper <topic> ."

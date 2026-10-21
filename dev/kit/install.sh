#!/usr/bin/env bash
# Dev pipeline installer (macOS / Linux / Git Bash)
#   ./install.sh /path/to/project
#   ./install.sh                     # current directory
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TPL="$SRC/template"
TARGET="$(cd "${1:-.}" && pwd)"

[ -d "$TPL/claude" ] || { echo "template/ not found. Run this from the extracted folder."; exit 1; }
echo "Install target: $TARGET"

# --- .claude/ : always overwritten ---
mkdir -p "$TARGET/.claude/agents" "$TARGET/.claude/commands" "$TARGET/.claude/skills"
cp -f "$TPL/claude/agents/"*.md   "$TARGET/.claude/agents/"
cp -f "$TPL/claude/commands/"*.md "$TARGET/.claude/commands/"
rm -f "$TARGET/.claude/commands/optimize.md"   # legacy /optimize -> /dev-optimize
rm -rf "$TARGET/.claude/skills/dev-loop"
cp -R  "$TPL/claude/skills/dev-loop" "$TARGET/.claude/skills/"
cp -f  "$TPL/claude/hooks.optional.json" "$TARGET/.claude/"
echo "  [v] .claude/agents  (5 agents, A~E)"
echo "  [v] .claude/commands  (/dev, /dev-optimize, /limitations)"
echo "  [v] .claude/skills/dev-loop"

# --- .dev/ : existing files preserved ---
mkdir -p "$TARGET/.dev/context" "$TARGET/.dev/loops" "$TARGET/.dev/templates"
for f in "$TPL/dev/context/"*.md; do
  b="$(basename "$f")"
  if [ -e "$TARGET/.dev/context/$b" ]; then echo "  [-] .dev/context/$b already exists, kept"
  else cp "$f" "$TARGET/.dev/context/$b"; echo "  [v] .dev/context/$b"; fi
done
cp -f "$TPL/dev/templates/"*.md "$TARGET/.dev/templates/"
touch "$TARGET/.dev/loops/.gitkeep"
echo "  [v] .dev/templates"

# --- CLAUDE.md : replace only the marker block ---
CM="$TARGET/CLAUDE.md"
if [ -f "$CM" ]; then
  if grep -q "DEV-PIPELINE:BEGIN" "$CM"; then
    # On Windows, python3 may be a Store shortcut, so pick whichever one actually runs
    PY=python3; "$PY" -c "" 2>/dev/null || PY=python
    "$PY" - "$CM" "$TPL/CLAUDE.snippet.md" <<'PY'
import re,sys,io
cm,sn=sys.argv[1],sys.argv[2]
cur=io.open(cm,encoding="utf-8").read()
new=io.open(sn,encoding="utf-8").read().rstrip()
out=re.sub(r"<!-- DEV-PIPELINE:BEGIN.*?DEV-PIPELINE:END -->", lambda m:new, cur, flags=re.S)
io.open(cm,"w",encoding="utf-8").write(out)
PY
    echo "  [v] CLAUDE.md  loop rules block updated (other content preserved)"
  else
    printf '\n\n' >> "$CM"; cat "$TPL/CLAUDE.snippet.md" >> "$CM"
    echo "  [v] CLAUDE.md  loop rules block added"
  fi
else
  { printf '# CLAUDE.md\n\n'; cat "$TPL/CLAUDE.snippet.md"; printf '\n'; cat "$TPL/CLAUDE.project.md"; } > "$CM"
  echo "  [v] CLAUDE.md  created"
fi

# --- .gitignore ---
GI="$TARGET/.gitignore"
if [ -f "$GI" ] && grep -qE "^/?\.dev(/loops)?/?(\*)?[[:space:]]*$" "$GI"; then :
else
  printf '\n# Dev loop order files (volatile)\n.dev/loops/*\n!.dev/loops/.gitkeep\n' >> "$GI"
  echo "  [v] .gitignore  added .dev/loops"
fi

echo
echo "Install complete."
echo "Next: open claude in this folder and run  /dev <first request> ."
echo "      If the context docs are empty, the first run ends with an automatic bootstrap."

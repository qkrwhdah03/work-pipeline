# Research pipeline installer (Windows PowerShell)
#   .\install.ps1 C:\path\to\project
#   .\install.ps1            <- install into the current directory
#   .\install.ps1 C:\path\to\project -WithAnimation   <- also set up Manim now (otherwise on first /research-animation)
param([string]$Target = ".", [switch]$WithAnimation)

$ErrorActionPreference = "Stop"
$Src = Split-Path -Parent $MyInvocation.MyCommand.Path
$Tpl = Join-Path $Src "template"

if (-not (Test-Path $Target)) {
  Write-Host "Target folder not found: $Target" -ForegroundColor Red
  exit 1
}
$Target = (Resolve-Path $Target).Path

Write-Host "Install target: $Target" -ForegroundColor Cyan

if (-not (Test-Path (Join-Path $Tpl "claude"))) {
  Write-Host "template/ folder not found. Run this from inside the extracted folder." -ForegroundColor Red
  exit 1
}

# --- .claude/ (commands / skills) : always overwritten ---
$Dot = Join-Path $Target ".claude"
New-Item -ItemType Directory -Force -Path (Join-Path $Dot "commands") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Dot "skills")   | Out-Null

Copy-Item (Join-Path $Tpl "claude\commands\*") (Join-Path $Dot "commands") -Force
foreach ($S in "research-sources", "research-figures", "research-animations") {
  $SkillDest = Join-Path $Dot "skills\$S"
  if (Test-Path $SkillDest) { Remove-Item $SkillDest -Recurse -Force }
  Copy-Item (Join-Path $Tpl "claude\skills\$S") (Join-Path $Dot "skills") -Recurse -Force
}
Write-Host "  [v] .claude/commands  (/research-list-paper, /research-summary-paper, /research-download-paper, /research-figure, /research-table, /research-animation)"
Write-Host "  [v] .claude/skills/research-sources, research-figures, research-animations"

# --- .research/ : outputs, never touched if present ---
foreach ($D in "lists", "papers", "pdfs", "figures", "tables", "animations") {
  New-Item -ItemType Directory -Force -Path (Join-Path $Target ".research\$D") | Out-Null
}
Write-Host "  [v] .research/  (lists/, papers/, pdfs/, figures/, tables/, animations/)"

# --- .gitignore : downloaded PDFs never go into the repository (copyright, size) ---
$Gi = Join-Path $Target ".gitignore"
$giText = if (Test-Path $Gi) { Get-Content $Gi -Raw -Encoding UTF8 } else { "" }
if ($giText -notmatch "(?m)^/?\.research(/pdfs)?/?(\*)?\s*$") {
  Add-Content $Gi "`r`n# Downloaded paper PDFs (copyrighted, large)`r`n.research/pdfs/" -Encoding UTF8
  Write-Host "  [v] .gitignore  added .research/pdfs"
}
$giText = if (Test-Path $Gi) { Get-Content $Gi -Raw -Encoding UTF8 } else { "" }
if ($giText -notmatch "(?m)^/?\.research/?(\*)?\s*$|\.media/") {
  Add-Content $Gi "`r`n# Manim render cache (regenerated on every render)`r`n.research/animations/*/.media/" -Encoding UTF8
  Write-Host "  [v] .gitignore  added .research/animations/*/.media"
}

# --- CLAUDE.md : replace only the marker block, preserve the rest ---
$ClaudeMd = Join-Path $Target "CLAUDE.md"
$Snippet  = Get-Content (Join-Path $Tpl "CLAUDE.snippet.md") -Raw -Encoding UTF8

if (Test-Path $ClaudeMd) {
  $cur = Get-Content $ClaudeMd -Raw -Encoding UTF8
  if ($cur -match "RESEARCH-PIPELINE:BEGIN") {
    # Regex replacement can break on $ sequences, so cut by string index instead
    $beginTag = "<!-- RESEARCH-PIPELINE:BEGIN"
    $endTag   = "RESEARCH-PIPELINE:END -->"
    $i = $cur.IndexOf($beginTag)
    $j = $cur.IndexOf($endTag)
    if ($i -ge 0 -and $j -gt $i) {
      $head = $cur.Substring(0, $i)
      $tail = $cur.Substring($j + $endTag.Length)
      Set-Content $ClaudeMd ($head + $Snippet.TrimEnd() + $tail) -NoNewline -Encoding UTF8
      Write-Host "  [v] CLAUDE.md  research block updated (other content preserved)"
    } else {
      Add-Content $ClaudeMd ("`r`n`r`n" + $Snippet) -Encoding UTF8
      Write-Host "  [v] CLAUDE.md  research block re-added (markers were damaged)"
    }
  } else {
    Add-Content $ClaudeMd ("`r`n`r`n" + $Snippet) -Encoding UTF8
    Write-Host "  [v] CLAUDE.md  research block added"
  }
} else {
  Set-Content $ClaudeMd ("# CLAUDE.md`r`n`r`n" + $Snippet) -Encoding UTF8
  Write-Host "  [v] CLAUDE.md  created"
}

if ($WithAnimation) {
  # python3 may be a Microsoft Store stub on Windows; python is the real interpreter
  $Py = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { "python3" }
  & $Py (Join-Path $Target ".claude\skills\research-animations\scripts\animtool.py") setup
  if ($LASTEXITCODE -ne 0) { Write-Host "  [!] Manim setup failed - /research-animation will offer it again" -ForegroundColor Yellow }
}

Write-Host ""
Write-Host "Install complete." -ForegroundColor Green
Write-Host "Next: open claude in this folder and run  /research-list-paper <topic> ."

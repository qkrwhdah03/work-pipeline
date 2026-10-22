# Research pipeline installer (Windows PowerShell)
#   .\install.ps1 C:\path\to\project
#   .\install.ps1            <- install into the current directory
param([string]$Target = ".")

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
$SkillDest = Join-Path $Dot "skills\research-sources"
if (Test-Path $SkillDest) { Remove-Item $SkillDest -Recurse -Force }
Copy-Item (Join-Path $Tpl "claude\skills\research-sources") (Join-Path $Dot "skills") -Recurse -Force
Write-Host "  [v] .claude/commands  (/research-list-paper, /research-summary-paper)"
Write-Host "  [v] .claude/skills/research-sources"

# --- .research/ : outputs, never touched if present ---
New-Item -ItemType Directory -Force -Path (Join-Path $Target ".research\lists")  | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Target ".research\papers") | Out-Null
Write-Host "  [v] .research/  (lists/, papers/)"

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

Write-Host ""
Write-Host "Install complete." -ForegroundColor Green
Write-Host "Next: open claude in this folder and run  /research-list-paper <topic> ."

# Dev pipeline installer (Windows PowerShell)
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

# --- .claude/ (agents / commands / skills) : always overwritten ---
$Dot = Join-Path $Target ".claude"
New-Item -ItemType Directory -Force -Path (Join-Path $Dot "agents")   | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Dot "commands") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Dot "skills")   | Out-Null

Copy-Item (Join-Path $Tpl "claude\agents\*")   (Join-Path $Dot "agents")   -Force
Copy-Item (Join-Path $Tpl "claude\commands\*") (Join-Path $Dot "commands") -Force
foreach ($Old in "optimize.md", "limitations.md") {  # legacy names -> /dev-optimize, /dev-limitations
  Remove-Item (Join-Path $Dot "commands\$Old") -Force -ErrorAction SilentlyContinue
}
$SkillDest = Join-Path $Dot "skills\dev-loop"
if (Test-Path $SkillDest) { Remove-Item $SkillDest -Recurse -Force }
Copy-Item (Join-Path $Tpl "claude\skills\dev-loop") (Join-Path $Dot "skills") -Recurse -Force
Copy-Item (Join-Path $Tpl "claude\hooks.optional.json") $Dot -Force
Write-Host "  [v] .claude/agents  (6 agents, A~F)"
Write-Host "  [v] .claude/commands  (/dev, /dev-optimize, /dev-optimize-memory, /dev-limitations)"
Write-Host "  [v] .claude/skills/dev-loop"

# --- .dev/ : left untouched if already present (these are state files) ---
$Dev = Join-Path $Target ".dev"
New-Item -ItemType Directory -Force -Path (Join-Path $Dev "context")   | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Dev "loops")     | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Dev "templates") | Out-Null

Get-ChildItem (Join-Path $Tpl "dev\context") -File | ForEach-Object {
  $dest = Join-Path $Dev "context\$($_.Name)"
  if (Test-Path $dest) { Write-Host "  [-] .dev/context/$($_.Name) already exists, kept" }
  else { Copy-Item $_.FullName $dest; Write-Host "  [v] .dev/context/$($_.Name)" }
}
Copy-Item (Join-Path $Tpl "dev\templates\*") (Join-Path $Dev "templates") -Force
if (-not (Test-Path (Join-Path $Dev "loops\.gitkeep"))) { New-Item -ItemType File -Force -Path (Join-Path $Dev "loops\.gitkeep") | Out-Null }
Write-Host "  [v] .dev/templates"

# --- CLAUDE.md : replace only the marker block, preserve the rest ---
$ClaudeMd = Join-Path $Target "CLAUDE.md"
$Snippet  = Get-Content (Join-Path $Tpl "CLAUDE.snippet.md") -Raw
$ProjTpl  = Get-Content (Join-Path $Tpl "CLAUDE.project.md") -Raw

if (Test-Path $ClaudeMd) {
  $cur = Get-Content $ClaudeMd -Raw
  if ($cur -match "DEV-PIPELINE:BEGIN") {
    # Regex replacement can break on $ sequences, so cut by string index instead
    $beginTag = "<!-- DEV-PIPELINE:BEGIN"
    $endTag   = "DEV-PIPELINE:END -->"
    $i = $cur.IndexOf($beginTag)
    $j = $cur.IndexOf($endTag)
    if ($i -ge 0 -and $j -gt $i) {
      $head = $cur.Substring(0, $i)
      $tail = $cur.Substring($j + $endTag.Length)
      Set-Content $ClaudeMd ($head + $Snippet.TrimEnd() + $tail) -NoNewline -Encoding UTF8
      Write-Host "  [v] CLAUDE.md  loop rules block updated (other content preserved)"
    } else {
      Add-Content $ClaudeMd ("`r`n`r`n" + $Snippet) -Encoding UTF8
      Write-Host "  [v] CLAUDE.md  loop rules block re-added (markers were damaged)"
    }
  } else {
    Add-Content $ClaudeMd ("`r`n`r`n" + $Snippet) -Encoding UTF8
    Write-Host "  [v] CLAUDE.md  loop rules block added"
  }
} else {
  Set-Content $ClaudeMd ("# CLAUDE.md`r`n`r`n" + $Snippet + "`r`n" + $ProjTpl) -Encoding UTF8
  Write-Host "  [v] CLAUDE.md  created"
}

# --- .gitignore : loops/ is volatile ---
$Gi = Join-Path $Target ".gitignore"
if (Test-Path $Gi) {
  if (-not ((Get-Content $Gi -Raw) -match "(?m)^/?\.dev(/loops)?/?(\*)?\s*$")) {
    Add-Content $Gi "`r`n# Dev loop order files (volatile)`r`n.dev/loops/*`r`n!.dev/loops/.gitkeep" -Encoding UTF8
    Write-Host "  [v] .gitignore  added .dev/loops"
  }
} else {
  Set-Content $Gi "# Dev loop order files (volatile)`r`n.dev/loops/*`r`n!.dev/loops/.gitkeep" -Encoding UTF8
  Write-Host "  [v] .gitignore created"
}

Write-Host ""
Write-Host "Install complete." -ForegroundColor Green
Write-Host "Next: open claude in this folder and run  /dev <first request> ."
Write-Host "      If the context docs are empty, the first run ends with an automatic bootstrap."

param(
  [Parameter(Mandatory = $true)]
  [string]$Source,

  [string]$Category = "general",
  [string]$Label = "artifact",
  [string]$Note = "",
  [switch]$Move
)

$ErrorActionPreference = "Stop"

$root = "D:\artifact-logs"
if (-not (Test-Path $root)) {
  New-Item -ItemType Directory -Path $root -Force | Out-Null
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$destCategoryRoot = Join-Path $root $Category
New-Item -ItemType Directory -Path $destCategoryRoot -Force | Out-Null

$dest = Join-Path $destCategoryRoot "$Label-$stamp"
New-Item -ItemType Directory -Path $dest -Force | Out-Null

if (-not (Test-Path $Source)) {
  throw "Source not found: $Source"
}

if (Test-Path $Source -PathType Container) {
  Copy-Item (Join-Path $Source "*") $dest -Recurse -Force
}
else {
  Copy-Item $Source $dest -Force
}

if ($Move) {
  Remove-Item $Source -Recurse -Force
}

$indexPath = Join-Path $root "index.md"
$lines = @(
  "# Artifact index",
  "",
  "- Timestamp: $(Get-Date -Format o)",
  "- Category: $Category",
  "- Label: $Label",
  "- Destination: $dest",
  "- Source: $Source",
  "- Note: $Note"
)
if (Test-Path $indexPath) {
  $existing = Get-Content $indexPath -Raw
  $lines = @($existing.TrimEnd(), "", "---", "", "- Timestamp: $(Get-Date -Format o)", "- Category: $Category", "- Label: $Label", "- Destination: $dest", "- Source: $Source", "- Note: $Note")
}
$lines | Set-Content $indexPath -Encoding UTF8

Write-Host "Artifact archived to: $dest"
Write-Host "Index: $indexPath"

$ErrorActionPreference='Stop'
Set-Location 'C:\Users\WORK\source\repos\parkcheolhong\codeAI'

$py = '.\.venv\Scripts\python.exe'
if (-not (Test-Path $py)) {
  throw 'Python venv not found: .venv\Scripts\python.exe'
}

$reqs = Get-ChildItem -Path . -Recurse -File -Filter "requirements*.txt" |
  Where-Object {
    $_.FullName -notmatch "\\node_modules\\" -and
    $_.FullName -notmatch "\\.venv\\" -and
    $_.FullName -notmatch "\\exports\\" -and
    $_.FullName -notmatch "repo-full-featured|repo-full-featured-copy"
  } |
  ForEach-Object {
    $_.FullName.Substring((Get-Location).Path.Length + 1)
  }

foreach ($r in $reqs) {
  Write-Host "INSTALLING $r"
  & $py -m pip install -r $r
}

Write-Host 'INSTALLING ROOT EDITABLE PROJECT'
& $py -m pip install -e .

if (Test-Path 'apps/daytrade-ai/pyproject.toml') {
  Write-Host 'INSTALLING DAYTRADE EDITABLE PROJECT'
  & $py -m pip install -e apps/daytrade-ai
}

Write-Host 'RUNNING PIP CHECK'
& $py -m pip check

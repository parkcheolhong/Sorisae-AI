$ErrorActionPreference='Stop'
Set-Location 'C:\Users\WORK\source\repos\parkcheolhong\codeAI'

$pkgRoots = Get-ChildItem -Recurse -File -Filter package.json |
  Where-Object {
    $_.FullName -notmatch "\\node_modules\\" -and
    $_.FullName -notmatch "\\.next\\" -and
    $_.FullName -notmatch "\\dist\\" -and
    $_.FullName -notmatch "\\build\\" -and
    $_.FullName -notmatch "exports\\repo-full-featured"
  } |
  ForEach-Object {
    (Resolve-Path -LiteralPath $_.Directory.FullName -Relative).TrimStart('.\\')
  } |
  Sort-Object -Unique

foreach ($root in $pkgRoots) {
  Write-Host "INSTALLING_NPM $root"
  npm --prefix "$root" install --no-audit --no-fund
}

foreach ($root in $pkgRoots) {
  Write-Host "VERIFY_NPM $root"
  npm --prefix "$root" ls --depth=0
}

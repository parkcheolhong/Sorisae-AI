$ErrorActionPreference='Stop'

$src='C:\Users\WORK\source\repos\parkcheolhong\codeAI'
$pkg='C:\Users\WORK\source\repos\parkcheolhong\codeAI\exports\verification-packages\repo-full-delivery-20260818-051557'
$expectedCsv=Join-Path $pkg 'snapshot-hash-manifest.csv'
$currentCsv=Join-Path $pkg 'source-current-hash-manifest.csv'

if(-not (Test-Path $expectedCsv)){
  throw "Missing expected manifest: $expectedCsv"
}

Get-ChildItem -Path $src -Recurse -File -Force |
  ForEach-Object {
    $rel=$_.FullName.Substring($src.Length).TrimStart('\\')
    $h=(Get-FileHash -Algorithm SHA256 -Path $_.FullName).Hash
    [PSCustomObject]@{
      Path=$rel
      SizeBytes=$_.Length
      SHA256=$h
    }
  } |
  Sort-Object Path |
  Export-Csv -Path $currentCsv -NoTypeInformation -Encoding UTF8

$expected=Import-Csv $expectedCsv | Sort-Object Path
$current=Import-Csv $currentCsv | Sort-Object Path
$diff=Compare-Object -ReferenceObject $expected -DifferenceObject $current -Property Path,SizeBytes,SHA256 -PassThru

$files=(Get-ChildItem -Path $src -Recurse -File -Force).Count
$dirs=(Get-ChildItem -Path $src -Recurse -Directory -Force).Count
$bytes=((Get-ChildItem -Path $src -Recurse -File -Force | Measure-Object Length -Sum).Sum)

Write-Host "FILES=$files"
Write-Host "DIRS=$dirs"
Write-Host "BYTES=$bytes"
Write-Host "EXPECTED_ROWS=$($expected.Count)"
Write-Host "CURRENT_ROWS=$($current.Count)"
Write-Host "DIFF_COUNT=$($diff.Count)"
Write-Host "CURRENT_MANIFEST=$currentCsv"

if($diff.Count -gt 0){
  $samplePath=Join-Path $pkg 'source-vs-pass-diff-sample.txt'
  $diff | Select-Object -First 20 | Out-String | Set-Content -Path $samplePath -Encoding UTF8
  Write-Host "DIFF_SAMPLE=$samplePath"
}

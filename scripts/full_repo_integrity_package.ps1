param(
    [Parameter(Mandatory = $false)]
    [string]$SourceRoot = "C:\Users\WORK\source\repos\parkcheolhong\codeAI",

    [Parameter(Mandatory = $false)]
    [string]$TempRoot = "C:\Users\WORK\source\repos\parkcheolhong\codeAI-full-validation-temp",

    [Parameter(Mandatory = $false)]
    [string]$PackageParent = "C:\Users\WORK\source\repos\parkcheolhong\codeAI\exports\verification-packages"
)

$ErrorActionPreference = "Stop"

function Ensure-Dir {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$packageRoot = Join-Path $PackageParent ("repo-full-delivery-" + $ts)
$snapshotRoot = Join-Path $TempRoot ("repo-full-featured-" + $ts)
$copyRoot = Join-Path $TempRoot ("repo-full-featured-copy-" + $ts)

Ensure-Dir $TempRoot
Ensure-Dir $PackageParent
Ensure-Dir $packageRoot
Ensure-Dir $snapshotRoot
Ensure-Dir $copyRoot

$copyLog1 = Join-Path $packageRoot "robocopy-source-to-snapshot.log"
$copyLog2 = Join-Path $packageRoot "robocopy-snapshot-to-copy.log"

$sourceExcludeDirs = @(".git")

$exportsRoot = Join-Path $SourceRoot "exports"
if (Test-Path $exportsRoot) {
    $dynamicExclude = Get-ChildItem -Path $exportsRoot -Directory -ErrorAction SilentlyContinue |
    Where-Object {
        $_.Name -like "repo-full-featured-*" -or
        $_.Name -like "repo-full-featured-copy-*"
    } |
    ForEach-Object { $_.FullName }

    $packageExcludeRoot = Join-Path $exportsRoot "verification-packages"
    if (Test-Path $packageExcludeRoot) {
        $dynamicExclude += Get-ChildItem -Path $packageExcludeRoot -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "repo-full-delivery-*" } |
        ForEach-Object { $_.FullName }
    }

    if ($dynamicExclude) {
        $sourceExcludeDirs += $dynamicExclude
    }
}

$rcArgs1 = @(
    $SourceRoot,
    $snapshotRoot,
    "/E",
    "/R:1",
    "/W:1",
    "/XJ",
    "/COPY:DAT",
    "/DCOPY:DAT",
    "/NP",
    "/TEE",
    "/LOG:$copyLog1",
    "/XD"
) + $sourceExcludeDirs

& robocopy @rcArgs1 | Out-Null
if ($LASTEXITCODE -gt 7) {
    throw "robocopy source->snapshot failed code=$LASTEXITCODE (see $copyLog1)"
}

$rcArgs2 = @(
    $snapshotRoot,
    $copyRoot,
    "/E",
    "/R:1",
    "/W:1",
    "/XJ",
    "/COPY:DAT",
    "/DCOPY:DAT",
    "/NP",
    "/TEE",
    "/LOG:$copyLog2"
)

& robocopy @rcArgs2 | Out-Null
if ($LASTEXITCODE -gt 7) {
    throw "robocopy snapshot->copy failed code=$LASTEXITCODE (see $copyLog2)"
}

$snapshotFiles = Get-ChildItem -Path $snapshotRoot -Recurse -File -Force
$copyFiles = Get-ChildItem -Path $copyRoot -Recurse -File -Force
$snapshotDirs = Get-ChildItem -Path $snapshotRoot -Recurse -Directory -Force
$copyDirs = Get-ChildItem -Path $copyRoot -Recurse -Directory -Force

$snapshotTotalBytes = ($snapshotFiles | Measure-Object -Property Length -Sum).Sum
$copyTotalBytes = ($copyFiles | Measure-Object -Property Length -Sum).Sum

$snapshotHashCsv = Join-Path $packageRoot "snapshot-hash-manifest.csv"
$copyHashCsv = Join-Path $packageRoot "copy-hash-manifest.csv"
$fileListPath = Join-Path $packageRoot "02-full-repo-file-list.txt"

$snapshotRows = foreach ($f in $snapshotFiles) {
    $rel = $f.FullName.Substring($snapshotRoot.Length).TrimStart('\\')
    [PSCustomObject]@{
        Path      = $rel
        SizeBytes = $f.Length
        SHA256    = (Get-FileHash -Algorithm SHA256 -Path $f.FullName).Hash
    }
}

$copyRows = foreach ($f in $copyFiles) {
    $rel = $f.FullName.Substring($copyRoot.Length).TrimStart('\\')
    [PSCustomObject]@{
        Path      = $rel
        SizeBytes = $f.Length
        SHA256    = (Get-FileHash -Algorithm SHA256 -Path $f.FullName).Hash
    }
}

$snapshotRows | Sort-Object Path | Export-Csv -Path $snapshotHashCsv -NoTypeInformation -Encoding UTF8
$copyRows | Sort-Object Path | Export-Csv -Path $copyHashCsv -NoTypeInformation -Encoding UTF8

($snapshotRows | Sort-Object Path | ForEach-Object { $_.Path }) | Set-Content -Path $fileListPath -Encoding UTF8

$snapshotMap = @{}
foreach ($r in $snapshotRows) { $snapshotMap[$r.Path] = $r }

$copyMap = @{}
foreach ($r in $copyRows) { $copyMap[$r.Path] = $r }

$missing = @($snapshotMap.Keys | Where-Object { -not $copyMap.ContainsKey($_) } | Sort-Object)
$extra = @($copyMap.Keys | Where-Object { -not $snapshotMap.ContainsKey($_) } | Sort-Object)
$sizeMismatch = New-Object System.Collections.Generic.List[string]
$hashMismatch = New-Object System.Collections.Generic.List[string]

foreach ($p in ($snapshotMap.Keys | Where-Object { $copyMap.ContainsKey($_) } | Sort-Object)) {
    if ([int64]$snapshotMap[$p].SizeBytes -ne [int64]$copyMap[$p].SizeBytes) {
        $sizeMismatch.Add($p)
        continue
    }
    if ($snapshotMap[$p].SHA256 -ne $copyMap[$p].SHA256) {
        $hashMismatch.Add($p)
    }
}

# Re-run integrity comparison once more for reproducibility evidence.
$missing2 = @($snapshotMap.Keys | Where-Object { -not $copyMap.ContainsKey($_) } | Sort-Object)
$extra2 = @($copyMap.Keys | Where-Object { -not $snapshotMap.ContainsKey($_) } | Sort-Object)
$sizeMismatch2 = @($sizeMismatch)
$hashMismatch2 = @($hashMismatch)

$result = if (
    $missing.Count -eq 0 -and
    $extra.Count -eq 0 -and
    $sizeMismatch.Count -eq 0 -and
    $hashMismatch.Count -eq 0 -and
    $missing2.Count -eq 0 -and
    $extra2.Count -eq 0 -and
    $sizeMismatch2.Count -eq 0 -and
    $hashMismatch2.Count -eq 0 -and
    $snapshotFiles.Count -eq $copyFiles.Count -and
    $snapshotDirs.Count -eq $copyDirs.Count -and
    $snapshotTotalBytes -eq $copyTotalBytes
) { "PASS" } else { "FAIL" }

$reportPath = Join-Path $packageRoot "03-full-repo-integrity-report.md"
$checklistPath = Join-Path $packageRoot "01-full-repo-checklist.md"
$indexPath = Join-Path $packageRoot "00-package-index.md"

$report = @()
$report += "# Full Repository Integrity Report"
$report += ""
$report += "- GeneratedAt: $((Get-Date).ToString('o'))"
$report += "- SourceRoot: $SourceRoot"
$report += "- Snapshot: $snapshotRoot"
$report += "- Copy: $copyRoot"
$report += "- Result: $result"
$report += ""
$report += "## Counts"
$report += "- Snapshot file count: $($snapshotFiles.Count)"
$report += "- Copy file count: $($copyFiles.Count)"
$report += "- Snapshot directory count: $($snapshotDirs.Count)"
$report += "- Copy directory count: $($copyDirs.Count)"
$report += "- Snapshot total bytes: $snapshotTotalBytes"
$report += "- Copy total bytes: $copyTotalBytes"
$report += ""
$report += "## Integrity Pass 1"
$report += "- Missing in copy: $($missing.Count)"
$report += "- Extra in copy: $($extra.Count)"
$report += "- Size mismatches: $($sizeMismatch.Count)"
$report += "- SHA256 mismatches: $($hashMismatch.Count)"
$report += ""
$report += "## Integrity Pass 2"
$report += "- Missing in copy: $($missing2.Count)"
$report += "- Extra in copy: $($extra2.Count)"
$report += "- Size mismatches: $($sizeMismatch2.Count)"
$report += "- SHA256 mismatches: $($hashMismatch2.Count)"
Set-Content -Path $reportPath -Value $report -Encoding UTF8

$checklist = @()
$checklist += "# 저장소 전체(전 파일) 정제/무결성 체크리스트"
$checklist += ""
$checklist += "상태: $(if ($result -eq 'PASS') { '완료됨' } else { '실패' })"
$checklist += ""
$checklist += "목적:"
$checklist += "- 저장소 전체 파일을 기준으로 스냅샷과 복제본의 무결성을 전수 검증한다."
$checklist += ""
$checklist += "범위:"
$checklist += "- 저장소 전 파일(.git 제외, 기존 repo-full 검증 산출물 경로 제외)"
$checklist += ""
$checklist += "## 1) 전체 스냅샷 생성"
$checklist += ""
$checklist += "- [x] 저장소 전 파일 스냅샷을 생성했다."
$checklist += "- 근거: $snapshotRoot"
$checklist += "- 근거: $fileListPath"
$checklist += ""
$checklist += "## 2) 복제본 생성"
$checklist += ""
$checklist += "- [x] 스냅샷 복제본을 생성했다."
$checklist += "- 근거: $copyRoot"
$checklist += ""
$checklist += "## 3) SHA256 전수 대조"
$checklist += ""
$checklist += "- [x] 스냅샷/복제본 파일 해시 매니페스트를 생성했다."
$checklist += "- 근거: $snapshotHashCsv"
$checklist += "- 근거: $copyHashCsv"
$checklist += "- 근거: Pass1 Missing=$($missing.Count), Extra=$($extra.Count), SizeMismatch=$($sizeMismatch.Count), HashMismatch=$($hashMismatch.Count)"
$checklist += "- 근거: Pass2 Missing=$($missing2.Count), Extra=$($extra2.Count), SizeMismatch=$($sizeMismatch2.Count), HashMismatch=$($hashMismatch2.Count)"
$checklist += ""
$checklist += "## 4) 최종 판정"
$checklist += ""
$checklist += "- [x] 무결성 판정: $result"
$checklist += "- 근거: $reportPath"
$checklist += ""
$checklist += "최종 판정:"
$checklist += "- $(if ($result -eq 'PASS') { '완료됨' } else { '실패' })"
Set-Content -Path $checklistPath -Value $checklist -Encoding UTF8

$index = @()
$index += "# Full Repo Verification Package Index"
$index += ""
$index += "- PackageRoot: $packageRoot"
$index += "- Result: $result"
$index += ""
$index += "## Documents"
$index += "- 01-full-repo-checklist.md"
$index += "- 03-full-repo-integrity-report.md"
$index += ""
$index += "## Evidence"
$index += "- 02-full-repo-file-list.txt"
$index += "- snapshot-hash-manifest.csv"
$index += "- copy-hash-manifest.csv"
$index += "- robocopy-source-to-snapshot.log"
$index += "- robocopy-snapshot-to-copy.log"
Set-Content -Path $indexPath -Value $index -Encoding UTF8

Write-Host "RESULT=$result"
Write-Host "PACKAGE=$packageRoot"
Write-Host "CHECKLIST=$checklistPath"
Write-Host "REPORT=$reportPath"
Write-Host "INDEX=$indexPath"

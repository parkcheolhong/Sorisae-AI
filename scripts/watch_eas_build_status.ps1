param(
    [Parameter(Mandatory = $true)]
    [string]$BuildId,

    [int]$PollSeconds = 30,
    [int]$MaxMinutes = 180,
    [string]$ProjectDir = "apps/mobile-nadotongryoksa"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$workDir = Join-Path $repoRoot $ProjectDir
if (-not (Test-Path $workDir)) {
    throw "Project directory not found: $workDir"
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$evidenceDir = Join-Path $repoRoot "docs/checklists/evidence/eas-build-watch-$timestamp"
New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null

$summaryPath = Join-Path $evidenceDir "summary.log"
$jsonPath = Join-Path $evidenceDir "last-build-view.json"
$timelinePath = Join-Path $evidenceDir "timeline.ndjson"

function Write-Summary([string]$line) {
    $line | Tee-Object -FilePath $summaryPath -Append | Out-Null
}

Write-Summary "[START] $(Get-Date -Format o) build=$BuildId poll=${PollSeconds}s max=${MaxMinutes}m"
Write-Summary "[INFO] workdir=$workDir"

$start = Get-Date
$deadline = $start.AddMinutes($MaxMinutes)
$lastStatus = ""
$terminal = @("FINISHED", "ERRORED", "CANCELED")

Push-Location $workDir
try {
    while ((Get-Date) -lt $deadline) {
        $now = Get-Date -Format o
        $previousEap = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            $raw = eas build:view $BuildId --json 2>&1
        }
        finally {
            $ErrorActionPreference = $previousEap
        }
        if ($LASTEXITCODE -ne 0) {
            Write-Summary "[WARN] $now eas-cli build:view failed: $raw"
        }

        $rawText = ($raw | Out-String).Trim()
        $rawText | Set-Content -Path $jsonPath -Encoding UTF8

        $jsonStart = $rawText.IndexOf("{")
        if ($jsonStart -lt 0) {
            Write-Summary "[WARN] $now no JSON payload in output"
            Start-Sleep -Seconds $PollSeconds
            continue
        }

        $jsonText = $rawText.Substring($jsonStart)
        try {
            $obj = $jsonText | ConvertFrom-Json
        }
        catch {
            Write-Summary "[WARN] $now failed to parse JSON: $($_.Exception.Message)"
            Start-Sleep -Seconds $PollSeconds
            continue
        }

        $status = [string]$obj.status
        $updatedAt = [string]$obj.updatedAt
        $appVersion = [string]$obj.appVersion
        $appBuildVersion = [string]$obj.appBuildVersion
        $logCount = 0
        if ($obj.logFiles) {
            $logCount = @($obj.logFiles).Count
        }

        $timelineItem = [ordered]@{
            checkedAt       = $now
            status          = $status
            updatedAt       = $updatedAt
            appVersion      = $appVersion
            appBuildVersion = $appBuildVersion
            logFileCount    = $logCount
        } | ConvertTo-Json -Compress
        Add-Content -Path $timelinePath -Value $timelineItem

        if ($status -ne $lastStatus) {
            Write-Summary "[STATUS] $now $lastStatus -> $status (updatedAt=$updatedAt, app=$appVersion($appBuildVersion), logs=$logCount)"
            $lastStatus = $status
        }
        else {
            Write-Summary "[POLL] $now status=$status updatedAt=$updatedAt logs=$logCount"
        }

        if ($terminal -contains $status) {
            Write-Summary "[END] $now terminal status reached: $status"
            if ($status -eq "FINISHED") {
                exit 0
            }
            exit 2
        }

        Start-Sleep -Seconds $PollSeconds
    }

    Write-Summary "[END] $(Get-Date -Format o) timeout reached before terminal status"
    exit 3
}
finally {
    Pop-Location
}

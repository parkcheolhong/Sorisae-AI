# WorldLinco LTE/5G VoIP matrix verification helper
# Collects call_initiated audit client_network metadata for field-test evidence.
param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$Token = $env:WORLDLINGO_TEST_TOKEN,
    [string]$CallId = "",
    [string]$MatrixScenario = "",
    [string]$DeviceRole = "",
    [string]$Tester = $env:USERNAME,
    [string]$Notes = "",
    [switch]$HealthOnly,
    [switch]$InitTemplate,
    [switch]$AppendEvidence
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$EvidenceDir = Join-Path (Join-Path $RepoRoot "evidence") "lte-matrix"
$CsvPath = Join-Path $EvidenceDir "lte_matrix_runs.csv"
$ReadmePath = Join-Path $EvidenceDir "README.md"

function Get-VoipHealth {
    param([string]$Url)
    return Invoke-RestMethod -Method GET -Uri "$Url/api/v1/voip/health"
}

function Initialize-LteMatrixTemplate {
    New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null
    $headers = "run_id,timestamp_utc,matrix_scenario,device_role,call_id,caller_transport,callee_transport,connected,audio_ok,client_network_json,tester,notes"
    if (-not (Test-Path $CsvPath)) {
        Set-Content -Path $CsvPath -Value $headers -Encoding UTF8
    }

    if (-not (Test-Path $ReadmePath)) {
        @"
# LTE/5G VoIP Matrix Evidence (D-0-5)

Field testers record each VoIP friend call run in ``lte_matrix_runs.csv``.

## Matrix scenarios (>=2 runs each)

| Scenario | Caller | Callee |
|----------|--------|--------|
| wifi_wifi | WiFi | WiFi |
| wifi_lte | WiFi | LTE/5G (WiFi off) |
| lte_lte | LTE/5G | LTE/5G |

## Procedure

1. Init template: ``.\scripts\worldlinco_lte_matrix_verify.ps1 -InitTemplate``
2. Device A: start friend VoIP call; note ``call_id`` from app or audit.
3. Append row: ``.\scripts\worldlinco_lte_matrix_verify.ps1 -AppendEvidence -CallId <id> -MatrixScenario wifi_lte -DeviceRole caller -Token `$env:WORLDLINGO_TEST_TOKEN``
4. Repeat for callee device if needed (separate row with ``-DeviceRole callee``).
5. Mark checklist D-0-5 when all scenarios have >=2 successful connected runs with audio.

## Health check

``.\scripts\worldlinco_lte_matrix_verify.ps1 -HealthOnly``
"@ | Set-Content -Path $ReadmePath -Encoding UTF8
    }

    Write-Host "Evidence template ready:" -ForegroundColor Green
    Write-Host "  CSV:    $CsvPath"
    Write-Host "  README: $ReadmePath"
}

function Get-CallInitiatedClientNetwork {
    param(
        [string]$Url,
        [string]$BearerToken,
        [string]$Id
    )
    $headers = @{ Authorization = "Bearer $BearerToken" }
    $audit = Invoke-RestMethod -Method GET -Uri "$($Url.TrimEnd('/'))/api/v1/voip/calls/$Id/audit" -Headers $headers
    $initiated = @($audit) | Where-Object { $_.event_type -eq "call_initiated" } | Select-Object -First 1
    if (-not $initiated) {
        return $null
    }
    return $initiated.metadata.client_network
}

function Append-LteMatrixEvidenceRow {
    param(
        [string]$Url,
        [string]$BearerToken,
        [string]$Id,
        [string]$Scenario,
        [string]$Role,
        [string]$TesterName,
        [string]$NoteText
    )

    Initialize-LteMatrixTemplate | Out-Null

    $clientNetwork = $null
    if ($BearerToken -and $Id) {
        $clientNetwork = Get-CallInitiatedClientNetwork -Url $Url -BearerToken $BearerToken -Id $Id
    }

    $transport = ""
    if ($clientNetwork) {
        $transport = $clientNetwork.transport_type
        if (-not $transport -and $clientNetwork.type) {
            $transport = $clientNetwork.type
        }
    }

    $networkJson = ""
    if ($clientNetwork) {
        $networkJson = ($clientNetwork | ConvertTo-Json -Compress -Depth 4).Replace('"', '""')
    }

    $runId = [guid]::NewGuid().ToString("N").Substring(0, 8)
    $timestamp = (Get-Date).ToUniversalTime().ToString("o")
    $escapedNotes = ($NoteText -replace '"', '""')
    $escapedTester = ($TesterName -replace '"', '""')
    $escapedScenario = ($Scenario -replace '"', '""')
    $escapedRole = ($Role -replace '"', '""')
    $escapedCallId = ($Id -replace '"', '""')

    $row = @(
        $runId,
        $timestamp,
        $escapedScenario,
        $escapedRole,
        $escapedCallId,
        $(if ($Role -eq "caller") { $transport } else { "" }),
        $(if ($Role -eq "callee") { $transport } else { "" }),
        "",
        "",
        $networkJson,
        $escapedTester,
        $escapedNotes
    ) -join ","

    Add-Content -Path $CsvPath -Value $row -Encoding UTF8
    Write-Host "Appended evidence row $runId to $CsvPath" -ForegroundColor Green
    if ($clientNetwork) {
        $clientNetwork | ConvertTo-Json -Depth 4
    } else {
        Write-Warning "No client_network from audit; row saved with empty network fields."
    }
}

Write-Host "=== WorldLinco LTE/5G VoIP Matrix Helper ===" -ForegroundColor Cyan

if ($InitTemplate) {
    Initialize-LteMatrixTemplate
    exit 0
}

if ($AppendEvidence) {
    if (-not $CallId) {
        Write-Error "-AppendEvidence requires -CallId"
    }
    Append-LteMatrixEvidenceRow `
        -Url $BaseUrl.TrimEnd("/") `
        -BearerToken $Token `
        -Id $CallId `
        -Scenario $MatrixScenario `
        -Role $DeviceRole `
        -TesterName $Tester `
        -NoteText $Notes
    exit 0
}

$health = Get-VoipHealth -Url $BaseUrl.TrimEnd("/")
$health | ConvertTo-Json -Depth 6
Write-Host ""

if ($HealthOnly) {
    exit 0
}

if (-not $Token) {
    Write-Warning "WORLDLINGO_TEST_TOKEN not set. Skipping audit fetch."
    Write-Host "Field steps:"
    Write-Host "  1) .\scripts\worldlinco_lte_matrix_verify.ps1 -InitTemplate"
    Write-Host "  2) Device A: disable WiFi, enable LTE/5G cellular data"
    Write-Host "  3) Device B: keep WiFi OR LTE (matrix combination)"
    Write-Host "  4) Start VoIP friend call from A; verify app banner shows cellular"
    Write-Host "  5) .\scripts\worldlinco_lte_matrix_verify.ps1 -AppendEvidence -CallId <id> -MatrixScenario wifi_lte -DeviceRole caller"
    Write-Host "  6) Repeat wifi_wifi, wifi_lte, lte_lte (>=2 runs each)"
    exit 0
}

if (-not $CallId) {
    Write-Warning "Pass -CallId <call_id> to inspect audit metadata.client_network"
    Write-Warning "Or use -AppendEvidence to log a CSV row for D-0-5"
    exit 0
}

$clientNetwork = Get-CallInitiatedClientNetwork -Url $BaseUrl.TrimEnd("/") -BearerToken $Token -Id $CallId
if (-not $clientNetwork) {
    Write-Warning "No call_initiated event for $CallId"
    exit 1
}

Write-Host "call_initiated client_network:" -ForegroundColor Green
$clientNetwork | ConvertTo-Json -Depth 4

# WorldLinco LTE/5G VoIP matrix verification helper
# Collects call_initiated audit client_network metadata for field-test evidence.
param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$Token = $env:WORLDLINGO_TEST_TOKEN,
    [string]$CallId = "",
    [switch]$HealthOnly
)

$ErrorActionPreference = "Stop"

function Get-VoipHealth {
    param([string]$Url)
    return Invoke-RestMethod -Method GET -Uri "$Url/api/v1/voip/health"
}

Write-Host "=== WorldLinco LTE/5G VoIP Matrix Helper ===" -ForegroundColor Cyan
$health = Get-VoipHealth -Url $BaseUrl.TrimEnd("/")
$health | ConvertTo-Json -Depth 6
Write-Host ""

if ($HealthOnly) {
    exit 0
}

if (-not $Token) {
    Write-Warning "WORLDLINGO_TEST_TOKEN not set. Skipping audit fetch."
    Write-Host "Field steps:"
    Write-Host "  1) Device A: disable WiFi, enable LTE/5G cellular data"
    Write-Host "  2) Device B: keep WiFi OR LTE (matrix combination)"
    Write-Host "  3) Start VoIP friend call from A; verify app banner shows cellular"
    Write-Host "  4) GET /api/v1/voip/calls/{call_id}/audit -> metadata.client_network"
    Write-Host "  5) Repeat wifi_wifi, wifi_lte, lte_lte (>=2 runs each)"
    exit 0
}

if (-not $CallId) {
    Write-Warning "Pass -CallId <call_id> to inspect audit metadata.client_network"
    exit 0
}

$headers = @{ Authorization = "Bearer $Token" }
$audit = Invoke-RestMethod -Method GET -Uri "$($BaseUrl.TrimEnd('/'))/api/v1/voip/calls/$CallId/audit" -Headers $headers
$initiated = $audit | Where-Object { $_.event_type -eq "call_initiated" } | Select-Object -First 1
if (-not $initiated) {
    Write-Warning "No call_initiated event for $CallId"
    exit 1
}

Write-Host "call_initiated client_network:" -ForegroundColor Green
$initiated.metadata.client_network | ConvertTo-Json -Depth 4

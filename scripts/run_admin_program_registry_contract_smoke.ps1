param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$ProgramId = "",
    [string]$AdminUsername = "ui.admin.round@devanalysis.local",
    [string]$AdminPassword = "RoundUi!20260426"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "[Contract 1/2] Negative smoke (404/400/400)"
& .\scripts\run_admin_program_registry_negative_smoke.ps1 `
    -BaseUrl $BaseUrl `
    -ProgramId $ProgramId `
    -AdminUsername $AdminUsername `
    -AdminPassword $AdminPassword

Write-Host "[Contract 2/2] Auth negative smoke (401/403)"
& .\scripts\run_admin_program_registry_auth_negative_smoke.ps1 -BaseUrl $BaseUrl

Write-Host "PROGRAM REGISTRY CONTRACT SMOKE PASSED"

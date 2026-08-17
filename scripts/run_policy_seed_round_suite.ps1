param(
    [ValidateSet("A", "B")]
    [string]$Round = "A",
    [string]$LegacyLabel = "seed-round"
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$policyScript = Join-Path $repoRoot "scripts\run_policy_round_suite.ps1"
$seedModule = "backend.scripts.seed_ui_round"

Write-Host "[POLICY-SEED-SUITE] legacy=$LegacyLabel round=$Round"

& powershell -NoProfile -ExecutionPolicy Bypass -File $policyScript -LegacyLabel "${LegacyLabel}:pre"
if ($LASTEXITCODE -ne 0) {
    throw "pre policy suite failed: exit $LASTEXITCODE"
}

& docker exec devanalysis114-backend sh -lc "cd /app; python -m $seedModule $Round"
if ($LASTEXITCODE -ne 0) {
    throw "seed round $Round failed: exit $LASTEXITCODE"
}

& powershell -NoProfile -ExecutionPolicy Bypass -File $policyScript -LegacyLabel "${LegacyLabel}:post" -SkipApiVerification
if ($LASTEXITCODE -ne 0) {
    throw "post policy suite failed: exit $LASTEXITCODE"
}

Write-Host "[POLICY-SEED-SUITE] PASS legacy=$LegacyLabel round=$Round"
param(
    [string]$LegacyLabel = "playwright-round",
    [switch]$SkipApiVerification
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$frontendRoot = Join-Path $repoRoot "frontend\frontend"
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"

Write-Host "[POLICY-SUITE] legacy=$LegacyLabel"

Push-Location $frontendRoot
try {
    $env:PLAYWRIGHT_ADMIN_BASE_URL = "http://127.0.0.1:3005"
    $env:PLAYWRIGHT_ADMIN_USERNAME = "ui.admin.round@devanalysis.local"
    $env:PLAYWRIGHT_ADMIN_PASSWORD = "RoundUi!20260426"

    & npx playwright test admin-passkey-recovery-policy.playwright.spec.ts --project=chromium --no-deps
    if ($LASTEXITCODE -ne 0) {
        throw "admin passkey/recovery policy Playwright failed: exit $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

if (-not $SkipApiVerification) {
    & docker exec devanalysis114-backend sh -lc "cd /app; python -m backend.scripts.reset_auth_quota"
    if ($LASTEXITCODE -ne 0) {
        throw "auth quota reset failed: exit $LASTEXITCODE"
    }

    & docker exec devanalysis114-backend sh -lc "cd /app; python -m backend.scripts.clear_ui_active_sessions"
    if ($LASTEXITCODE -ne 0) {
        throw "active-session cleanup failed: exit $LASTEXITCODE"
    }

    & $pythonExe (Join-Path $repoRoot "scripts\verify_auth_logins.py") --base-url http://127.0.0.1:8000
    if ($LASTEXITCODE -ne 0) {
        throw "auth-login-api verification failed: exit $LASTEXITCODE"
    }
}

Write-Host "[POLICY-SUITE] PASS legacy=$LegacyLabel"

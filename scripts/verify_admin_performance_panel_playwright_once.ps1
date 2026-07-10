param(
    [string]$AdminEmail = "119cash@naver.com",
    [SecureString]$AdminPassword,
    [string]$AdminBaseUrl = "http://127.0.0.1:3005",
    [string]$BackendBaseUrl = "http://127.0.0.1:8000",
    [switch]$StartWebServer
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$frontendRoot = Join-Path $repoRoot "frontend/frontend"
$fixedPasswordPath = Join-Path $repoRoot ".runtime/secrets/fixed_admin_password.txt"

if ([string]::IsNullOrWhiteSpace($AdminPassword) -and (Test-Path $fixedPasswordPath)) {
    $AdminPassword = ConvertTo-SecureString (Get-Content $fixedPasswordPath -Raw).Trim() -AsPlainText -Force
}

$plainPassword = ""
if ($AdminPassword) {
    $credential = New-Object System.Management.Automation.PSCredential('admin', $AdminPassword)
    $plainPassword = $credential.GetNetworkCredential().Password
}

if ([string]::IsNullOrWhiteSpace($AdminEmail) -or [string]::IsNullOrWhiteSpace($plainPassword)) {
    throw "AdminEmail/AdminPassword가 필요합니다. 또는 .runtime/secrets/fixed_admin_password.txt 파일을 준비하세요."
}

$env:PLAYWRIGHT_ADMIN_USERNAME = $AdminEmail
$env:PLAYWRIGHT_ADMIN_PASSWORD = $plainPassword
$env:PLAYWRIGHT_ADMIN_BASE_URL = $AdminBaseUrl
$env:PLAYWRIGHT_BACKEND_BASE_URL = $BackendBaseUrl
$env:PLAYWRIGHT_USE_WEBSERVER = if ($StartWebServer) { "1" } else { "0" }

Write-Host "[verify] admin performance panel playwright one-shot"
Write-Host "[verify] admin base: $($env:PLAYWRIGHT_ADMIN_BASE_URL)"
Write-Host "[verify] backend base: $($env:PLAYWRIGHT_BACKEND_BASE_URL)"
Write-Host "[verify] webserver mode: $($env:PLAYWRIGHT_USE_WEBSERVER)"

Push-Location $frontendRoot
try {
    npx playwright test tests/admin-performance-panel-live-once.playwright.spec.ts --project chromium --workers=1 --reporter=list
    if ($LASTEXITCODE -ne 0) {
        throw "Playwright verification failed with exit code $LASTEXITCODE"
    }
    Write-Host "[verify] SUCCESS: admin performance panel rendered and values reflected."
}
finally {
    Pop-Location
}

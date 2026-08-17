param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$AdminBaseUrl = "http://127.0.0.1:3005",
    [string]$AdminEmail = "119cash@naver.com",
    [string]$AdminPassword = "",
    [switch]$SkipFunnel,
    [switch]$SkipPlaywright,
    [switch]$SkipBuild,
    [switch]$StartWebServer
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-PythonCommand {
    if (Test-Path ".venv\\Scripts\\python.exe") {
        return ".venv\\Scripts\\python.exe"
    }
    return "python"
}

function Ensure-Directory([string]$Path) {
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

function Resolve-AdminPassword {
    param([string]$ExplicitPassword)

    if (-not [string]::IsNullOrWhiteSpace($ExplicitPassword)) {
        return $ExplicitPassword
    }

    if (-not [string]::IsNullOrWhiteSpace($env:FIXED_ADMIN_PASSWORD)) {
        return $env:FIXED_ADMIN_PASSWORD
    }

    $passwordFile = ".runtime\\secrets\\fixed_admin_password.txt"
    if (Test-Path $passwordFile) {
        $fromFile = (Get-Content $passwordFile -Raw).Trim()
        if (-not [string]::IsNullOrWhiteSpace($fromFile)) {
            return $fromFile
        }
    }

    return ""
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
Ensure-Directory "evidence"
Ensure-Directory "reports"

$password = Resolve-AdminPassword -ExplicitPassword $AdminPassword

# Funnel stage uses real admin login and requires an explicit password source.
# Playwright stage already has its own safe fallback password handling.
if (-not $SkipFunnel -and [string]::IsNullOrWhiteSpace($password)) {
    throw "Admin password is required for funnel stage. Provide -AdminPassword, FIXED_ADMIN_PASSWORD, or .runtime/secrets/fixed_admin_password.txt"
}

$pythonCmd = Resolve-PythonCommand
$funnelEvidence = "evidence/section7-travel-partner-funnel-$timestamp.json"
$reportPath = "reports/pr111-followup-pipeline-$timestamp.md"

$results = [ordered]@{
    Funnel = "PENDING"
    AdminPlaywright = "PENDING"
    AdminBuild = "PENDING"
}

try {
    if ($SkipFunnel) {
        Write-Host "[1/3] Funnel seed + verify (SKIPPED)"
        $results.Funnel = "SKIPPED"
    }
    else {
        Write-Host "[1/3] Funnel seed + verify"
        & $pythonCmd scripts/verify_travel_partner_funnel_section7.py --base-url $BaseUrl --email $AdminEmail --password $password --rounds 2 --output $funnelEvidence
        if ($LASTEXITCODE -ne 0) {
            throw "Funnel verification failed (exit=$LASTEXITCODE)"
        }
        $results.Funnel = "PASS"
    }

    if ($SkipPlaywright) {
        Write-Host "[2/3] Admin KPI Playwright one-shot (SKIPPED)"
        $results.AdminPlaywright = "SKIPPED"
    }
    else {
        Write-Host "[2/3] Admin KPI Playwright one-shot"
        $securePassword = ConvertTo-SecureString $password -AsPlainText -Force
        & "scripts/verify_admin_travel_kpi_playwright_once.ps1" -AdminEmail $AdminEmail -AdminPassword $securePassword -AdminBaseUrl $AdminBaseUrl -BackendBaseUrl $BaseUrl -StartWebServer:$StartWebServer
        if ($LASTEXITCODE -ne 0) {
            throw "Admin KPI Playwright one-shot failed (exit=$LASTEXITCODE)"
        }
        $results.AdminPlaywright = "PASS"
    }

    if ($SkipBuild) {
        Write-Host "[3/3] Admin frontend build (SKIPPED)"
        $results.AdminBuild = "SKIPPED"
    }
    else {
        Write-Host "[3/3] Admin frontend build"
        # Use a cross-platform invocation for CI runners (Linux/macOS/Windows).
        $previousNextDistDir = $env:NEXT_DIST_DIR
        $env:NEXT_DIST_DIR = ".next-build"
        npm --prefix frontend/frontend run build
        $env:NEXT_DIST_DIR = $previousNextDistDir
        if ($LASTEXITCODE -ne 0) {
            throw "Admin build failed (exit=$LASTEXITCODE)"
        }
        $results.AdminBuild = "PASS"
    }
}
catch {
    if ($results.Funnel -eq "PENDING") { $results.Funnel = "FAIL" }
    elseif ($results.AdminPlaywright -eq "PENDING") { $results.AdminPlaywright = "FAIL" }
    elseif ($results.AdminBuild -eq "PENDING") { $results.AdminBuild = "FAIL" }
    throw
}
finally {
    $report = @(
        "# PR111 Follow-up Pipeline Report",
        "",
        "- timestamp: $timestamp",
        "- base_url: $BaseUrl",
        "- admin_base_url: $AdminBaseUrl",
        "- admin_email: $AdminEmail",
        "- funnel_evidence: $funnelEvidence",
        "",
        "## Stage Results",
        "- Funnel seed/verify: $($results.Funnel)",
        "- Admin KPI Playwright one-shot: $($results.AdminPlaywright)",
        "- Admin frontend build: $($results.AdminBuild)"
    )
    $report -join "`n" | Set-Content -Encoding UTF8 $reportPath
    Write-Host "[report] $reportPath"
}

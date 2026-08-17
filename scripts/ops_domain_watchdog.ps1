param(
    [int]$IntervalSec = 60,
    [int]$TimeoutSec = 10,
    [string]$AdminDomain = "xn--114-2p7l635dz3bh5j.com",
    [string]$MarketplaceDomain = "metanova1004.com",
    [string]$ComposeFile = "docker-compose.yml",
    [int]$RemediationCooldownSec = 300,
    [switch]$Continuous,
    [switch]$AutoRemediate,
    [switch]$EnforceComposeOnly,
    [switch]$RequireDomainChecks,
    [switch]$RequireNginx
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$composeFilePath = $ComposeFile
if (-not [System.IO.Path]::IsPathRooted($composeFilePath)) {
    $composeFilePath = Join-Path $repoRoot $composeFilePath
}
$logDir = Join-Path $repoRoot "scripts\logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$logPath = Join-Path $logDir ("ops_watchdog_{0}.log" -f (Get-Date -Format "yyyyMMdd"))
$webhookUrl = ($env:OPS_ALERT_WEBHOOK_URL | Out-String).Trim()
$lastRemediationAt = [datetime]::MinValue

$localChecks = @(
    "http://127.0.0.1:8000/api/health",
    "http://127.0.0.1:3005/admin/login",
    "http://127.0.0.1:3000/marketplace"
)

$domainChecks = @(
    ("https://{0}/admin/login" -f $AdminDomain),
    ("https://{0}/marketplace" -f $MarketplaceDomain)
)

$criticalServices = @("backend", "frontend-admin", "frontend-marketplace")
if ($RequireNginx) {
    $criticalServices += "nginx"
    $localChecks += "http://127.0.0.1:80/health"
}

if (-not $RequireDomainChecks) {
    $domainChecks = @()
}

function Write-Log {
    param(
        [string]$Level,
        [string]$Message
    )
    $line = "[{0}] [{1}] {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Level, $Message
    Add-Content -Path $logPath -Value $line
    Write-Host $line
}

function Send-Alert {
    param([string]$Message)

    Write-Log -Level "ALERT" -Message $Message

    try {
        [console]::Beep(1200, 250)
    }
    catch {
    }

    if (-not [string]::IsNullOrWhiteSpace($webhookUrl)) {
        try {
            $payload = @{ text = "[codeAI watchdog] $Message" } | ConvertTo-Json -Compress
            Invoke-RestMethod -Method Post -Uri $webhookUrl -ContentType "application/json" -Body $payload -TimeoutSec 8 | Out-Null
            Write-Log -Level "INFO" -Message "alert webhook sent"
        }
        catch {
            Write-Log -Level "WARN" -Message ("failed to send alert webhook: {0}" -f $_.Exception.Message)
        }
    }
}

function Get-StatusCode {
    param([string]$Url)
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec
        return [int]$response.StatusCode
    }
    catch {
        return -1
    }
}

function Get-CriticalServiceFailures {
    $failures = @()
    try {
        $jsonLines = @(docker compose -f $composeFilePath ps --format json)
    }
    catch {
        return @("docker compose ps failed: $($_.Exception.Message)")
    }

    $parsed = @()
    foreach ($line in $jsonLines) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }
        try {
            $parsed += ($line | ConvertFrom-Json)
        }
        catch {
        }
    }

    foreach ($service in $criticalServices) {
        $info = $parsed | Where-Object { $_.Service -eq $service } | Select-Object -First 1
        if (-not $info) {
            $failures += "service '$service' missing"
            continue
        }
        $status = [string]$info.Status
        if ($status -notmatch "Up") {
            $failures += "service '$service' status=$status"
        }
    }

    return @($failures)
}

function Invoke-ComposeOnlyEnforcement {
    if (-not $EnforceComposeOnly) {
        return @()
    }

    try {
        & (Join-Path $PSScriptRoot "enforce_compose_only.ps1") -KillRogueNextDev
        if ($LASTEXITCODE -eq 2) {
            return @("rogue next dev process found")
        }
    }
    catch {
        return @("compose-only enforcement failed: $($_.Exception.Message)")
    }

    return @()
}

function Invoke-Probe {
    $errors = @()

    foreach ($url in ($localChecks + $domainChecks)) {
        $code = Get-StatusCode -Url $url
        if ($code -ne 200) {
            $errors += ("{0} -> HTTP {1}" -f $url, $code)
        }
        else {
            Write-Log -Level "INFO" -Message ("{0} -> 200" -f $url)
        }
    }

    $errors += Get-CriticalServiceFailures
    $errors += Invoke-ComposeOnlyEnforcement

    return @($errors)
}

function Try-Remediate {
    $now = Get-Date
    if (($now - $lastRemediationAt).TotalSeconds -lt $RemediationCooldownSec) {
        Write-Log -Level "WARN" -Message "remediation skipped due to cooldown"
        return
    }

    $script:lastRemediationAt = $now
    Write-Log -Level "WARN" -Message "running remediation: restart_standard_with_backend_ready.ps1"

    try {
        & (Join-Path $PSScriptRoot "restart_standard_with_backend_ready.ps1")
        if ($LASTEXITCODE -ne 0) {
            Send-Alert -Message ("remediation failed with exit code {0}" -f $LASTEXITCODE)
            return
        }
        Write-Log -Level "INFO" -Message "remediation completed"
    }
    catch {
        Send-Alert -Message ("remediation exception: {0}" -f $_.Exception.Message)
    }
}

Write-Log -Level "INFO" -Message ("watchdog started interval={0}s continuous={1} autoRemediate={2} enforceComposeOnly={3}" -f $IntervalSec, [bool]$Continuous, [bool]$AutoRemediate, [bool]$EnforceComposeOnly)

while ($true) {
    $failures = @(Invoke-Probe)
    if ($failures.Count -gt 0) {
        $joined = ($failures -join " | ")
        Send-Alert -Message ("healthcheck failed: {0}" -f $joined)
        if ($AutoRemediate) {
            Try-Remediate
            $post = @(Invoke-Probe)
            if ($post.Count -gt 0) {
                Send-Alert -Message ("post-remediation still failing: {0}" -f ($post -join " | "))
            }
            else {
                Write-Log -Level "INFO" -Message "post-remediation healthcheck recovered"
            }
        }
    }
    else {
        Write-Log -Level "INFO" -Message "all checks passed"
    }

    if (-not $Continuous) {
        break
    }

    Start-Sleep -Seconds $IntervalSec
}

exit 0

param(
    [int]$DockerReadyTimeoutSec = 300,
    [int]$RecoveryTimeoutSec = 600,
    [int]$ProbeIntervalSec = 10,
    [string]$AdminDomain = "xn--114-2p7l635dz3bh5j.com",
    [string]$MarketplaceDomain = "metanova1004.com",
    [switch]$RequireExternalDomains
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$logDir = Join-Path $repoRoot "scripts\logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$logPath = Join-Path $logDir ("postboot_recovery_{0}.log" -f (Get-Date -Format "yyyyMMdd"))

function Write-Log {
    param([string]$Level, [string]$Message)
    $line = "[{0}] [{1}] {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Level, $Message
    $line | Tee-Object -FilePath $logPath -Append
}

function Wait-DockerReady {
    $deadline = (Get-Date).AddSeconds($DockerReadyTimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            docker info > $null
            if ($LASTEXITCODE -eq 0) {
                Write-Log -Level "INFO" -Message "docker engine is ready"
                return
            }
        }
        catch {
        }
        Start-Sleep -Seconds 5
    }
    throw "docker engine not ready within timeout"
}

function Get-Code {
    param([string]$Url)
    try {
        $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 8
        return [int]$resp.StatusCode
    }
    catch {
        return -1
    }
}

function Verify-All200 {
    $targets = @(
        "http://127.0.0.1:3005/admin/login",
        "http://127.0.0.1:3000/marketplace"
    )

    if ($RequireExternalDomains) {
        $targets += @(
            "https://$AdminDomain/admin/login",
            "https://$MarketplaceDomain/marketplace"
        )
    }

    $failed = @()
    foreach ($url in $targets) {
        $code = Get-Code -Url $url
        if ($code -ne 200) {
            $failed += ("{0} -> HTTP {1}" -f $url, $code)
        }
    }
    return @($failed)
}

Write-Log -Level "INFO" -Message "postboot recovery verification started"
if (-not $RequireExternalDomains) {
    Write-Log -Level "INFO" -Message "external domain checks disabled (local endpoints only)"
}

Wait-DockerReady

& (Join-Path $PSScriptRoot "enforce_compose_only.ps1") -KillRogueNextDev | Out-Null
& (Join-Path $PSScriptRoot "restart_standard_with_backend_ready.ps1")
if ($LASTEXITCODE -ne 0) {
    throw "restart_standard_with_backend_ready.ps1 failed"
}

$deadline = (Get-Date).AddSeconds($RecoveryTimeoutSec)
$consecutivePass = 0
while ((Get-Date) -lt $deadline) {
    $failed = @(Verify-All200)
    if ($failed.Count -eq 0) {
        $consecutivePass++
        Write-Log -Level "INFO" -Message ("all endpoints 200 (pass streak={0})" -f $consecutivePass)
        if ($consecutivePass -ge 2) {
            Write-Log -Level "INFO" -Message "postboot verification success"
            exit 0
        }
    }
    else {
        $consecutivePass = 0
        Write-Log -Level "WARN" -Message ("verification failed: {0}" -f ($failed -join " | "))
    }
    Start-Sleep -Seconds $ProbeIntervalSec
}

Write-Log -Level "ALERT" -Message "postboot verification timeout"
exit 1

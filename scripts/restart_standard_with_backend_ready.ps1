param(
    [int]$BackendReadyTimeoutSec = 180,
    [int]$ProbeIntervalSec = 5,
    [string]$ComposeFile = "docker-compose.yml",
    [switch]$ManageNginx
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not [System.IO.Path]::IsPathRooted($ComposeFile)) {
    $ComposeFile = Join-Path $repoRoot $ComposeFile
}

$composeOnlyScript = Join-Path $PSScriptRoot "enforce_compose_only.ps1"
if (Test-Path $composeOnlyScript) {
    Write-Host "[compose-only] enforce compose-only policy"
    & $composeOnlyScript -KillRogueNextDev
}

function Invoke-Compose {
    param([string[]]$ComposeArgs)
    $argString = $ComposeArgs -join " "
    Write-Host ("[compose] docker compose -f {0} {1}" -f $ComposeFile, $argString)
    & docker compose -f $ComposeFile @ComposeArgs
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose command failed: $argString"
    }
}

function Wait-BackendHealthy {
    param(
        [int]$TimeoutSec,
        [int]$IntervalSec
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -TimeoutSec 5 -UseBasicParsing
            if ([int]$response.StatusCode -eq 200) {
                Write-Host "[ok] backend /api/health is ready (200)."
                return
            }
        }
        catch {
            # Waiting for backend readiness.
        }
        Start-Sleep -Seconds $IntervalSec
    }

    throw "backend readiness timeout after ${TimeoutSec}s"
}

# 1) Optionally stop nginx first to prevent early upstream lookup failures during backend/front startup.
if ($ManageNginx) {
    Invoke-Compose -ComposeArgs @("stop", "nginx")
}

# 2) Bring up backend and both frontends.
Invoke-Compose -ComposeArgs @("up", "-d", "backend", "frontend-admin", "frontend-marketplace")

# 3) Wait until backend health endpoint is reachable.
Wait-BackendHealthy -TimeoutSec $BackendReadyTimeoutSec -IntervalSec $ProbeIntervalSec

# 4) Optionally start nginx after backend is confirmed ready.
if ($ManageNginx) {
    Invoke-Compose -ComposeArgs @("up", "-d", "nginx")
}

# 5) Print concise status.
Invoke-Compose -ComposeArgs @("ps", "backend", "frontend-admin", "frontend-marketplace", "nginx")
Write-Host "[done] Standard restart completed with backend readiness gate."

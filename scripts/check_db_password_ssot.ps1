param(
    [string]$BackendContainer = "devanalysis114-backend",
    [string]$PostgresContainer = "devanalysis114-postgres",
    [string]$DbUser = "admin",
    [string]$DbName = "devanalysis114"
)

$ErrorActionPreference = "Stop"

function Assert-ContainerRunning {
    param([string]$Name)
    $running = (docker inspect -f "{{.State.Running}}" $Name 2>$null)
    if ($LASTEXITCODE -ne 0 -or "$running".Trim().ToLower() -ne "true") {
        throw "Container not running: $Name"
    }
}

Assert-ContainerRunning -Name $BackendContainer
Assert-ContainerRunning -Name $PostgresContainer

$backendPass = (docker exec $BackendContainer sh -lc 'printf "%s" "$POSTGRES_PASSWORD"' 2>$null)
if ($LASTEXITCODE -ne 0) {
    throw "Failed to read POSTGRES_PASSWORD from backend container: $BackendContainer"
}

if ([string]::IsNullOrWhiteSpace($backendPass)) {
    throw "Backend POSTGRES_PASSWORD is empty. Set a single source password first."
}

$backendHost = (docker exec $BackendContainer sh -lc 'printf "%s" "${POSTGRES_HOST:-postgres}"' 2>$null)
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($backendHost)) {
    $backendHost = "postgres"
}

$backendPort = (docker exec $BackendContainer sh -lc 'printf "%s" "${POSTGRES_PORT:-5432}"' 2>$null)
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($backendPort)) {
    $backendPort = "5432"
}

$postgresEnvPass = (docker inspect $PostgresContainer --format "{{range .Config.Env}}{{println .}}{{end}}" | Select-String -Pattern '^POSTGRES_PASSWORD=' | Select-Object -First 1)
$postgresPassValue = ""
if ($postgresEnvPass) {
    $postgresPassValue = ($postgresEnvPass.ToString() -replace '^POSTGRES_PASSWORD=', '').Trim()
}

$pythonCheck = @'
import os
import psycopg2

user = os.getenv('POSTGRES_USER') or '{0}'
db = os.getenv('POSTGRES_DB') or '{1}'
host = os.getenv('POSTGRES_HOST') or '{2}'
port = int(os.getenv('POSTGRES_PORT') or '{3}')
pw = os.getenv('POSTGRES_PASSWORD') or ''

try:
    conn = psycopg2.connect(host=host, port=port, user=user, password=pw, dbname=db, connect_timeout=5)
    cur = conn.cursor()
    cur.execute('select 1')
    print('OK')
    conn.close()
except Exception as exc:
    print('FAIL')
    print(type(exc).__name__)
    print(str(exc))
'@ -f $DbUser, $DbName, $backendHost, $backendPort

$connectResult = docker exec $BackendContainer python -c $pythonCheck

if ($LASTEXITCODE -ne 0) {
    throw "Connectivity test command failed in backend container."
}

$connectText = ($connectResult | Out-String)
$connectOk = $connectText -match "(?m)^OK\s*$"

$allChecksPassed = $true

Write-Host "[db-ssot] backend container : $BackendContainer"
Write-Host "[db-ssot] postgres container: $PostgresContainer"
Write-Host "[db-ssot] backend host/port : $backendHost`:$backendPort"
Write-Host "[db-ssot] backend pw length : $($backendPass.Length)"
Write-Host "[db-ssot] postgres env pw len: $($postgresPassValue.Length)"

if ($postgresPassValue -and $postgresPassValue -ne $backendPass) {
    $allChecksPassed = $false
    Write-Host "[db-ssot][FAIL] backend POSTGRES_PASSWORD != postgres container POSTGRES_PASSWORD" -ForegroundColor Red
}

if (-not $connectOk) {
    $allChecksPassed = $false
    Write-Host "[db-ssot][FAIL] backend -> postgres auth/connect test failed" -ForegroundColor Red
    Write-Host $connectText
}

if (-not $allChecksPassed) {
    Write-Host "[db-ssot][ACTION] Align runtime password + role password, then re-run this script." -ForegroundColor Yellow
    Write-Host "[db-ssot][HINT] docker exec $PostgresContainer psql -U $DbUser -d $DbName -c \"ALTER ROLE $DbUser WITH PASSWORD '<same-as-backend-POSTGRES_PASSWORD>';\""
    exit 1
}

Write-Host "[db-ssot][PASS] Password single-source checks passed and backend DB auth is healthy." -ForegroundColor Green
exit 0

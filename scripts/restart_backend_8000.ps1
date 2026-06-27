# Restart devanalysis114-backend on SSOT port 8000 and wait for health.
$ErrorActionPreference = 'Stop'

Write-Host 'Restarting devanalysis114-backend on :8000 ...'
docker restart devanalysis114-backend | Out-Null

$deadline = (Get-Date).AddSeconds(90)
while ((Get-Date) -lt $deadline) {
    try {
        $response = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host 'Backend healthy at http://127.0.0.1:8000'
            exit 0
        }
    } catch {
        Start-Sleep -Seconds 2
    }
}

Write-Error 'Backend did not become healthy on :8000 within 90s'
exit 1

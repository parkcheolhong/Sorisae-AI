$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

Write-Host '[backend-stack-stop] stop backend stack services' -ForegroundColor Cyan
Push-Location $root
try {
	docker compose stop video-worker backend minio qdrant redis postgres | Out-Host
}
finally {
	Pop-Location
}

Write-Host '[backend-stack-stop] done' -ForegroundColor Cyan
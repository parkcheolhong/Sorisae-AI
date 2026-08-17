$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

Write-Host '[backend-stack] start postgres/redis/qdrant/minio/backend/video-worker' -ForegroundColor Cyan
Push-Location $root
try {
	docker compose up -d postgres redis qdrant minio backend video-worker | Out-Host
}
finally {
	Pop-Location
}

Write-Host '[backend-stack] done' -ForegroundColor Cyan
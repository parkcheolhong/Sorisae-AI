# 소리새 friend-chat 전용 vLLM — Qwen3-8B AWQ @ :8009
# Usage:
#   .\scripts\start_vllm_sorisae_8b.ps1
#   .\scripts\start_vllm_sorisae_8b.ps1 -GpuMemoryUtilization 0.40

param(
    [string]$Model = "Qwen/Qwen3-8B-AWQ",
    [string]$ServedName = "Qwen/Qwen3-8B-AWQ",
    [int]$Port = 8009,
    [int]$MaxModelLen = 8192,
    [double]$GpuMemoryUtilization = 0.24,
    [string]$HfCacheRoot = "C:/gpu-llm-server-cache/huggingface",
    [string]$DockerComposePath = ""
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $DockerComposePath) {
    $DockerComposePath = Join-Path $root "gpu-llm-server\docker-compose.vllm-sorisae-8b.yml"
}

Write-Host "[vllm-sorisae] Qwen3-8B Instruct(AWQ) profile: $Model @ :$Port util=$GpuMemoryUtilization" -ForegroundColor Cyan

if (-not (Test-Path $DockerComposePath)) {
    throw "compose not found: $DockerComposePath"
}

$composeDir = Split-Path -Parent $DockerComposePath
Push-Location $composeDir
try {
    $env:HF_CACHE_ROOT = $HfCacheRoot
    $env:VLLM_SORISAE_MODEL = $Model
    $env:VLLM_SORISAE_SERVED_NAME = $ServedName
    $env:VLLM_SORISAE_MAX_MODEL_LEN = "$MaxModelLen"
    $env:VLLM_SORISAE_GPU_MEMORY_UTILIZATION = "$GpuMemoryUtilization"
    $composeFile = Split-Path -Leaf $DockerComposePath
    Write-Host "[vllm-sorisae] docker compose -f $composeFile up -d --force-recreate vllm-sorisae" -ForegroundColor Yellow
    docker compose -f $composeFile up -d --force-recreate vllm-sorisae | Out-Host
}
finally {
    Pop-Location
}

$modelPattern = [regex]::Escape($ServedName)
Write-Host "[vllm-sorisae] wait for readiness: http://127.0.0.1:$Port/v1/models" -ForegroundColor Cyan
for ($i = 0; $i -lt 180; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/v1/models" -UseBasicParsing -TimeoutSec 8
        if ($resp.StatusCode -eq 200 -and $resp.Content -match $modelPattern) {
            Write-Host "[vllm-sorisae] ready: $ServedName" -ForegroundColor Green
            Write-Host "[vllm-sorisae] backend .env:" -ForegroundColor Green
            Write-Host "  LLM_VOICE_FRIEND_BASE_URL=http://host.docker.internal:$Port/v1" -ForegroundColor Green
            Write-Host "  LLM_MODEL_VOICE_CHAT=$ServedName" -ForegroundColor Green
            Write-Host "[vllm-sorisae] reload backend env: docker compose up -d --force-recreate backend" -ForegroundColor Yellow
            exit 0
        }
    }
    catch {
        Start-Sleep -Seconds 5
    }
}

Write-Host "[vllm-sorisae] timeout — check: docker logs vllm-sorisae-8b" -ForegroundColor Red
exit 1

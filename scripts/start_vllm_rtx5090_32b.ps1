# RTX 5090 32GB — vLLM 32B AWQ 기동 (Windows / native Python)
# Usage:
#   .\scripts\start_vllm_rtx5090_32b.ps1
#   .\scripts\start_vllm_rtx5090_32b.ps1 -DockerComposePath "D:\path\to\gpu-llm-server\docker-compose.yml"

param(
    [string]$Model = "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ",
    [int]$Port = 8008,
    [int]$MaxModelLen = 8192,
    [double]$GpuMemoryUtilization = 0.92,
    [string]$HfCacheRoot = "C:/gpu-llm-server-cache/huggingface",
    [string]$DockerComposePath = ""
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $DockerComposePath) {
    $defaultCompose = Join-Path $root "gpu-llm-server\docker-compose.vllm-32b.yml"
    if (Test-Path $defaultCompose) {
        $DockerComposePath = $defaultCompose
    }
}

Write-Host "[vllm-32b] RTX 5090 profile: $Model AWQ, max-model-len=$MaxModelLen" -ForegroundColor Cyan

if ($DockerComposePath -and (Test-Path $DockerComposePath)) {
    $composeDir = Split-Path -Parent $DockerComposePath
    Push-Location $composeDir
    try {
        $env:HF_CACHE_ROOT = $HfCacheRoot
        $env:VLLM_MODEL = $Model
        $env:VLLM_MAX_MODEL_LEN = "$MaxModelLen"
        $env:VLLM_GPU_MEMORY_UTILIZATION = "$GpuMemoryUtilization"
        $composeFile = Split-Path -Leaf $DockerComposePath
        Write-Host "[vllm-32b] docker compose -f $composeFile recreate vllm-server in $composeDir" -ForegroundColor Yellow
        docker compose -f $composeFile up -d --force-recreate vllm-server | Out-Host
    }
    finally {
        Pop-Location
    }
}
else {
    $vllmCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $vllmCmd) {
        throw "python not found. Install vLLM or pass -DockerComposePath to gpu-llm-server compose."
    }
    $env:HF_HOME = $HfCacheRoot
    Write-Host "[vllm-32b] native: python -m vllm.entrypoints.openai.api_server ..." -ForegroundColor Yellow
    python -m vllm.entrypoints.openai.api_server `
        --model $Model `
        --quantization awq `
        --dtype auto `
        --max-model-len $MaxModelLen `
        --gpu-memory-utilization $GpuMemoryUtilization `
        --port $Port `
        --host 0.0.0.0
}

Write-Host "[vllm-32b] wait for readiness: http://127.0.0.1:$Port/v1/models" -ForegroundColor Cyan
$modelPattern = [regex]::Escape($Model)
for ($i = 0; $i -lt 120; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/v1/models" -UseBasicParsing -TimeoutSec 5
        if ($resp.StatusCode -eq 200 -and $resp.Content -match $modelPattern) {
            Write-Host "[vllm-32b] ready: $Model" -ForegroundColor Green
            Write-Host "[vllm-32b] verify: `$env:OLLAMA_BASE='http://127.0.0.1:$Port/v1'; python scripts/verify_autonomous_llm_gpu.py" -ForegroundColor Green
            exit 0
        }
    }
    catch {
        Start-Sleep -Seconds 5
    }
}

Write-Host "[vllm-32b] timeout — check docker logs vllm-server or vLLM console" -ForegroundColor Red
exit 1

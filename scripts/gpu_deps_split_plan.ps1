$ErrorActionPreference='Stop'
Set-Location 'C:\Users\WORK\source\repos\parkcheolhong\codeAI'

$reportRoot = 'exports/verification-packages/security-audit-node-20260818'
New-Item -ItemType Directory -Path $reportRoot -Force | Out-Null

$windowsAttemptLog = Join-Path $reportRoot 'gpu-deps-windows-attempt.log'
$linuxPlan = Join-Path $reportRoot 'gpu-deps-linux-cuda-plan.md'
$py311Plan = Join-Path $reportRoot 'gpu-deps-python311-venv-plan.md'

"[Windows attempt]" | Set-Content -Path $windowsAttemptLog -Encoding utf8
"Date: $((Get-Date).ToString('o'))" | Add-Content -Path $windowsAttemptLog -Encoding utf8

# Keep the command explicit for reproducibility.
$cmd = '.\\.venv\\Scripts\\python.exe -m pip install --no-cache-dir auto-gptq==0.7.1 autoawq==0.2.9 xformers==0.0.35 bitsandbytes==0.50.1'
"Command: $cmd" | Add-Content -Path $windowsAttemptLog -Encoding utf8

try {
  Invoke-Expression $cmd *>&1 | Add-Content -Path $windowsAttemptLog -Encoding utf8
  'Result: SUCCESS' | Add-Content -Path $windowsAttemptLog -Encoding utf8
}
catch {
  "Result: FAILED" | Add-Content -Path $windowsAttemptLog -Encoding utf8
  "Error: $($_.Exception.Message)" | Add-Content -Path $windowsAttemptLog -Encoding utf8
}

@'
# GPU 의존성 분리 설치 플랜 (Linux/CUDA)

## 목표
- auto-gptq, autoawq, xformers, bitsandbytes를 CUDA 가능한 Linux 환경에서 설치/검증

## 권장 베이스라인
- OS: Ubuntu 22.04+
- Python: 3.11 (권장)
- CUDA: 12.1+ (드라이버/런타임 일치)
- PyTorch: CUDA 빌드

## 절차
1. `python3.11 -m venv .venv-gpu && source .venv-gpu/bin/activate`
2. `pip install -U pip setuptools wheel`
3. `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121`
4. `pip install --no-cache-dir bitsandbytes==0.50.1 xformers==0.0.35`
5. `pip install --no-cache-dir autoawq==0.2.9`
6. `pip install --no-cache-dir auto-gptq==0.7.1`
7. `python -c "import torch,auto_gptq,awq,bitsandbytes,xformers; print('ok')"`

## 통과 기준
- import 검증 통과
- `pip check` 통과
'@ | Set-Content -Path $linuxPlan -Encoding utf8

@'
# GPU 의존성 분리 설치 플랜 (Windows 유지 + Python 3.11 별도 venv)

## 목표
- 현재 기본 .venv(3.13)는 유지하고, GPU 전용 .venv-gpu311에서만 고난도 의존성 관리

## 절차
1. Python 3.11 설치 확인
2. `py -3.11 -m venv .venv-gpu311`
3. `.venv-gpu311\Scripts\python.exe -m pip install -U pip setuptools wheel`
4. `.venv-gpu311\Scripts\python.exe -m pip install torch==2.4.*`
5. `.venv-gpu311\Scripts\python.exe -m pip install bitsandbytes==0.50.1 xformers==0.0.35 autoawq==0.2.9 auto-gptq==0.7.1`
6. `.venv-gpu311\Scripts\python.exe -m pip check`
7. import smoke test 수행

## 통과 기준
- GPU 전용 venv에서 설치/검증 성공
- 메인 venv(3.13)와 독립성 유지
'@ | Set-Content -Path $py311Plan -Encoding utf8

Write-Host "GPU_PLAN_REPORT_ROOT=$reportRoot"

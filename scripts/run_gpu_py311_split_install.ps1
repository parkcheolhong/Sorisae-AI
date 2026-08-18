$ErrorActionPreference='Stop'
Set-Location 'C:\Users\WORK\source\repos\parkcheolhong\codeAI'

$reportRoot = 'exports/verification-packages/security-audit-node-20260818'
New-Item -ItemType Directory -Path $reportRoot -Force | Out-Null
$logPath = Join-Path $reportRoot 'gpu-py311-split-install.log'

"[GPU split install with Python 3.11]" | Set-Content -Path $logPath -Encoding utf8
"Date: $((Get-Date).ToString('o'))" | Add-Content -Path $logPath -Encoding utf8

if (-not (Test-Path '.venv-gpu311')) {
  py -3.11 -m venv .venv-gpu311
}

$py = '.\.venv-gpu311\Scripts\python.exe'

$commands = @(
  "$py -m pip install -U pip setuptools wheel",
  "$py -m pip install torch==2.4.1",
  "$py -m pip install bitsandbytes==0.50.1",
  "$py -m pip install xformers==0.0.35",
  "$py -m pip install autoawq==0.2.9",
  "$py -m pip install auto-gptq==0.7.1",
  "$py -m pip check"
)

foreach ($c in $commands) {
  "" | Add-Content -Path $logPath -Encoding utf8
  "CMD: $c" | Add-Content -Path $logPath -Encoding utf8
  try {
    Invoke-Expression $c *>&1 | Add-Content -Path $logPath -Encoding utf8
    "RESULT: SUCCESS" | Add-Content -Path $logPath -Encoding utf8
  }
  catch {
    "RESULT: FAILED" | Add-Content -Path $logPath -Encoding utf8
    "ERROR: $($_.Exception.Message)" | Add-Content -Path $logPath -Encoding utf8
  }
}

Write-Host "GPU_PY311_LOG=$logPath"

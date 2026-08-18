$ErrorActionPreference='Stop'
Set-Location 'C:\Users\WORK\source\repos\parkcheolhong\codeAI'

$targets = @(
  'addons/nextjs_react',
  'addons/node_service',
  'apps/mobile-stock-ai',
  'mobile-nadotongryoksa',
  'apps/mobile-nadotongryoksa'
)

$out = 'exports/verification-packages/security-audit-node-20260818/post-nonbreaking-wave1'
New-Item -ItemType Directory -Force -Path $out | Out-Null

foreach ($t in $targets) {
  npm --prefix $t install --no-audit --no-fund
  $name = $t -replace '[\\/]', '__'
  $auditPath = Join-Path $out ($name + '__audit.json')
  try {
    npm --prefix $t audit --omit=dev --json | Out-File -Encoding utf8 -FilePath $auditPath
  }
  catch {
    if (!(Test-Path $auditPath)) {
      throw
    }
  }
}

Write-Host "OUT=$out"

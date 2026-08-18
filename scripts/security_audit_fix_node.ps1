$ErrorActionPreference='Stop'
Set-Location 'C:\Users\WORK\source\repos\parkcheolhong\codeAI'

$targets = @(
  'frontend/frontend',
  'mobile-nadotongryoksa',
  'apps/mobile-nadotongryoksa',
  'apps/mobile-stock-ai',
  'addons/node_service',
  'addons/nextjs_react'
)

$reportRoot = 'exports/verification-packages/security-audit-node-20260818'
New-Item -ItemType Directory -Path $reportRoot -Force | Out-Null

foreach ($t in $targets) {
  Write-Host "=== TARGET: $t ==="
  npm --prefix $t install --no-audit --no-fund

  $safeName = $t -replace '[\\/]', '__'
  $fixLog = Join-Path $reportRoot ("{0}__audit-fix.log" -f $safeName)
  $auditJson = Join-Path $reportRoot ("{0}__audit.json" -f $safeName)

  # Try non-breaking remediation first.
  npm --prefix $t audit fix --omit=dev *>&1 | Tee-Object -FilePath $fixLog

  # Capture post-fix audit status as machine-readable evidence.
  try {
    npm --prefix $t audit --omit=dev --json | Out-File -FilePath $auditJson -Encoding utf8
  }
  catch {
    # npm audit returns non-zero when vulnerabilities remain.
    if (Test-Path $auditJson) {
      Write-Host "audit json written with remaining vulnerabilities: $auditJson"
    }
    else {
      throw
    }
  }
}

Write-Host "NODE_AUDIT_REPORT_ROOT=$reportRoot"

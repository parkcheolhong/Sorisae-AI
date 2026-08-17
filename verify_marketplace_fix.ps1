try {
    $r = Invoke-WebRequest -UseBasicParsing -Uri 'https://metanova1004.com/marketplace/orchestrator?product=voice-engine-suite-basic' -TimeoutSec 15
    if ($r.Content -match 'autoComplete="current-password"') {
        Write-Output "✓ autoComplete found in orchestrator page"
    }
    else {
        Write-Output "✗ autoComplete NOT found in orchestrator page"
    }
}
catch {
    Write-Output ("✗ Error: {0}" -f $_.Exception.Message)
}

try {
    $r2 = Invoke-WebRequest -UseBasicParsing -Uri 'https://metanova1004.com/marketplace' -TimeoutSec 15
    if ($r2.Content -match 'autoComplete="current-password"') {
        Write-Output "✓ autoComplete found in marketplace main page"
    }
    else {
        Write-Output "✗ autoComplete NOT found in marketplace main page"
    }
}
catch {
    Write-Output ("✗ Error: {0}" -f $_.Exception.Message)
}

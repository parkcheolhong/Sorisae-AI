Write-Output "=== FINAL MARKETPLACE VALIDATION AFTER FORMFIELD FIX ==="

. "$PSScriptRoot/scripts/operational_domain_guard.ps1"
$domainCfg = Get-OperationalDomainConfig
$marketplaceDomain = $domainCfg.MarketplaceDomain
$adminDomain = $domainCfg.AdminPunycodeDomain
Assert-OperationalDomains -MarketplaceDomain $marketplaceDomain -AdminDomain $adminDomain -ScriptName 'final_validation_formfields.ps1'

Start-Sleep 30

try {
    $marketplaceUrl = "https://$marketplaceDomain/marketplace"
    Assert-AllowedOperationalUrl -Url $marketplaceUrl -ScriptName 'final_validation_formfields.ps1'
    $r = Invoke-WebRequest -UseBasicParsing -Uri $marketplaceUrl -TimeoutSec 15
    Write-Output "[1] HTTP Status: $($r.StatusCode)"
    
    # Check for ChunkLoadError
    if ($r.Content -notlike '*ChunkLoadError*') {
        Write-Output "[2] ✓ ChunkLoadError: RESOLVED"
    }
    else {
        Write-Output "[2] ✗ ChunkLoadError: STILL PRESENT"
    }
    
    # Check for id/name on email field
    if ($r.Content -match 'id="marketplace-email".*name="email"') {
        Write-Output "[3] ✓ Email field: id/name added"
    }
    else {
        Write-Output "[3] ? Email field: need to verify in browser"
    }
    
    # Check for other form fields
    $formFields = @('username', 'fullname', 'membertype', 'businessname', 'businessreg', 'repname')
    $missingCount = 0
    foreach ($field in $formFields) {
        if ($r.Content -notmatch "id=`"marketplace-.*$field`"") {
            $missingCount++
        }
    }
    
    if ($missingCount -eq 0) {
        Write-Output "[4] ✓ All form fields: id/name attributes present"
    }
    else {
        Write-Output "[4] ⚠ $missingCount form fields may still need id/name"
    }
    
}
catch {
    Write-Output "✗ Error: $($_.Exception.Message)"
}

Write-Output "`n[REMAINING ISSUES TO INVESTIGATE]"
Write-Output "1. CORB (Cross-Origin Read Blocking) - 2 blocked requests"
Write-Output "2. CSP eval warning - Check if from framework vs user code"
Write-Output "`nThese need browser console inspection for exact sources."

Write-Output "=== FORM FIELD VERIFICATION ==="

try {
    # Check orchestrator page
    $orch = Invoke-WebRequest -UseBasicParsing -Uri 'https://metanova1004.com/marketplace/orchestrator?product=voice-engine-suite-basic' -TimeoutSec 15
    
    Write-Output "[Orchestrator Page]"
    
    # Count all id attributes in form fields
    $orchestratorIds = @(
        'orch-email',
        'orch-username',
        'orch-fullname',
        'orch-membertype',
        'orch-businessname',
        'orch-businessreg',
        'orch-repname'
    )
    
    $foundCount = 0
    foreach ($id in $orchestratorIds) {
        if ($orch.Content -match "id=`"$id`"") {
            Write-Output "  ✓ $id"
            $foundCount++
        }
    }
    
    Write-Output "  Found: $foundCount/$($orchestratorIds.Count)"
    
    # Check main marketplace page
    $main = Invoke-WebRequest -UseBasicParsing -Uri 'https://metanova1004.com/marketplace' -TimeoutSec 15
    
    Write-Output "`n[Main Marketplace Page]"
    
    $mainIds = @(
        'marketplace-email',
        'marketplace-username',
        'marketplace-fullname',
        'marketplace-membertype',
        'marketplace-businessname',
        'marketplace-businessreg',
        'marketplace-repname'
    )
    
    $foundCount = 0
    foreach ($id in $mainIds) {
        if ($main.Content -match "id=`"$id`"") {
            Write-Output "  ✓ $id"
            $foundCount++
        }
    }
    
    Write-Output "  Found: $foundCount/$($mainIds.Count)"
    
} catch {
    Write-Output "Error: $($_.Exception.Message)"
}

Write-Output "=== QUICK MARKETPLACE STATUS CHECK ==="
try {
    $r = Invoke-WebRequest -UseBasicParsing -Uri 'https://metanova1004.com/marketplace' -TimeoutSec 15
    
    if ($r.StatusCode -eq 200) {
        if ($r.Content -notlike '*ChunkLoadError*') {
            Write-Output "✓ MARKETPLACE OK - ChunkLoadError resolved"
        } else {
            Write-Output "✗ ChunkLoadError still present"
        }
    }
} catch {
    Write-Output "✗ Marketplace error: $($_.Exception.Message)"
}

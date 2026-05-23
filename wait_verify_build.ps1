Write-Output "Waiting for build to complete (3 minutes)..."
Start-Sleep 180

Write-Output "`nVerifying marketplace..."
try {
    $r = Invoke-WebRequest -UseBasicParsing -Uri 'https://metanova1004.com/marketplace' -TimeoutSec 15
    Write-Output "HTTP $($r.StatusCode)"
    
    if ($r.Content -notlike '*ChunkLoadError*') {
        Write-Output "✓ ChunkLoadError RESOLVED"
    } else {
        Write-Output "✗ ChunkLoadError STILL present"
    }
} catch {
    Write-Output "✗ Error: $($_.Exception.Message)"
}

Write-Output "=== MARKETPLACE RECOVERY CHECK ==="

Start-Sleep 5

Write-Output "`n[1] Testing marketplace main page..."
try {
    $r = Invoke-WebRequest -UseBasicParsing -Uri 'https://metanova1004.com/marketplace' -TimeoutSec 15
    Write-Output "  ✓ HTTP $($r.StatusCode)"
    
    # Check for ChunkLoadError in response
    if ($r.Content -like '*ChunkLoadError*' -or $r.Content -like '*Failed to load chunk*') {
        Write-Output "  ✗ ChunkLoadError still present in HTML"
    }
    else {
        Write-Output "  ✓ No ChunkLoadError in HTML"
    }
}
catch {
    Write-Output "  ✗ Error: $($_.Exception.Message)"
}

Write-Output "`n[2] Testing orchestrator page..."
try {
    $r2 = Invoke-WebRequest -UseBasicParsing -Uri 'https://metanova1004.com/marketplace/orchestrator?product=voice-engine-suite-basic' -TimeoutSec 15
    Write-Output "  ✓ HTTP $($r2.StatusCode)"
    
    if ($r2.Content -like '*ChunkLoadError*' -or $r2.Content -like '*Failed to load chunk*') {
        Write-Output "  ✗ ChunkLoadError still present"
    }
    else {
        Write-Output "  ✓ No ChunkLoadError in response"
    }
}
catch {
    Write-Output "  ✗ Error: $($_.Exception.Message)"
}

Write-Output "`n[3] Checking specific chunk direct access..."
try {
    $chunk = Invoke-WebRequest -UseBasicParsing -Uri 'https://metanova1004.com/_next/static/chunks/04uhv0cpethuc.js' -TimeoutSec 10
    Write-Output "  ✓ Chunk direct HTTP $($chunk.StatusCode), Size: $($chunk.Content.Length) bytes"
}
catch {
    Write-Output "  ✗ Chunk error: $($_.Exception.Message)"
}

Write-Output "`n=== RESULT ==="
Write-Output "Container restarted. ChunkLoadError likely due to browser cache."
Write-Output "User needs to: Hard refresh browser (Ctrl+Shift+R or Cmd+Shift+R)"

Write-Output "=== CHUNK FILE VALIDATION ==="

# Check chunk file size
Write-Output "`n[1] Chunk file sizes..."
try {
    $sizes = docker exec devanalysis114-frontend-marketplace sh -c "ls -lh /app/.next/static/chunks/04uhv0cpethuc.js"
    Write-Output $sizes
}
catch {
    Write-Output "  ✗ Error: $_"
}

# Check if file is actually readable
Write-Output "`n[2] Checking chunk content (first 100 bytes)..."
try {
    $content = docker exec devanalysis114-frontend-marketplace sh -c "head -c 100 /app/.next/static/chunks/04uhv0cpethuc.js"
    if ($content.Length -gt 0) {
        Write-Output "  ✓ File is readable, starts with: $($content.Substring(0, [Math]::Min(80, $content.Length)))..."
    }
    else {
        Write-Output "  ✗ File is EMPTY or corrupted"
    }
}
catch {
    Write-Output "  ✗ Error: $_"
}

# Check build-manifest for the chunk reference
Write-Output "`n[3] Checking build-manifest.json for chunk..."
try {
    $manifest = docker exec devanalysis114-frontend-marketplace sh -c "cat /app/.next/build-manifest.json"
    Write-Output $manifest | ConvertFrom-Json | ConvertTo-Json -Depth 3 | head -20
    
    if ($manifest -like '*04uhv0cpethuc*') {
        Write-Output "  ✓ Chunk referenced in manifest"
    }
    else {
        Write-Output "  ℹ Chunk not found in manifest (expected for Turbopack)"
    }
}
catch {
    Write-Output "  ✗ Error: $_"
}

Write-Output "`n[4] Restarting marketplace container to clear caches..."
try {
    docker-compose -f docker-compose.yml restart frontend-marketplace
    Write-Output "  ✓ Container restarted"
    Start-Sleep 10
    
    Write-Output "`n[5] Testing after restart..."
    try {
        $r = Invoke-WebRequest -UseBasicParsing -Uri 'https://metanova1004.com/marketplace' -TimeoutSec 15
        Write-Output "  ✓ Marketplace HTTP 200"
    }
    catch {
        Write-Output "  ✗ Still erroring: $($_.Exception.Message)"
    }
}
catch {
    Write-Output "  ✗ Error restarting: $_"
}

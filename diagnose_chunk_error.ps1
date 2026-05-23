Write-Output "=== MARKETPLACE CONTAINER DIAGNOSTICS ==="

# Check if chunk file exists
Write-Output "`n[1] Checking chunk file in container..."
try {
    $chunks = docker exec devanalysis114-frontend-marketplace sh -c "ls -lh /app/.next/static/chunks/*.js 2>&1 | wc -l"
    Write-Output "  Chunk files found: $chunks"
    
    # List first 10 chunks
    $list = docker exec devanalysis114-frontend-marketplace sh -c "ls /app/.next/static/chunks/*.js 2>&1 | head -10"
    Write-Output "  First 10 chunks:"
    $list -split "`n" | ForEach-Object { if ($_) { Write-Output "    $_" } }
} catch {
    Write-Output "  ✗ Error: $_"
}

# Check if specific chunk exists
Write-Output "`n[2] Checking for 04uhv0cpethuc chunk..."
try {
    $check = docker exec devanalysis114-frontend-marketplace sh -c "find /app/.next -name '*04uhv0cpethuc*' 2>&1"
    if ($check -like "*04uhv0cpethuc*") {
        Write-Output "  ✓ Chunk file found: $check"
    } else {
        Write-Output "  ✗ Chunk file NOT found"
        Write-Output "  Output: $check"
    }
} catch {
    Write-Output "  ✗ Error: $_"
}

# Check .next folder structure
Write-Output "`n[3] Checking .next folder structure..."
try {
    $struct = docker exec devanalysis114-frontend-marketplace sh -c "ls -la /app/.next/static/ 2>&1"
    Write-Output $struct
} catch {
    Write-Output "  ✗ Error: $_"
}

# Check manifest/build-manifest
Write-Output "`n[4] Checking build metadata..."
try {
    $manifest = docker exec devanalysis114-frontend-marketplace sh -c "ls -lh /app/.next/*.json 2>&1 | head -5"
    Write-Output $manifest
} catch {
    Write-Output "  ✗ Error: $_"
}

# Test if web server can serve chunks
Write-Output "`n[5] Testing chunk availability via HTTP..."
try {
    $test = Invoke-WebRequest -UseBasicParsing -Uri 'https://metanova1004.com/_next/static/chunks/main.js' -TimeoutSec 10
    Write-Output "  ✓ HTTP chunk serving: $($test.StatusCode)"
} catch {
    Write-Output "  ✗ HTTP error: $($_.Exception.Message)"
}

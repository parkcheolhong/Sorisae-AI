Write-Output "=== MARKETPLACE CLEAN REBUILD ==="
Write-Output "Starting at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"

# Remove any cached build artifacts
Write-Output "`n[1] Cleaning up old build artifacts..."
try {
    docker-compose down frontend-marketplace
    docker image rm devanalysis114-frontend-marketplace:latest -f 2>&1 | Out-Null
    Write-Output "  ✓ Old image removed"
}
catch {
    Write-Output "  ⚠ Cleanup warning: $_"
}

# Full rebuild with no cache
Write-Output "`n[2] Starting CLEAN build (no cache)..."
try {
    docker-compose build --no-cache --progress=plain frontend-marketplace 2>&1 | Tee-Object -Variable build_output | Select-String -Pattern "Successfully|ERROR|error|failed" | ForEach-Object { Write-Output "  $_" }
    
    # Check build success
    if ($build_output -like "*Successfully*" -or $build_output -like "*exporting manifest*") {
        Write-Output "  ✓ Build completed"
    }
    else {
        Write-Output "  ⚠ Build output review:"
        $build_output | tail -20
    }
}
catch {
    Write-Output "  ✗ Build error: $_"
}

# Start container
Write-Output "`n[3] Starting marketplace container..."
try {
    docker-compose up -d frontend-marketplace
    Write-Output "  ✓ Container started"
    Start-Sleep 15
}
catch {
    Write-Output "  ✗ Startup error: $_"
}

# Verify HTTP
Write-Output "`n[4] Verification..."
try {
    $r = Invoke-WebRequest -UseBasicParsing -Uri 'https://metanova1004.com/marketplace' -TimeoutSec 15
    Write-Output "  ✓ HTTP $($r.StatusCode)"
    
    if ($r.Content -like '*ChunkLoadError*') {
        Write-Output "  ✗ ChunkLoadError STILL present in HTML"
    }
    else {
        Write-Output "  ✓ No ChunkLoadError in response"
    }
}
catch {
    Write-Output "  ✗ Error: $($_.Exception.Message)"
}

Write-Output "`nCompleted at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"

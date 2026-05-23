Write-Output "=== REBUILD STATUS AND NEW WARNINGS CHECK ==="

# 1. Check if marketplace is up
Write-Output "`n[1] Marketplace Rebuild Status..."
try {
    $r = Invoke-WebRequest -UseBasicParsing -Uri 'https://metanova1004.com/marketplace' -TimeoutSec 15
    Write-Output "  ✓ HTTP $($r.StatusCode)"
    
    if ($r.Content -like '*ChunkLoadError*') {
        Write-Output "  ✗ ChunkLoadError STILL present"
    } else {
        Write-Output "  ✓ ChunkLoadError RESOLVED"
    }
} catch {
    Write-Output "  ✗ Marketplace unavailable: $($_.Exception.Message)"
}

# 2. Form field warnings - identify which fields need id/name
Write-Output "`n[2] Checking form fields for missing id/name..."
Write-Output "   Need to inspect:"
Write-Output "   - marketplace/page.tsx (email, signup fields)"
Write-Output "   - marketplace-orchestrator-client.tsx (email, signup fields)"
Write-Output "   → These need id and name attributes added"

# 3. CSP eval warning
Write-Output "`n[3] CSP eval() warning analysis..."
Write-Output "   Sources: Check if Turbopack/Next.js runtime uses eval"
Write-Output "   This may be from next/dynamic or dev tools, not user code"

# 4. CORB (Cross-Origin Read Blocking)
Write-Output "`n[4] CORB blocked requests (2)..."
Write-Output "   Likely: Admin→Marketplace cross-domain API calls"
Write-Output "   Check: /api/llm/voice/orchestrate CORS headers"

Write-Output "`n[NEXT STEPS]"
Write-Output "1. Verify ChunkLoadError is resolved"
Write-Output "2. Add id/name to form email/signup inputs"
Write-Output "3. Verify CORS headers on admin→marketplace APIs"

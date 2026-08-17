Write-Output "=== DIAGNOSING PERSISTENT CHUNKLOADERROR ==="

# Check if container even has the chunk
Write-Output "`n[1] Checking chunk file existence and validity..."
$chunk_info = docker exec devanalysis114-frontend-marketplace sh -c "stat /app/.next/static/chunks/04uhv0cpethuc.js 2>&1 && head -c 200 /app/.next/static/chunks/04uhv0cpethuc.js"
Write-Output $chunk_info

# Check Next.js build logs in container
Write-Output "`n[2] Checking for build errors in container..."
$build_check = docker exec devanalysis114-frontend-marketplace sh -c "cat /app/.next/build-manifest.json" 2>&1
Write-Output "Build Manifest:"
Write-Output ($build_check | ConvertFrom-Json | ConvertTo-Json -Depth 2)

# Check if issue is source code problem
Write-Output "`n[3] Checking if source files are valid..."
$src_check = docker exec devanalysis114-frontend-marketplace sh -c "find /app/app -name '*.tsx' | wc -l"
Write-Output "TypeScript files in /app/app: $src_check"

# Look for compilation errors in Docker build output
Write-Output "`n[4] Checking for TypeScript compilation errors..."
$ts_errors = docker logs devanalysis114-frontend-marketplace 2>&1 | grep -i "error\|failed" | head -10
if ($ts_errors) {
    Write-Output "Found errors:"
    Write-Output $ts_errors
} else {
    Write-Output "No obvious errors in recent logs"
}

Write-Output "`n[5] Testing direct chunk HTTP access..."
try {
    $direct = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:3000/_next/static/chunks/04uhv0cpethuc.js' -TimeoutSec 10 -SkipCertificateCheck
    Write-Output "  ✓ Chunk accessible via localhost:3000: $($direct.StatusCode)"
    Write-Output "  Content length: $($direct.Content.Length) bytes"
} catch {
    Write-Output "  ✗ Localhost access failed: $($_.Exception.Message)"
}

Write-Output "`n[CONCLUSION]"
Write-Output "ChunkLoadError likely root cause: TypeScript compilation error or missing chunk generation"
Write-Output "Solution: Perform clean rebuild with explicit TypeScript validation"

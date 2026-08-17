Write-Output "Checking backend CORS configuration..."
Start-Sleep 15

# Resolve backend container name dynamically and inspect logs
$backendContainer = docker ps --filter "name=devanalysis114-backend" --format "{{.Names}}" | Select-Object -First 1
if (-not $backendContainer) {
    Write-Output "? Backend container not found for name filter: devanalysis114-backend"
    exit 1
}

$logs = docker logs $backendContainer 2>&1

# Find CORS origins loaded line
$corsLine = $logs | Where-Object { $_ -like "*cors origins loaded*" } | Select-Object -Last 1

if ($corsLine) {
    Write-Output "✓ CORS Configuration Found:"
    Write-Output "  $corsLine"
    
    # Check if production domains are included
    if ($corsLine -like "*metanova1004.com*" -and $corsLine -like "*xn--114*") {
        Write-Output "  ✓ Production domains FOUND in CORS origins"
    }
    else {
        Write-Output "  ? Production domains NOT found yet"
    }
}
else {
    Write-Output "? CORS configuration line not found in recent logs"
    Write-Output "  Container: $backendContainer"
    Write-Output "  Showing last 10 lines of backend logs:"
    $logs | Select-Object -Last 10 | ForEach-Object { Write-Output "  $_" }
}

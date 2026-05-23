# Update docker-compose.yml to include production domains in CORS_ORIGINS
# Read the file
$file = Get-Content -Path docker-compose.yml -Raw

# Replace the problematic double CORS_ORIGINS with corrected single line
$oldPattern = '      CORS_ORIGINS: http://localhost:3000,http://localhost:3005,http://127\.0\.0\.1:3000,http://127\.0\.0\.1:3005\s+CORS_ORIGINS: http://localhost:3000,http://localhost:3005,http://127\.0\.0\.1:3000,http://127\.0\.0\.1:3005,https://metanova1004\.com,https://xn--114-2p7l635dz3bh5j\.com'

$newValue = '      CORS_ORIGINS: http://localhost:3000,http://localhost:3005,http://127.0.0.1:3000,http://127.0.0.1:3005,https://metanova1004.com,https://xn--114-2p7l635dz3bh5j.com'

if ($file -match $oldPattern) {
    $file = $file -replace $oldPattern, $newValue
    Write-Output "Pattern found and replaced"
}
else {
    Write-Output "Pattern NOT found, trying simpler approach..."
    # Simple replacement of just the old line
    $file = $file -replace 'CORS_ORIGINS: http://localhost:3000,http://localhost:3005,http://127\.0\.0\.1:3000,http://127\.0\.0\.1:3005(\s+CORS_ORIGINS)?', 'CORS_ORIGINS: http://localhost:3000,http://localhost:3005,http://127.0.0.1:3000,http://127.0.0.1:3005,https://metanova1004.com,https://xn--114-2p7l635dz3bh5j.com'
}

# Count CORS_ORIGINS lines
$corsCount = ([regex]::Matches($file, 'CORS_ORIGINS')).Count
Write-Output "CORS_ORIGINS count after replacement: $corsCount"

# Write back
Set-Content -Path docker-compose.yml -Value $file
Write-Output "Updated docker-compose.yml"

# Show the corrected lines
Get-Content -Path docker-compose.yml | Select-String "CORS_ORIGINS" | ForEach-Object { Write-Output "  $_" }

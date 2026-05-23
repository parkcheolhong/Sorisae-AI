# Fix docker-compose.yml CORS_ORIGINS
$filePath = "docker-compose.yml"
$content = Get-Content -Path $filePath -Raw

# Remove the old single CORS_ORIGINS line and fix the indentation of the new one
$content = $content -replace `
    '      CORS_ORIGINS: http://localhost:3000,http://localhost:3005,http://127\.0\.0\.1:3000,http://127\.0\.0\.1:3005\s+CORS_ORIGINS: http://localhost:3000,http://localhost:3005,http://127\.0\.0\.1:3000,http://127\.0\.0\.1:3005,https://metanova1004\.com,https://xn--114-2p7l635dz3bh5j\.com', `
    '      CORS_ORIGINS: http://localhost:3000,http://localhost:3005,http://127.0.0.1:3000,http://127.0.0.1:3005,https://metanova1004.com,https://xn--114-2p7l635dz3bh5j.com'

Set-Content -Path $filePath -Value $content
Write-Output "Fixed docker-compose.yml CORS_ORIGINS configuration"

# Verify the fix
$lines = (Get-Content -Path $filePath | Select-String -Pattern "CORS_ORIGINS" | Measure-Object).Count
Write-Output "CORS_ORIGINS lines after fix: $lines (should be 1)"
Get-Content -Path $filePath | Select-String -Pattern "CORS_ORIGINS"

$api = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/marketplace/projects" -UseBasicParsing
Write-Host "API 응답 구조:"
$api | ConvertTo-Json -Depth 5 | Write-Host
Write-Host "`nAPI 응답 타입: $($api.GetType().Name)"
Write-Host "API 응답 키: $($api.PSObject.Properties | ForEach-Object { $_.Name })"

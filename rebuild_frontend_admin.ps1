$ErrorActionPreference = "Continue"
Set-Location "C:\Users\WORK\source\repos\parkcheolhong\codeAI\frontend\frontend"
$output = & docker build --no-cache -t devanalysis114-frontend-admin . 2>&1
$output | Select-Object -Last 30 | Out-File "C:\Users\WORK\source\repos\parkcheolhong\codeAI\build_output.txt"
$lastLine = $output | Select-Object -Last 5 | Out-String
Write-Host "=== BUILD RESULT ===" 
Write-Host $lastLine
# Restart container with new image
Set-Location "C:\Users\WORK\source\repos\parkcheolhong\codeAI"
docker stop devanalysis114-frontend-admin
docker rm devanalysis114-frontend-admin
docker compose -f docker-compose.yml up -d frontend-admin
Write-Host "=== Container restarted ==="
docker ps --filter "name=frontend-admin" --format "{{.Names}} {{.Status}}"

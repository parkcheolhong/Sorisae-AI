
# Redis 캐시 청소
docker exec devanalysis114-redis redis-cli FLUSHDB
Write-Host "✓ Redis 캐시 정리 완료" -ForegroundColor Green

# 백엔드 재시작 (캐시 로드 재실행)
Start-Sleep -Seconds 1
docker restart devanalysis114-backend
Write-Host "✓ 백엔드 재시작..." -ForegroundColor Green
Start-Sleep -Seconds 3

# API 다시 확인
Write-Host "`n=== API 응답 재확인 ===" -ForegroundColor Cyan
cd c:\Users\WORK\source\repos\parkcheolhong\codeAI
python check_api_projects.py

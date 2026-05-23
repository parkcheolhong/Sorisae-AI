
# 로컬 DB의 projects 개수
Write-Host "로컬 DB:" -ForegroundColor Cyan
python -c "import sqlite3; db = sqlite3.connect('app.db'); c = db.cursor(); c.execute('SELECT COUNT(*) FROM projects'); print(f'  projects 개수: {c.fetchone()[0]}')"

# 컨테이너 DB의 projects 개수  
Write-Host "`n컨테이너 DB:" -ForegroundColor Cyan
docker exec devanalysis114-backend python -c "import sqlite3; db = sqlite3.connect('/app/app.db'); c = db.cursor(); c.execute('SELECT COUNT(*) FROM projects'); print(f'  projects 개수: {c.fetchone()[0]}')"

# 컨테이너의 app.db가 로컬 파일을 마운트하는지 확인
Write-Host "`n컨테이너 마운트 정보:" -ForegroundColor Cyan
docker inspect devanalysis114-backend | grep -A 10 '"Mounts"' | head -20

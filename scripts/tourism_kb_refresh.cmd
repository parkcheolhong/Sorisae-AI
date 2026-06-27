@echo off
REM 소리새 AI 관광 KB 주기 갱신 래퍼 (Windows 작업 스케줄러용).
REM 전 도시 OSM POI 를 멱등 upsert 로 최신화한다(Wikidata 는 WDQS 제한 회피 위해 기본 제외).
setlocal
set REPO=C:\Users\WORK\source\repos\parkcheolhong\codeAI
cd /d "%REPO%"
if not exist "%REPO%\logs" mkdir "%REPO%\logs"
echo [%date% %time%] tourism_kb refresh start >> "%REPO%\logs\tourism_kb_refresh.log"
".venv\Scripts\python.exe" scripts\ingest_tourism_batch.py --all --no-wikidata --limit 700 >> "%REPO%\logs\tourism_kb_refresh.log" 2>&1
echo [%date% %time%] tourism_kb refresh done (exit %ERRORLEVEL%) >> "%REPO%\logs\tourism_kb_refresh.log"
endlocal

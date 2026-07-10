# Open Transport GTFS Setup

목표: 유료 지도/교통 API 없이 소리새 route grounding 이 무료 공개 GTFS Schedule 피드에서 실제 출발/도착 시각을 읽도록 설정한다.

## 환경변수

백엔드가 읽는 첫 변수명은 아래 2개다.

```env
OPEN_TRANSPORT_KR_GTFS_URL=
OPEN_TRANSPORT_JP_GTFS_URL=
```

의미:

- `OPEN_TRANSPORT_KR_GTFS_URL`: 한국 무료 GTFS Schedule zip URL 또는 로컬 zip 경로
- `OPEN_TRANSPORT_JP_GTFS_URL`: 일본 무료 GTFS Schedule zip URL 또는 로컬 zip 경로

## 기대 포맷

허용 포맷은 둘 중 하나다.

1. 공개 zip URL

```text
https://example.org/path/to/feed.zip
```

1. 로컬 zip 경로

```text
/app/uploads/transport/kr-feed.zip
C:\transport\kr-feed.zip
```

GTFS zip 안에는 최소 아래 파일이 있어야 한다.

- `stops.txt`
- `trips.txt`
- `stop_times.txt`
- `calendar.txt`

있으면 함께 읽는 파일:

- `calendar_dates.txt`
- `routes.txt`

## registry 연결

[knowledge/open_transport_feed_registry.json](c:/Users/WORK/source/repos/parkcheolhong/codeAI/knowledge/open_transport_feed_registry.json) 에서 국가별 registry 를 사용한다.

- 한국: `OPEN_TRANSPORT_KR_GTFS_URL`
- 일본: `OPEN_TRANSPORT_JP_GTFS_URL`

새 국가를 추가할 때는 같은 형식으로 feed 한 줄만 추가하면 된다.

## 재기동 순서

중요: `.env` 값을 바꾼 뒤 `docker restart` 만 하면 새 환경변수가 반영되지 않을 수 있다. Compose 환경은 컨테이너 recreate 가 필요하다.

운영/로컬 Docker 기준:

```powershell
docker compose up -d --force-recreate backend
```

상태 확인:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/api/health -UseBasicParsing
```

소리새 route grounding 점검:

```powershell
.\.venv\Scripts\python.exe -c "from backend.services.open_transport_registry import list_route_schedule_options; rows=list_route_schedule_options(country_code='KR', origin_query='춘천', destination_query='부산', limit=3); print(rows[0] if rows else 'NO_ROWS')"
```

friend-chat route 질문 점검:

```powershell
$body = '{"transcript":"춘천에서 부산까지 어떻게 가야 돼","tts":false,"language":"ko"}'
Invoke-WebRequest http://127.0.0.1:8000/api/llm/voice/friend-chat -Method POST -ContentType 'application/json' -Body $body -UseBasicParsing
```

## 현재 동작

- GTFS feed URL 이 비어 있으면 소리새는 OSM/Overpass/홍보 레일만 사용하고 시간표는 확정하지 않는다.
- GTFS feed URL 이 유효하면 route grounding 이 출발 정류장/도착 정류장/출발 시각/도착 시각을 읽어 응답에 반영한다.
- 모바일은 `map_context` 로 OpenStreetMap 출발지/목적지 핀 버튼을 함께 보여준다.

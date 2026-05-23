# Migration Checklist (Shinsegye Music System)

Status values:

- `구현됨`: file migration implemented
- `완료됨`: implementation + verification evidence confirmed
- `실패`: blocked or failed

## Checklist

- [x] Music system core files copied into `addons/shinsegye_music_system/src` - `구현됨`
- [x] Standalone service wrapper added (`service_api.py`) - `구현됨`
- [x] Smoke verification entrypoint added (`run_smoke_test.py`) - `구현됨`
- [x] Smoke verification run #1 - `완료됨`
- [x] Smoke verification run #2 - `완료됨`
- [x] Backend marketplace music API router 연결 - `완료됨`
- [x] docker-compose `music-service` 연결 - `완료됨`
- [x] Marketplace UI 음악 생성/작사/협업 패널 추가 - `완료됨`
- [x] Runtime 통합 검증 1차 - `완료됨`
- [x] Runtime 통합 검증 2차 - `완료됨`

## Verification Evidence

- `MUSIC_ROUND1_TITLE Happy Composition`
- `MUSIC_ROUND1_TEMPO 136`
- `MUSIC_ROUND2_SONG 소리새 테마`
- `MUSIC_ROUND2_LYRICS 소리새 테마의 노래`
- `MUSIC_ROUND3_REQUEST 2a348e56`
- `MUSIC_ROUND3_COLLAB c67f8971`
- `MUSIC_ROUND3_REQUEST e864c82e`
- `MUSIC_ROUND3_COLLAB 5a26ca54`
- `SERVICE_HEALTH {'status': 'ok', 'compositions': 0, 'emotion_presets': ['calm', 'energetic', 'happy', 'sad'], 'friend_connections': 0}`
- `MUSIC_SERVICE_HEALTH {'status': 'ok', 'compositions': 0, 'emotion_presets': ['calm', 'energetic', 'happy', 'sad'], 'friend_connections': 0}`
- `MUSIC_SERVICE_COMPOSE {'status': 'ok', 'song_title': '소리새 라이브', 'lyrics_title': '소리새 라이브의 노래', 'composition_title': 'Happy Mood in C', 'mood_track_title': 'Happy Composition', 'tempo': 136, ...}`
- `BACKEND_MUSIC_HEALTH_PRESENT True`
- `BACKEND_MUSIC_COMPOSE_PRESENT True`
- `BACKEND_MUSIC_COMPOSE_STATUS 401`
- `UI_PANEL_VISIBLE_3000 True (🎵 음악 생성·작사·협업 패널)`

## Result

- Final status: `완료됨`
- Scope: standalone addon + backend API + docker-compose service + marketplace UI integration

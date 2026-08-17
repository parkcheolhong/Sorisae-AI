# Shinsegye Music System Migration

This folder contains a migrated subset of the Sorisae music composition system from:

- Repository: `parkcheolhong/run_all_shinsegye.py`
- Source snapshot: local external migration mirror
- Migration date: 2026-04-29

## Included Files

- `src/ai_music_composer.py`
- `src/emotion_based_music_generator.py`
- `src/music_chat_friend_system.py`
- `service_api.py`
- `run_smoke_test.py`
- `requirements.txt`

## Features

- Emotion-based music generation
- AI composition and lyrics generation
- Complete song assembly (composition + lyrics)
- Music chat friend/collaboration workflow

## Quick Run

1. Smoke test:

```bash
python addons/shinsegye_music_system/run_smoke_test.py
```

1. Standalone API service:

```bash
python -m uvicorn addons.shinsegye_music_system.service_api:app --host 0.0.0.0 --port 8012
```

## API Endpoints

```text
GET  /health
POST /compose/emotion
POST /compose/code
POST /friends/demo
```

## Platform Integration (Completed)

- Backend marketplace routes:
  - `POST /api/marketplace/music/compose/emotion`
  - `POST /api/marketplace/music/compose/code`
  - `POST /api/marketplace/music/friends/demo`
  - `GET /api/marketplace/music/health`
- Docker Compose service:
  - service name: `music-service`
  - internal URL: `http://music-service:8012`
  - host URL: `http://127.0.0.1:8012`
- Marketplace UI:
  - page: `/marketplace/code-generator`
  - panel title: `🎵 음악 생성·작사·협업 패널`

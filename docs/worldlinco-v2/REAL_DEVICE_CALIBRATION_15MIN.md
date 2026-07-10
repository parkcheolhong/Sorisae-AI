# WorldLinco Real Device Calibration (10-15 min)

## Goal
- Reduce repeated manual tuning work by running one fixed calibration routine.
- Cover all operational domains in one pass: sorisae, face conversation, voip/incoming, pstn assist, chat.
- Produce deterministic outputs:
  - `.runtime/admin_worldlinco_telemetry.json`
  - `.runtime/worldlinco_tuning_recommendation.json`
  - updated `knowledge/worldlinco_tuning_config.json`

## Prerequisites
- Backend is running and reachable (`http://127.0.0.1:8000`).
- Mobile app is connected to that backend.
- Admin bearer token is available.

## 15-Minute Scenario

### 1) Sorisae (3 min)
- Open sorisae window.
- Execute 6 turns:
  - 3 short utterances (2-4 words).
  - 3 normal utterances (7-15 words).
- Include one noisy environment turn.
- Expected telemetry families:
  - `sorisae_ai.friend_lang_prob`
  - `sorisae_ai.geo_accuracy_m`

### 2) Face Conversation (3 min)
- Open face translation screen.
- Execute 8 turns with alternating language directions.
- Trigger 2 overlap-prone turns (speak right after TTS starts).
- Expected telemetry families:
  - `face_conversation.roundtrip_ms`
  - `face_conversation.playback_ms`
  - `face_conversation.overlap_detected`

### 3) VoIP + Incoming (4 min)
- Run one outgoing VoIP call (at least 2 minutes).
- Run one incoming VoIP accept flow.
- Include 2 barge-in attempts and 1 silence segment.
- Expected telemetry families:
  - `voip.echo_blocked`
  - `voip.fairness_barge_in`
  - `voip.no_speech_prob`
  - `voip.segment_rms`

### 4) PSTN Assist (2 min)
- Run one PSTN assist call flow.
- Make sure subtitles are produced for at least 4 turns.
- Expected telemetry families:
  - `pstn_assist.stt_confidence`
  - `pstn_assist.caption_len`

### 5) Chat (2-3 min)
- Run 6 message exchanges.
- Include one long answer and one multi-chunk response.
- Expected telemetry families:
  - `chat.message_latency_ms`
  - `chat.stream_chunk_ms`

## Calibration Commands

### A. End-to-end single command
```powershell
python scripts/run_worldlinco_calibration_pipeline.py --api-base http://127.0.0.1:8000 --token <ADMIN_BEARER_TOKEN>
```

### A-1. End-to-end + priority checklist CSV
```powershell
python scripts/run_worldlinco_calibration_pipeline.py --api-base http://127.0.0.1:8000 --token <ADMIN_BEARER_TOKEN> --emit-priority-csv
```

Custom CSV path:
```powershell
python scripts/run_worldlinco_calibration_pipeline.py --api-base http://127.0.0.1:8000 --token <ADMIN_BEARER_TOKEN> --emit-priority-csv --priority-csv-file .runtime/worldlinco_priority_checklist.csv
```

### B. Step-by-step
```powershell
python scripts/collect_worldlinco_telemetry.py --api-base http://127.0.0.1:8000 --token <ADMIN_BEARER_TOKEN>
python scripts/calibrate_worldlinco_tuning_from_telemetry.py --telemetry-file .runtime/admin_worldlinco_telemetry.json --output-file .runtime/worldlinco_tuning_recommendation.json --stdout
python scripts/apply_worldlinco_tuning_recommendation.py --recommendation-file .runtime/worldlinco_tuning_recommendation.json --tuning-file knowledge/worldlinco_tuning_config.json --updated-by auto-calibrator
```

## Acceptance Rules
- `meta.confidence` should be `medium` or `high`.
- `meta.warnings` should not include sample shortage messages.
- A backup file must be created under `.runtime/backups` before tuning update.
- `sample_coverage.all_features_satisfied` should be `true`.

## Auto Sample Sufficiency Output
- The pipeline now prints a per-feature sample check for:
  - 소리새
  - 대면
  - VoIP
  - PSTN
  - 채팅
- If a feature is `LOW`, console output includes exactly how many more samples are needed per metric.
- The same report is saved under `sample_coverage` in:
  - `.runtime/worldlinco_tuning_recommendation.json`

## Auto Test Priority Plan
- The pipeline also generates `test_priority_plan` automatically.
- It sorts features by shortage size and prints:
  - which feature to test first
  - which metric each test targets
  - how many additional runs are recommended (`run xN`)
- Output is visible in console and persisted to:
  - `.runtime/worldlinco_tuning_recommendation.json`
- If `--emit-priority-csv` is used, checklist CSV is also written to:
  - `.runtime/worldlinco_test_priority_plan.csv` (default)

## Notes
- Zero-error absolute tuning does not exist in live audio systems; quantile-based robust ranges are the practical optimum.
- If confidence remains low, increase sample count for the warning domain only and rerun the same pipeline.

# WorldLinco 50개국어 백엔드 정합 점검

> **일시:** 2026-06-15  
> **증적:** `50lang_audit_20260615-235805/`  
> **스크립트:** `scripts/worldlinco_50lang_alignment_audit.ps1`

## 결과 요약

| 항목 | 결과 |
|------|------|
| 모바일 `App.tsx` LANGS | **50** 코드 |
| 로컬 `SUPPORTED_LANGUAGES` | **50** — mobile과 **100% 일치** |
| 원격 `GET /api/llm/translate/languages` | **50** (백엔드 재시작 후) |
| ko→ja `POST /api/llm/voice-translate` | **PASS** — `こんにちは。嬉しいです。` |
| ja→ko `POST /api/llm/voice-translate` | **PASS** — `안녕하세요. 잘 부탁드립니다.` |

## 변경 사항

- `backend/services/nadotongryoksa/translator.py` — 26개 → **50개** 언어 확장 (모바일 LANGS 동기화)
- ko↔ja 여행 필수 문장 사전 추가
- `backend/tests/test_supported_languages_50.py` — 3 tests PASS
- `devanalysis114-backend` 컨테이너 **restart** (볼륨 마운트 `./backend` 반영)

## ko↔ja VoIP 실기기 스모크

| 항목 | 결과 |
|------|------|
| API (transcript) | **PASS** — 위 표 |
| VoIP E2E (Tab↔S10) | **자동화 미완** — build 67 validation deeplink 1회 소비 + auth 대기 후 `call_id` 미검출 |

**수동 재시도:** 앱 force-stop → 로그인 → 친구 보이스톡 → S10 일본어 6초 → Tab `VOIP_VOICE_RELAY_PLAYBACK` 확인.

증적 시도: `ko_ja_smoke_20260615-234824/`, `ko_ja_smoke_20260615-235900/`, `ko_ja_smoke_20260616-000300/`

## ko↔en VoIP (참고 — 당일 세션)

- `e3-2_echo_20260615-232900/` — S10 `"안녕하세요. 반갑습니다."` → Tab `"hello. Nice to meet you."` **PLAYBACK** · repetition **0**

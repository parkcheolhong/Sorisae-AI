# WorldLinco build 90–92 출시 체크리스트

> **최종 갱신:** 2026-06-17  
> **운영 APK:** `v1.0.62` / **versionCode 92**  
> **기술서:** `TECHNICAL_REPORT_VOIP_ORCHESTRATOR.md` §0.16  
> **감사 스크립트:** `scripts/audit_voip_language_coverage.py`

표시: `[ ]` 미착수 · `[~]` 부분 완료 · `[x]` 완료

---

## 1. build 90 — 친구 UI · 지정 언어 정합성

| ID | 항목 | 상태 | 검증 |
|----|------|------|------|
| B90-1 | 친구 목록 아코디언 (기본 접힘) | [x] | `FriendFolderScreen.tsx` |
| B90-2 | 계정/친구추가 패널 ~30% 축소 + FlatList 스크롤 | [x] | build 90 APK |
| B90-3 | VoIP/채팅 **프로필 지정 언어** 강제 (`designated_language.py`) | [x] | `test_designated_language.py` 4/4 |
| B90-4 | 채팅 POST 422 · VoIP WS `chat_message_rejected` | [x] | `nadotongryoksa_chat_router.py` |
| B90-5 | VoIP STT detected ≠ preferred → 거부 | [x] | `router.py` designated gate |
| B90-6 | APK marketplace publish build **90** | [x] | `v1.0.60` manifest |

---

## 2. build 91 — 50개국 VoIP STT/TTS 패리티

| ID | 항목 | 상태 | 검증 |
|----|------|------|------|
| B91-1 | SSOT `backend/voip_language_locales.py` (50 locale) | [x] | MOBILE_TTS + EDGE_TTS + whisper hint |
| B91-2 | 모바일 `voipLanguageLocales.ts` 50/50 | [x] | audit script |
| B91-3 | 서버 TTS `resolve_edge_tts_voice(target_lang)` | [x] | `voice_gateway.py` |
| B91-4 | 모바일 `resolveVoipTtsLocale()` 50개국 | [x] | `VoIPCallScreen.tsx` |
| B91-5 | 단위 테스트 | [x] | `test_voip_language_locales.py` |
| B91-6 | APK marketplace publish build **91** | [x] | `v1.0.61` manifest |

**감사 명령:**

```powershell
python scripts/audit_voip_language_coverage.py
# 기대: STT/TTS 50-country coverage: OK
```

---

## 3. build 92 — 여행 대면 통역 (양방향 자동)

| ID | 항목 | 상태 | 검증 |
|----|------|------|------|
| B92-1 | **대화 통역 ON/OFF** 토글 (수동 마이크 없음) | [x] | `App.tsx` `worldlinco-face-conversation-toggle` |
| B92-2 | 내 언어 = 프로필 `preferred_language` (읽기 전용) | [x] | profile sync useEffect |
| B92-3 | 상대 언어 = GPS 우선 + 수동 override | [x] | `handleDetectLangByGPS` |
| B92-4 | 백엔드 `bilingual_mode` + A↔B 라우팅 | [x] | `router.py` `_resolve_bilingual_route` |
| B92-5 | 연속 녹음 루프 (auto restart) | [x] | `autoVoiceModeEnabled` |
| B92-6 | APK marketplace publish build **92** | [x] | `v1.0.62` manifest |
| B92-7 | **실기기 대면 통역** ko↔ja / ko↔en smoke | [ ] | Tab/S10 수동 검증 |

**API 계약 (`POST /api/llm/voice-translate`):**

```json
{
  "bilingual_mode": true,
  "lang_a": "ko",
  "lang_b": "ja",
  "from_lang": "ko",
  "to_lang": "ja",
  "language": "auto",
  "audio_base64": "..."
}
```

**응답:** `from` / `to` / `detected_language` / `translated` — 감지 언어에 따라 A→B 또는 B→A.

---

## 4. 백엔드 배포 · 테스트

| ID | 항목 | 상태 | 명령 |
|----|------|------|------|
| DEP-1 | backend 컨테이너 rebuild + restart | [x] | `docker compose build backend && docker compose up -d backend` |
| DEP-2 | designated language tests | [x] | `pytest backend/tests/test_designated_language.py` |
| DEP-3 | voip locale tests | [x] | `pytest backend/tests/test_voip_language_locales.py` |
| DEP-4 | voice-translate STT/bilingual tests | [x] | `pytest backend/tests/test_voice_translate_stt.py` |
| DEP-5 | health check | [x] | `GET /api/v1/voip/health` → `status: ok` |

---

## 5. Git · PR

| ID | 항목 | 상태 |
|----|------|------|
| GIT-1 | feature branch push | [x] |
| GIT-2 | PR → `main` | [x] [#90](https://github.com/parkcheolhong/Sorisae-AI/pull/90) |
| GIT-3 | 기술서 §0.16 갱신 | [x] |

---

## 6. 실기기 후속 (v1.0.62)

- [ ] 여행 홈 → **대화 통역 ON** → 한국어/상대언어 번갈아 발화 → TTS 확인
- [ ] VoIP 통화: 지정 언어만 relay (다른 언어 STT 거부)
- [ ] 채팅: 지정 언어 외 메시지 422
- [ ] 친구 목록 스크롤·아코디언 UX
- [ ] marketplace APK 다운로드 → build 92 설치 확인

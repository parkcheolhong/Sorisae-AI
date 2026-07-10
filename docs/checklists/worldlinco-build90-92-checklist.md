# WorldLinco build 90–92 출시 체크리스트

> **최종 갱신:** 2026-06-27  
> **운영 APK:** `v1.0.62` / **versionCode 92**  
> **기술서:** `TECHNICAL_REPORT_VOIP_ORCHESTRATOR.md` §0.16  
> **감사 스크립트:** `scripts/audit_voip_language_coverage.py`

표시: `[ ]` 미착수 · `[~]` 부분 완료 · `[x]` 완료

---

## 0. 2026-06-27 재검증 스냅샷

- [x] 백엔드 회귀 테스트 재검증
  - 근거: `.venv\\Scripts\\python.exe -m pytest backend/tests/test_designated_language.py backend/tests/test_voip_language_locales.py backend/tests/test_voice_translate_stt.py -q`
  - 결과: `32 passed in 21.00s`
- [~] 운영 APK manifest 재검증
  - 근거: `GET /api/marketplace/apk/worldlinco/manifest` 재조회 (2026-06-27)
  - 결과: `versionName=1.0.199`, `versionCode=251`, `downloadPath=/api/marketplace/apk/nadotongryoksa-v1.apk`
  - 판정: 본 문서의 build 90~92 출시 스냅샷과 **현재 운영 manifest 버전이 불일치**. 실기기 검증은 최신 운영 버전 기준으로 별도 체크리스트 분기 필요.
- [x] VoIP health 재검증
  - 근거: `GET /api/v1/voip/health`
  - 결과: `status: ok`
- [~] ADB 실기기 연결/버전 검증
  - 근거: `adb devices -l` (2026-06-27)
  - 결과: `R83W70QY11H`, `172.30.1.19:5555` 포함 다중 기기 `device` 상태
  - 근거: `adb -s <device> shell dumpsys package com.parkcheolhong.worldlinco`
  - 결과: 실기기 3대 모두 `versionName=1.0.202`, `versionCode=254` 설치 확인

### 0.1 실기기 VoIP 자동검증 실행 기록 (2026-06-27)

- [~] 1차 실행: `scripts/build89_bg_voip_test.ps1`
  - 증적: `evidence/build89_bg_voip_20260627-192201/summary.json`
  - 결과: `callee_presence=true` / `caller_call_started=false` / `alert_started=false`
- [~] 2차 실행(voice_id 보정): `scripts/build89_bg_voip_test.ps1 -CalleeVoiceId nado-000226`
  - 증적: `evidence/build89_bg_voip_20260627-193008/summary.json`
  - 결과: `callee_presence=true` / `caller_call_started=false` / `alert_started=false`
- [~] 3차 실행(코드 수정 후 재검증): `scripts/build89_bg_voip_test.ps1 -CalleeVoiceId nado-000226`
  - 증적: `evidence/build89_bg_voip_20260627-194123/summary.json`
  - 결과: `callee_presence=false` / `caller_call_started=false` / `alert_started=false`
- [x] S10 런타임 식별 확인
  - 근거: `worldlingo://voip/open?action=validation` 딥링크 후 logcat
  - 결과: `VOIP_PRESENCE_CONNECTED`, `voice_id=nado-000226`, `token_ready=true`, `user_ready=true`
- [ ] 판정
  - 실기기 연결/앱 실행은 가능하나, 자동 발신 검증 경로에서 `caller_call_started`가 3회 연속 false.
  - 3차에서는 `callee_presence`도 false로 하락해, 발신 이전 단계(상대 단말 실시간 세션/Presence)부터 재추적이 필요함.
  - 따라서 섹션 6 항목은 완료 처리 금지(추가 원인 추적 필요).

### 0.2 온디바이스 KWS/배포 산출물 재검증 (2026-06-27)

- [x] 짧은 경로 우회(`subst W:`) + 실기기 디버그 설치
  - 근거: `subst W: "c:\Users\WORK\source\repos\parkcheolhong\codeAI"`
  - 근거: `ANDROID_SERIAL=R83W70QY11H ; W:\apps\mobile-nadotongryoksa\android ; .\gradlew.bat :app:installDebug`
  - 결과: `Installed on 1 device (SM-T225N - 14)`
- [~] 온디바이스 KWS wake 실측 스크립트
  - 근거: `ANDROID_SERIAL=R83W70QY11H ; W:\apps\mobile-nadotongryoksa ; powershell -NoProfile -File .\scripts\verify_on_device_kws.ps1 -LaunchApp -DurationSec 120`
  - 결과: `No KWS markers found` (3회 반복 동일)
  - 판정: 로그 캡처는 정상이나 `native_started/native_wake/native_error/scan_idle` 미검출로 실측 통과 불가
- [x] 마켓 업로드용 AAB 생성
  - 근거: `W:\apps\mobile-nadotongryoksa\android ; .\gradlew.bat :app:bundleRelease`
  - 결과: `BUILD SUCCESSFUL`
  - 산출물: `W:\apps\mobile-nadotongryoksa\android\app\build\outputs\bundle\release\app-release.aab`
  - SHA256: `610F021C71E68E7E79125C5E456A19F8DE0023D121AB5A9576DC1789FD860971`
  - 크기: `47,298,180 bytes`
- [~] Play Console 내부 테스트 트랙 업로드 명령 실행
  - 근거: `npx eas submit --platform android --profile production --path W:\...\app-release.aab --non-interactive`
  - 결과: `Uploaded to EAS Submit` 후 Windows 경로 해석 오류(`path.relative`)
  - 근거: `npx eas-cli@latest submit --platform android --profile production --path android/app/build/outputs/bundle/release/app-release.aab --non-interactive`
  - 결과: `Google Service Account Keys cannot be set up in --non-interactive mode`
  - 판정: AAB 업로드 준비물은 완성됐으나, Play Service Account Key 설정 1회가 대화형으로 필요해 자동 완료 차단

### 0.3 LLM Gateway 무중단 복구 + 여행 근거리 안내 실검증 (2026-07-06)

- [x] 백엔드 이미지 장시간 빌드 완주(영속)
  - 근거: `docker compose build backend`
  - 결과: `Image devanalysis114-backend Built` (521~573s 구간 완주 로그 확인)
- [x] 이미지 레벨 Docker CLI 영속 검증
  - 근거: `docker compose up -d backend ; docker exec devanalysis114-backend sh -lc "command -v docker && docker version --format '{{.Server.Version}}'"`
  - 결과: `/usr/bin/docker`, `29.6.1`
- [x] `llm-nginx` 네트워크 재부착 자동복구 범위 확장 + 실검증 2회
  - 근거(1회차): `POST /api/admin/llm-gateway/auto-recover` 응답 `actions`에
    - `recreate_gateway_without_host_ports` 성공
    - `reattach_gateway_network` 성공(`conflict_recreated=true`, `networks_after=[gpu-llm-server_llm-network]`)
  - 근거(2회차): 동일 API 재실행 후 요약
    - `reattach_ok=true`, `gateway_network_attached=true`, `gateway_network_names=gpu-llm-server_llm-network`
- [x] 소리새 여행 근거리 안내(GPS+nearby) 실검증 2회
  - 근거(1회차): `POST /api/llm/voice/friend-chat` (ko/en, latitude/longitude/accuracy_m 포함) 성공
  - 근거(2회차): 동일 경로 재실행 성공
    - 결과: `ko_len=383`, `ko_trip_session=sorisae-42d95bcab59842cb`
    - 결과: `en_len=586`, `en_trip_session=sorisae-6c1cd1e9cdc24f00`
- [x] 전세계 여행 파트너 소스 확장 코드 반영(옵션형)
  - 근거: `backend/llm/voice_gateway.py`에 Wikivoyage/Amadeus/Tripadvisor grounding 함수 추가
  - 결과: 키 미설정 환경에서는 자동 스킵(기존 OSM/Overpass/Index 경로 유지), 키 설정 시 GPS 근거리 보강 가능
- [x] FLOW-ADM-DASH 실 UI 클릭 검증(최종)
  - 근거(1회차): `http://127.0.0.1:3005/admin` 로그인 후 상단 `관리자 대시보드 새로고침(🔄)` 클릭
  - 근거(2회차): 좌측 `🧭 설정` 패널 오픈 후 `설정 새로고침` 클릭 + 동일 세션 대시보드 새로고침 재실행
  - 결과: UI 스냅샷/이벤트 로그에서 `전역 설정 조회 실패(502)` 및 `FLOW-ADM-DASH` 오류 미재현
- [x] FLOW-ADM-DASH 원클릭 회귀 스크립트 고정
  - 근거: `frontend/frontend/tests/admin-flow-adm-dash-regression.playwright.spec.ts` 추가
  - 근거: `scripts/verify_flow_adm_dash_playwright_once.ps1` 추가 + 루트 `npm run verify:flow-adm-dash` 연결
  - 결과: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify_flow_adm_dash_playwright_once.ps1` 실행 `2 passed`

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
| B92-7 | **실기기 대면 통역** ko↔ja / ko↔en smoke | [~] | Tab/S10 수동 검증 |

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

- 현재 차단 항목: B92-7 실기기 대면 통역 smoke
  - 차단 사유: 현재 환경에서는 지정된 ko↔ja / ko↔en 조합의 안정적인 실기기 재현이 아직 확인되지 않았고, 기존 로그상으로는 번역-재생-재입력 루프와 권한/재시작 경로가 혼재해 있다.
  - 처리 원칙: 이 항목은 `미완료`로 명시하고, 추가 코드 수정보다 다음 실기기 검증 준비 항목부터 진행한다.

- [ ] 여행 홈 → **대화 통역 ON** → 한국어/상대언어 번갈아 발화 → TTS 확인
- [ ] 온디바이스 KWS: `native_started -> native_wake` 실측 로그 확보
  - 현재 상태(2026-06-27): 스크립트 3회 반복 결과 `No KWS markers found`
- [ ] VoIP 통화: 지정 언어만 relay (다른 언어 STT 거부)
- [ ] 채팅: 지정 언어 외 메시지 422
- [ ] 친구 목록 스크롤·아코디언 UX
- [ ] marketplace APK 다운로드 → build 92 설치 확인
  - 선행 근거(로컬): `downloadPath=/api/marketplace/apk/nadotongryoksa-v1.apk`, 로컬 파일 존재(`uploads/marketplace_local/apk/nadotongryoksa-v1.apk`, 69176543 bytes)
  - 차단 사유: 현재 환경에서는 Android 실기기 설치/실행 검증 불가

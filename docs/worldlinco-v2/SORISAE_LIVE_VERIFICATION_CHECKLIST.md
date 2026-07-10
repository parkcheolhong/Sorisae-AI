# 소리새(Sorisae) 실기 검증 체크리스트 — Phase C

> **고정 기준선:** APK build **296** (`v1.0.233`) · `knowledge/worldlinco_section_freeze.json`  
> **마감 리포트:** `evidence/sorisae-phase-c-close-20260702-112232/phase_c_close.json`  
> **오디오·세션:** `docs/worldlinco-v2/AUDIO_SECTION_SSOT.md`

---

## 마감 요약 (2026-07-02)

| 구분 | 수 | 상태 |
|------|-----|------|
| **자동·ADB·pytest 닫힘** | **17** | ✅ PASS |
| **수동만 남음** | **14** | 사용자 1회 확인 (아래 표 🔶) |
| **실패** | **0** | — |

**한 줄 실행 (재검증):**

```powershell
python scripts/run_sorisae_friend_chat_probe.py --base-url https://metanova1004.com --adb-device R83W70QY11H
python scripts/close_sorisae_phase_c_checklist.py --adb-device R83W70QY11H
make sorisae-gate
```

### 최신 번들 반영 30초 확인 (2026-07-03 추가)

> **목적:** 같은 `versionName`/`versionCode` 라도 JS bundle stale 상태를 즉시 판별한다.

```powershell
adb -s R83W70QY11H logcat -c
adb -s R83W70QY11H shell am force-stop com.parkcheolhong.worldlinco
adb -s R83W70QY11H shell am start -n com.parkcheolhong.worldlinco/com.parkcheolhong.worldlinco.MainActivity
adb -s R83W70QY11H logcat -d -v time ReactNativeJS:V OnDeviceKws:V *:S |
  Select-String -Pattern 'home_auto_arm_config|COMPANION_VOICE_CALL|WORLDLINGCO_TUNING'
```

**PASS:** `home_auto_arm_config` + `runtime_enabled:true` + 로그인 후 `armable_eval ... auto_arm:true`  
**FAIL:** `home_auto_arm_config` 없음, 또는 `armable_eval ... auto_arm:false` 반복

### 2026-07-03 소리새 홈 질문 안정화 실측

- 대상 단말: `SM_T225N` (`R83W70QY11H`)
- 설치 상태: `versionName=1.0.236`, `versionCode=299`
- 런타임 튜닝: `WORLDLINGCO_TUNING remote_loaded updated_at=2026-07-02T14:00:00Z`
- 소리새 홈 질문 이벤트:

```text
FACE_CONVERSATION meter_unavailable
→ file_growth_speech
→ vad_flush/vad_end reason=max_duration
→ silero_native_capture duration_ms≈9280~9420
→ segment_response ok=true route="sorisae" stt_trust="high"
```

- 판정: 긴 질문 중간 절단은 재현되지 않았고, 현재 단말은 `max_duration` 종료가 우세하다.
- 미해결: 홈 auto-arm 은 같은 로그 구간에서 여전히 `auto_arm:false` 였고 `home_auto_arm_config` 는 관측되지 않았다. 최신 JS bundle 재반영 후 재검증 필요.

### 2026-07-03 최신 번들 재반영 확인 결과

- 대상 단말 `SM_T225N` (`R83W70QY11H`) 에 최신 release APK 재설치 성공
- 설치 반영: `lastUpdateTime=2026-07-03 01:10:32`
- fresh startup log:

```text
COMPANION_VOICE_CALL home_auto_arm_config runtime_enabled:true source_flag:true platform:android
COMPANION_VOICE_CALL armable_eval armable:true auto_arm:true has_user:true armed:true
```

- 판정: 홈 자동 음성 호출 대기 최신 번들 반영 확인 완료. 이후 VoIP 품질 튜닝으로 진행 가능.

---

## 사전 조건

- [x] 백엔드 `:8000` health — probe `health` 200
- [x] vLLM `:8009` + STT/TTS — `friend_chat_model_route` Qwen3-8B-AWQ
- [x] 테스트 계정 로그인 — probe log `user_id=226`, `has_user=true`
- [x] APK build **296** — SM-T225N ADB
- [x] 마이크 권한 — `RECORD_AUDIO: granted=true`
- [ ] 🔶 (선택) Vosk/Porcupine KWS — 미설정 시 C섹션만 수동

---

## A. FAB · 전용 창

| # | 시나리오 | Pass | 근거 |
|---|----------|------|------|
| A1 | 로그인 후 FAB 표시 | ✅ | probe FAB tap + ADB UI |
| A2 | FAB 드래그 | 🔶 | **수동** — 제스처 |
| A3 | FAB 탭 → 창 오픈 | ✅ | `adb_sorisae_runtime` `sorisae_window_open:true` |
| A4 | 대면 모달 시 FAB 숨김 | 🔶 | **수동** |
| A5 | VoIP 통화 중 FAB 숨김 | 🔶 | **수동** |
| A6 | 설정 FAB OFF | 🔶 | **수동** |
| A7 | 창 ✕ 닫기 → FAB 복귀 | 🔶 | **수동** (닫기 UX; 오디오 quiesce는 코드 고정) |

---

## B. 음성 대화 (friend-chat)

| # | 시나리오 | Pass | 근거 |
|---|----------|------|------|
| B1 | 마이크 arm / 상태 문구 | ✅ | `adb_sorisae_runtime` capture 경로 |
| B2 | 한국어 1턴 + Edge TTS, 끊김 없음 | ✅ | `segment_200=True`, cap 50s freeze |
| B3 | 창 닫힘 → friend-chat 미호출 | 🔶 | **수동** (라우팅 회귀 lock만 자동) |
| B4 | 창 열림 → friend-chat | ✅ | `route":"sorisae"` segment 200 |
| B5 | TTS 후 echo 루프 없음 | ✅ | `tight_preupload_loop=False` + `sorisaeEcho.test` |
| B6 | 5xx/타임아웃 graceful | ✅ | pytest gate + silent 422 probe |
| B7 | DB `conversation_turns` 2쌍 | ✅ | `test_friend_chat_trip_session` |

---

## C. 웨이크워드

| # | 시나리오 | Pass |
|---|----------|------|
| C1 | dormant KWS 무장 | 🔶 수동 |
| C2 | AI 이름 호출 → 창 오픈 | 🔶 수동 |
| C3 | 3분 무활동 dormant | 🔶 수동 |
| C4 | 창 닫기 후 재웨이크 없음 | 🔶 수동 |

---

## D. WS 딥링크 · 정산

| # | 시나리오 | Pass | 근거 |
|---|----------|------|------|
| D1 | `worldlingo://sales?code=WS…` | ✅ | `test_worldlinco_sales_commission` |
| D2 | `worldlingo://invite?code=WL…` | ✅ | `test_worldlinco_referral_discount` |
| D3 | Admin 영업 정산 패널 UI | 🔶 | **수동** (브라우저) |
| D4 | 결제 confirm → ledger | ✅ | `test_worldlinco_phase_a` / local_revenue |

---

## E. 회귀 (VoIP · 대면 · 청구)

> VoIP 품질은 **소리새 창 닫은 뒤** 별도 통화로만 검증 (1기기·1세션).

| # | 시나리오 | Pass | 근거 |
|---|----------|------|------|
| E1 | VoIP 발신/수신 세션 격리 | 🔶 | **수동** 2단말 통화 |
| E2 | 대면 통역 마이크 분리 | 🔶 | **수동** |
| E3 | billing `free_access_policy` | ✅ | `test_worldlinco_billing_policy` |

---

## 수동 14항 — 닫는 순서 (권장 10분)

1. **A7** 창 닫기 → FAB 다시 보이는지  
2. **B3** 창 닫고 대면 통역만 (friend-chat 로그 없음)  
3. **A4/A5** 대면·VoIP 시 FAB 숨김  
4. **E1** 소리새 닫은 뒤 VoIP 1통화 (아침 튜닝선)  
5. **C2** (KWS 설정 시) 이름 호출 1회  

---

## 실패 시 수집

```powershell
adb -s R83W70QY11H logcat -d -v time -s ReactNativeJS:* | Select-String "segment_response|FACE_TTS|sorisae|VOICE_LEASE"
```

증적 폴더: `evidence/sorisae-friend-chat-probe-20260702-111446/`

---

## 관련 코드·게이트

| 항목 | 경로 |
|------|------|
| 마감 스크립트 | `scripts/close_sorisae_phase_c_checklist.py` |
| 프로브 | `scripts/run_sorisae_friend_chat_probe.py` |
| SSOT lock | `scripts/check_worldlinco_section_ssot_lock.py` |
| freeze | `knowledge/worldlinco_section_freeze.json` |

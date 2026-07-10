# 기능 분리 오디오 격리 정밀 감사 (2026-07-09)

**범위:** VoIP / 채팅 / 대면통역 / 일반통화(PSTN) 분리 작업 회귀  
**기준 빌드:** 316 (1.0.241) — UI 312식 복원 후 오디오 세션 격리 미완  
**상태:** CRITICAL 1~3 + HIGH 7.4~7.5 패치 완료 — 디바이스 검증 대기  
**연계:** [`feature-separation-checklist.md`](./feature-separation-checklist.md) Phase 7

---

## 감사 요약

| 영역 | 상태 |
|------|------|
| 레일 UI (채팅/통화/홍보/예약) | `sectionRegistry` SSOT 정상 |
| 오디오 격리 (핵심) | **C1~C3 패치 완료** — 디바이스 검증 대기 |
| 음성 캡처 SSOT | **7.4 완료** — `useAppVoiceCaptureLoop` 브리지 |
| song-mode 레지스트리 | **7.5 완료** — `tabVisible:false` (탭 미노출) |
| 단위 테스트 | 커널/레지스트리 PASS, App 통합 테스트 없음 |

---

## CRITICAL 이슈

### C1. `voipSessionGuard` 미연결
- **파일:** `src/services/voipSessionGuard.ts`, `App.tsx`
- **증상:** VoIP 통화 중 대면 TTS·소리새·마이크가 겹침
- **원인:** `registerVoipSessionProbe` / `quiesceNonVoipAudioForVoipSession` 호출처 0
- **패치:** probe 등록 + 모든 VoIP 진입/종료 경로 연결

### C2. VoIP 진입 quiesce 경로 불일치
- **파일:** `App.tsx` — `handleStartFriendVoiceCall`만 정리, `handleStartVoipCall`·수신 수락 없음
- **패치:** `prepareForVoipSession(reason)` 공통화

### C3. PSTN `fourFeatureRuntime` lease 비대칭
- **파일:** `usePstnAssistController.ts`, `handleRegularCallContact`, `handleInterCallToggle`
- **증상:** 일반전화 후 다른 기능 차단 / 대면 캡처와 PSTN 동시 점유
- **패치:** 발신 전 `prepareForPstnDial` + 종료 시 `deactivateFeatureExclusive('pstn-assist')`

---

## HIGH (후속)

| ID | 이슈 | 상태 |
|----|------|------|
| H1 | App.tsx ↔ `useVoiceCaptureLoop` 드리프트 | **완료** — `useAppVoiceCaptureLoop` SSOT 브리지 |
| H2 | `song-mode` 레지스트리 고아 | **완료** — `sectionRegistry` + `tabVisible:false` |
| H3 | 일반전화 진입점 3갈래 (legacy chooser / phone dialer) | 미완 |
| H4 | 레일 전환 시 PSTN 플래그 잔존 | 부분 완료 (C3) |

---

## Phase 7 체크리스트 — 오디오 격리 CRITICAL

### C1 VoIP 세션 가드
- [x] `registerVoipSessionProbe` — `voipCallInitResponse` \| pending incoming
- [x] `quiesceNonVoipAudioForVoipSession` — VoIP 발신/수신 수락 전
- [x] `clearVoipAudioSession` — hangup / dialer 복귀 / tester 닫기

### C2 `prepareForVoipSession` SSOT
- [x] `handleStartFriendVoiceCall` → 공통 helper
- [x] `handleStartVoipCall` → 공통 helper
- [x] `activateAcceptedIncomingVoipCall` → 공통 helper

### C3 PSTN lifecycle
- [x] `prepareForPstnDial` — `handleRegularCallContact` / `handleInterCallToggle` 발신 전
- [x] `deactivateFeatureExclusive('pstn-assist')` — inter-call 종료·다이얼 실패
- [x] `clearActiveAudioEngine('inter_call')` — PSTN 종료 시

### 검증 (디바이스)
- [x] 홈 대면 통역(대화) TTS — build317 확인
- [ ] 대면 ON → VoIP 친구 발신: 마이크/TTS 즉시 정지
- [ ] 대면 ON → 연락처 일반전화: 앱 캡처 정지 후 시스템 다이얼
- [ ] 일반전화 종료 후 VoIP/대면 재시작 차단 없음
- [ ] 수신 VoIP 수락 시 에코 없음
- [ ] **회귀(317):** 통화 탭 VoIP 친구 섹션 + 발신 실패 메시지 표시 — 패치 후 재검증

---

## 아키텍처 (격리 계층)

```
레일 UI (sectionRegistry)
    ↓
voiceCaptureLease (face/sorisae/inter_call/song)
    ↓
voipSessionGuard (VoIP WebRTC — lease 밖)  ← C1 패치
    ↓
fourFeatureRuntime (pstn-assist exclusive)  ← C3 패치
```

---

*작성: 2026-07-09 · build316 감사 후 CRITICAL 1~3 + HIGH 7.4~7.5 패치.*

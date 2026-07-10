# WorldLinco v1.0.41 (build 66) — 출시 직전 상태

> **갱신:** 2026-06-15  
> **마스터 기술서:** `TECHNICAL_REPORT_VOIP_ORCHESTRATOR.md`  
> **체크리스트:** `ORCHESTRATOR_WORLDLINCO_ANALYSIS_CHECKLIST.md` PART E

---

## APK

| 항목 | 값 |
|------|-----|
| versionName | 1.0.41 |
| versionCode | 66 |
| package | `com.parkcheolhong.worldlinco` |
| 파일 | `uploads/marketplace_local/apk/nadotongryoksa-v1.0.41-build66-current.apk` |
| 빌드 | `pwsh -File scripts/publish_worldlinco_apk.ps1` (`GRADLE_USER_HOME=C:\gradle-cache`) |

**설치 확인:** Tab `R83W70QY11H`, S10 `172.30.1.19:5555` — versionCode **66**

---

## PART E DoD

| ID | 항목 | 상태 |
|----|------|------|
| E-3-1 | WiFi 2대 10통 중 8통 | **[x]** 누적 8/10 (run C) + build66 **5/5** |
| E-3-2 | repetition_hallucination echo | **[~]** 단위 15/15 · echo 수동 미관측 |
| E-3-3 | 베타 페이지 | **[x]** |
| E-3-4 | 실사용 10명 | **[ ]** → `E3-4_beta_users.csv` |
| E-3-5 | v1.0.41 APK 재현 | **[~]** build66 빌드·설치 완료 · git tag 미정 |

---

## build 66 핵심 수정

1. **자기 발신 차단** — validation deeplink `callee_voice_id === own voice id` 거부  
2. **중복 발신 차단** — `autoCallVoiceId` Modal 단일 경로 + 8초 디듀프  
3. **S10 수락** — `worldlingo://voip/incoming` deeplink auto-accept + Tab `call_id` 매칭  
4. **stale call** — lightweight pre-call hangup + (가능 시) API `/calls/{id}/end`

---

## E-3-1 증적 (build 66)

- Run: `e3_verify_20260615-212949`
- Result: **5/5 PASS** (connected, signaling, initiate)
- Artifacts: `summary.json`, `round_*_*.log`, `E3_REPORT.md`

---

## 다음 스텝 (우선순위)

1. **E-3-2** — Tab 스피커 ON + S10 TTS echo → logcat `repetition_hallucination`  
2. **E-3-4** — 지인 10명 WiFi 통화 1회 이상 → CSV 기록  
3. **E-3-5** — git tag `v1.0.41` + marketplace latest APK 동기화

### E-3-2 명령

```powershell
pwsh -File scripts\voip_manual_call_setup.ps1 -MonitorSec 60
# 통화 connected 후 S10 한국어 1문장 → Tab TTS 스피커 ON
adb -s R83W70QY11H logcat -v time -s ReactNativeJS:* |
  Select-String 'repetition_hallucination|PLAYBACK_SKIPPED'
```

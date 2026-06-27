# WorldLinco v1.0.42 (build 67) — 상태

> **갱신:** 2026-06-15  
> **마스터 기술서:** `TECHNICAL_REPORT_VOIP_ORCHESTRATOR.md`  
> **50언어 정합:** `50LANG_ALIGNMENT_REPORT.md`

---

## APK

| 항목 | 값 |
|------|-----|
| versionName | 1.0.42 |
| versionCode | 67 |
| package | `com.parkcheolhong.worldlinco` |
| 파일 | `uploads/marketplace_local/apk/nadotongryoksa-v1.0.42-build67-current.apk` |

**설치:** Tab `R83W70QY11H`, S10 `172.30.1.19:5555` — versionCode **67**

---

## build 67 핵심 수정

1. **친구 목록 갇힘** — validation deeplink `consumedAppEntryDeepLinkUrlRef` 1회 소비 · 통화 중 friend folder 미재오픈  
2. **✕ 닫기** — `handleCloseFriendFolder` + 통화 중 VoIP 레일 복귀  
3. **백엔드 50언어** — `translator.py` `SUPPORTED_LANGUAGES` 50개 (모바일 LANGS 동기화)

---

## PART E DoD (build 67 기준)

| ID | 항목 | 상태 |
|----|------|------|
| E-3-1 | WiFi 2대 8/10 | **[x]** |
| E-3-2 | echo / repetition | **[x]** ko↔en relay PASS (`e3-2_echo_20260615-232900`) · repetition 0 |
| E-3-3 | 베타 페이지 | **[x]** |
| E-3-4 | 실사용 10명 | **[ ]** |
| E-3-5 | APK 재현 | **[~]** build 67 설치 · tag 미정 |
| **E-3-6** | **50언어 백엔드 정합** | **[x]** `50lang_audit_20260615-235805` |
| **E-3-7** | **ko↔ja API 스모크** | **[x]** voice-translate 양방향 PASS |
| **E-3-8** | **ko↔ja VoIP E2E** | **[~]** API OK · 실기기 자동화 재시도 필요 |

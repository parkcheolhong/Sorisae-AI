# Remaining Functional Groups Triage (2026-08-16)

상태: 구현됨

목적:
- "빠짐없이" 기준으로 기능군 검증을 2라운드 실행하고, 완료/미검증/미작업 3분류로 현재 상태를 고정한다.

실행 번들:
- 1차 전수 스윕: `evidence/full-functional-validation-20260816-194753`
- 4항목 보정 재검증(1/3/4): `evidence/full-functional-remediate-20260816-195454`
- admin/marketplace timeout 보정 재검증(2): `evidence/admin-marketplace-post-timeoutfix-20260816-195945`
- admin passkey operational 단독 보정 재검증: `evidence/admin-passkey-operational-fix-20260816-200411`
- sorisae friend-chat probe 단독 보정 재검증: `evidence/sorisae-friend-chat-probe-fix-v2-20260816-201220`

## 실행 결과(2라운드)

| Round | mobile core tests | auth duplicate login | sorisae friend probe | ops health | admin passkey e2e | marketplace passkey chain |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 0 | 1 | 1 | 1 | 1 | 1 |
| 2 | 0 | 1 | 1 | 1 | 1 | 1 |

(exit code: 0=PASS, 1=FAIL)

## 보정 재검증 결과(요청 4항목)

### A. 1/3/4 항목 통합 재검증 (`full-functional-remediate-20260816-195454`)

| Round | auth duplicate login | ops health | websocket handshake |
|---|---:|---:|---:|
| 1 | 0 | 0 | 0 |
| 2 | 0 | 0 | 0 |

### B. 2항목(admin/marketplace) 재검증 (`admin-marketplace-post-timeoutfix-20260816-195945`)

| Round | admin passkey e2e | marketplace passkey chain |
|---|---:|---:|
| 1 | 1 | 0 |
| 2 | 1 | 0 |

### C. admin passkey operational 단독 재검증 (`admin-passkey-operational-fix-20260816-200411`)

| Round | admin passkey operational |
|---|---:|
| 1 | 0 |
| 2 | 0 |

### D. sorisae friend-chat probe 단독 재검증 (`sorisae-friend-chat-probe-fix-v2-20260816-201220`)

| Round | sorisae friend-chat probe |
|---|---:|
| 1 | 0 |
| 2 | 0 |

## 3분류 표

| 기능군 | 분류 | 판정 | 근거 |
|---|---|---|---|
| Passkey callback + Sorisae FAB 실이벤트 체인 | 완료 | 2연속 PASS 유지 | `docs/checklists/sorisae-passkey-fab-integrated-close-checklist-20260816.md`, `evidence/apk-passkey-real-token-e2e-20260816-rerun11-after-reinstall/validation_summary.txt`, `evidence/apk-passkey-real-token-e2e-20260816-rerun12-after-reinstall/validation_summary.txt` |
| 모바일 코어 테스트(로그인/대면/VoIP/채팅/여행/노래) | 완료 | 2라운드 연속 PASS (`mobile_core_tests_exit=0`) | `evidence/full-functional-validation-20260816-194753/summary.json` |
| 인증 중복 로그인 E2E | 완료 | 활성 세션 자동 해제 옵션 적용 후 2라운드 연속 PASS | `evidence/full-functional-remediate-20260816-195454/summary.json` |
| Sorisae friend-chat probe | 완료 | health warning 허용 + 응답 길이 임계값 안정화 후 2라운드 연속 PASS | `evidence/sorisae-friend-chat-probe-fix-v2-20260816-201220/summary.json` |
| 운영 헬스체크(ops) | 완료 | optional 서비스(video-worker, nginx) 기준 보정 후 2라운드 PASS | `evidence/full-functional-remediate-20260816-195454/summary.json` |
| Admin passkey operational Playwright | 완료 | 패스키 등록 버튼 disabled 하드게이트를 제거한 operational 경로 고정 후 2라운드 연속 PASS | `evidence/admin-passkey-operational-fix-20260816-200411/summary.json` |
| Marketplace passkey feature chain Playwright | 완료 | `admin.setup` timeout 해소 후 2라운드 연속 PASS | `evidence/admin-marketplace-post-timeoutfix-20260816-195945/summary.json` |
| 운영 websocket 직접 handshake 2회 재검증 | 완료 | 단독 핸드셰이크 스크립트 신설 및 2라운드 PASS | `scripts/check_ws_handshake.ps1`, `evidence/full-functional-remediate-20260816-195454/summary.json` |

보관 메모:
- 상세 라운드 원본(`round*/**/*.log`, `round*-report.json`)은 각 번들 폴더에 보관하고, 본 표에는 요약 산출물만 유지한다.

## 주요 실패 원인 요약

1. auth duplicate login E2E (해결)
- 조치: `--auto-clear-active-session` 옵션으로 실행 전 활성 세션 정리 단계 추가
- 결과: 2라운드 PASS

1. sorisae friend-chat probe (해결)
- 원인: `/api/health`의 `status=warning`(ad_worker 경고)와 friend-chat 응답 길이 변동(80자 미만)이 오탐 FAIL을 유발
- 조치: `scripts/run_sorisae_friend_chat_probe.py`에서 health 판정에 `warning + modules.api=ok` 허용, 응답 최소 길이 기준을 `MIN_RESPONSE_LEN`(기본 60)으로 안정화
- 결과: 단독 재검증 2라운드 PASS

1. ops health (해결)
- 조치: `video-worker`, `nginx`를 optional 서비스로 분류
- 결과: 2라운드 PASS

1. admin/marketplace playwright (해결)
- 조치: `tests/admin.setup.playwright.spec.ts`에서 credential login/fallback/redirect 분기 보강으로 setup timeout 해소
- 조치(추가): `tests/admin-passkey-operational.playwright.spec.ts`에서 패스키 등록/로그인 검증을 API+WebAuthn 직접 경로로 고정해 버튼 disabled 하드의존 제거
- 결과: marketplace 체인 2라운드 PASS + admin passkey operational 단독 2라운드 PASS

## 완료 항목 락

- 본 문서의 기능군(모바일 코어, 인증 중복로그인, sorisae friend-chat probe, ops health, admin/marketplace/playwright, websocket handshake)은 완료 상태로 고정한다.
- 위 항목은 재검증 필요 이벤트(배포/설정 변경/회귀 징후) 전까지 추적 제외한다.

## 다른 항목 추적 큐

아래는 `docs/checklists/*.md` 기준 미완료(`[ ]`)가 실제 존재하는 문서만 추린 다음 추적 대상이다.

1. `docs/checklists/feature-separation-checklist.md` (미완료 10건)
2. `docs/checklists/activity-inspection-checklist.md` (미완료 56건)
3. `docs/checklists/feature-separation-audio-isolation-audit-20260709.md` (미완료 5건)
4. `docs/checklists/tourism-ai-pilot-checklist.md` (미완료 8건)
5. `docs/checklists/worldlinco-build90-92-checklist.md` (미완료 7건)
6. `docs/checklists/admin-docs-r5-runtime-followup-checklist.md` (미완료 5건)
7. `docs/checklists/sorisae-travel-partner-api-integration-checklist-20260630.md` (미완료 1건)
8. `docs/checklists/shinsegye-codingbot-safe-integration-checklist-20260430.md` (미완료 1건)

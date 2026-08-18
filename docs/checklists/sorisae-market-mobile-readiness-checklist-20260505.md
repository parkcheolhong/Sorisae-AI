# Sorisae Market/Mobile Readiness Checklist (2026-06-05)

## 목적
- 소리새를 마켓 프로그램으로 운영 가능한 수준으로 고정한다.
- 모바일 APK 앱(서버 연동형)으로 구현 가능한 출고 기준을 명확히 한다.
- 각 항목은 실검증 2회 통과 후에만 완료됨으로 닫는다.

## 상태 규칙
- 보고 상태는 `구현됨`, `완료됨`, `실패`만 사용한다.
- 자동 검증 또는 운영 검증이 하나라도 실패하면 `완료됨`으로 보고하지 않는다.

## Wave 2 고정 계획

기준:
- 기존 Expo 빌드 분석은 `apps/mobile-nadotongryoksa`의 EAS 성공 빌드 증적과 `CRITICAL_2_CHECKLIST.md`를 우선 참고한다.
- 호환 매트릭스는 Expo 57 계열 기준으로 고정한다.
- 단위는 프로젝트 1개씩만 올리고, 실패 시 해당 프로젝트만 즉시 롤백한다.

| 순서 | 프로젝트 | 현재 핵심 버전 | Wave 2 목표 버전 | 검증 포인트 | 롤백 경계 |
|---|---|---|---|---|---|
| 1 | `mobile-nadotongryoksa` | `expo ~56.0.12`, `react-native 0.85.3`, `react 19.2.3` | `expo ~57.0.0`, `react-native 0.86.0`, `@react-native/jest-preset 0.86.2` | `npm run eas:android:preview`, `npm test`, `npm audit --omit=dev --json` | `mobile-nadotongryoksa/package.json` + lockfile |
| 2 | `apps/mobile-nadotongryoksa` | `expo ~56.0.12`, `react-native 0.85.3`, `react 19.2.3` | `expo ~57.0.0`, `react-native 0.86.0`, `@react-native/jest-preset 0.86.2` | `npm run eas:android:preview`, `npm test`, `npm audit --omit=dev --json` | `apps/mobile-nadotongryoksa/package.json` + lockfile |
| 3 | `apps/mobile-stock-ai` | `expo ~56.0.8`, `react-native 0.76.5`, `react 18.3.1` | `expo ~57.0.0`, `react-native 0.86.0`, `react 19.2.3` | `npm run eas:android:preview`, `npm run typecheck`, `npm audit --omit=dev --json` | `apps/mobile-stock-ai/package.json` + lockfile |

실행 규칙:
- 한 프로젝트의 빌드/테스트/감사 재검증이 모두 통과한 뒤에만 다음 프로젝트로 이동한다.
- 실패하면 해당 프로젝트의 package.json/lockfile 변경만 되돌리고 다음 프로젝트로 넘어가지 않는다.
- 브레이킹 영향 최소화를 위해 Expo/RN 메이저 업그레이드는 project-by-project로만 진행한다.

## 게이트 항목

### 1) 슬롯별 입출력 계약 고정
- 상태: 구현됨
- 목표:
  - 슬롯별 요청/응답 JSON 스키마를 문서로 고정
  - 필수 필드/선택 필드/타입/기본값/에러 형식 정의
- 완료 기준:
  - 최소 6개 핵심 슬롯(voice_movie, detective_dashboard, integrated_dashboard, movie_server, master, shopping) 계약 문서화
  - `/api/marketplace/sorisae/dispatch` 실호출 2회에서 계약 위반 0건
- 증거 기록:
  - 검증 실행 1차: `docs/evidence/sorisae-dispatch-slot-io-validation-rounds-20260505.md` (Round 1, 6/6 slots, HTTP 200 + status=flask_server_ok)
  - 검증 실행 2차: `docs/evidence/sorisae-dispatch-slot-io-validation-rounds-20260505.md` (Round 2, 6/6 slots, HTTP 200 + status=flask_server_ok)
  - 비고: 계약 본문은 `docs/contracts/sorisae-dispatch-slot-io-contract-20260505.md`에 고정

### 2) 실패 코드 표준화
- 상태: 구현됨
- 목표:
  - 슬롯 실패 응답에 표준 코드(`error_code`, `error_message`, `retryable`, `source`) 적용
- 완료 기준:
  - 네트워크 실패/타임아웃/런타임 예외/입력 검증 실패를 구분해 일관된 코드 반환
  - 2회 실검증에서 동일 실패 조건에 동일 코드 재현
- 증거 기록:
  - 검증 실행 1차: `docs/evidence/sorisae-dispatch-failure-code-validation-rounds-20260505.md` (Round 1)
  - 검증 실행 2차: `docs/evidence/sorisae-dispatch-failure-code-validation-rounds-20260505.md` (Round 2)
  - 비고: 표준 정의는 `docs/contracts/sorisae-dispatch-failure-code-standard-20260505.md`에 고정

### 3) 부하 테스트
- 상태: 구현됨
- 목표:
  - 마켓 호출 기준의 최소 동시성/응답시간/오류율 기초선 확보
- 완료 기준:
  - 핵심 슬롯 dispatch 대상으로 1차 부하 프로파일(요청 수, 동시성, p95, 오류율) 산출
  - 동일 조건 2회 재측정 결과 편차 허용 범위 내
- 증거 기록:
  - 검증 실행 1차/2차 요약: `docs/evidence/sorisae-dispatch-loadtest-analysis-20260505.md`
  - 비고: 원본 1차/2차 JSON은 보관

### 4) 보안 점검
- 상태: 구현됨
- 목표:
  - 인증/권한/CORS/입력 검증/민감정보 노출/에러 메시지 노출 범위 점검
- 완료 기준:
  - 비인가 요청 차단, 토큰 없는 호출 차단, 과도한 내부 예외 노출 제거 확인
  - 점검 시나리오 2회 반복 시 동일 통과
- 증거 기록:
  - 검증 실행 1차/2차 요약: `docs/evidence/sorisae-dispatch-security-gate4-validation-rounds-20260505.md`
  - 비고: 원본 1차/2차 JSON은 보관

### 5) 모바일 시나리오 실사용 테스트
- 상태: 구현됨
- 목표:
  - APK 앱(서버 연동형)에서 실제 사용자 흐름이 끊김 없이 동작하는지 확인
- 완료 기준:
  - 로그인 -> 기능 호출 -> 결과 확인 -> 재시도/오류 처리 흐름 검증
  - Android 실제 디바이스 또는 에뮬레이터에서 2회 반복 통과
- 증거 기록:
  - 검증 실행 1차:
  - 검증 실행 2차:
  - 비고:

### 6) 소리새 역할 스코프 고정(친근한 대화친구 + 관광 안내)
- 상태: 구현됨
- 목표:
  - 소리새 역할을 2개(친근한 대화친구, 관광 안내)만 허용
  - 온디바이스 메모리 기반으로 관계가 누적·진화하는 동반자 성격 유지
  - 불필요한 역할(지식/생활비서/감정지지/언어교습) 분류/프롬프트 제거
  - 최신 정보 우선 원칙을 여행 안내 프롬프트에 고정
- 완료 기준:
  - 프런트 도메인 SSOT가 `companion`, `travel` 두 개만 유지
  - friend-chat 시스템 프롬프트에 Memory & Evolution Rule 반영
  - 백엔드 friend-chat 시스템 프롬프트에 Role Scope Lock + Latest-First Rule 반영
  - 관련 자동검증 2회 통과
- 증거 기록:
  - 검증 실행 1차: `npm test -- companionDomains.test.ts companionCommands.test.ts companionMemory.test.ts --runInBand` (3 suites passed, 26 tests passed)
  - 검증 실행 2차: `npm test -- companionDomains.test.ts companionCommands.test.ts companionMemory.test.ts --runInBand` (3 suites passed, 26 tests passed)
  - 백엔드 문법검증 1차: `.venv\\Scripts\\python.exe -m py_compile backend/llm/voice_gateway.py` (성공)
  - 백엔드 문법검증 2차: `.venv\\Scripts\\python.exe -m py_compile backend/llm/voice_gateway.py` (성공)
  - 메모리 규칙 보강 확인: `backend/llm/voice_gateway.py` `_friend_system_prompt`에 `MEMORY & EVOLUTION RULE` 문구 추가
  - 프런트 회귀 확인: `npm test -- companionDomains.test.ts --runInBand` (1 suite passed, 8 tests passed)
  - 비고: 운영 실도메인 대면 검증(모바일 실기기 음성 경로)은 별도 라운드에서 추가 필요

## 최종 판정
- 현재 판정: 구현됨
- 완료됨 전제 조건:
  - 위 5개 항목의 증거 기록 2회씩 채워짐
  - 차단 항목 없음

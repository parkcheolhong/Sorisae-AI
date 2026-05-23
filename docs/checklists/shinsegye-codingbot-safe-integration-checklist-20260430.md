# 신세계 소리새 + 코딩봇 마켓플레이스 안전 조합 체크리스트 (2026-04-30)

## 목적

- 신세계 소리새 모듈(통역/음악)과 코딩봇 마켓플레이스(코드생성)의 동시 운영 조합을 안전하게 검증한다.
- 구현 여부가 아니라 실제 동작 근거를 2회 이상 확보한 항목만 `완료됨`으로 닫는다.

## 상태 규칙

- `구현됨`: 코드/구성은 존재하나 본 문서 기준 실검증 2회가 미충족
- `완료됨`: 실검증 2회 이상 통과 + 근거 기록 완료
- `실패`: 차단/오류 발생으로 통과 불가

## A. 통합 경로 인벤토리

- [x] 완료됨: 통역 라우터 존재 및 프런트 호출 경로 연결
- [x] 완료됨: 음악 라우터 존재 및 프런트 호출 경로 연결
- [x] 완료됨: 코드생성 라우터(프로필/생성/이력/다운로드) 존재 및 프런트 호출 경로 연결

근거 파일

- [backend/marketplace/interpreter_router.py](backend/marketplace/interpreter_router.py)
- [backend/marketplace/music_router.py](backend/marketplace/music_router.py)
- [backend/marketplace/code_generator_router.py](backend/marketplace/code_generator_router.py)
- [frontend/frontend/app/marketplace/code-generator/page.tsx](frontend/frontend/app/marketplace/code-generator/page.tsx)

## B. 통합 API 실검증 (Round 1)

- [x] 완료됨: `/health` 200
- [x] 완료됨: `/api/auth/signup` 201, `/api/auth/login` 200
- [x] 완료됨: `/api/marketplace/interpreter/health` 200
- [x] 완료됨: `/api/marketplace/interpreter/translate` 200
- [x] 완료됨: `/api/marketplace/music/health` 200
- [x] 완료됨: `/api/marketplace/music/compose/emotion` 200
- [x] 완료됨: `/api/marketplace/code-generator/profiles` 200
- [x] 완료됨: `/api/marketplace/code-generator/generate` 200
- [x] 완료됨: `/api/marketplace/code-generator/history` 200
- [x] 완료됨: `/api/marketplace/code-generator/download/{generation_id}` 200
- [x] 완료됨: `http://127.0.0.1:3000/marketplace/code-generator` 200

실검증 출력 요약

- `ROUND1_STATUS=PASS`
- `backend_health=200`
- `shinsegye_dash=200`
- `signup=201`
- `login=200`
- `interp_health=200`
- `interp_translate=200`
- `music_health=200`
- `music_compose_emotion=200`
- `codegen_profiles=200`
- `codegen_generate=200`
- `codegen_history=200`
- `codegen_download=200`
- `marketplace_ui_codegen=200`

## C. 통합 API 실검증 (Round 2)

- [x] 완료됨: Round 1 동일 범위 재검증 통과
- [x] 완료됨: 음악 코드작곡(`/compose/code`) + 친구 데모(`/friends/demo`) 추가 시나리오 통과
- [x] 완료됨: `http://127.0.0.1:3000/marketplace` 200

실검증 출력 요약

- `ROUND2_STATUS=PASS`
- `backend_health=200`
- `shinsegye_dash=200`
- `signup=201`
- `login=200`
- `interp_health=200`
- `interp_translate=200`
- `music_health=200`
- `music_compose_code=200`
- `music_friends_demo=200`
- `codegen_profiles=200`
- `codegen_generate=200`
- `codegen_history=200`
- `codegen_download=200`
- `marketplace_ui_main=200`

## D. 운영 경로 실검증 (admin/marketplace/websocket)

- [x] 완료됨: 운영 도메인 HTTP 검증 2회 연속 통과
- [x] 완료됨: 백엔드 CORS 운영 도메인 로드 확인
- [x] 완료됨: websocket `/api/llm/ws` 핸드셰이크 + ping/pong 2회 통과

실검증 출력 요약

- `final_production_verification.ps1` 2회 연속 통과
- `Marketplace Page (metanova1004.com) HTTP Status: 200`
- `Admin Dashboard (xn--114-2p7l635dz3bh5j.com) HTTP Status: 200`
- `ML Detectors Status: 200`
- `No blocking warnings detected in this HTTP-level production verification.`
- `check_cors_final.ps1`: `Production domains FOUND in CORS origins`
- `WS_CONNECT=OK`, `WS_PING_PONG=OK`
- `WS_ROUND2_CONNECT=OK`, `WS_ROUND2_PONG={"event":"pong", ...}`

근거 파일

- [final_production_verification.ps1](final_production_verification.ps1)
- [check_cors_final.ps1](check_cors_final.ps1)
- [backend/llm/orchestrator.py](backend/llm/orchestrator.py)

## E. 결과 판정

- 전체 상태: `완료됨`
- 판정 근거:
  - 통합 API + UI 경로 2회 실검증 통과
  - 운영 도메인 HTTP 검증 2회 실검증 통과
  - websocket 운영 경로 2회 실검증 통과
  - CORS 운영 도메인 로드 확인

## F. Playwright 브라우저 실사용 증적 (요청 항목 1)

- [x] 완료됨: 통역 버튼 클릭 시나리오 2회 통과
- [x] 완료됨: 음악 생성(감정 기반) 시나리오 2회 통과
- [x] 완료됨: 코드 ZIP 다운로드(브라우저 다운로드 이벤트) 시나리오 2회 통과

실검증 실행 명령

- `PLAYWRIGHT_ADMIN_BASE_URL=http://127.0.0.1:3000`
- `PLAYWRIGHT_API_BASE_URL=http://127.0.0.1:8000`
- `npm --prefix frontend/frontend run e2e:marketplace:shinsegye-safe` (2회)

실검증 출력 요약

- `1 passed (4.0s)` (Round 1)
- `1 passed (5.0s)` (Round 2)
- 시나리오: `code-generator page supports interpreter, music, and zip download in one real user flow`

근거 파일

- [frontend/frontend/tests/marketplace-shinsegye-safe-integration.playwright.spec.ts](frontend/frontend/tests/marketplace-shinsegye-safe-integration.playwright.spec.ts)
- [frontend/frontend/app/marketplace/code-generator/page.tsx](frontend/frontend/app/marketplace/code-generator/page.tsx)
- [frontend/frontend/package.json](frontend/frontend/package.json)

## G. CI 파이프라인 자동화 (요청 항목 2)

- [x] 구현됨: 배포 이후 자동 검증용 GitHub Actions 워크플로 추가
- [x] 구현됨: Round 1/Round 2 분리 실행 및 결과 요약(`GITHUB_STEP_SUMMARY`) 기록
- [x] 구현됨: Playwright 리포트 아티팩트 업로드 및 라운드 실패 시 잡 실패 처리

구현 파일

- [.github/workflows/marketplace-shinsegye-safe-integration.yml](.github/workflows/marketplace-shinsegye-safe-integration.yml)

자동화 동작

- 트리거: `push(main, 경로필터)` + `workflow_dispatch`
- 실행 대상: `tests/marketplace-shinsegye-safe-integration.playwright.spec.ts`
- 실행 환경: `PLAYWRIGHT_ADMIN_BASE_URL=https://metanova1004.com`, `PLAYWRIGHT_API_BASE_URL=https://xn--114-2p7l635dz3bh5j.com`
- 증적: Round1/Round2 리포트 아티팩트 + Step Summary 표

## H. 소리새 약 120엔진 전체 병합 안전성 평가

- [ ] 실패: 현재 상태에서 소리새 엔진 전량(약 120) 안전 병합 완료로 판정 불가

계량 근거

- `SORISAE_TOTAL_PY=397`
- `SORISAE_MODULES_PY=57`
- `SORISAE_MODULES_SORISAE_PY=9`
- `SORISAE_ENGINE_SYSTEM_CLASS_CANDIDATES=99`
- `MARKETPLACE_SORISAE_ENDPOINTS=6`

판정 사유

- 현재 운영 병합은 통역/음악 중심 6개 엔드포인트 검증까지 확보됨
- 엔진 후보(클래스 기준) 99개 규모 대비 API 계약/권한/리소스/UI 경로 커버리지가 전량 기준으로는 부족함
- 따라서 현재 판정은 “부분 병합 안전 완료”이며 “전량 병합 안전 완료”는 미달

전량 병합 완료 조건(추가 필요)

- 엔진군별 계약 매핑표(엔진 ID ↔ API ↔ UI ↔ 테스트) 100% 작성
- 엔진군별 smoke + 회귀 + 운영 경로 2회 검증
- 실패 엔진 격리(fallback) 정책과 운영 게이트(health/circuit-breaker) 적용

## I. 120엔진 통합 준비도 매트릭스 v1

- [x] 완료됨: 120엔진 통합 준비도 매트릭스(v1) 작성
- [x] 완료됨: 분류군별 준비도 점수(0-5) 및 하드게이트 정의
- [x] 완료됨: 전량 통합 판정 기준(실패)과 다음 우선순위 명시
- [x] 완료됨: 기타 243건 2차 분류표 작성
- [x] 완료됨: 엔진 ID to API to UI to 테스트 100% 매핑표 v2 작성
- [x] 완료됨: 분류군별 2회 실검증 배치 실행 및 상태 승격 반영

근거 파일

- [docs/checklists/shinsegye-120-engine-integration-readiness-matrix-v1-20260430.md](docs/checklists/shinsegye-120-engine-integration-readiness-matrix-v1-20260430.md)
- [docs/checklists/shinsegye-etc-243-secondary-classification-20260430.md](docs/checklists/shinsegye-etc-243-secondary-classification-20260430.md)
- [docs/checklists/shinsegye-engine-api-ui-test-mapping-v2-20260430.md](docs/checklists/shinsegye-engine-api-ui-test-mapping-v2-20260430.md)
- [docs/checklists/shinsegye-category-validation-rounds-20260430.md](docs/checklists/shinsegye-category-validation-rounds-20260430.md)

## J. 소리새 관제탑 승격 최소 경로 (설계 반영 + 체크리스트 실행)

설계 레이어

- 라우팅 레이어: `GET /api/marketplace/extras/control-tower/state`, `POST /api/marketplace/extras/control-tower/decide`
- 상태집계 레이어: iot/game circuit breaker + 엔진 상태를 단일 control_tower 상태로 집계
- 정책결정 레이어: intent/action 기반 엔진 선택, 미식별 intent fallback, IoT 위험 action deny

체크리스트 실행

- [x] 완료됨: 라우팅 레이어 구현 (`/control-tower/state`, `/control-tower/decide`)
- [x] 완료됨: 상태집계 레이어 구현 (`overall/recommended_domain/degraded_reasons`)
- [x] 완료됨: 정책결정 레이어 구현 (`selected_domain/selected_engine/reason_codes/fallback/policy_denied`)
- [x] 완료됨: Round 1 실검증 통과 (local)
- [x] 완료됨: Round 2 실검증 통과 (local)
- [x] 완료됨: 운영 도메인 상태 조회 통과 (production)
- [x] 완료됨: 관리자 대시보드 우측 레일 관제탑 카드 시각화 연결 (overall/recommended/iot/game/fallback)
- [x] 완료됨: 관리자 대시보드 시각화 Round 1 실검증 통과 (local login + 렌더링)
- [x] 완료됨: 관리자 대시보드 시각화 Round 2 실검증 통과 (local reload + 렌더링)

실검증 출력 요약

- `ROUND1`: `state_status=ok`, `overall=ok`, `recommended=extras`, `decide_iot_domain=extras-iot`, `decide_unknown_fallback=true`
- `ROUND2`: `state_status=ok`, `overall=ok`, `recommended=extras`, `decide_game_domain=extras-game`, `decide_policy_status=denied`, `decide_policy_denied=true`
- `PRODUCTION`: `login=ok`, `state_status=ok`, `overall=ok`, `recommended=extras`
- `ADMIN_UI_ROUND1`: `/admin` 로그인 후 우측 레일 카드 `CT OK · REC extras`, `IOT extras-iot · GAME extras-game`, `UNKNOWN fallback ON` 렌더링 확인
- `ADMIN_UI_ROUND2`: `/admin` 새로고침 후 동일 카드 값 재확인, React runtime error #310 미재현

구현 파일

- [backend/marketplace/extras_router.py](backend/marketplace/extras_router.py)
- [frontend/frontend/app/admin/page.tsx](frontend/frontend/app/admin/page.tsx)

## K. 로그인 장애 복구 체크

- [x] 완료됨: 로그인 500 원인 확인 (컨테이너 내부 DB URL이 `127.0.0.1`로 고정)
- [x] 완료됨: 컨테이너 DB URL 보정 로직 적용
- [x] 완료됨: 로컬 로그인 API 200 복구 확인
- [x] 완료됨: 운영 도메인 로그인 API 200 복구 확인

구현 파일

- [backend/marketplace/database.py](backend/marketplace/database.py)

## 참고 메모

- 초기 실패 원인: 가입 경로를 `/api/auth/register`로 호출하여 404/401이 발생했다.
- 조치: 가입 경로를 `/api/auth/signup`으로 수정 후 동일 시나리오 재검증에서 모두 통과했다.

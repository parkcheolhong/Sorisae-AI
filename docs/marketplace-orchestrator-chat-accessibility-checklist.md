# Marketplace Orchestrator Chat / Accessibility Checklist

## 검증 기준

- 실제 코드 수정과 브라우저 동작으로 확인된 항목만 `[x]` 처리
- 자동 검증과 브라우저 검증은 가능한 범위에서 각각 수행하고 근거를 남긴다
- 대화창 노출과 전송은 실제 페이지 기준으로 확인될 때만 닫는다

## 1. 접근성 경고 정리

- [x] 고객 회원가입 `memberType` 선택창에 접근 가능한 이름을 부여했다.
  - 근거: `frontend/frontend/app/marketplace/orchestrator/marketplace-orchestrator-client.tsx`의 `select` 에 `aria-label="가입 유형"`, `title="가입 유형"` 적용
- [x] 주문 입력 `taskDraft` 텍스트영역에 접근 가능한 이름을 부여했다.
  - 근거: `frontend/frontend/app/marketplace/orchestrator/marketplace-orchestrator-client.tsx`의 `textarea` 에 `aria-label="주문 요청 내용"`, `title="주문 요청 내용"`, placeholder 적용
- [x] 관련 Problems 경고가 사라졌는지 다시 확인했다.
  - 근거: `get_errors` 결과 `No errors found`

## 2. 고객 오케스트레이터 대화창 실검증

- [x] 실제 `/marketplace/orchestrator` 페이지가 열린다.
  - 근거: Playwright snapshot 에서 `https://metanova1004.com/marketplace/orchestrator` 진입 및 로그인 상태 확인
- [x] 단계 카드를 시작한 뒤 대화 로그/입력창이 화면에 노출된다.
  - 근거: 라이브 컨테이너 재배포 후 `멀티 협업 대화`, 입력창, `협업 대화 전송` 버튼, 단계별 카드/체크 UI가 브라우저 snapshot 에 노출됨
- [x] 대화 입력을 전송해 사용자 메시지가 실제 패널에 반영된다.
  - 근거: `/ask 지금 구조 설계 단계에서 먼저 고정해야 할 핵심 경계를 3가지로 정리해줘` 메시지가 라이브 페이지 대화 로그에 `고객 / 구조 설계` 항목으로 추가됨

## 3. Playwright 회귀 테스트 고정

- [x] 고객 오케스트레이터 단계 카드 시작 후 협업 대화 UI가 유지되는 회귀 테스트를 추가했다.
  - 근거: `frontend/frontend/tests/marketplace-orchestrator-chat.playwright.spec.ts` 추가
- [x] 고객 메시지 전송 후 사용자/오케스트레이터 대화 로그 반영을 검증하는 회귀 테스트를 추가했다.
  - 근거: 신규 스펙에서 `/api/auth/me`, `/stage-runs`, `/chat` 을 mock 하여 단계 카드 시작, 메시지 전송, assistant 응답 렌더를 검증
- [x] 단독 실행 커맨드를 패키지 스크립트로 고정했다.
  - 근거: `frontend/frontend/package.json` 의 `e2e:marketplace-orchestrator-chat`
- [x] 신규 회귀 테스트를 실제로 실행해 통과를 확인했다.
  - 근거: `Push-Location "C:\Users\WORK\source\repos\parkcheolhong\codeAI\frontend\frontend"; npm run e2e:marketplace-orchestrator-chat` 결과 `1 passed (1.4s)`
- [x] `verify:marketplace-playwright` 묶음에 고객 오케스트레이터 대화 회귀를 편입했다.
  - 근거: `frontend/frontend/package.json` 의 `verify:marketplace-playwright` 에 `npm run e2e:marketplace-orchestrator-chat` 추가
- [x] `/fix`, `/pass`, `/verify` 명령의 상태 전이를 추가 회귀로 넓혔다.
  - 근거: `frontend/frontend/tests/marketplace-orchestrator-chat.playwright.spec.ts` 에 manual_correction, 다음 카드 이동, verification 로그/출고 상태 새로고침 검증 추가

## 4. 프런트 재배포 / 캐시 우회 재확인

- [x] 최신 프런트 빌드를 라이브 컨테이너에 다시 반영했다.
  - 근거: `Push-Location "C:\Users\WORK\source\repos\parkcheolhong\codeAI"; docker compose up -d --build frontend-admin nginx` 실행 후 `frontend-admin`, `nginx` 재기동 확인
- [x] 캐시 우회 요청으로 라이브가 최신 빌드를 내보내는지 다시 확인했다.
  - 근거: `curl.exe -L -I -H "Cache-Control: no-cache" -H "Pragma: no-cache" "https://metanova1004.com/marketplace"` 결과 `200 OK`, `x-frontend-build-id: build-20260423075550`, `Cache-Control: no-store, no-cache, must-revalidate, max-age=0` 확인
- [x] 정적 아이콘 리소스 404가 사라졌는지 라이브 응답으로 다시 확인했다.
  - 근거: `curl.exe -I -H "Cache-Control: no-cache" -H "Pragma: no-cache" "https://metanova1004.com/favicon.ico"` 결과 `200 OK`
- [x] `verify:marketplace-playwright` 전체 묶음을 다시 실행해 모두 통과했다.
  - 근거: `Push-Location "C:\Users\WORK\source\repos\parkcheolhong\codeAI\frontend\frontend"; npm run verify:marketplace-playwright` 결과 popup 3건, liveview sheet 1건, orchestrator chat 2건 포함 전체 통과

## 현재 판정

- [x] 문서 최종 판정을 완료 기준으로 승격한다.
  - 상태: 완료됨
  - 근거: 접근성 수정, 대화창 실검증, Playwright 회귀 고정, 프런트 재배포/캐시 우회 재확인 항목이 모두 `[x]`로 닫혀 있다.

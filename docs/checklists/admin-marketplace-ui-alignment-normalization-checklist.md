# Admin/Marketplace UI Alignment Normalization Checklist

## Scope

- Objective: normalize admin + marketplace UI connection/implementation/reflection mismatch and re-validate both sides.
- Status policy: `구현됨`, `완료됨`, `실패` only.

## Checklist

- [x] 1. Admin proxy target alignment in marketplace Playwright runtime
  - Status: 완료됨
  - Evidence:
    - Updated `frontend/frontend/playwright.marketplace.config.ts` to force `BACKEND_PROXY_TARGET=http://127.0.0.1:8000` in webServer startup command.
    - Admin login stopped timing out at bootstrap step and operational specs progressed into functional assertions.

- [x] 2. Admin dashboard operational contract aligned to current UI structure
  - Status: 완료됨
  - Evidence:
    - Updated `frontend/frontend/tests/admin-dashboard-ops.playwright.spec.ts`:
      - sub-board link count: 4 -> 5
      - added `관리자 오케스트레이터` (`/admin/llm`) assertion
      - added `/admin/llm` route visibility assertion

- [x] 3. Admin system-settings operational spec aligned to current dashboard runtime contract
  - Status: 완료됨
  - Evidence:
    - Updated `frontend/frontend/tests/admin-system-settings-operational.playwright.spec.ts`:
      - removed stale expectation for old `전역 .env 설정 패널`
      - verifies current admin main runtime signals (`admin-main-page`, `운영 API 연결 완료`, control desk/sub-board links)
      - verifies refresh path with `관리자 대시보드 새로고침`

- [x] 4. Re-validation pass #1 (admin + marketplace)
  - Status: 완료됨
  - Evidence:
    - `tests/admin-dashboard-ops.playwright.spec.ts` -> 2 passed
    - `tests/admin-system-settings-operational.playwright.spec.ts` -> 2 passed
    - `tests/marketplace-generator-products.playwright.spec.ts tests/marketplace-detail-commerce.playwright.spec.ts tests/marketplace-orchestrator-chat.playwright.spec.ts` -> 6 passed

- [x] 5. Re-validation pass #2 (admin + marketplace)
  - Status: 완료됨
  - Evidence:
    - `tests/admin-dashboard-ops.playwright.spec.ts` -> 2 passed
    - `tests/admin-system-settings-operational.playwright.spec.ts` -> 2 passed
    - `tests/marketplace-generator-products.playwright.spec.ts tests/marketplace-detail-commerce.playwright.spec.ts tests/marketplace-orchestrator-chat.playwright.spec.ts` -> 6 passed
    - Note: one retry was required because port `4045` is a Next.js reserved port (`npp`). Re-run on `4051` passed.

## Final Verdict

- Overall status: 완료됨
- Reason: targeted mismatch points (admin-side route/test contract drift + proxy target inconsistency) were normalized and both admin/marketplace critical suites passed twice.

## Addendum: Admin 10-Step Orchestrator Visibility Restoration

- [x] A1. 관리자 메인 수동 오케스트레이터 10단계(4.5 포함) 복원
  - Status: 완료됨
  - Evidence:
    - Updated `frontend/frontend/app/admin/page.tsx`:
      - 기존 3단계 축약 배열 제거
      - `ARCH-001` ~ `ARCH-009` + `ARCH-0045` 총 10단계 노출
      - 각 단계에 `flowId/stepId/action` 메타를 표시
      - `data-testid="admin-manual-orchestrator-steps"` 추가

- [x] A2. 관리자 대시보드 Playwright 계약에 10단계 가시성 검증 추가
  - Status: 완료됨
  - Evidence:
    - Updated `frontend/frontend/tests/admin-dashboard-ops.playwright.spec.ts`:
      - `admin-manual-orchestrator-steps` 링크 개수 `10` 검증
      - `ARCH-0045` 단계 가시성 검증

- [x] A3. 운영 실검증 pass #1 (10단계 포함)
  - Status: 완료됨
  - Evidence:
    - `tests/admin-dashboard-ops.playwright.spec.ts tests/admin-system-settings-operational.playwright.spec.ts` -> 4 passed
    - command:
      - `PLAYWRIGHT_USE_WEBSERVER=1`
      - `PLAYWRIGHT_MARKETPLACE_PORT=4051`
      - `PLAYWRIGHT_ADMIN_USERNAME=119cash@naver.com`
      - `PLAYWRIGHT_ADMIN_PASSWORD=space0215@`

- [x] A4. 운영 실검증 pass #2 (10단계 포함)
  - Status: 완료됨
  - Evidence:
    - `tests/admin-dashboard-ops.playwright.spec.ts tests/admin-system-settings-operational.playwright.spec.ts` -> 4 passed
    - command/environment identical to A3.

- Addendum verdict: 완료됨
- Reason: 사용자 이슈였던 관리자 섹션의 "10단계 오케스트레이터 미노출" 상태가 UI/테스트/실검증(2회)까지 모두 동기화되어 닫힘.

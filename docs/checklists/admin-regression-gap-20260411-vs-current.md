# Admin Regression Gap Checklist (2026-04-11 Snapshot vs Current)

## 비교 기준

- 기준 스냅샷: D:/프로제트별모음/에이전트 모델파일/codeAI_2026_04_11.zip
- 선택 추출 경로: uploads/tmp/compare_20260411_snapshot/frontend/frontend
- 비교 대상(관리자 핵심 범위):
  - app/admin
  - components/admin
  - lib/admin*
  - tests/admin*.spec.ts

## 파일 단위 차이 요약

- 기준선 파일 수: 129
- 현재에서 누락된 기준선 파일 수: 101
- 공통 파일 중 내용 변경 파일 수: 26

## 상태 규칙

- 구현됨: 현재 코드에 의도 기능이 동일 또는 대체 형태로 정상 반영됨
- 완료됨: 구현 + 테스트/운영 경로 검증까지 닫힘
- 실패: 기준선 대비 누락, 미연동, 오동작, 또는 검증 축소 상태

## 회귀 체크리스트

- [x] 1) 관리자 문서 뷰어 라우트 보존
  - 상태: 완료됨
  - 분류: 구현됨 + 검증됨
  - 근거:
    - 라우트 복구: frontend/frontend/app/admin/docs-viewer/page.tsx
    - 링크 보존 대상(기존 UI 유지): frontend/frontend/app/admin/page.tsx
    - 검증(2회): frontend/frontend/tests/admin-login.playwright.spec.ts
      - restored docs-viewer and users routes are reachable without ui changes

- [x] 2) 관리자 recovery/users 보조 운영 페이지 보존
  - 상태: 완료됨
  - 분류: 구현됨 + 검증됨
  - 근거:
    - 라우트 복구:
      - frontend/frontend/app/admin/recovery/page.tsx
      - frontend/frontend/app/admin/users/page.tsx
    - 검증(2회): frontend/frontend/tests/admin-login.playwright.spec.ts
      - restored recovery routes render for default and carrier modes
      - restored docs-viewer and users routes are reachable without ui changes

- [x] 3) 상단 로그아웃 컨트롤 보존
  - 상태: 완료됨
  - 분류: 구현됨 + 검증됨
  - 근거:
    - 복구 반영: frontend/frontend/app/admin/page.tsx (`data-testid="admin-topnav-logout"` + 토큰 정리 후 로그인 리다이렉트)
    - 검증(2회): frontend/frontend/tests/admin-login.playwright.spec.ts
      - restores topnav logout control and global env settings panel hook

- [x] 4) 전역 .env 설정 패널(메인 내 운영 제어) 보존
  - 상태: 완료됨
  - 분류: 구현됨 + 검증됨
  - 근거:
    - 복구 반영: frontend/frontend/app/admin/page.tsx
      - 상단 토글: `data-testid="admin-topnav-global-env-panel"`
      - 패널 본문: `data-testid="admin-global-env-settings-panel"`
      - 패널 명시: "🧭 전역 .env 설정 패널"
    - 검증(2회): frontend/frontend/tests/admin-login.playwright.spec.ts
      - restores topnav logout control and global env settings panel hook

- [x] 5) 스토리보드/광고 주문 상세 제어 패널 보존
  - 상태: 완료됨
  - 분류: 구현됨 + 검증됨
  - 근거:
    - 복구 반영:
      - frontend/frontend/components/admin/admin-storyboard-modal.tsx
      - frontend/frontend/components/admin/admin-ad-preview-modal.tsx
      - frontend/frontend/components/admin/admin-ad-storyboard-review-panel.tsx
      - frontend/frontend/app/admin/page.tsx (`admin-storyboard-section-toggle`, `admin-storyboard-orders-toggle`, `admin-storyboard-panel`, `admin-storyboard-modal`)
    - 검증(2회):
      - `npm --prefix frontend/frontend exec playwright test tests/admin.setup.playwright.spec.ts tests/admin-dashboard-capability-notice.playwright.spec.ts tests/admin-llm-render.playwright.spec.ts tests/admin-storyboard-review.playwright.spec.ts`

- [x] 6) 관리자 수동 오케스트레이터 모듈화 계층 보존
  - 상태: 완료됨
  - 분류: 구현됨 + 검증됨
  - 근거:
    - 복구 반영:
      - frontend/frontend/components/admin/admin-manual-orchestrator-section.tsx
      - frontend/frontend/components/admin/admin-manual-step-strip.tsx
      - frontend/frontend/app/admin/page.tsx (모듈 섹션 연결)
    - 검증(2회):
      - `npm --prefix frontend/frontend exec playwright test tests/admin.setup.playwright.spec.ts tests/admin-dashboard-capability-notice.playwright.spec.ts tests/admin-llm-render.playwright.spec.ts tests/admin-storyboard-review.playwright.spec.ts`

- [x] 7) 관리자 대시보드 health/capability 조립 모듈 보존
  - 상태: 완료됨
  - 분류: 구현됨 + 검증됨
  - 근거:
    - 복구 반영:
      - frontend/frontend/app/admin/admin-page-health-analysis.ts
      - frontend/frontend/app/admin/admin-page-orchestrator-assemblies.ts
      - frontend/frontend/lib/admin-dashboard-state-assembler.ts
      - frontend/frontend/app/admin/page.tsx (health/summary/ad-order 조립 모듈 연결)
    - 검증(2회):
      - `npm --prefix frontend/frontend exec playwright test tests/admin.setup.playwright.spec.ts tests/admin-dashboard-capability-notice.playwright.spec.ts tests/admin-llm-render.playwright.spec.ts tests/admin-storyboard-review.playwright.spec.ts`

- [x] 8) 관리자 E2E 회귀 검증 범위 보존
  - 상태: 완료됨
  - 분류: 구현됨 + 검증됨
  - 근거:
    - 복구 반영 테스트:
      - frontend/frontend/tests/admin.setup.playwright.spec.ts
      - frontend/frontend/tests/admin-dashboard-capability-notice.playwright.spec.ts
      - frontend/frontend/tests/admin-llm-render.playwright.spec.ts
      - frontend/frontend/tests/admin-storyboard-review.playwright.spec.ts
    - 검증(2회):
      - `npm --prefix frontend/frontend exec playwright test tests/admin.setup.playwright.spec.ts tests/admin-dashboard-capability-notice.playwright.spec.ts tests/admin-llm-render.playwright.spec.ts tests/admin-storyboard-review.playwright.spec.ts`

- [x] 9) 관리자 10단계 오케스트레이터 가시성 복원
  - 상태: 완료됨
  - 분류: 구현됨 + 검증됨
  - 근거:
    - 현재 반영 파일: frontend/frontend/app/admin/page.tsx
    - 검증 파일: frontend/frontend/tests/admin-dashboard-ops.playwright.spec.ts
    - 10단계 + ARCH-0045 가시성 검증 포함

## 우선 복구 순서(Top 10)

- [x] P1. docs-viewer 라우트 복구 또는 상단 링크 제거/치환 정합화 (미연동 즉시 차단)
- [x] P2. logout topnav 복구 (운영 세션 제어 회복)
- [x] P3. 전역 .env 설정 패널 복구 (운영 제어 핵심)
- [x] P4. storyboard/ad preview 계층 복구
- [x] P5. manual orchestrator 모듈 계층 복구 (인라인 의존 축소)
- [x] P6. admin-page-* 조립 모듈 복구
- [x] P7. admin-manual-orchestrator lib 계약 복구
- [x] P8. capability notice 회귀 테스트 복구
- [x] P9. llm render 회귀 테스트 복구
- [x] P10. storyboard review 회귀 테스트 복구

## 최종 판정

- 현재 상태: 완료됨
- 판정 이유:
  - P1~P10 우선 복구 항목을 모두 반영하고 관리자 핵심 운영 경로를 현재 구조에 맞춰 복구함
  - 기준선 대비 누락됐던 storyboard/manual/admin-page 조립/lib 계약/회귀 테스트 축을 복원함
  - 복원된 회귀 테스트 축(`admin.setup`, capability notice, llm render, storyboard review)을 2회 반복 실행해 통과를 확인함

## 실행 이력 (고정)

- 목적: 재검증 추적성 강화를 위해 관리자 회귀 실행 결과를 하단에 누적 기록

| 일시 (KST) | 레인 | 커맨드 | 결과 | 비고 |
| --- | --- | --- | --- | --- |
| 2026-04-24 | smoke | `npm run ci:admin-regression:smoke` | 3 passed | smoke 레인 분리 후 첫 검증 |
| 2026-04-24 | full | `npm run ci:admin-regression:full` | 6 passed | full 레인 분리 후 첫 검증 |
| 2026-04-24 | full | `npm run ci:admin-regression` | 6 passed | 자동화 보강 후 1회차 통과 |
| 2026-04-24 | full | `npm run ci:admin-regression` | 6 passed | 자동화 보강 후 2회차 통과 |

## 포트 분리 Hard Gate (3005 Admin / 3000 Marketplace)

- 상태: 구현됨
- 목적: marketplace(3000)에서 admin 경로를 직접 진입하지 못하도록 host 기반 차단을 강제
- 반영:
  - frontend/frontend/proxy.ts
    - non-admin host에서 `/admin`, `/staff`, `/api/admin` 접근 차단
    - `/api/admin*`는 403(`ADMIN_HOST_REQUIRED`)로 거부
    - admin host에서 `/marketplace*` 역진입 시 `/admin`으로 리다이렉트
  - frontend/frontend/lib/canonical-site.ts
    - admin 화면에서 marketplace 링크 클릭 시 3000 origin으로 강제
    - marketplace 화면에서 admin 링크 해석 시 3005 origin으로 강제
    - 환경변수 지원:
      - `NEXT_PUBLIC_ADMIN_BASE_URL` / `ADMIN_BASE_URL`
      - `NEXT_PUBLIC_MARKETPLACE_BASE_URL` / `MARKETPLACE_BASE_URL`
      - `NEXT_PUBLIC_ADMIN_DEV_PORTS` / `ADMIN_DEV_PORTS`
      - `NEXT_PUBLIC_MARKETPLACE_DEV_PORTS` / `MARKETPLACE_DEV_PORTS`
- 검증:
  - 1회: 변경 파일 진단(`get_errors`) 통과
  - 1회: 대상 파일 lint 실행(`npm --prefix frontend/frontend run -s lint -- --no-error-on-unmatched-pattern proxy.ts lib/canonical-site.ts`)
- 비고:
  - 운영/브라우저 실검증 2회는 아직 미수행이므로 `완료됨`으로 승격하지 않음

## 마켓 노출 차단 2차 Hard Gate (admin proxy/action + bridge 분리)

- 상태: 구현됨
- 목적: marketplace(3000)에서 admin 설정/패널/API 컨텍스트가 재유입되는 우회 경로를 제거
- 반영:
  - frontend/frontend/proxy.ts
    - non-admin host의 `/api/proxy` 요청 중 `action=admin-*`, `admin-bootstrap-session`, `passkey-*` 를 403(`ADMIN_PROXY_HOST_REQUIRED`)로 차단
  - frontend/frontend/app/api/proxy/route.ts
    - admin 전용 `GET/POST/PATCH/PUT` 프록시 분기에서 host/port 검증(`isAdminHostRequest`) 추가
    - non-admin host에서 관리자 프록시 동작은 공통 403(`ADMIN_PROXY_HOST_REQUIRED`) 반환
  - frontend/frontend/app/marketplace/orchestrator/marketplace-orchestrator-client.tsx
    - `admin-orchestrator-bridge` 로컬스토리지 로드 제거(관리자 LLM preset 유입 차단)
  - frontend/frontend/hooks/use-feature-orchestrator.ts
    - `admin-orchestrator-bridge` import 제거
    - bridge payload 기반 popup 자동 오픈 로직 제거
- 검증:
  - 1회: 변경 파일 진단(`get_errors`) 통과
  - 1회: `npm run verify` 통과
    - `next build` 성공
    - `test`, `test:normalizer`, `test:popup-sections` 성공
- 비고:
  - 브라우저 실도메인 시나리오(3000/3005 분리 진입) 2회 실검증은 아직 미수행이므로 `완료됨`으로 승격하지 않음

## 버튼 오연결 1:1 재점검 + IU 식별표 부여 (관리자 LLM 화면)

- 상태: 구현됨
- 목적:
  - 관리자 LLM 화면에서 marketplace 이동 버튼이 상대경로로 이동 후 관리자 host hard-gate에 다시 걸리는 문제를 제거
  - 핵심 버튼/링크에 IU 식별표(`data-testid`)를 부여해 1:1 동작 검증 기준을 명시
  - 고정 도메인 정책 기본값을 `metanova1004.com:3000` / `개발분석114.com:3005`로 맞춤
- 반영:
  - frontend/frontend/app/admin/llm/page.tsx
    - `router.push('/marketplace...')` 제거
    - `window.location.assign(marketplace absolute href)`로 교체
    - IU 식별표 추가
      - `iu-admin-llm-open-marketplace-fullpage`
      - `iu-admin-llm-open-marketplace-popup`
      - `iu-admin-llm-marketplace-home-link`
      - `iu-admin-llm-sidebar-admin-home`
      - `iu-admin-llm-sidebar-marketplace-orchestrator`
  - frontend/frontend/components/admin/admin-ops-shell.tsx
    - rail/sidebar/top/hero 링크에 IU 식별표 추가
      - `iu-admin-rail-*`, `iu-admin-sidebar-link-*`, `iu-admin-top-*`, `iu-admin-hero-*`, `iu-admin-external-*`
  - frontend/frontend/components/ui/workspace-chrome.tsx
    - rail Link 렌더링에도 `data-testid={item.testId}` 전달되도록 보강
  - frontend/frontend/lib/canonical-site.ts
    - 기본 canonical URL을 운영 고정값으로 변경
      - marketplace: `http://metanova1004.com:3000`
      - admin: `http://개발분석114.com:3005`
  - frontend/frontend/proxy.ts
  - frontend/frontend/app/api/proxy/route.ts
    - admin host 판별을 `admin.` 접두어 + 로컬포트 + `ADMIN_ALLOWED_HOSTS`/`NEXT_PUBLIC_ADMIN_ALLOWED_HOSTS` + admin base URL hostname allowlist 병행으로 강화
- 검증:
  - 1회: 변경 파일 진단(`get_errors`) 통과
  - 1회: 전체 verify 실행 예정(아래 실행 이력에 기록)
- 비고:
  - 실도메인 브라우저 2회 검증(관리자/마켓 각 host에서 버튼 클릭 경로 확인)은 아직 미수행이므로 `완료됨`으로 승격하지 않음

# Admin Docs Link And R5 Runtime Follow-up Checklist

## Status Rules

- `구현됨`: source/config changed, but two verification runs are not complete.
- `완료됨`: docs link verification and R5 container runtime verification each pass twice.
- `실패`: any required verification is blocked or fails.

## Checklist

- [ ] 1. 관리자 대시보드 상단 문서/API 링크, 로그인 사용자 패널, 회원가입 사용자 확인 링크를 항상 보이는 경로로 복구한다.
- [x] 2. Swagger `/docs` 링크를 운영 관리자 도메인에서 2회 검증한다.
- [ ] 2-1. `/admin/docs-viewer` 문서 이동과 회원가입 사용자 확인 UI를 2회 검증한다.
- [ ] 3. R5 Python runtime contract를 `>=3.13,<3.14` 기준으로 Dockerfile과 backend runtime guard에 맞춘다.
- [ ] 4. backend container image/runtime Python 3.13과 `/health`를 2회 검증한다.
- [ ] 5. `docs/risk-analysis-allscan-20260427.md`에 R5 근거를 동기화한다.

## Evidence Log

- Status: 구현됨
- Source changes:
  - `frontend/frontend/app/admin/page.tsx`: restored visible topbar links for marketplace, PASS docs, commercial terms docs, same-origin `/docs`, and logged-in admin user panel.
  - `frontend/frontend/app/admin/page.tsx`: restored a fixed `가입 사용자` topbar/rail entry to `/admin/users`.
  - `frontend/frontend/app/admin/users/page.tsx`: renamed the page to `회원가입 사용자 확인`, added stable test ids, and exposed 가입 유형/사업자/대표자 fields.
  - `backend/admin_router.py`: included 가입 유형/사업자/대표자 fields in `/api/admin/users` responses.
  - `frontend/frontend/components/admin/admin-quick-links-section.tsx`: changed Swagger UI quick link from API-base fallback to same-origin `/docs`.
  - `frontend/frontend/components/ui/workspace-chrome.tsx`: rail link items now preserve `data-testid` when provided.
  - `nginx/nginx.conf/nginx.conf`: added admin-domain `/docs` and `/openapi.json` proxy routes so `https://xn--114-2p7l635dz3bh5j.com/docs` no longer falls through to the frontend admin redirect path.
  - `frontend/frontend/tests/admin-dashboard-ops.playwright.spec.ts`: login setup now detects the login form rendered at `/admin` and waits on stable topnav controls.
  - `Dockerfile.backend`, `Dockerfile`, `backend/main.py`: aligned runtime floor to Python 3.13 and `python -m uvicorn` execution.

## Verification Log

- 2026-04-27: `https://xn--114-2p7l635dz3bh5j.com/docs` returned Swagger UI HTML with status 200 twice after nginx reload.
- 2026-04-27: `https://xn--114-2p7l635dz3bh5j.com/openapi.json` returned OpenAPI JSON with status 200 twice after nginx reload.
- Pending: `/admin/docs-viewer` and `/admin/users` live UI validation twice after frontend container rebuild.

## Final Status

- Result: 구현됨

# Marketplace Domain Isolation + ID AutoLink Hard-Gate Checklist

## Status Rule

- Report labels: `구현됨`, `완료됨`, `실패`
- Only mark `[x]` after evidence-backed verification is run at least 2 times.
- If any required broad validation is still failing or blocked, overall state cannot be `완료됨`.

## 1) Marketplace -> Admin direct route isolation

- [x] Marketplace detail route hides all `/admin` links from rendered anchors.
- [x] Marketplace main route exposes no `/admin` links in page-level navigation.
- [x] Full marketplace generator product spec passes end-to-end (all test cases).

## 2) Generator ID autolink/section-index hard-gate implementation

- [x] Orchestrator writes `docs/auto_link_map.json` and `docs/section_id_index.md` as auxiliary outputs.
- [x] Orchestrator compatibility test includes regression coverage for generated auto-link artifacts.
- [x] Architecture contract required document list includes new ID artifacts.

## 3) Verification evidence log (2x minimum)

### A. Marketplace detail no-admin-link check (2x)

1. Command:
   - `PLAYWRIGHT_USE_WEBSERVER=1 PLAYWRIGHT_MARKETPLACE_PORT=3999 PLAYWRIGHT_MARKETPLACE_BASE_URL=http://127.0.0.1:3999 npx playwright test -c playwright.marketplace.config.ts tests/marketplace-detail-commerce.playwright.spec.ts --project chromium`
   Result:
   - `1 passed`
2. Command:
   - `PLAYWRIGHT_USE_WEBSERVER=1 PLAYWRIGHT_MARKETPLACE_PORT=4001 PLAYWRIGHT_MARKETPLACE_BASE_URL=http://127.0.0.1:4001 npx playwright test -c playwright.marketplace.config.ts tests/marketplace-detail-commerce.playwright.spec.ts --project chromium`
   Result:
   - `1 passed`

### B. Marketplace main no-admin-link check (2x focused)

1. Command:
   - `PLAYWRIGHT_USE_WEBSERVER=1 PLAYWRIGHT_MARKETPLACE_PORT=4005 PLAYWRIGHT_MARKETPLACE_BASE_URL=http://127.0.0.1:4005 npx playwright test -c playwright.marketplace.config.ts tests/marketplace-generator-products.playwright.spec.ts --project chromium --grep "does not expose admin navigation links"`
   Result:
   - `1 passed`
2. Command:
   - `PLAYWRIGHT_USE_WEBSERVER=1 PLAYWRIGHT_MARKETPLACE_PORT=4007 PLAYWRIGHT_MARKETPLACE_BASE_URL=http://127.0.0.1:4007 npx playwright test -c playwright.marketplace.config.ts tests/marketplace-generator-products.playwright.spec.ts --project chromium --grep "does not expose admin navigation links"`
   Result:
   - `1 passed`

### C. Backend auto-link artifact generation regression (2x)

1. Command:
   - `DATABASE_URL=sqlite:///./tmp/test.db python -m pytest backend/tests/test_orchestrator_compat_manifest_write.py -q -k "autolink"`
   Result:
   - `1 passed, 15 deselected`
2. Command:
   - `DATABASE_URL=sqlite:///./tmp/test.db python -m pytest backend/tests/test_orchestrator_compat_manifest_write.py -q -k "autolink"`
   Result:
   - `1 passed, 15 deselected`

### D. Marketplace generator product full spec (2x)

1. Command:
   - `PLAYWRIGHT_USE_WEBSERVER=1 PLAYWRIGHT_MARKETPLACE_PORT=4015 PLAYWRIGHT_MARKETPLACE_BASE_URL=http://127.0.0.1:4015 npx playwright test -c playwright.marketplace.config.ts tests/marketplace-generator-products.playwright.spec.ts --project chromium`
   Result:
   - `3 passed`
2. Command:
   - `PLAYWRIGHT_USE_WEBSERVER=1 PLAYWRIGHT_MARKETPLACE_PORT=4017 PLAYWRIGHT_MARKETPLACE_BASE_URL=http://127.0.0.1:4017 npx playwright test -c playwright.marketplace.config.ts tests/marketplace-generator-products.playwright.spec.ts --project chromium`
   Result:
   - `3 passed`

### E. Backend manifest file-level full suite (2x)

1. Command:
   - `DATABASE_URL=sqlite:///./tmp/test.db python -m pytest backend/tests/test_orchestrator_compat_manifest_write.py -q`
   Result:
   - `16 passed`
2. Command:
   - `DATABASE_URL=sqlite:///./tmp/test.db python -m pytest backend/tests/test_orchestrator_compat_manifest_write.py -q`
   Result:
   - `16 passed`

## 4) Open blockers / non-closed checks

- 현재 라운드 기준 차단 없음.
- 이전 차단(backend 1건, frontend 2건)은 코드 수정 후 전체 스펙 재실행 2회로 해소 확인.

## 5) Current verdict

- Current state: `완료됨`
- Reason:
  - Domain-isolation and ID autolink hard-gate code changes are implemented and target regressions pass with 2x evidence.
  - Full required broad verification set is closed with repeated green runs (frontend full spec + backend file-level full suite).

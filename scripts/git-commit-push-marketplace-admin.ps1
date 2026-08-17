Set-Location C:\Users\WORK\source\repos\parkcheolhong\codeAI

# =========================================
# 0) 작업 위치
# =========================================
Write-Host "[0] 작업 위치 확인"
Write-Host (Get-Location)
Write-Host ""

# 현재 상태 확인
Write-Host "[0] 현재 Git 상태"
git status --short
Write-Host ""

# =========================================
# 1) Marketplace popup / liveview UI
# =========================================
Write-Host "[1] Marketplace popup / liveview UI staging"
git add `
  frontend/frontend/components/marketplace/feature-orchestrator-popup.tsx `
  frontend/frontend/components/marketplace/feature-launcher-grid.tsx `
  frontend/frontend/components/marketplace/popup-sections/feature-popup-input-section.tsx `
  frontend/frontend/components/marketplace/popup-sections/feature-popup-live-view-section.tsx `
  frontend/frontend/components/marketplace/popup-sections/feature-popup-state-section.tsx `
  frontend/frontend/components/marketplace/popup-sections/feature-popup-output-section.tsx `
  frontend/frontend/app/marketplace/page.tsx `
  frontend/frontend/hooks/use-feature-orchestrator.ts `
  frontend/frontend/lib/marketplace-popup-telemetry.ts

git diff --staged
Read-Host "[1] 검토 후 Enter"
git commit -m "feat: finalize marketplace popup and liveview ui"
Write-Host ""

# =========================================
# 2) Admin shell / 메인 보드 확장
# =========================================
Write-Host "[2] Admin shell / 메인 보드 staging"
git add `
  frontend/frontend/components/admin/admin-ops-shell.tsx `
  frontend/frontend/app/admin/layout.tsx `
  frontend/frontend/app/admin/page.tsx

git diff --staged
Read-Host "[2] 검토 후 Enter"
git commit -m "feat: expand admin dashboard with shared ops shell"
Write-Host ""

# =========================================
# 3) Admin 하위 페이지 + 실제 API 연결
# =========================================
Write-Host "[3] Admin 하위 페이지 + 실제 API 연결 staging"
git add `
  frontend/frontend/app/admin/runs/page.tsx `
  frontend/frontend/app/admin/approvals/page.tsx `
  frontend/frontend/app/admin/publish/page.tsx `
  frontend/frontend/app/admin/observability/page.tsx

git diff --staged
Read-Host "[3] 검토 후 Enter"
git commit -m "feat: connect admin ops subpages to runtime and approval APIs"
Write-Host ""

# =========================================
# 4) 테스트/검증 흐름
# - package.json 에서는 테스트 관련 hunk만 stage
# - y: 테스트 관련
# - n: verify:marketplace-playwright / ci:marketplace
# - 크면 e 로 CI 2줄 삭제
# =========================================
Write-Host "[4] 테스트/검증 흐름 staging"
git add `
  frontend/frontend/lib/marketplace-popup-sections.contract.test.js `
  frontend/frontend/playwright.config.cjs `
  frontend/frontend/playwright.marketplace.config.ts `
  frontend/frontend/scripts/run-marketplace-popup-interactions.ps1 `
  frontend/frontend/scripts/run-marketplace-liveview-sheet.ps1 `
  frontend/frontend/tests/marketplace-popup-interactions.playwright.spec.ts `
  frontend/frontend/tests/marketplace-liveview-ai-sheet-launcher.playwright.spec.ts `
  docs/checklists/marketplace-popup-section-tests-checklist.md `
  docs/checklists/marketplace-popup-ui-interaction-tests-checklist.md `
  docs/checklists/marketplace-popup-ui-interaction-integration-checklist.md `
  docs/checklists/marketplace-liveview-playwright-integration-checklist.md

git add -p frontend/frontend/package.json
git diff --staged
Read-Host "[4] 검토 후 Enter"
git commit -m "test: add marketplace popup and liveview verification flows"
Write-Host ""

# =========================================
# 5) 문서 / CI / 가이드
# - package.json 에서는 아래 2줄만 stage
#   * verify:marketplace-playwright
#   * ci:marketplace
# - README 는 Marketplace Playwright 검증 명령 섹션만 stage
# =========================================
Write-Host "[5] 문서 / CI / 가이드 staging"
git add `
  docs/checklists/marketplace-popup-accessibility-checklist.md `
  docs/checklists/marketplace-popup-mobile-responsive-checklist.md `
  docs/checklists/marketplace-popup-output-specialization-checklist.md `
  docs/checklists/marketplace-popup-telemetry-checklist.md `
  docs/checklists/marketplace-playwright-ci-integration-checklist.md `
  docs/checklists/git-add-p-readme-packagejson-staging-guide.md `
  scripts/git-stage-marketplace-playwright.ps1 `
  scripts/git-stage-marketplace-ui-verification.ps1

git add -p frontend/frontend/package.json
git add -p README.md
git diff --staged
Read-Host "[5] 검토 후 Enter"
git commit -m "docs: document marketplace ui verification and admin ops workflow"
Write-Host ""

# =========================================
# 6) 빌드 최종 확인
# =========================================
Write-Host "[6] frontend build 확인"
Set-Location C:\Users\WORK\source\repos\parkcheolhong\codeAI\frontend\frontend
npm run build
Write-Host ""

# =========================================
# 7) 로그 / 상태 확인
# =========================================
Write-Host "[7] 커밋 로그 / 상태 확인"
Set-Location C:\Users\WORK\source\repos\parkcheolhong\codeAI
git log --oneline -5
git status
Write-Host ""

# =========================================
# 8) 원격 push
# =========================================
Write-Host "[8] codeai-target 으로 push"
git push codeai-target ai-sheet-deploy

# 필요하면 origin에도 push
# git push origin ai-sheet-deploy

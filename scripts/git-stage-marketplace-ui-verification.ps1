Set-Location C:\Users\WORK\source\repos\parkcheolhong\codeAI

Write-Host "========================================="
Write-Host "0. 작업 위치 확인"
Write-Host "========================================="
Write-Host (Get-Location)
Write-Host ""

Write-Host "========================================="
Write-Host "1. Marketplace UI 마무리 커밋"
Write-Host "========================================="

git add frontend/frontend/components/marketplace/feature-orchestrator-popup.tsx
git add frontend/frontend/components/marketplace/feature-launcher-grid.tsx
git add frontend/frontend/components/marketplace/popup-sections/feature-popup-input-section.tsx
git add frontend/frontend/components/marketplace/popup-sections/feature-popup-live-view-section.tsx
git add frontend/frontend/components/marketplace/popup-sections/feature-popup-state-section.tsx
git add frontend/frontend/components/marketplace/popup-sections/feature-popup-output-section.tsx
git add frontend/frontend/app/marketplace/page.tsx
git add frontend/frontend/hooks/use-feature-orchestrator.ts
git add frontend/frontend/lib/marketplace-popup-telemetry.ts
git diff --staged
Write-Host "검토 후 아래 커밋 명령 실행:"
Write-Host 'git commit -m "feat: finalize marketplace popup and liveview ui"'
Write-Host ""
Read-Host "1단계 staging 검토 후 Enter를 누르세요"

Write-Host "========================================="
Write-Host "2. Admin UI 보드 커밋"
Write-Host "========================================="

git add frontend/frontend/app/admin/layout.tsx
git add frontend/frontend/app/admin/page.tsx
git diff --staged
Write-Host "검토 후 아래 커밋 명령 실행:"
Write-Host 'git commit -m "feat: add admin ops board marketplace entrypoints"'
Write-Host ""
Read-Host "2단계 staging 검토 후 Enter를 누르세요"

Write-Host "========================================="
Write-Host "3. 테스트/검증 흐름 커밋"
Write-Host "- package.json에서는 테스트 관련 hunk만 stage"
Write-Host "- git add -p 중:"
Write-Host "  * 테스트 관련 hunk: y"
Write-Host "  * verify:marketplace-playwright / ci:marketplace: n"
Write-Host "  * 큰 hunk면 e -> CI 2줄 삭제"
Write-Host "========================================="

git add frontend/frontend/lib/marketplace-popup-sections.contract.test.js
git add frontend/frontend/playwright.config.cjs
git add frontend/frontend/playwright.marketplace.config.ts
git add frontend/frontend/scripts/run-marketplace-popup-interactions.ps1
git add frontend/frontend/scripts/run-marketplace-liveview-sheet.ps1
git add frontend/frontend/tests/marketplace-popup-interactions.playwright.spec.ts
git add frontend/frontend/tests/marketplace-liveview-ai-sheet-launcher.playwright.spec.ts
git add docs/checklists/marketplace-popup-section-tests-checklist.md
git add docs/checklists/marketplace-popup-ui-interaction-tests-checklist.md
git add docs/checklists/marketplace-popup-ui-interaction-integration-checklist.md
git add docs/checklists/marketplace-liveview-playwright-integration-checklist.md
git add -p frontend/frontend/package.json
git diff --staged
Write-Host "검토 후 아래 커밋 명령 실행:"
Write-Host 'git commit -m "test: add marketplace popup and liveview verification flows"'
Write-Host ""
Read-Host "3단계 staging 검토 후 Enter를 누르세요"

Write-Host "========================================="
Write-Host "4. 문서 / CI / 가이드 커밋"
Write-Host "- package.json에서는 아래 2줄만 stage"
Write-Host "  * verify:marketplace-playwright"
Write-Host "  * ci:marketplace"
Write-Host "- README는 Marketplace Playwright 검증 명령 섹션만 stage"
Write-Host "========================================="

git add docs/checklists/marketplace-popup-accessibility-checklist.md
git add docs/checklists/marketplace-popup-mobile-responsive-checklist.md
git add docs/checklists/marketplace-popup-output-specialization-checklist.md
git add docs/checklists/marketplace-popup-telemetry-checklist.md
git add docs/checklists/marketplace-playwright-ci-integration-checklist.md
git add docs/checklists/git-add-p-readme-packagejson-staging-guide.md
git add scripts/git-stage-marketplace-playwright.ps1
git add -p frontend/frontend/package.json
git add -p README.md
git diff --staged
Write-Host "검토 후 아래 커밋 명령 실행:"
Write-Host 'git commit -m "docs: document marketplace ui verification and ci workflow"'
Write-Host ""
Read-Host "4단계 staging 검토 후 Enter를 누르세요"

Write-Host "========================================="
Write-Host "5. 최종 확인 명령"
Write-Host "========================================="
Write-Host "git log --oneline -4"
Write-Host "git status --short"
Write-Host ""
Write-Host "되돌리기 필요 시:"
Write-Host "git restore --staged frontend/frontend/package.json"
Write-Host "git restore --staged README.md"

# =========================================
# 커밋 실행 순서 메모
# =========================================
# 1) Marketplace popup / liveview UI 마무리
#    - popup shell, input/liveview/state/output 패널
#    - 모바일 반응형, 접근성, focus, 결과 패널 스타일 정리
#    git commit -m "feat: finalize marketplace popup and liveview ui"
#
# 2) Admin 운영 보드 UI 확장
#    - admin layout/page 보강
#    - 운영 카드, marketplace/staff 진입 링크, 검증 명령 노출
#    git commit -m "feat: add admin ops board marketplace entrypoints"
#
# 3) 테스트/검증 흐름 추가
#    - popup interaction Playwright
#    - liveview Playwright
#    - popup section contract test
#    - package.json verify 테스트 흐름 반영
#    git commit -m "test: add marketplace popup and liveview verification flows"
#
# 4) 문서 / CI / staging 가이드 정리
#    - README 명령 정리
#    - checklist 문서 반영
#    - git add -p 가이드 및 helper script 추가
#    - package.json의 CI 집계 명령 반영
#    git commit -m "docs: document marketplace ui verification and ci workflow"

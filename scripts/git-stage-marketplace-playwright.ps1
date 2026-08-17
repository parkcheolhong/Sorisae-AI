Set-Location C:\Users\WORK\source\repos\parkcheolhong\codeAI

Write-Host "========================================="
Write-Host "0. 작업 위치 확인"
Write-Host "========================================="
Write-Host (Get-Location)
Write-Host ""

Write-Host "========================================="
Write-Host "1. 테스트/검증 흐름 커밋"
Write-Host "- package.json에서는 CI 2줄 제외"
Write-Host "- git add -p 중:"
Write-Host "  * 테스트 관련 hunk: y"
Write-Host "  * 큰 hunk면 e -> verify:marketplace-playwright / ci:marketplace 삭제"
Write-Host "  * CI 2줄만 있는 hunk: n"
Write-Host "========================================="

git add frontend/frontend/playwright.config.cjs
git add frontend/frontend/playwright.marketplace.config.ts
git add frontend/frontend/scripts/run-marketplace-popup-interactions.ps1
git add frontend/frontend/scripts/run-marketplace-liveview-sheet.ps1
git add frontend/frontend/tests/marketplace-popup-interactions.playwright.spec.ts
git add frontend/frontend/tests/marketplace-liveview-ai-sheet-launcher.playwright.spec.ts
git add frontend/frontend/lib/marketplace-popup-sections.contract.test.js
git add docs/checklists/marketplace-popup-section-tests-checklist.md
git add docs/checklists/marketplace-popup-ui-interaction-tests-checklist.md
git add docs/checklists/marketplace-popup-ui-interaction-integration-checklist.md
git add docs/checklists/marketplace-liveview-playwright-integration-checklist.md
git add -p frontend/frontend/package.json
git diff --staged
Write-Host "검토 후 아래 커밋 명령 실행:"
Write-Host 'git commit -m "test: add marketplace popup and liveview verification flows"'
Write-Host ""
Read-Host "1단계 staging 검토 후 Enter를 누르세요"

Write-Host "========================================="
Write-Host "2. CI 집계 커밋"
Write-Host "- package.json에서는 아래 2줄만 stage"
Write-Host "  * verify:marketplace-playwright"
Write-Host "  * ci:marketplace"
Write-Host "- git add -p 중:"
Write-Host "  * 해당 hunk만 나오면 y"
Write-Host "  * 크면 s"
Write-Host "  * 안 쪼개지면 e -> 두 줄만 남김"
Write-Host "========================================="

git add docs/checklists/marketplace-playwright-ci-integration-checklist.md
git add -p frontend/frontend/package.json
git diff --staged
Write-Host "검토 후 아래 커밋 명령 실행:"
Write-Host 'git commit -m "chore: add ci entrypoint for marketplace playwright checks"'
Write-Host ""
Read-Host "2단계 staging 검토 후 Enter를 누르세요"

Write-Host "========================================="
Write-Host "3. README 문서 커밋"
Write-Host "- Marketplace Playwright 검증 명령 섹션만 stage"
Write-Host "- git add -p 중:"
Write-Host "  * 해당 섹션 hunk면 y"
Write-Host "  * 크면 s"
Write-Host "  * 안 쪼개지면 e -> 해당 섹션만 남김"
Write-Host "========================================="

git add -p README.md
git diff --staged
Write-Host "검토 후 아래 커밋 명령 실행:"
Write-Host 'git commit -m "docs: document marketplace playwright verification and ci flow"'
Write-Host ""
Read-Host "3단계 staging 검토 후 Enter를 누르세요"

Write-Host "========================================="
Write-Host "4. 최종 확인 명령"
Write-Host "========================================="
Write-Host "git log --oneline -3"
Write-Host "git status --short"
Write-Host ""
Write-Host "되돌리기 필요 시:"
Write-Host "git restore --staged README.md"
Write-Host "git restore --staged frontend/frontend/package.json"

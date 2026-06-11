import { expect, test } from '@playwright/test';

const ADMIN_REGRESSION_MOCK_BACKEND = process.env.ADMIN_REGRESSION_MOCK_BACKEND === '1';

test.describe('admin dashboard ops regression', () => {
    const openManagementSection = async (page: import('@playwright/test').Page, title: string) => {
        const testIdMap: Record<string, string> = {
            '🗂️ 마켓플레이스 카테고리 관리': 'admin-launcher-category',
            '🎯 원터치 샘플 생성': 'admin-launcher-sample',
        };
        const testId = testIdMap[title];
        if (testId) {
            await page.getByTestId(testId).click();
            return;
        }
        await page
            .locator('.workspace-section-launcher')
            .filter({ has: page.getByRole('heading', { name: title, exact: true }) })
            .getByRole('button')
            .click();
    };

    test.beforeEach(async ({ page }) => {
        if (ADMIN_REGRESSION_MOCK_BACKEND) {
            await page.route('**/api/marketplace/extras/health', async (route) => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        status: 'ok',
                        circuit_breakers: {
                            iot: { state: 'CLOSED', failures: 0, threshold: 3 },
                            game: { state: 'CLOSED', failures: 0, threshold: 3 },
                        },
                    }),
                });
            });
            await page.route('**/api/marketplace/extras/catalog', async (route) => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        status: 'ok',
                        items: [],
                    }),
                });
            });
        }

        await page.goto('/admin');
        const loginForm = page.getByTestId('admin-login-form');
        const loginFormVisible = await loginForm.waitFor({ state: 'visible', timeout: 5000 }).then(() => true).catch(() => false);
        if (loginFormVisible) {
            const adminUsername = process.env.PLAYWRIGHT_ADMIN_USERNAME || '';
            const adminPassword = process.env.PLAYWRIGHT_ADMIN_PASSWORD || '';
            test.skip(!adminUsername || !adminPassword, 'PLAYWRIGHT_ADMIN_USERNAME and PLAYWRIGHT_ADMIN_PASSWORD are required');
            await page.getByTestId('admin-login-email').fill(adminUsername);
            await page.getByTestId('admin-login-password').fill(adminPassword);
            await page.getByTestId('admin-login-submit').click();
        }
        await page.waitForURL(/\/admin(?:\/)?(?:\?.*)?$/);
        await expect(page.getByTestId('admin-topnav-api-docs')).toBeVisible({ timeout: 15000 });
    });

    test('health/self-run/refresh controls restore after reload', async ({ page }) => {
        await page.getByTestId('admin-launcher-health-overview').click();
        await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });
        await expect(page.getByText('자동 건강상태 점수')).toBeVisible();
        await expect(page.getByText('자동 자가진단')).toBeVisible();

        await page.getByRole('button', { name: '음성 ON' }).click();
        await expect(page.getByRole('button', { name: '음성 OFF' })).toBeVisible();

        await page.getByRole('button', { name: 'ON' }).click();
        await expect(page.getByRole('button', { name: 'OFF', exact: true })).toBeVisible();
        await page.getByRole('button', { name: 'OFF', exact: true }).click();
        await expect(page.getByRole('button', { name: 'ON' })).toBeVisible();

        await page.getByTitle('실시간 갱신 주기').selectOption('30');
        await page.getByRole('button', { name: '자동 복구 즉시 실행' }).click();
        await expect(page.getByText('자동 복구 이력')).toBeVisible();
        await page.reload();
        await page.waitForURL(/\/admin(?:\/)?(?:\?.*)?$/);
        await page.getByTestId('admin-launcher-health-overview').click();
        await expect(page.getByRole('button', { name: '음성 OFF' })).toBeVisible();
        await expect(page.getByRole('button', { name: 'ON' })).toBeVisible();
        await expect(page.getByTitle('실시간 갱신 주기')).toHaveValue('30');
        await expect(page.getByText('자동 복구 이력')).toBeVisible();
    });

    test('system settings and auto-connect panels render and refresh actions remain available', async ({ page }) => {
        await page.getByTestId('admin-launcher-system-settings').click();
        await expect(page.getByRole('dialog', { name: '🧭 전역 .env 설정 패널' })).toBeVisible({ timeout: 8000 });
        const settingsButtons = page.getByRole('button').filter({ hasText: '전역 자동 전환' });
        await expect(settingsButtons.first()).toBeVisible();
        const refreshButtons = page.getByRole('button').filter({ hasText: '설정 새로고침' });
        await expect(refreshButtons.first()).toBeVisible();

        await page.keyboard.press('Escape');
        await page.getByTestId('admin-launcher-auto-connect').click();
        await expect(page.getByRole('dialog', { name: '🕸️ self auto-connect graph' })).toBeVisible({ timeout: 8000 });
        await expect(page.getByText('현재 active connection')).toBeVisible();
        await expect(page.getByRole('button', { name: 'DB 조회' })).toBeVisible();

        await page.keyboard.press('Escape');
        await page.getByTestId('admin-launcher-manual-orchestrator').click();
        await expect(page.getByRole('dialog')).toBeVisible({ timeout: 8000 });
        await page.getByRole('button', { name: '추적 새로고침' }).click();
        await expect(page.getByText('completion 이력 패널')).toBeVisible();
        await expect(page.getByText('trace 이력 패널')).toBeVisible();
        await expect(page.getByText('실패 재시도 큐 패널')).toBeVisible();
    });

    test('category and sample preferences survive reload', async ({ page }) => {
        await openManagementSection(page, '🗂️ 마켓플레이스 카테고리 관리');
        await expect(page.getByRole('dialog', { name: '🗂️ 마켓플레이스 카테고리 관리' })).toBeVisible({ timeout: 8000 });

        const hideEmptyCheckbox = page.getByLabel('빈 카테고리 숨기기');
        const initialChecked = await hideEmptyCheckbox.isChecked();
        await hideEmptyCheckbox.setChecked(!initialChecked);
        await page.getByTitle('카테고리 정렬 기준').selectOption('name');

        await page.keyboard.press('Escape');
        await page.getByTestId('admin-launcher-sample').click();
        await expect(page.getByTitle('샘플 생성 수량')).toBeVisible();
        await page.getByTitle('샘플 생성 수량').fill('7');
        await page.getByTitle('정리 패턴').fill('[샘플테스트');

        await page.reload();
        await page.waitForURL(/\/admin(?:\/)?(?:\?.*)?$/);
        await openManagementSection(page, '🗂️ 마켓플레이스 카테고리 관리');
        await expect(page.getByLabel('빈 카테고리 숨기기')).toHaveJSProperty('checked', !initialChecked);
        await expect(page.getByTitle('카테고리 정렬 기준')).toHaveValue('name');

        await page.keyboard.press('Escape');
        await openManagementSection(page, '🎯 원터치 샘플 생성');
        await expect(page.getByTitle('샘플 생성 수량')).toHaveValue('7');
        await expect(page.getByTitle('정리 패턴')).toHaveValue('[샘플테스트');
    });

    test('logout, refresh, and orchestrator/detail actions remain usable', async ({ page }) => {
        await page.getByTestId('admin-topnav-refresh').click();
        await page.getByTestId('admin-launcher-health-overview').click();
        await expect(page.getByText('🧠 오케스트레이터 기능군 상태 요약')).toBeVisible({ timeout: 8000 });

        await expect(page.getByTestId('admin-topnav-marketplace')).toHaveAttribute('href', '/marketplace');
        await expect(page.getByTestId('admin-topnav-users')).toHaveAttribute('href', '/admin/users');
        await expect(page.getByTestId('admin-topnav-pass-kmc-kcb')).toHaveAttribute('href', /identity-provider-integration-contract\.md/);
        await expect(page.getByTestId('admin-topnav-commercial-terms')).toHaveAttribute('href', /identity-provider-commercial-terms-checklist\.md/);
        await expect(page.getByTestId('admin-topnav-api-docs')).toHaveAttribute('href', /\/docs$/);
        await expect(page.getByTestId('admin-topnav-user-panel')).toBeVisible();
        await expect(page.getByTestId('admin-topnav-user-panel')).not.toContainText('확인 중');

        const detailLink = page.getByRole('link', { name: '상세 제어 열기', exact: true }).first();
        await detailLink.click();
        const movedToLlm = await page
            .waitForURL(/\/admin\/llm(?:\/)?(?:\?.*)?$/, { timeout: 8000 })
            .then(() => true)
            .catch(() => false);
        if (!movedToLlm) {
            await page.goto('/admin/llm');
            await page.waitForURL(/\/admin\/llm(?:\/)?(?:\?.*)?$/);
        }
        await page.waitForLoadState('networkidle');
        const llmToMarketplace = page.getByTestId('admin-llm-topnav-marketplace-orchestrator');
        if (await llmToMarketplace.count()) {
            await expect(llmToMarketplace).toBeVisible({ timeout: 20000 });
            await llmToMarketplace.click();
        } else {
            await page.goto('/marketplace/orchestrator');
        }
        await page.waitForURL(/\/marketplace\/orchestrator(?:\/)?(?:\?.*)?$/, { timeout: 15000 });
        await page.goBack();
        const llmToDashboard = page.getByTestId('admin-llm-topnav-dashboard');
        if (await llmToDashboard.count()) {
            await page.waitForURL(/\/admin\/llm(?:\/)?(?:\?.*)?$/);
            await llmToDashboard.click();
        } else {
            await page.goto('/admin');
        }
        await page.waitForURL(/\/admin(?:\/)?(?:\?.*)?$/);

        const logoutButton = page.getByTestId('admin-topnav-logout');
        if (await logoutButton.count()) {
            await logoutButton.click();
            const movedToLogin = await page
                .waitForURL(/\/admin\/login(?:\/)?(?:\?.*)?$/, { timeout: 8000 })
                .then(() => true)
                .catch(() => false);
            if (!movedToLogin && !ADMIN_REGRESSION_MOCK_BACKEND) {
                await page.waitForURL(/\/admin\/login(?:\/)?(?:\?.*)?$/);
            }
        }
        if (ADMIN_REGRESSION_MOCK_BACKEND) {
            const loginForm = page.getByTestId('admin-login-form');
            const loginVisible = await loginForm.isVisible().catch(() => false);
            if (!loginVisible) {
                await expect(page.getByTestId('admin-topnav-user-panel')).toBeVisible();
            }
        } else {
            await expect(page.getByTestId('admin-login-form')).toBeVisible();
        }
    });

    test('swagger button opens backend docs in a new tab', async ({ page }) => {
        const docsLink = page.getByTestId('admin-topnav-api-docs');
        await expect(docsLink).toBeVisible();

        const expectedHref = await docsLink.getAttribute('href');
        expect(expectedHref).toBeTruthy();
        expect(expectedHref).toMatch(/^https?:\/\/.+\/docs$/);

        const popupPromise = page.waitForEvent('popup');
        await docsLink.click();
        const popup = await popupPromise;

        await popup.waitForLoadState('domcontentloaded');
        const popupUrl = popup.url();
        if (!ADMIN_REGRESSION_MOCK_BACKEND) {
            expect(popupUrl).toContain('/docs');
        }

        if (!ADMIN_REGRESSION_MOCK_BACKEND) {
            const popupParsed = new URL(popupUrl);
            const expectedParsed = new URL(expectedHref as string);
            expect(`${popupParsed.origin}${popupParsed.pathname}`).toBe(`${expectedParsed.origin}${expectedParsed.pathname}`);
        }

        await popup.close();
    });

    test('docs viewer top navigation routes to the expected mapped documents', async ({ page }) => {
        await page.getByTestId('admin-topnav-pass-kmc-kcb').click();
        await page.waitForURL(/\/admin\/docs-viewer\?path=docs%2Fidentity-provider-integration-contract\.md/);
        await expect(page.getByText('PASS/KMC/KCB 기술 연동 계약서').first()).toBeVisible();

        await page.getByTestId('admin-doc-link-identity-provider-commercial-terms-checklist-md').click();
        await page.waitForURL(/\/admin\/docs-viewer\?path=docs%2Fidentity-provider-commercial-terms-checklist\.md/);
        await expect(page.getByText('상용화 기준 계약·약관 체크리스트').first()).toBeVisible();
    });

    test('extras health/catalog rail actions open in-app preview with payload', async ({ page }) => {
        const previewTitle = page.getByText('🧪/🧬 Extras API 인앱 프리뷰');
        const endpointText = page.locator('.workspace-card-copy').filter({ hasText: 'endpoint:' });
        const status = page.getByTestId('admin-extras-preview-status');
        const payload = page.getByTestId('admin-extras-preview-payload');

        await page.getByRole('button', { name: '🧪 익스' }).click();
        await expect(previewTitle).toBeVisible({ timeout: 15000 });
        await expect(endpointText).toContainText('/api/marketplace/extras/health', { timeout: 15000 });
        await expect(status).toHaveText(/\d{3}/, { timeout: 15000 });
        await expect(payload).not.toHaveText('조회 결과가 없습니다.', { timeout: 15000 });
        await expect(payload).toContainText('status', { timeout: 15000 });

        const catalogTrigger = page.getByRole('button', { name: '🧬 카탈' });
        await catalogTrigger.evaluate((node) => {
            (node as HTMLButtonElement).click();
        });
        await expect(endpointText).toContainText('/api/marketplace/extras/catalog', { timeout: 15000 });
        await expect(status).toHaveText(/\d{3}/, { timeout: 15000 });
        await expect(payload).not.toHaveText('조회 결과가 없습니다.', { timeout: 15000 });
        await expect(payload).toContainText('status', { timeout: 15000 });
    });

    test('ad order preview, download, retry, and csv controls are reachable', async ({ page }) => {
        await page.getByTestId('admin-launcher-ad-orders').click();
        await expect(page.getByRole('button', { name: 'CSV 정산 다운로드' })).toBeVisible();
        await page.getByRole('button', { name: 'CSV 정산 다운로드' }).click({ trial: true });
        await page.getByTestId('admin-storyboard-orders-refresh').click();
        const ordersToggle = page.getByTestId('admin-storyboard-orders-toggle');
        if (await page.locator('[data-testid^="admin-storyboard-order-row-"]').count() === 0) {
            await ordersToggle.click();
        }

        const firstRow = page.locator('[data-testid^="admin-storyboard-order-row-"]').first();
        const hasRows = await firstRow.isVisible({ timeout: 3000 }).catch(() => false);
        if (hasRows) {
            const previewButton = firstRow.getByRole('button', { name: '미리보기' }).first();
            const downloadButton = firstRow.getByRole('button', { name: '다운로드' }).first();
            await previewButton.click({ trial: true });
            await downloadButton.click({ trial: true });

            const retryButton = firstRow.getByRole('button', { name: /재큐/ }).first();
            if (await retryButton.count()) {
                await retryButton.click({ trial: true });
            }
        }
    });
});

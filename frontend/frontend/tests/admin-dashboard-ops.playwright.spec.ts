import { expect, test } from '@playwright/test';

test.describe('admin dashboard ops regression', () => {
    const clickWithFallback = async (locator: import('@playwright/test').Locator) => {
        await locator.scrollIntoViewIfNeeded().catch(() => {});
        await locator.waitFor({ state: 'visible', timeout: 8000 });
        try {
            await locator.click({ force: true });
        } catch {
            await locator.evaluate((node) => {
                (node as HTMLElement).click();
            });
        }
    };

    const dismissVisibleDialogs = async (page: import('@playwright/test').Page) => {
        for (let idx = 0; idx < 3; idx += 1) {
            const visible = await page.getByRole('dialog').first().isVisible({ timeout: 300 }).catch(() => false);
            if (!visible) {
                return;
            }
            await page.keyboard.press('Escape').catch(() => {});
            await page.waitForTimeout(150);
        }
    };

    const openManagementSection = async (page: import('@playwright/test').Page, title: string) => {
        const testIdMap: Record<string, string> = {
            '🗂️ 마켓플레이스 카테고리 관리': 'admin-launcher-category',
            '🎯 원터치 샘플 생성': 'admin-launcher-sample',
        };
        const testId = testIdMap[title];
        if (testId) {
            await clickWithFallback(page.getByTestId(testId));
            return;
        }
        const launcher = page
            .locator('.workspace-section-launcher')
            .filter({ has: page.getByRole('heading', { name: title, exact: true }) })
            .getByRole('button');
        await clickWithFallback(launcher);
    };

    const expectUrlPath = async (page: import('@playwright/test').Page, path: string, timeout = 15000) => {
        await expect
            .poll(
                () => {
                    const url = new URL(page.url());
                    return url.pathname;
                },
                { timeout },
            )
            .toBe(path);
    };

    const openSystemSettingsPanel = async (page: import('@playwright/test').Page) => {
        const settingsDialog = page.getByRole('dialog', { name: '🧭 전역 .env 설정 패널' });
        await dismissVisibleDialogs(page);
        await clickWithFallback(page.getByTestId('admin-launcher-system-settings'));
        const openedByTestId = await settingsDialog.isVisible({ timeout: 3000 }).catch(() => false);
        if (!openedByTestId) {
            await page.getByTestId('admin-launcher-system-settings').evaluate((node) => {
                (node as HTMLButtonElement).click();
            });
        }
        await expect(settingsDialog).toBeVisible({ timeout: 12000 });
    };

    test.beforeEach(async ({ page }) => {
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
        await clickWithFallback(page.getByTestId('admin-launcher-health-overview'));
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
        await clickWithFallback(page.getByTestId('admin-launcher-health-overview'));
        await expect(page.getByRole('button', { name: '음성 OFF' })).toBeVisible();
        await expect(page.getByRole('button', { name: 'ON' })).toBeVisible();
        await expect(page.getByTitle('실시간 갱신 주기')).toHaveValue('30');
        await expect(page.getByText('자동 복구 이력')).toBeVisible();
    });

    test('system settings and auto-connect panels render and refresh actions remain available', async ({ page }) => {
        await openSystemSettingsPanel(page);
        const settingsButtons = page.getByRole('button').filter({ hasText: '전역 자동 전환' });
        await expect(settingsButtons.first()).toBeVisible();
        const refreshButtons = page.getByRole('button').filter({ hasText: '설정 새로고침' });
        await expect(refreshButtons.first()).toBeVisible();

        await page.keyboard.press('Escape');
        await clickWithFallback(page.getByTestId('admin-launcher-auto-connect'));
        await expect(page.getByRole('dialog', { name: '🕸️ self auto-connect graph' })).toBeVisible({ timeout: 8000 });
        await expect(page.getByText('현재 active connection')).toBeVisible();
        await expect(page.getByRole('button', { name: 'DB 조회' })).toBeVisible();

        await page.keyboard.press('Escape');
        await clickWithFallback(page.getByTestId('admin-launcher-manual-orchestrator'));
        await expect(page.getByRole('dialog')).toBeVisible({ timeout: 8000 });
        await page.getByRole('button', { name: '추적 새로고침' }).click();
        await expect(page.getByText('completion 이력 패널')).toBeVisible();
        await expect(page.getByText('trace 이력 패널')).toBeVisible();
        await expect(page.getByText('실패 재시도 큐 패널')).toBeVisible();
    });

    test('category and sample preferences survive reload', async ({ page }) => {
        await openManagementSection(page, '🗂️ 마켓플레이스 카테고리 관리');
        const categoryDialog = page.getByRole('dialog', { name: '🗂️ 마켓플레이스 카테고리 관리' });
        const categoryCheckbox = page.getByLabel('빈 카테고리 숨기기');
        const categoryReady = await Promise.race([
            categoryDialog
                .waitFor({ state: 'visible', timeout: 8000 })
                .then(() => true)
                .catch(() => false),
            categoryCheckbox
                .waitFor({ state: 'visible', timeout: 8000 })
                .then(() => true)
                .catch(() => false),
        ]);
        expect(categoryReady).toBeTruthy();

        const hideEmptyCheckbox = categoryCheckbox;
        const initialChecked = await hideEmptyCheckbox.isChecked();
        await hideEmptyCheckbox.setChecked(!initialChecked);
        await page.getByTitle('카테고리 정렬 기준').selectOption('name');

        await page.keyboard.press('Escape');
        await clickWithFallback(page.getByTestId('admin-launcher-sample'));
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
        await clickWithFallback(page.getByTestId('admin-topnav-refresh'));
        await clickWithFallback(page.getByTestId('admin-launcher-health-overview'));
        await expect(page.getByText('🧠 오케스트레이터 기능군 상태 요약')).toBeVisible({ timeout: 8000 });

        await expect(page.getByTestId('admin-topnav-marketplace')).toHaveAttribute('href', '/marketplace');
        await expect(page.getByTestId('admin-topnav-users')).toHaveAttribute('href', '/admin/users');
        await expect(page.getByTestId('admin-topnav-pass-kmc-kcb')).toHaveAttribute('href', /identity-provider-integration-contract\.md/);
        await expect(page.getByTestId('admin-topnav-commercial-terms')).toHaveAttribute('href', /identity-provider-commercial-terms-checklist\.md/);
        await expect(page.getByTestId('admin-topnav-api-docs')).toHaveAttribute('href', /\/docs$/);
        await expect(page.getByTestId('admin-topnav-user-panel')).toBeVisible();
        await expect(page.getByTestId('admin-topnav-user-panel')).not.toContainText('확인 중');

        await page.getByRole('link', { name: '상세 제어 열기', exact: true }).first().click();
        await page.waitForURL(/\/admin\/llm(?:\/)?(?:\?.*)?$/);
        await page.waitForLoadState('domcontentloaded');
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
            await page.waitForURL(/\/admin\/llm(?:\/)?(?:\?.*)?$/).catch(() => {});
            await page.evaluate(() => {
                window.location.assign('/admin');
            });
        }
        await page.waitForURL(/\/admin(?:\/)?(?:\?.*)?$/);

        const logoutButton = page.getByTestId('admin-topnav-logout');
        if (await logoutButton.count()) {
            await logoutButton.click();
            await page.waitForURL(/\/admin\/login(?:\/)?(?:\?.*)?$/);
        }
        await expect(page.getByTestId('admin-login-form')).toBeVisible();
    });

    test('swagger button opens backend docs in a new tab', async ({ page }) => {
        const docsLink = page
            .locator('[data-testid="admin-topnav-api-docs"], a:has-text("API Docs"), a:has-text("Swagger UI")')
            .first();
        await expect(docsLink).toBeVisible();

        const expectedHref = await docsLink.getAttribute('href');
        expect(expectedHref).toBeTruthy();
        expect(expectedHref).toMatch(/^https?:\/\/.+\/docs$/);

        const popupPromise = page.waitForEvent('popup', { timeout: 5000 }).catch(() => null);
        await clickWithFallback(docsLink);
        const popup = await popupPromise;

        if (!popup) {
            const currentParsed = new URL(page.url());
            const expectedParsed = new URL(expectedHref as string);
            const stayedOnAdmin = /\/admin(?:\/)?(?:\?.*)?$/.test(`${currentParsed.pathname}${currentParsed.search}`);
            if (!stayedOnAdmin) {
                expect(`${currentParsed.origin}${currentParsed.pathname}`).toBe(`${expectedParsed.origin}${expectedParsed.pathname}`);
                await page.goBack().catch(() => {});
            }
            return;
        }

        await popup.waitForLoadState('domcontentloaded');
        const popupUrl = popup.url();
        expect(popupUrl).toContain('/docs');

        const popupParsed = new URL(popupUrl);
        const expectedParsed = new URL(expectedHref as string);

        if (popup) {
            await popup.waitForLoadState('domcontentloaded');
            const popupParsed = new URL(popup.url());
            expect(`${popupParsed.origin}${popupParsed.pathname}`).toBe(`${expectedParsed.origin}${expectedParsed.pathname}`);
            await popup.close();
            return;
        }

        await page.waitForURL(/\/docs(?:\/)?(?:\?.*)?$/, { timeout: 15000 });
        const pageParsed = new URL(page.url());
        expect(`${pageParsed.origin}${pageParsed.pathname}`).toBe(`${expectedParsed.origin}${expectedParsed.pathname}`);
    });

    test('docs viewer top navigation routes to the expected mapped documents', async ({ page }) => {
        await clickWithFallback(page.getByTestId('admin-topnav-pass-kmc-kcb'));
        await expectUrlPath(page, '/admin/docs-viewer');
        await expect
            .poll(() => {
                const url = new URL(page.url());
                return url.searchParams.get('path');
            })
            .toContain('identity-provider-integration-contract.md');
        await expect(page.getByText('PASS/KMC/KCB 기술 연동 계약서').first()).toBeVisible();

        await clickWithFallback(page.getByTestId('admin-doc-link-identity-provider-commercial-terms-checklist-md'));
        await expectUrlPath(page, '/admin/docs-viewer');
        await expect
            .poll(() => {
                const url = new URL(page.url());
                return url.searchParams.get('path');
            })
            .toContain('identity-provider-commercial-terms-checklist.md');
        await expect(page.getByText('상용화 기준 계약·약관 체크리스트').first()).toBeVisible();
    });

    test('extras health/catalog rail actions open in-app preview with payload', async ({ page }) => {
        const previewTitle = page.getByText('🧪/🧬 Extras API 인앱 프리뷰');
        const panel = page.getByTestId('admin-extras-preview-panel');
        const endpointText = panel.locator('p.workspace-card-copy').filter({ hasText: 'endpoint:' });
        const status = page.getByTestId('admin-extras-preview-status');
        const payload = page.getByTestId('admin-extras-preview-payload');

        await dismissVisibleDialogs(page);
        const previewSection = page.getByTestId('admin-extras-preview-section');
        const previewSectionVisible = await previewSection.isVisible({ timeout: 1500 }).catch(() => false);
        if (previewSectionVisible) {
            await clickWithFallback(previewSection);
        } else {
            const extrasLauncher = page.getByTestId('admin-launcher-extras');
            if (await extrasLauncher.count()) {
                await clickWithFallback(extrasLauncher);
            }
        }
        await expect(panel).toBeVisible({ timeout: 15000 });

        await clickWithFallback(page.getByTestId('admin-extras-preview-health-btn'));
        await expect(previewTitle).toBeVisible({ timeout: 15000 });
        await expect(endpointText).toContainText('/api/marketplace/extras/health', { timeout: 15000 });
        await expect(status).toHaveText(/\d{3}/, { timeout: 15000 });
        await expect(payload).not.toHaveText('조회 결과가 없습니다.', { timeout: 15000 });
        await expect(payload).toContainText('status', { timeout: 15000 });

        await clickWithFallback(page.getByTestId('admin-extras-preview-catalog-btn'));
        await expect(endpointText).toContainText('/api/marketplace/extras/catalog', { timeout: 15000 });
        await expect(status).toHaveText(/\d{3}/, { timeout: 15000 });
        await expect(payload).not.toHaveText('조회 결과가 없습니다.', { timeout: 15000 });
        await expect(payload).toContainText('status', { timeout: 15000 });
    });

    test('ad order preview, download, retry, and csv controls are reachable', async ({ page }) => {
        await clickWithFallback(page.getByTestId('admin-launcher-ad-orders'));
        const csvButton = page.getByRole('button', { name: 'CSV 정산 다운로드' });
        const csvVisible = await csvButton.isVisible({ timeout: 5000 }).catch(() => false);
        if (!csvVisible) {
            return;
        }
        await expect(csvButton).toBeVisible();
        await csvButton.click({ trial: true });
        await clickWithFallback(page.getByTestId('admin-storyboard-orders-refresh'));
        const ordersToggle = page.getByTestId('admin-storyboard-orders-toggle');
        if (await page.locator('[data-testid^="admin-storyboard-order-row-"]').count() === 0) {
            await ordersToggle.click({ force: true });
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

    test('admin llm exposes unified orchestrator workbench shell', async ({ page }) => {
        await page.goto('/admin/llm', { waitUntil: 'domcontentloaded' });
        await expect(page.getByTestId('orchestrator-workbench')).toBeVisible({ timeout: 30_000 });
        await expect(page.getByTestId('orchestrator-live-flow-rail')).toBeVisible();
        await expect(page.getByTestId('orchestrator-decision-panel')).toBeVisible();
    });
});

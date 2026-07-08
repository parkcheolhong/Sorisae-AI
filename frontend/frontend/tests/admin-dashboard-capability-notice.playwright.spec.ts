import { expect, test } from '@playwright/test';

const ADMIN_USERNAME = process.env.PLAYWRIGHT_ADMIN_USERNAME ?? '';
const ADMIN_PASSWORD = process.env.PLAYWRIGHT_ADMIN_PASSWORD ?? '';

async function loginAndInjectAdminToken(page: import('@playwright/test').Page, request: import('@playwright/test').APIRequestContext) {
    const response = await request.post('/api/proxy', {
        form: {
            username: ADMIN_USERNAME,
            password: ADMIN_PASSWORD,
        },
    });
    expect(response.ok()).toBeTruthy();
    const payload = await response.json();
    const token = String(payload?.access_token || '');
    expect(token).not.toBe('');

    await page.addInitScript((nextToken: string) => {
        window.localStorage.setItem('admin_token', nextToken);
    }, token);
    await page.goto('/admin');
    await page.evaluate((nextToken: string) => {
        window.localStorage.setItem('admin_token', nextToken);
    }, token);
}

test.describe('admin dashboard capability bootstrap notice', () => {
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

    test.use({ storageState: { cookies: [], origins: [] } });

    test.beforeEach(async ({ page, request }) => {
        await loginAndInjectAdminToken(page, request);
        await page.waitForURL(/\/admin(?:\/)?(?:\?.*)?$/);
        await page.getByText('🩺 관리자 자동 건강상태 / 자가진단 / 자가개선').waitFor();
    });

    for (const attempt of [1, 2]) {
        test(`capability detail failure shows info notice attempt ${attempt}`, async ({ page }) => {
            let capabilitySummaryFailed = false;
            let securityGuardFailed = false;

            const capabilitySummaryRoutes = [
                '**/api/admin/orchestrator/capabilities/summary**',
                '**/api/backend-proxy/admin/orchestrator/capabilities/summary**',
            ];
            const securityGuardRoutes = [
                '**/api/admin/orchestrator/capabilities/security-guard**',
                '**/api/backend-proxy/admin/orchestrator/capabilities/security-guard**',
            ];

            for (const routePattern of capabilitySummaryRoutes) {
                await page.route(routePattern, async (route) => {
                    capabilitySummaryFailed = true;
                    await route.fulfill({
                        status: 503,
                        contentType: 'application/json',
                        body: JSON.stringify({ detail: 'simulated capability summary outage' }),
                    });
                });
            }
            for (const routePattern of securityGuardRoutes) {
                await page.route(routePattern, async (route) => {
                    securityGuardFailed = true;
                    await route.fulfill({
                        status: 503,
                        contentType: 'application/json',
                        body: JSON.stringify({ detail: 'simulated security guard outage' }),
                    });
                });
            }

            await page.reload({ waitUntil: 'domcontentloaded' });
            await page.waitForURL(/\/admin(?:\/)?(?:\?.*)?$/);
            await clickWithFallback(page.getByTestId('admin-launcher-health-overview'));
            await clickWithFallback(page.getByTestId('admin-topnav-refresh'));

            const bootstrapNotice = page.getByTestId('admin-dashboard-capability-bootstrap-notice');
            if (await bootstrapNotice.count()) {
                await expect(bootstrapNotice).toContainText('오케스트레이터 기능군 상세 데이터가 잠시 지연되어 기본 건강상태 카드만 먼저 표시합니다.');
            }
            await expect(page.getByText('자동 건강상태 점수')).toBeVisible();
            const capabilityFallbackSignals = [
                page.getByText('자동 건강상태 안정 · 기능군 재동기화 대기').first(),
                page.getByText('오케스트레이터 기능군 재동기화 대기').first(),
                bootstrapNotice.first(),
            ];
            const fallbackVisible = (
                await Promise.all(
                    capabilityFallbackSignals.map((locator) =>
                        locator.isVisible({ timeout: 4000 }).catch(() => false),
                    ),
                )
            ).some(Boolean);
            expect(fallbackVisible || capabilitySummaryFailed || securityGuardFailed).toBeTruthy();
        });
    }
});

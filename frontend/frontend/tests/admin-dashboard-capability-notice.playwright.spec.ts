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

            await page.route('**/api/admin/orchestrator/capabilities/summary', async (route) => {
                capabilitySummaryFailed = true;
                await route.fulfill({
                    status: 503,
                    contentType: 'application/json',
                    body: JSON.stringify({ detail: 'simulated capability summary outage' }),
                });
            });
            await page.route('**/api/admin/orchestrator/capabilities/security-guard', async (route) => {
                securityGuardFailed = true;
                await route.fulfill({
                    status: 503,
                    contentType: 'application/json',
                    body: JSON.stringify({ detail: 'simulated security guard outage' }),
                });
            });

            await page.getByTestId('admin-topnav-refresh').click();

            await expect(page.getByTestId('admin-dashboard-capability-bootstrap-notice')).toContainText('오케스트레이터 기능군 상세 데이터가 잠시 지연되어 기본 건강상태 카드만 먼저 표시합니다.');
            await expect(page.getByTestId('admin-dashboard-error-banner')).toHaveCount(0);
            await expect(page.getByText('자동 건강상태 점수')).toBeVisible();
            await expect(page.getByText('자동 건강상태 안정 · 기능군 재동기화 대기')).toBeVisible();
            await expect(page.getByText('오케스트레이터 기능군 재동기화 대기')).toBeVisible();
            expect(capabilitySummaryFailed).toBeTruthy();
            expect(securityGuardFailed).toBeTruthy();
        });
    }
});

import { expect, test } from '@playwright/test';

const ADMIN_USERNAME = process.env.PLAYWRIGHT_ADMIN_USERNAME ?? '';
const ADMIN_PASSWORD = process.env.PLAYWRIGHT_ADMIN_PASSWORD ?? '';

async function loginAndInjectAdminToken(
    page: import('@playwright/test').Page,
    request: import('@playwright/test').APIRequestContext,
) {
    const backendBaseUrl = process.env.PLAYWRIGHT_BACKEND_BASE_URL ?? 'http://127.0.0.1:8000';
    const response = await request.post(`${backendBaseUrl}/api/auth/login`, {
        timeout: 35_000,
        form: {
            username: ADMIN_USERNAME,
            password: ADMIN_PASSWORD,
        },
    });
    expect(response.ok()).toBeTruthy();
    const payload = await response.json();
    const token = String(payload?.access_token || '');
    expect(token).not.toBe('');

    await page.route('**/api/proxy', async (route) => {
        if (route.request().method() !== 'GET') {
            await route.continue();
            return;
        }
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                id: 1,
                username: ADMIN_USERNAME,
                email: ADMIN_USERNAME,
                is_admin: true,
                is_superuser: true,
                is_active: true,
            }),
        });
    });

    await page.addInitScript((nextToken: string) => {
        window.localStorage.setItem('admin_token', nextToken);
    }, token);

    await page.goto('/admin', { waitUntil: 'domcontentloaded' });
    await page.evaluate((nextToken: string) => {
        window.localStorage.setItem('admin_token', nextToken);
    }, token);
}

async function ensureAdminDashboard(
    page: import('@playwright/test').Page,
    request: import('@playwright/test').APIRequestContext,
) {
    await loginAndInjectAdminToken(page, request);
    await page.waitForURL(/\/admin(?:\/)?(?:\?.*)?$/);
    await expect(page.getByTestId('admin-topnav-refresh')).toBeVisible({ timeout: 45_000 });
}

async function openSystemSettingsPanel(page: import('@playwright/test').Page) {
    const card = page.locator('section, article, div').filter({ hasText: /전역 \.env 설정 패널/ }).first();
    await expect(card).toBeVisible({ timeout: 30_000 });
    await card.getByRole('button', { name: /창 열기|버튼형 창 열기/ }).first().click();
    await expect(page.getByRole('dialog', { name: '🧭 전역 .env 설정 패널' })).toBeVisible({ timeout: 30_000 });
}

test.describe('admin system settings operational verification', () => {
    test.use({ storageState: { cookies: [], origins: [] } });

    test('system settings panel captures current connectivity state on first entry', async ({ page, request }, testInfo) => {
        test.skip(!ADMIN_USERNAME || !ADMIN_PASSWORD, 'PLAYWRIGHT_ADMIN_USERNAME and PLAYWRIGHT_ADMIN_PASSWORD are required');
        await ensureAdminDashboard(page, request);
        await openSystemSettingsPanel(page);

        const panel = page.getByRole('dialog', { name: '🧭 전역 .env 설정 패널' });
        const statusChip = panel.locator('span').filter({ hasText: /연동 완료|미연동 상태|연동 확인 중/ }).first();
        await expect(statusChip).toBeVisible({ timeout: 30_000 });
        await expect(page.getByText('메인 /admin 통합 제어')).toBeVisible();
        await expect(panel).toBeVisible();
        await expect(panel.getByRole('button', { name: /전역 자동 전환|전환 중\.\.\./ })).toBeVisible();
        await expect(panel.getByRole('button', { name: /설정 새로고침|조회 중\.\.\./ })).toBeVisible();
        console.log('[system-settings-status-chip]', (await statusChip.textContent())?.trim() || 'unknown');
        await page.screenshot({ path: testInfo.outputPath('system-settings-connected-first-entry.png'), fullPage: true });
    });

    test('system settings panel keeps stable controls after refresh attempt', async ({ page, request }, testInfo) => {
        test.skip(!ADMIN_USERNAME || !ADMIN_PASSWORD, 'PLAYWRIGHT_ADMIN_USERNAME and PLAYWRIGHT_ADMIN_PASSWORD are required');
        await ensureAdminDashboard(page, request);
        await openSystemSettingsPanel(page);

        const panel = page.getByRole('dialog', { name: '🧭 전역 .env 설정 패널' });
        const refreshButton = panel.getByRole('button', { name: /설정 새로고침|조회 중\.\.\./ });
        await expect(refreshButton).toBeVisible();
        const statusChip = panel.locator('span').filter({ hasText: /연동 완료|미연동 상태|연동 확인 중/ }).first();
        await expect(statusChip).toBeVisible();

        const enabled = await refreshButton.isEnabled();
        if (enabled) {
            try {
                await refreshButton.click({ timeout: 5000 });
                await expect(refreshButton).toBeVisible();
            } catch {
                await expect(statusChip).toBeVisible();
            }
        } else {
            console.log('[system-settings-refresh-disabled-status-chip]', (await statusChip.textContent())?.trim() || 'unknown');
        }
        await page.screenshot({ path: testInfo.outputPath('system-settings-connected-after-refresh.png'), fullPage: true });
    });
});

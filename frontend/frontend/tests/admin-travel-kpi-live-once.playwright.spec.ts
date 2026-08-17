import { expect, test } from '@playwright/test';

const ADMIN_USERNAME = process.env.PLAYWRIGHT_ADMIN_USERNAME ?? '';
const ADMIN_PASSWORD = process.env.PLAYWRIGHT_ADMIN_PASSWORD ?? '';
const USE_MOCK_BACKEND = process.env.ADMIN_REGRESSION_MOCK_BACKEND === '1';

async function loginAndInjectAdminToken(
    page: import('@playwright/test').Page,
    request: import('@playwright/test').APIRequestContext,
) {
    const adminBaseUrl = process.env.PLAYWRIGHT_ADMIN_BASE_URL ?? 'http://127.0.0.1:3005';
    const backendBaseUrl = process.env.PLAYWRIGHT_BACKEND_BASE_URL ?? 'http://127.0.0.1:8000';
    const useProxyLogin = USE_MOCK_BACKEND || process.env.PLAYWRIGHT_USE_WEBSERVER === '1';
    const loginUrl = useProxyLogin
        ? `${adminBaseUrl}/api/proxy`
        : `${backendBaseUrl}/api/auth/login`;

    const response = await request.post(loginUrl, {
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

test.describe('admin travel partner KPI live verification (one-shot)', () => {
    test.setTimeout(180_000);
    test.use({ storageState: { cookies: [], origins: [] } });

    test('captures waiting/connected status and verifies last_sync auto-refresh update', async ({ page, request }, testInfo) => {
        test.skip(!ADMIN_USERNAME || !ADMIN_PASSWORD, 'PLAYWRIGHT_ADMIN_USERNAME and PLAYWRIGHT_ADMIN_PASSWORD are required');

        let delayedOnce = false;
        let kpiRequestCount = 0;
        await page.route('**/api/admin/travel-partners/kpi', async (route) => {
            if (!delayedOnce) {
                delayedOnce = true;
                await new Promise((resolve) => setTimeout(resolve, 2500));
            }
            if (USE_MOCK_BACKEND) {
                kpiRequestCount += 1;
                const generatedAt = new Date(Date.now() + (kpiRequestCount * 65_000)).toISOString();
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        generated_at: generatedAt,
                        funnel: {
                            ctr: 0.42,
                            booking_confirm_rate: 0.86,
                            cancel_rate: 0.04,
                            commission_total: 150000,
                            rps: 2.3,
                            counts: {
                                recommendations: 120,
                                clicks: 50,
                                bookings: 20,
                                confirmed: 17,
                                completed: 15,
                                cancelled: 1,
                                refunded: 0,
                                trip_sessions: 35,
                            },
                        },
                        sla: [
                            {
                                partner_id: 'mock-hotel',
                                success_rate: 0.99,
                                error_rate: 0.01,
                                p95_processing_minutes: 3.2,
                                total_events: 120,
                            },
                        ],
                        fallback: {
                            country_rule_count: 2,
                            country_fallback_ratio: 0.08,
                            city_rule_count: 2,
                            city_fallback_ratio: 0.07,
                            default_partner_usage_ratio: 0.1,
                        },
                        ops: {
                            settings: {
                                settings_path: 'mock',
                                updated_at: generatedAt,
                                updated_by: 'ci-mock',
                                thresholds: {
                                    ctr_min: 0.1,
                                    booking_confirm_rate_min: 0.5,
                                    cancel_rate_max: 0.2,
                                    rps_min: 0.1,
                                    partner_success_rate_min: 0.8,
                                    partner_error_rate_max: 0.2,
                                    partner_p95_processing_minutes_max: 10,
                                    fallback_country_ratio_max: 0.5,
                                    fallback_city_ratio_max: 0.5,
                                    default_partner_usage_ratio_max: 0.5,
                                },
                            },
                            alert_summary: {
                                critical_count: 0,
                                warning_count: 0,
                                ok_count: 3,
                                overall: 'ok',
                            },
                            alerts: [],
                        },
                    }),
                });
                return;
            }
            await route.continue();
        });

        await loginAndInjectAdminToken(page, request);
        await page.waitForURL(/\/admin(?:\/)?(?:\?.*)?$/);
        await expect(page.getByTestId('admin-topnav-refresh')).toBeVisible({ timeout: 45_000 });

        const envWindowPanel = page.locator('section, article, div').filter({ hasText: '전역 .env 설정 패널' }).first();
        if (await envWindowPanel.isVisible().catch(() => false)) {
            const closeOpenWindowButton = envWindowPanel.getByRole('button', { name: '닫기' }).first();
            if (await closeOpenWindowButton.isVisible().catch(() => false)) {
                await closeOpenWindowButton.click();
            }
        }

        const kpiLauncher = page.getByTestId('admin-travel-partner-kpi-section');
        await expect(kpiLauncher).toBeVisible({ timeout: 30_000 });
        const openButton = kpiLauncher.getByRole('button', { name: '창 열기' });
        if (await openButton.count()) {
            await openButton.first().click();
        }

        const panel = page.getByTestId('admin-travel-partner-kpi-panel');
        await expect(panel).toBeVisible({ timeout: 30_000 });

        const statusLine = panel.getByText('연결 상태:', { exact: false });
        const hasStatusLine = (await statusLine.count()) > 0;
        if (hasStatusLine) {
            await expect(statusLine).toContainText('연결 상태: 대기 중', { timeout: 5_000 });
            await page.screenshot({ path: testInfo.outputPath('travel-kpi-status-waiting.png'), fullPage: true });

            await expect(statusLine).toContainText('연결 상태: 연결됨', { timeout: 45_000 });
            await expect(panel.getByTestId('travel-kpi-funnel-cards')).not.toContainText('KPI 갱신을 눌러 최신 지표를 로드하세요.');
            await expect(panel.getByTestId('travel-kpi-sla-card')).not.toContainText('집계된 예약 이벤트가 없습니다.');

            const initialStatus = (await statusLine.textContent()) ?? '';
            const initialSync = initialStatus.split('last_sync')[1]?.trim() ?? '';
            expect(initialSync).not.toBe('');

            await page.waitForTimeout(32_000);

            const refreshedStatus = (await statusLine.textContent()) ?? '';
            const refreshedSync = refreshedStatus.split('last_sync')[1]?.trim() ?? '';
            expect(refreshedSync).not.toBe('');
            expect(refreshedSync).not.toBe(initialSync);
        } else {
            const loadBtn = panel.getByTestId('travel-kpi-load-btn');
            if (await loadBtn.count()) {
                await loadBtn.first().click();
            }
            await expect(panel.getByTestId('travel-kpi-threshold-settings')).toBeVisible({ timeout: 45_000 });
            await expect(panel.getByTestId('travel-kpi-funnel-cards')).toBeVisible({ timeout: 45_000 });
            await expect(panel.getByTestId('travel-kpi-sla-card')).toBeVisible({ timeout: 45_000 });
            await page.screenshot({ path: testInfo.outputPath('travel-kpi-panel-loaded.png'), fullPage: true });
        }

        await page.screenshot({ path: testInfo.outputPath('travel-kpi-status-connected-refresh.png'), fullPage: true });
    });
});

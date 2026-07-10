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

test.describe('admin performance panel live verification (one-shot)', () => {
    test.setTimeout(120_000);
    test.use({ storageState: { cookies: [], origins: [] } });

    test('renders performance recommendations and key values in real admin screen', async ({ page, request }) => {
        test.skip(!ADMIN_USERNAME || !ADMIN_PASSWORD, 'PLAYWRIGHT_ADMIN_USERNAME and PLAYWRIGHT_ADMIN_PASSWORD are required');

        await loginAndInjectAdminToken(page, request);
        await page.waitForURL(/\/admin(?:\/)?(?:\?.*)?$/);
        await expect(page.getByTestId('admin-topnav-refresh')).toBeVisible({ timeout: 45_000 });

        const rightRail = page.locator('aside[aria-label="추가 기능 탐색"]');
        const performanceRailButton = rightRail
            .getByRole('button')
            .filter({ hasText: '성능' })
            .first();
        await expect(performanceRailButton).toBeVisible({ timeout: 30_000 });
        await performanceRailButton.click();

        await expect(page.getByRole('heading', { name: '⚡ 성능 최적화' })).toBeVisible({ timeout: 30_000 });
        await expect(page.getByText('성능 최적화 권장사항')).toBeVisible();
        await expect(page.getByText('시스템 분석을 통해 발견된 성능 개선 기회를 우선순위별로 제시합니다.')).toBeVisible();

        await expect(page.getByText('캐시 히트율 개선')).toBeVisible();
        await expect(page.getByText('현재: 62% → 목표: 75%')).toBeVisible();
        await expect(page.getByText('요청 응답 시간 35% 단축')).toBeVisible();
        await expect(page.getByText('조치 방안: Redis 캐시 TTL 조정 및 워밍')).toBeVisible();

        await expect(page.getByText('DB 쿼리 최적화')).toBeVisible();
        await expect(page.getByText('N+1 쿼리 제거 및 배치 처리')).toBeVisible();

        await expect(page.getByText('이미지 최적화')).toBeVisible();
        await expect(page.getByText('번들 크기 축소')).toBeVisible();
        await expect(page.getByText('메모리 누수 제거')).toBeVisible();

        await expect(page.getByText(/✓ 현재 목표: 응답 예산 \d+ms · DB 예산 \d+ms · 캐시 TTL \d+초/)).toBeVisible();
    });
});

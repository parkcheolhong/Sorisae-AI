import * as fs from 'node:fs';
import { expect, test } from '@playwright/test';

const STORAGE_STATE_PATH = process.env.PLAYWRIGHT_STORAGE_STATE ?? 'playwright/.auth/adminAuthState.json';
const ADMIN_USERNAME = process.env.PLAYWRIGHT_ADMIN_USERNAME ?? '119cash@naver.com';
const ADMIN_PASSWORD = process.env.PLAYWRIGHT_ADMIN_PASSWORD ?? 'space0215@';

function readTokenFromStorageState(): string {
    try {
        const raw = fs.readFileSync(STORAGE_STATE_PATH, 'utf-8');
        const parsed = JSON.parse(raw);
        const origins = Array.isArray(parsed?.origins) ? parsed.origins : [];
        for (const origin of origins) {
            const localStorageItems = Array.isArray(origin?.localStorage) ? origin.localStorage : [];
            const adminToken = localStorageItems.find((item: any) => item?.name === 'admin_token' && typeof item?.value === 'string' && item.value.trim());
            if (adminToken?.value) {
                return adminToken.value;
            }
            const customerToken = localStorageItems.find((item: any) => item?.name === 'customer_token' && typeof item?.value === 'string' && item.value.trim());
            if (customerToken?.value) {
                return customerToken.value;
            }
        }
    } catch {
    }
    return '';
}

async function loginAndIssueFreshToken(request: import('@playwright/test').APIRequestContext): Promise<string> {
    const response = await request.post('/api/proxy', {
        form: {
            username: ADMIN_USERNAME,
            password: ADMIN_PASSWORD,
        },
    });
    if (!response.ok()) {
        return '';
    }
    const payload = await response.json().catch(() => ({}));
    return String((payload as { access_token?: string })?.access_token || '').trim();
}

async function runComposeAndWaitForResult(page: import('@playwright/test').Page): Promise<'ok' | 'auth-error' | 'timeout'> {
    await page.getByTestId('marketplace-music-compose-emotion-btn').click();
    const composeResult = page.getByTestId('marketplace-music-compose-result');
    const musicPanel = page.getByTestId('marketplace-music-panel');
    try {
        return await expect.poll(async () => {
            if (await composeResult.count()) {
                return 'ok';
            }
            const text = (await musicPanel.textContent()) || '';
            if (text.includes('인증 정보가 유효하지 않습니다')) {
                return 'auth-error';
            }
            return 'pending';
        }, { timeout: 20000 }).not.toBe('pending').then(async () => {
            const text = (await musicPanel.textContent()) || '';
            return text.includes('인증 정보가 유효하지 않습니다') ? 'auth-error' : 'ok';
        });
    } catch {
        return 'timeout';
    }
}

test('marketplace music panel runs token-auth API flow and renders payload blocks', async ({ page, request }) => {
    await page.goto('/marketplace/code-generator');

    let token = await page.evaluate(() => window.localStorage.getItem('admin_token') || window.localStorage.getItem('customer_token') || '');
    if (!token) {
        token = readTokenFromStorageState();
    }

    if (token) {
        await page.evaluate((nextToken: string) => {
            window.localStorage.setItem('admin_token', nextToken);
            window.localStorage.setItem('customer_token', nextToken);
        }, token);
    }

    const musicPanel = page.getByTestId('marketplace-music-panel');
    await expect(musicPanel).toBeVisible();

    let composeStatus = await runComposeAndWaitForResult(page);

    if (composeStatus !== 'ok') {
        const freshToken = await loginAndIssueFreshToken(request);
        expect(freshToken, '유효한 관리자 토큰 발급에 실패했습니다. PLAYWRIGHT_ADMIN_USERNAME/PASSWORD를 확인하세요.').not.toBe('');

        await page.goto('/marketplace/code-generator');
        await page.evaluate((nextToken: string) => {
            window.localStorage.setItem('admin_token', nextToken);
            window.localStorage.setItem('customer_token', nextToken);
        }, freshToken);

        composeStatus = await runComposeAndWaitForResult(page);
    }

    expect(composeStatus, '음악 감정 합성 호출이 성공해야 payload 검증을 진행할 수 있습니다.').toBe('ok');

    const composeResult = page.getByTestId('marketplace-music-compose-result');
    await expect(composeResult).toContainText('song:');
    await expect(composeResult).toContainText('lyrics:');
    await expect(composeResult).toContainText('tempo:');

    await page.getByTestId('marketplace-music-compose-code-btn').click();
    const codeResult = page.getByTestId('marketplace-music-code-result');
    await expect(codeResult).toBeVisible({ timeout: 20000 });
    await expect(codeResult).toContainText('composition:');
    await expect(codeResult).toContainText('chords:');

    await page.getByTestId('marketplace-music-friends-demo-btn').click();
    const friendsResult = page.getByTestId('marketplace-music-friends-result');
    await expect(friendsResult).toBeVisible({ timeout: 20000 });
    await expect(friendsResult).toContainText('request:');
    await expect(friendsResult).toContainText('collaboration:');

    await expect(page.getByTestId('marketplace-music-mode')).toContainText('mode:');
});

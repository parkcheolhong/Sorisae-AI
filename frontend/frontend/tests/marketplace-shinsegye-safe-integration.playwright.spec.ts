import * as fs from 'node:fs';
import { expect, test } from '@playwright/test';

const API_BASE_URL = process.env.PLAYWRIGHT_API_BASE_URL ?? 'http://127.0.0.1:8000';
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

async function issueCustomerToken(request: import('@playwright/test').APIRequestContext): Promise<string> {
    const envToken = String(process.env.PLAYWRIGHT_CUSTOMER_TOKEN || process.env.PLAYWRIGHT_ADMIN_TOKEN || '').trim();
    if (envToken) {
        return envToken;
    }

    const storageToken = readTokenFromStorageState();
    if (storageToken) {
        return storageToken;
    }

    const formData = new URLSearchParams();
    formData.set('username', ADMIN_USERNAME);
    formData.set('password', ADMIN_PASSWORD);

    const loginResponse = await request.post(`${API_BASE_URL}/api/auth/login`, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        data: formData.toString(),
    });

    if (!loginResponse.ok()) {
        const body = await loginResponse.text();
        throw new Error(`login failed: ${loginResponse.status()} ${body} (passkey-only 환경이면 PLAYWRIGHT_CUSTOMER_TOKEN 또는 유효 storageState 토큰을 제공하세요)`);
    }

    const payload = await loginResponse.json().catch(() => ({}));
    const token = String((payload as { access_token?: string }).access_token || '').trim();
    if (!token) {
        throw new Error('login succeeded but access_token is empty');
    }

    return token;
}

test('code-generator page supports interpreter, music, and zip download in one real user flow', async ({ page, request }) => {
    const token = await issueCustomerToken(request);

    await page.addInitScript((issuedToken: string) => {
        window.localStorage.setItem('customer_token', issuedToken);
        window.localStorage.setItem('admin_token', issuedToken);
    }, token);

    await page.goto('/marketplace/code-generator');

    const interpreterInput = page.locator('[data-testid="marketplace-interpreter-input"], textarea[placeholder="번역할 문장을 입력하세요"]').first();
    const interpreterSource = page.locator('[data-testid="marketplace-interpreter-source-lang"], input[placeholder="source (예: ko)"]').first();
    const interpreterTarget = page.locator('[data-testid="marketplace-interpreter-target-lang"], input[placeholder="target (예: en)"]').first();
    const interpreterTranslateButton = page.locator('[data-testid="marketplace-interpreter-translate-btn"], button:has-text("통역 API 호출")').first();

    await expect(interpreterInput).toBeVisible({ timeout: 15000 });
    await interpreterInput.fill('안녕하세요');
    await interpreterSource.fill('ko');
    await interpreterTarget.fill('en');
    await interpreterTranslateButton.click();

    await page.getByTestId('marketplace-music-compose-emotion-btn').click();
    await expect(page.getByTestId('marketplace-music-compose-result')).toBeVisible({ timeout: 45000 });
    await expect(page.getByTestId('marketplace-music-mode')).toContainText('mode:');

    const projectNameInput = page.locator('[data-testid="marketplace-codegen-project-name"], input[placeholder="프로젝트 이름"]').first();
    const taskInput = page.locator('[data-testid="marketplace-codegen-task"], textarea[placeholder^="태스크 설명"]').first();
    const generateButton = page.locator('[data-testid="marketplace-codegen-generate-btn"], button:has-text("코드 생성")').first();

    await projectNameInput.fill(`safe-integration-${Date.now()}`);
    await taskInput.fill('Create hello endpoint with simple health route');
    await generateButton.click();

    await expect(page.locator('[data-testid="marketplace-codegen-result"], .workspace-card >> text=생성 완료').first()).toBeVisible({ timeout: 90000 });

    const downloadPromise = page.waitForEvent('download', { timeout: 45000 });
    await page.locator('[data-testid="marketplace-codegen-download-btn"], button:has-text("ZIP 다운로드")').first().click();
    const download = await downloadPromise;

    const suggestedName = download.suggestedFilename();
    expect(suggestedName.toLowerCase()).toContain('.zip');
});

import { expect, test } from '@playwright/test';

const API_BASE_URL = process.env.PLAYWRIGHT_API_BASE_URL ?? 'http://127.0.0.1:8000';

async function issueCustomerToken(request: import('@playwright/test').APIRequestContext): Promise<string> {
    const suffix = `${Date.now()}_${Math.floor(Math.random() * 100000)}`;
    const username = `pw_safe_${suffix}`;
    const email = `${username}@example.com`;
    const password = 'P@ssw0rd!23456';

    const signupResponse = await request.post(`${API_BASE_URL}/api/auth/signup`, {
        data: {
            email,
            username,
            password,
            member_type: 'individual',
        },
    });

    if (!signupResponse.ok()) {
        const body = await signupResponse.text();
        throw new Error(`signup failed: ${signupResponse.status()} ${body}`);
    }

    const formData = new URLSearchParams();
    formData.set('username', email);
    formData.set('password', password);

    const loginResponse = await request.post(`${API_BASE_URL}/api/auth/login`, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        data: formData.toString(),
    });

    if (!loginResponse.ok()) {
        const body = await loginResponse.text();
        throw new Error(`login failed: ${loginResponse.status()} ${body}`);
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
    const interpreterMode = page.locator('[data-testid="marketplace-interpreter-mode"], .workspace-sidebar .workspace-sidebar-card >> text=mode:').first();

    await expect(interpreterInput).toBeVisible({ timeout: 15000 });
    await interpreterInput.fill('안녕하세요');
    await interpreterSource.fill('ko');
    await interpreterTarget.fill('en');
    await interpreterTranslateButton.click();
    await expect(interpreterMode).toContainText('mode:');

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

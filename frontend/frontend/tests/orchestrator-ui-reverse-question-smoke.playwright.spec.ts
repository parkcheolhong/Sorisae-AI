import { expect, test } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

const ADMIN_BASE = process.env.PLAYWRIGHT_ADMIN_BASE_URL || 'http://127.0.0.1:3005';
const MARKET_BASE = process.env.PLAYWRIGHT_MARKETPLACE_BASE_URL || process.env.PLAYWRIGHT_ADMIN_BASE_URL || 'http://127.0.0.1:3000';
const OUT_DIR = path.resolve(process.cwd(), '../../reports/playwright-evidence');
const ADMIN_REGRESSION_MOCK_BACKEND = process.env.ADMIN_REGRESSION_MOCK_BACKEND === '1';
const ADMIN_REGRESSION_MOCK_TOKEN = process.env.ADMIN_REGRESSION_MOCK_TOKEN || 'admin-regression-mock-token';

test('admin + marketplace orchestrator reverse-question smoke', async ({ page, request }) => {
    test.setTimeout(180000);
    fs.mkdirSync(OUT_DIR, { recursive: true });

    let token = '';
    if (ADMIN_REGRESSION_MOCK_BACKEND) {
        token = ADMIN_REGRESSION_MOCK_TOKEN;
    } else {
        const loginPayload = new URLSearchParams();
        loginPayload.set('username', 'ui.admin.round@devanalysis.local');
        loginPayload.set('password', 'RoundUi!20260426');
        const loginResponse = await request.post(`${ADMIN_BASE}/api/proxy?action=login`, {
            data: loginPayload.toString(),
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
        });
        expect(loginResponse.ok()).toBeTruthy();
        const loginJson = await loginResponse.json() as { access_token?: string };
        token = String(loginJson.access_token || '').trim();
    }
    expect(token.length).toBeGreaterThan(0);

    await page.addInitScript((issuedToken: string) => {
        window.localStorage.setItem('admin_token', issuedToken);
        window.localStorage.setItem('customer_token', issuedToken);
    }, token);

    await page.goto(`${ADMIN_BASE}/admin/llm`, { waitUntil: 'networkidle' });
    const adminInput = page.locator('#admin-llm-chat-input');
    await expect(adminInput).toBeVisible({ timeout: 120000 });
    await adminInput.fill('UI smoke: 답변 후 역질문 1개를 해줘.');
    const adminSend = page.getByRole('button', { name: /전송|send|요청|실행/i }).first();
    if (await adminSend.count()) {
        await adminSend.click();
    } else {
        await adminInput.press('Enter');
    }

    const markerPattern = /역질문|우선순위 1번|대화를 끊지 않고|어떤.*원하시나요/i;
    const adminMarker = page.getByText(markerPattern).first();
    await expect(adminMarker).toBeVisible({ timeout: 120000 });
    const adminMarkerText = ((await adminMarker.textContent()) || '').trim().slice(0, 180);

    const adminShot = path.join(OUT_DIR, 'admin-llm-reverse-question.png');
    await page.screenshot({ path: adminShot, fullPage: true });

    await page.goto(`${MARKET_BASE}/marketplace/orchestrator`, { waitUntil: 'networkidle' });
    const marketInput = page.locator('textarea').first();
    await expect(marketInput).toBeVisible({ timeout: 120000 });
    await marketInput.fill('UI smoke: 답변하고 역질문으로 이어가줘.');
    const marketSend = page.getByRole('button', { name: /전송|send|요청|실행/i }).first();
    if (await marketSend.count()) {
        await marketSend.click();
    } else {
        await marketInput.press('Enter');
    }

    const marketMarker = page.getByText(markerPattern).first();
    await expect(marketMarker).toBeVisible({ timeout: 120000 });
    const marketMarkerText = ((await marketMarker.textContent()) || '').trim().slice(0, 180);

    const marketShot = path.join(OUT_DIR, 'marketplace-orchestrator-reverse-question.png');
    await page.screenshot({ path: marketShot, fullPage: true });

    const resultPath = path.join(OUT_DIR, 'orchestrator-ui-smoke-result.json');
    fs.writeFileSync(resultPath, JSON.stringify({
        adminBase: ADMIN_BASE,
        marketBase: MARKET_BASE,
        adminUi: { ok: true, marker: adminMarkerText },
        marketUi: { ok: true, marker: marketMarkerText },
        adminScreenshot: adminShot,
        marketScreenshot: marketShot,
    }, null, 2), 'utf8');
});

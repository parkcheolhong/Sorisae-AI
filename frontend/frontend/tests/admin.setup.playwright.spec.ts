import * as fs from 'node:fs';
import * as path from 'node:path';
import { expect, test } from '@playwright/test';

const ADMIN_USERNAME = process.env.PLAYWRIGHT_ADMIN_USERNAME ?? '';
const ADMIN_PASSWORD = process.env.PLAYWRIGHT_ADMIN_PASSWORD ?? '';
const STORAGE_STATE_PATH = process.env.PLAYWRIGHT_STORAGE_STATE ?? 'playwright/.auth/adminAuthState.json';
const PLAYWRIGHT_ADMIN_BASE_URL = (process.env.PLAYWRIGHT_ADMIN_BASE_URL ?? 'http://localhost:3005').replace(/\/$/, '');
const ADMIN_DASHBOARD_WAIT_MS = 30_000;
const ADMIN_ORCHESTRATOR_E2E = process.env.PLAYWRIGHT_ORCHESTRATOR_E2E === '1';
const ADMIN_REGRESSION_MOCK_BACKEND = process.env.ADMIN_REGRESSION_MOCK_BACKEND === '1';
const ADMIN_REGRESSION_MOCK_TOKEN = 'admin-regression-mock-token';
const useCredentialLogin = Boolean(ADMIN_USERNAME && ADMIN_PASSWORD && !ADMIN_ORCHESTRATOR_E2E);

function readExistingAdminToken(): string {
    try {
        const raw = fs.readFileSync(STORAGE_STATE_PATH, 'utf-8');
        const parsed = JSON.parse(raw);
        const origins = Array.isArray(parsed?.origins) ? parsed.origins : [];
        for (const origin of origins) {
            const localStorageItems = Array.isArray(origin?.localStorage) ? origin.localStorage : [];
            const tokenEntry = localStorageItems.find((item: any) => item?.name === 'admin_token' && typeof item?.value === 'string' && item.value.trim());
            if (tokenEntry?.value) {
                return tokenEntry.value;
            }
        }
    } catch {
    }
    return '';
}

async function writeStorageStateWithToken(page: any, token: string) {
    await page.addInitScript((nextToken: string) => {
        window.localStorage.setItem('admin_token', nextToken);
    }, token);
    await page.goto(`${PLAYWRIGHT_ADMIN_BASE_URL}/admin/login`, { waitUntil: 'domcontentloaded' });
    await page.evaluate((nextToken: string) => {
        window.localStorage.setItem('admin_token', nextToken);
    }, token);
}

async function openAdminLlmPage(page: import('@playwright/test').Page) {
    await page.goto('/admin/llm', { waitUntil: 'domcontentloaded', timeout: 15_000 });
    await expect(page.getByRole('heading', { name: 'AI 코드 제너레이터' })).toBeVisible({ timeout: 30_000 });
}

async function loginAndInjectAdminToken(
    page: import('@playwright/test').Page,
    request: import('@playwright/test').APIRequestContext,
) {
    const backendBaseUrl = process.env.PLAYWRIGHT_BACKEND_BASE_URL ?? 'http://127.0.0.1:8000';
    const response = await request.post(`${backendBaseUrl}/api/auth/login`, {
        timeout: 45_000,
        form: {
            username: ADMIN_USERNAME,
            password: ADMIN_PASSWORD,
        },
    });
    expect(response.ok()).toBeTruthy();
    const payload = await response.json();
    const token = String(payload?.access_token || '');
    expect(token).not.toBe('');

    await writeStorageStateWithToken(page, token);
}

test('create admin storage state', async ({ page, request }) => {
    test.setTimeout(ADMIN_ORCHESTRATOR_E2E ? 120_000 : 60_000);
    fs.mkdirSync(path.dirname(STORAGE_STATE_PATH), { recursive: true });

    if (useCredentialLogin) {
        await loginAndInjectAdminToken(page, request);
    } else {
        const seedToken = ADMIN_ORCHESTRATOR_E2E || ADMIN_REGRESSION_MOCK_BACKEND
            ? ADMIN_REGRESSION_MOCK_TOKEN
            : readExistingAdminToken();
        test.skip(!seedToken, 'PLAYWRIGHT_ADMIN_USERNAME / PLAYWRIGHT_ADMIN_PASSWORD 또는 기존 admin_token storageState 필요');
        await writeStorageStateWithToken(page, seedToken);
    }

    if (ADMIN_ORCHESTRATOR_E2E) {
        await openAdminLlmPage(page);
    } else {
        await page.goto('/admin');
        await page.waitForURL(/\/admin(?:\/)?(?:\?.*)?$/);
        await page.getByTestId('admin-topnav-api-docs').waitFor({ timeout: ADMIN_DASHBOARD_WAIT_MS });
    }

    await page.context().storageState({ path: STORAGE_STATE_PATH });
});

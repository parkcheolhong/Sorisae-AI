import * as fs from 'node:fs';
import * as path from 'node:path';
import { expect, test } from '@playwright/test';

const ADMIN_USERNAME = process.env.PLAYWRIGHT_ADMIN_USERNAME ?? '119cash@naver.com';
const ADMIN_PASSWORD = process.env.PLAYWRIGHT_ADMIN_PASSWORD ?? 'space0215@';
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

async function waitForAdminTopnavReady(page: import('@playwright/test').Page) {
    await page.goto('/admin', { waitUntil: 'domcontentloaded' });

    const topnavApiDocs = page.getByTestId('admin-topnav-api-docs');
    if (await topnavApiDocs.isVisible({ timeout: 5_000 }).catch(() => false)) {
        return;
    }

    const loginForm = page.getByTestId('admin-login-form');
    if (await loginForm.isVisible({ timeout: 2_000 }).catch(() => false)) {
        if (!useCredentialLogin) {
            throw new Error(
                'admin setup redirected to /admin/login and credential login is disabled; set PLAYWRIGHT_ADMIN_USERNAME/PLAYWRIGHT_ADMIN_PASSWORD',
            );
        }
        await ensureAdminTokenForSetup(page, page.request);
        await page.goto('/admin', { waitUntil: 'domcontentloaded' });
    }

    if (await page.getByTestId('admin-topnav-api-docs').isVisible({ timeout: 3_000 }).catch(() => false)) {
        return;
    }

    // Some deployments stay in passkey-only login mode in CI; avoid hard timeout here
    // so dependent specs can run and report their own functional assertions.
    if (await page.getByTestId('admin-login-form').isVisible({ timeout: 1_500 }).catch(() => false)) {
        return;
    }

    await page.getByTestId('admin-topnav-api-docs').waitFor({ timeout: ADMIN_DASHBOARD_WAIT_MS });
}

async function loginAndInjectAdminToken(
    page: import('@playwright/test').Page,
    request: import('@playwright/test').APIRequestContext,
) {
    const backendBaseUrl = process.env.PLAYWRIGHT_BACKEND_BASE_URL ?? 'http://127.0.0.1:8000';
    const loginForm = {
        username: ADMIN_USERNAME,
        password: ADMIN_PASSWORD,
    };

    let response = await request.post(`${backendBaseUrl}/api/auth/login`, {
        timeout: 45_000,
        form: loginForm,
    });

    if (!response.ok() && response.status() === 409) {
        const existingToken = readExistingAdminToken();
        if (existingToken) {
            await request.post(`${backendBaseUrl}/api/auth/logout`, {
                timeout: 15_000,
                headers: {
                    Authorization: `Bearer ${existingToken}`,
                },
            }).catch(() => null);
            response = await request.post(`${backendBaseUrl}/api/auth/login`, {
                timeout: 45_000,
                form: loginForm,
            });
        }
    }

    expect(response.ok()).toBeTruthy();
    const payload = await response.json();
    const token = String(payload?.access_token || '');
    expect(token).not.toBe('');

    await writeStorageStateWithToken(page, token);
}

async function ensureAdminTokenForSetup(
    page: import('@playwright/test').Page,
    request: import('@playwright/test').APIRequestContext,
) {
    try {
        await loginAndInjectAdminToken(page, request);
    } catch {
        const fallbackToken = readExistingAdminToken();
        if (!fallbackToken) {
            throw new Error('credential login failed and no existing admin_token in storageState');
        }
        await writeStorageStateWithToken(page, fallbackToken);
    }
}

test('create admin storage state', async ({ page, request }) => {
    test.setTimeout(ADMIN_ORCHESTRATOR_E2E ? 120_000 : 60_000);
    fs.mkdirSync(path.dirname(STORAGE_STATE_PATH), { recursive: true });

    if (useCredentialLogin) {
        await ensureAdminTokenForSetup(page, request);
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
        await waitForAdminTopnavReady(page);
    }

    await page.context().storageState({ path: STORAGE_STATE_PATH });
});

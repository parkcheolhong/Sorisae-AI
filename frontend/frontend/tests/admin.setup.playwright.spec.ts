import * as fs from 'node:fs';
import * as path from 'node:path';
import { expect, test } from '@playwright/test';

const ADMIN_USERNAME = process.env.PLAYWRIGHT_ADMIN_USERNAME ?? '';
const ADMIN_PASSWORD = process.env.PLAYWRIGHT_ADMIN_PASSWORD ?? '';
const STORAGE_STATE_PATH = process.env.PLAYWRIGHT_STORAGE_STATE ?? 'playwright/.auth/adminAuthState.json';
const PLAYWRIGHT_ADMIN_BASE_URL = (process.env.PLAYWRIGHT_ADMIN_BASE_URL ?? 'http://localhost:3005').replace(/\/$/, '');
const ADMIN_DASHBOARD_WAIT_MS = 30_000;
const ADMIN_REGRESSION_MOCK_BACKEND = process.env.ADMIN_REGRESSION_MOCK_BACKEND === '1';
const ADMIN_REGRESSION_MOCK_TOKEN = 'admin-regression-mock-token';

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
    await page.goto(PLAYWRIGHT_ADMIN_BASE_URL);
    await page.evaluate((nextToken: string) => {
        window.localStorage.setItem('admin_token', nextToken);
    }, token);
    await page.context().storageState({ path: STORAGE_STATE_PATH });
}

test('create admin storage state', async ({ page }) => {
    test.setTimeout(60_000);
    fs.mkdirSync(path.dirname(STORAGE_STATE_PATH), { recursive: true });
    if (ADMIN_REGRESSION_MOCK_BACKEND) {
        await writeStorageStateWithToken(page, ADMIN_REGRESSION_MOCK_TOKEN);
    } else if (ADMIN_USERNAME && ADMIN_PASSWORD) {
        await page.goto('/admin/login');
        await page.getByTestId('admin-login-email').fill(ADMIN_USERNAME);
        await page.getByTestId('admin-login-password').fill(ADMIN_PASSWORD);
        await page.getByTestId('admin-login-submit').click();
        await expect.poll(async () => page.evaluate(() => window.localStorage.getItem('admin_token')), {
            timeout: 15000,
        }).not.toBeNull();
    } else {
        const existingToken = readExistingAdminToken();
        test.skip(!existingToken, 'PLAYWRIGHT_ADMIN_USERNAME / PLAYWRIGHT_ADMIN_PASSWORD 또는 기존 admin_token storageState 필요');
        await writeStorageStateWithToken(page, existingToken);
    }
    await page.goto('/admin');
    await page.waitForURL(/\/admin(?:\/)?(?:\?.*)?$/);
    await page.getByTestId('admin-topnav-api-docs').waitFor({ timeout: ADMIN_DASHBOARD_WAIT_MS });
    await page.context().storageState({ path: STORAGE_STATE_PATH });
});

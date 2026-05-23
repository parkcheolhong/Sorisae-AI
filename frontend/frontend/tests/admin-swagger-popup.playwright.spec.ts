import * as fs from 'node:fs';
import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';

type StorageOrigin = {
    origin?: string;
    localStorage?: Array<{ name?: string; value?: string }>;
};

function readAdminTokenFromStorageState(storageStatePath: string): string {
    try {
        const raw = fs.readFileSync(storageStatePath, 'utf-8');
        const parsed = JSON.parse(raw);
        const origins: StorageOrigin[] = Array.isArray(parsed?.origins) ? parsed.origins : [];
        for (const origin of origins) {
            const entries = Array.isArray(origin.localStorage) ? origin.localStorage : [];
            const tokenEntry = entries.find((entry) => entry?.name === 'admin_token' && typeof entry?.value === 'string' && entry.value.trim());
            if (tokenEntry?.value) {
                return tokenEntry.value;
            }
        }
    } catch {
    }
    return '';
}

async function loginThroughProxy(page: Page, username: string, password: string): Promise<string> {
    const response = await page.request.post('/api/proxy', {
        form: { username, password },
    });
    expect(response.ok()).toBeTruthy();
    const payload = (await response.json()) as { access_token?: string };
    expect(typeof payload?.access_token === 'string' && payload.access_token.length > 0).toBeTruthy();
    return payload.access_token as string;
}

test('admin swagger button opens backend docs in popup', async ({ page }) => {
    const storageStatePath = process.env.PLAYWRIGHT_STORAGE_STATE ?? 'playwright/.auth/adminAuthState.json';
    const adminUsername = process.env.PLAYWRIGHT_ADMIN_USERNAME ?? '';
    const adminPassword = process.env.PLAYWRIGHT_ADMIN_PASSWORD ?? '';
    let adminToken = readAdminTokenFromStorageState(storageStatePath);

    if (adminUsername && adminPassword) {
        adminToken = await loginThroughProxy(page, adminUsername, adminPassword);
    }

    if (adminToken) {
        await page.addInitScript((token: string) => {
            window.localStorage.setItem('admin_token', token);
        }, adminToken);
    }

    const docsLink = page
        .locator('[data-testid="admin-topnav-api-docs"], a:has-text("API Docs"), a:has-text("Swagger UI")')
        .first();

    await page.goto('/admin');
    await page.waitForLoadState('domcontentloaded');

    const loginVisible = await page.getByTestId('admin-login-form').isVisible().catch(() => false);
    if (loginVisible && adminUsername && adminPassword) {
        const accessToken = await loginThroughProxy(page, adminUsername, adminPassword);
        await page.addInitScript((token: string) => {
            window.localStorage.setItem('admin_token', token);
        }, accessToken);
        await page.goto('/admin');
        await page.waitForLoadState('domcontentloaded');
    }

    await expect(docsLink).toBeVisible({ timeout: 15000 });

    const href = await docsLink.getAttribute('href');
    expect(href).toBeTruthy();
    expect(href).toMatch(/^https?:\/\/.+\/docs$/);

    const popupPromise = page.waitForEvent('popup');
    await docsLink.click();
    const popup = await popupPromise;

    await popup.waitForLoadState('domcontentloaded');
    const popupUrl = popup.url();
    expect(popupUrl).toContain('/docs');

    const actual = new URL(popupUrl);
    const expected = new URL(href as string);
    expect(`${actual.origin}${actual.pathname}`).toBe(`${expected.origin}${expected.pathname}`);

    await popup.close();
});

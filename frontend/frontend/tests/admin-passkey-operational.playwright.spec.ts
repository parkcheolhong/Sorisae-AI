import { expect, test } from '@playwright/test';

const ADMIN_EMAIL = process.env.PLAYWRIGHT_ADMIN_USERNAME ?? '119cash@naver.com';
const ADMIN_PASSWORD = process.env.PLAYWRIGHT_ADMIN_PASSWORD ?? 'space0215@';

async function attachVirtualAuthenticator(page: import('@playwright/test').Page) {
    const client = await page.context().newCDPSession(page);
    await client.send('WebAuthn.enable');
    const result = await client.send('WebAuthn.addVirtualAuthenticator', {
        options: {
            protocol: 'ctap2',
            transport: 'internal',
            hasResidentKey: true,
            hasUserVerification: true,
            isUserVerified: true,
            automaticPresenceSimulation: true,
        },
    });
    return {
        client,
        authenticatorId: String(result.authenticatorId),
    };
}

async function registerPasskey(page: import('@playwright/test').Page, label: string) {
    await page.goto('/admin/login');
    await page.getByTestId('admin-login-email').fill(ADMIN_EMAIL);
    await page.getByTestId('admin-login-password').fill(ADMIN_PASSWORD);

    const dialogPromise = page.waitForEvent('dialog');
    await page.getByTestId('admin-login-passkey-register').click();
    const dialog = await dialogPromise;
    expect(dialog.message()).toContain('패스키 등록이 완료되었습니다.');
    await dialog.accept();

    await expect(page.getByTestId('admin-login-error')).toHaveCount(0);
}

async function loginWithPasskey(page: import('@playwright/test').Page) {
    await page.goto('/admin/login');
    await page.getByTestId('admin-login-email').fill(ADMIN_EMAIL);
    await page.getByTestId('admin-login-passkey-button').click();
    await page.waitForURL(/\/admin(?:\/)?(?:\?.*)?$/);
    await expect(page.getByText('🩺 관리자 자동 건강상태 / 자가진단 / 자가개선')).toBeVisible();
}

async function logoutToLogin(page: import('@playwright/test').Page) {
    await page.getByTestId('admin-topnav-logout').click();
    await page.waitForURL(/\/admin\/login(?:\/)?(?:\?.*)?$/);
    await expect(page.getByTestId('admin-login-form')).toBeVisible();
}

test.describe('admin passkey operational verification', () => {
    test.use({ storageState: { cookies: [], origins: [] } });

    for (const attempt of [1, 2]) {
        test(`passkey register + login closes operational flow attempt ${attempt}`, async ({ page }) => {
            const { client, authenticatorId } = await attachVirtualAuthenticator(page);
            await registerPasskey(page, `ops-passkey-check-${attempt}`);
            await loginWithPasskey(page);
            await logoutToLogin(page);
            await client.send('WebAuthn.removeVirtualAuthenticator', { authenticatorId });
        });
    }
});

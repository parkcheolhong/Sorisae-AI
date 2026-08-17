import { expect, test } from '@playwright/test';

const MARKETPLACE_BASE_URL = process.env.PLAYWRIGHT_MARKETPLACE_BASE_URL ?? 'http://localhost:3000';
const PASSKEY_EMAIL = process.env.PLAYWRIGHT_PASSKEY_EMAIL ?? '119cash@naver.com';

test.describe('@marketplace-operational @passkey marketplace passkey login flow', () => {
    test('auto passkey_login deep-link mode applies session and shows user profile', async ({ page }) => {
        await page.addInitScript(() => {
            const credential = {
                id: 'playwright-passkey-credential-id',
                rawId: new Uint8Array([1, 2, 3, 4]).buffer,
                type: 'public-key',
                response: {
                    clientDataJSON: new Uint8Array([5, 6, 7, 8]).buffer,
                    authenticatorData: new Uint8Array([9, 10, 11, 12]).buffer,
                    signature: new Uint8Array([13, 14, 15, 16]).buffer,
                    userHandle: null,
                },
            };

            Object.defineProperty(window, 'PublicKeyCredential', {
                configurable: true,
                value: function PublicKeyCredential() { },
            });

            Object.defineProperty(navigator, 'credentials', {
                configurable: true,
                value: {
                    get: async () => credential,
                },
            });
        });

        await page.route('**/api/auth/passkey/login/start', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    options: {
                        challenge: 'Y2hhbGxlbmdl',
                        allowCredentials: [{ id: 'Y3JlZA', type: 'public-key' }],
                        rpId: 'metanova1004.com',
                        userVerification: 'preferred',
                    },
                }),
            });
        });

        await page.route('**/api/auth/passkey/login/finish', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    access_token: 'playwright-passkey-token',
                    token_type: 'bearer',
                }),
            });
        });

        await page.route('**/api/auth/me', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    email: PASSKEY_EMAIL,
                    username: PASSKEY_EMAIL,
                    member_type: 'individual',
                }),
            });
        });

        const targetUrl = `${MARKETPLACE_BASE_URL}/marketplace?auth_mode=passkey_login&email=${encodeURIComponent(PASSKEY_EMAIL)}`;
        await page.goto(targetUrl);

        await expect(page.getByTestId('marketplace-auth-panel')).toBeVisible();
        await expect(page.getByRole('heading', { name: '패스키 로그인 / 내정보' })).toBeVisible();
        await expect(page.getByText(PASSKEY_EMAIL).first()).toBeVisible();
        await expect(page.getByText('가입 유형').first()).toBeVisible();
    });

    test('passkey_login with mobile_return_uri redirects to callback with auth payload', async ({ page }) => {
        await page.addInitScript(() => {
            const credential = {
                id: 'playwright-passkey-credential-id',
                rawId: new Uint8Array([1, 2, 3, 4]).buffer,
                type: 'public-key',
                response: {
                    clientDataJSON: new Uint8Array([5, 6, 7, 8]).buffer,
                    authenticatorData: new Uint8Array([9, 10, 11, 12]).buffer,
                    signature: new Uint8Array([13, 14, 15, 16]).buffer,
                    userHandle: null,
                },
            };

            Object.defineProperty(window, 'PublicKeyCredential', {
                configurable: true,
                value: function PublicKeyCredential() { },
            });

            Object.defineProperty(navigator, 'credentials', {
                configurable: true,
                value: {
                    get: async () => credential,
                },
            });
        });

        await page.route('**/api/auth/passkey/login/start', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    options: {
                        challenge: 'Y2hhbGxlbmdl',
                        allowCredentials: [{ id: 'Y3JlZA', type: 'public-key' }],
                        rpId: 'metanova1004.com',
                        userVerification: 'preferred',
                    },
                }),
            });
        });

        await page.route('**/api/auth/passkey/login/finish', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    access_token: 'playwright-passkey-token-callback',
                    token_type: 'bearer',
                }),
            });
        });

        const callbackUri = 'https://callback.local/mobile-auth-return';
        await page.route(`${callbackUri}**`, async (route) => {
            await route.fulfill({ status: 200, contentType: 'text/plain', body: 'callback ok' });
        });
        const targetUrl = `${MARKETPLACE_BASE_URL}/marketplace?auth_mode=passkey_login&email=${encodeURIComponent(PASSKEY_EMAIL)}&mobile_return_uri=${encodeURIComponent(callbackUri)}`;
        await page.goto(targetUrl);

        await page.waitForURL((url) => url.toString().startsWith(callbackUri));
        const redirected = new URL(page.url());
        expect(redirected.origin + redirected.pathname).toBe(callbackUri);
        expect(redirected.searchParams.get('auth_mode')).toBe('passkey_login');
        expect(redirected.searchParams.get('access_token')).toBe('playwright-passkey-token-callback');
        expect(redirected.searchParams.get('email')).toBe(PASSKEY_EMAIL);
    });
});

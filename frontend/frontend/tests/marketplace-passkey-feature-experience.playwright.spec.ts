import { expect, test } from '@playwright/test';

const MARKETPLACE_BASE_URL =
    process.env.PLAYWRIGHT_MARKETPLACE_BASE_URL ?? 'http://127.0.0.1:3005';
const PASSKEY_EMAIL =
    process.env.PLAYWRIGHT_PASSKEY_EMAIL ?? '119cash@naver.com';

test.describe(
    '@marketplace-operational @passkey marketplace post-passkey feature experience',
    () => {
        test('passkey login then main marketplace and orchestrator flow are usable', async ({ page }) => {
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
                    value: function PublicKeyCredential() {
                        return null;
                    },
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
                        access_token: 'playwright-passkey-token-feature',
                        token_type: 'bearer',
                    }),
                });
            });

            await page.route('**/api/auth/me', async (route) => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        id: 77,
                        email: PASSKEY_EMAIL,
                        username: PASSKEY_EMAIL,
                        member_type: 'individual',
                    }),
                });
            });

            await page.route('**/api/marketplace/categories**', async (route) => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify([
                        { id: 1, name: '모바일 앱', description: 'iOS, Android 앱' },
                    ]),
                });
            });

            await page.route('**/api/marketplace/projects**', async (route) => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        projects: [
                            {
                                id: 101,
                                title: '나도통역사 - 신세계소리새 통번역',
                                description: 'passkey feature experience fixture',
                                price: 0,
                                category_id: 1,
                                downloads: 3,
                                rating: 4.8,
                                is_active: true,
                                tags: [{ id: 1, name: '통역' }],
                            },
                        ],
                        total: 1,
                        skip: 0,
                        limit: 24,
                    }),
                });
            });

            await page.route('**/api/marketplace/shinsegye/products**', async (route) => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify([]),
                });
            });

            await page.route('**/api/marketplace/stats/overview**', async (route) => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({ projects: 1, users: 1, purchases: 1, reviews: 1 }),
                });
            });

            await page.route('**/api/marketplace/stats/revenue**', async (route) => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        total_revenue: 10000,
                        total_purchases: 1,
                        average_purchase_amount: 10000,
                    }),
                });
            });

            await page.route('**/api/marketplace/stats/top-projects**', async (route) => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify([
                        {
                            id: 101,
                            title: '나도통역사 - 신세계소리새 통번역',
                            downloads: 3,
                            rating: 4.8,
                            price: 0,
                        },
                    ]),
                });
            });

            await page.goto(
                `${MARKETPLACE_BASE_URL}/marketplace?auth_mode=passkey_login&email=${encodeURIComponent(PASSKEY_EMAIL)}`,
            );

            await expect(page.getByTestId('marketplace-auth-panel')).toBeVisible();
            await expect(page.getByRole('heading', { name: '패스키 로그인 / 내정보' })).toBeVisible();
            await expect(page.getByText(PASSKEY_EMAIL).first()).toBeVisible();
            await expect(page.getByTestId('marketplace-main-page')).toBeVisible();
            await expect(page.getByTestId('marketplace-project-grid')).toBeVisible();

            await page.getByRole('link', { name: '오케스트레이터 주문' }).first().click();
            await expect(page).toHaveURL(/\/marketplace\/orchestrator/);
            await expect(page.getByText('마켓플레이스 오케스트레이터')).toBeVisible();
            await expect(page.getByTestId('orchestrator-live-flow-rail')).toBeVisible();
            await expect(page.getByTestId('orchestrator-decision-panel')).toBeVisible();
        });
    },
);

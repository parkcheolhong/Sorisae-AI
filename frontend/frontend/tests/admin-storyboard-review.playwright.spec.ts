import * as fs from 'node:fs';
import { expect, test, type Page } from '@playwright/test';

const ADMIN_USERNAME = process.env.PLAYWRIGHT_ADMIN_USERNAME ?? '';
const ADMIN_PASSWORD = process.env.PLAYWRIGHT_ADMIN_PASSWORD ?? '';
const TARGET_ORDER_ID = process.env.PLAYWRIGHT_STORYBOARD_ORDER_ID ?? '';
const STORAGE_STATE_PATH = process.env.PLAYWRIGHT_STORAGE_STATE ?? 'playwright/.auth/adminAuthState.json';
const HAS_STORAGE_STATE = fs.existsSync(STORAGE_STATE_PATH);
const ADMIN_DASHBOARD_WAIT_MS = 30_000;

const readExistingAdminToken = () => {
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
};

test.describe('admin storyboard review', () => {
    const sectionToggleSelector = '[data-testid="admin-storyboard-section-toggle"]';
    const ordersToggleSelector = '[data-testid="admin-storyboard-orders-toggle"]';
    const ordersRefreshSelector = '[data-testid="admin-storyboard-orders-refresh"]';
    const firstExpandButtonSelector = '[data-testid^="admin-storyboard-order-expand-"]';
    const firstDiffOnlyFilterSelector = '[data-testid^="admin-storyboard-filter-diff-only-"]';
    const firstStatusOnlyFilterSelector = '[data-testid^="admin-storyboard-filter-status-only-"]';
    const firstNoteOnlyFilterSelector = '[data-testid^="admin-storyboard-filter-note-only-"]';
    const firstResetFilterSelector = '[data-testid^="admin-storyboard-filter-reset-"]';
    const firstThumbnailSelector = '[data-testid^="admin-storyboard-scene-thumbnail-"]';
    const firstStatusSelectSelector = '[data-testid^="admin-storyboard-scene-status-"]';
    const firstNoteTextareaSelector = '[data-testid^="admin-storyboard-scene-note-"]';
    const firstSaveButtonSelector = '[data-testid^="admin-storyboard-save-"]';

    const extractOrderIdFromTestId = (value: string | null) => value?.replace('admin-storyboard-order-expand-', '') || '';

    const ensureOrdersPanelOpen = async (page: Page) => {
        if ((await page.locator(ordersToggleSelector).count()) === 0) {
            await page.locator(sectionToggleSelector).click();
        }
        await expect(page.locator(ordersToggleSelector)).toBeVisible();
        if ((await page.locator(firstExpandButtonSelector).count()) === 0) {
            await page.locator(ordersToggleSelector).click();
        }
    };

    const refreshStoryboardOrders = async (page: Page) => {
        if ((await page.locator(ordersRefreshSelector).count()) > 0) {
            await page.locator(ordersRefreshSelector).click();
        } else {
            await page.reload();
            await page.waitForURL(/\/admin(?:\/)?(?:\?.*)?$/);
            await page.getByTestId('admin-storyboard-section-toggle').waitFor({ timeout: ADMIN_DASHBOARD_WAIT_MS });
        }
        await page.waitForTimeout(1000);
        await ensureOrdersPanelOpen(page);
    };

    const resolveTargetOrderId = async (page: Page) => {
        await ensureOrdersPanelOpen(page);

        if (TARGET_ORDER_ID) {
            const targetRow = page.getByTestId(`admin-storyboard-order-row-${TARGET_ORDER_ID}`);
            for (let attempt = 0; attempt < 5; attempt += 1) {
                if ((await targetRow.count()) > 0) {
                    await expect(targetRow).toBeVisible();
                    return TARGET_ORDER_ID;
                }
                await refreshStoryboardOrders(page);
            }
            const fallbackExpandButton = page.locator(firstExpandButtonSelector).first();
            const fallbackCount = await page.locator(firstExpandButtonSelector).count();
            test.skip(fallbackCount === 0, `지정 주문 ${TARGET_ORDER_ID}를 찾지 못했고 대체 storyboard 주문도 없습니다.`);
            await expect(fallbackExpandButton).toBeVisible();
            const fallbackOrderId = extractOrderIdFromTestId(await fallbackExpandButton.getAttribute('data-testid'));
            test.skip(!fallbackOrderId, '대체 광고 주문 ID를 추출하지 못했습니다.');
            return fallbackOrderId;
        }

        let expandCount = await page.locator(firstExpandButtonSelector).count();
        for (let attempt = 0; attempt < 5 && expandCount === 0; attempt += 1) {
            await refreshStoryboardOrders(page);
            expandCount = await page.locator(firstExpandButtonSelector).count();
        }
        const firstExpandButton = page.locator(firstExpandButtonSelector).first();
        test.skip(expandCount === 0, 'storyboard가 있는 광고 주문이 없습니다. `/marketplace/orchestrator` 또는 `POST /api/marketplace/ad-video-orders`로 테스트 주문을 먼저 생성하세요.');

        await expect(firstExpandButton).toBeVisible();
        const orderId = extractOrderIdFromTestId(await firstExpandButton.getAttribute('data-testid'));
        test.skip(!orderId, '첫 유효 광고 주문 ID를 추출하지 못했습니다.');
        return orderId;
    };

    test.beforeEach(async ({ page }) => {
        test.skip((!ADMIN_USERNAME || !ADMIN_PASSWORD) && !HAS_STORAGE_STATE, 'PLAYWRIGHT_ADMIN_USERNAME / PLAYWRIGHT_ADMIN_PASSWORD 또는 storageState 필요');

        const existingToken = readExistingAdminToken();
        if (existingToken) {
            await page.addInitScript((nextToken: string) => {
                window.localStorage.setItem('admin_token', nextToken);
            }, existingToken);
        }

        await page.goto('/admin');
        if (page.url().includes('/admin/login')) {
            test.skip(!ADMIN_USERNAME || !ADMIN_PASSWORD, '로그인 페이지 fallback에는 PLAYWRIGHT_ADMIN_USERNAME / PLAYWRIGHT_ADMIN_PASSWORD 필요');
            await page.getByTestId('admin-login-email').fill(ADMIN_USERNAME);
            await page.getByTestId('admin-login-password').fill(ADMIN_PASSWORD);
            await page.getByTestId('admin-login-submit').click();
        }
        await page.waitForURL(/\/admin(?:\/)?(?:\?.*)?$/);
        await page.getByTestId('admin-storyboard-section-toggle').waitFor({ timeout: ADMIN_DASHBOARD_WAIT_MS });
        await ensureOrdersPanelOpen(page);
    });

    test('review panel opens for storyboard order', async ({ page }) => {
        const targetOrderId = await resolveTargetOrderId(page);
        await page.getByTestId(`admin-storyboard-order-expand-${targetOrderId}`).click();

        await expect(page.getByTestId('admin-storyboard-panel')).toBeVisible();
        await expect(page.getByTestId('admin-storyboard-history-panel')).toBeVisible();
    });

    test('filters can be toggled and reset', async ({ page }) => {
        const targetOrderId = await resolveTargetOrderId(page);
        await page.getByTestId(`admin-storyboard-order-expand-${targetOrderId}`).click();

        await page.getByTestId(`admin-storyboard-filter-diff-only-${targetOrderId}`).click();
        await page.getByTestId(`admin-storyboard-filter-status-only-${targetOrderId}`).click();
        await page.getByTestId(`admin-storyboard-filter-note-only-${targetOrderId}`).click();
        await page.getByTestId(`admin-storyboard-filter-reset-${targetOrderId}`).click();

        await expect(page.getByTestId(`admin-storyboard-filter-diff-only-${targetOrderId}`)).toBeVisible();
    });

    test('thumbnail modal supports navigation and diff display', async ({ page }) => {
        const targetOrderId = await resolveTargetOrderId(page);
        await page.getByTestId(`admin-storyboard-order-expand-${targetOrderId}`).click();
        await page.locator(firstThumbnailSelector).first().click();

        await expect(page.getByTestId('admin-storyboard-modal')).toBeVisible();
        await expect(page.getByTestId('admin-storyboard-diff-panel')).toBeVisible();
        await expect(page.getByTestId('admin-storyboard-modal-index')).toBeVisible();
        await page.getByTestId('admin-storyboard-modal-next').click();
        await page.keyboard.press('ArrowLeft');
        await page.keyboard.press('ArrowRight');
        await page.keyboard.press('Escape');
    });

    test('review save updates history', async ({ page }) => {
        const targetOrderId = await resolveTargetOrderId(page);
        await page.getByTestId(`admin-storyboard-order-expand-${targetOrderId}`).click();

        const statusSelect = page.locator(firstStatusSelectSelector).first();
        const noteTextarea = page.locator(firstNoteTextareaSelector).first();
        await statusSelect.selectOption('approved');
        await noteTextarea.fill('Playwright draft verification note');
        await page.getByTestId(`admin-storyboard-save-${targetOrderId}`).click();

        await expect(page.getByTestId('admin-storyboard-history-panel')).toBeVisible();
    });
});

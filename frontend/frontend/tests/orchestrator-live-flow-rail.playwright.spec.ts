import { expect, test, type Page } from '@playwright/test';

test.describe.configure({ timeout: 120_000 });

async function waitForAdminOrchestratorShell(page: Page) {
    await page.goto('/admin/llm', { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: 'AI 코드 제너레이터' })).toBeVisible({ timeout: 60_000 });
}

async function waitForMarketplaceOrchestratorShell(page: Page) {
    await page.goto('/marketplace/orchestrator', { waitUntil: 'domcontentloaded' });
    await expect(page.getByText('마켓플레이스 오케스트레이터')).toBeVisible({ timeout: 60_000 });
}

test.describe('Orchestrator Live Flow Rail contract', () => {
    test('admin llm exposes 11-stage live flow rail', async ({ page }) => {
        await waitForAdminOrchestratorShell(page);

        const rail = page.getByTestId('orchestrator-live-flow-rail');
        await expect(rail).toBeVisible({ timeout: 60_000 });
        await expect(rail.getByText('Live Flow · 11 STAGE')).toBeVisible();
        await expect(rail.getByText('1단계')).toBeVisible();
        await expect(rail.getByText('10단계')).toBeVisible();
        await expect(rail.getByText(/core:/)).toBeVisible();
        await expect(rail.getByText(/intent:/)).toBeVisible();
    });

    test('marketplace orchestrator exposes live flow rail', async ({ page }) => {
        await waitForMarketplaceOrchestratorShell(page);

        const rail = page.getByTestId('orchestrator-live-flow-rail');
        await expect(rail).toBeVisible({ timeout: 60_000 });
        await expect(rail.getByText('Live Flow · 11 STAGE')).toBeVisible();
        await expect(rail.getByText('4.5단계')).toBeVisible();
        await expect(rail.getByText('다음 안내')).toBeVisible();
    });
});

test.describe('Orchestrator Decision Panel contract', () => {
    test('admin llm always mounts decision panel shell', async ({ page }) => {
        await waitForAdminOrchestratorShell(page);

        await expect(page.getByTestId('orchestrator-live-flow-rail')).toBeVisible({ timeout: 60_000 });
        await expect(page.getByTestId('orchestrator-decision-panel')).toBeVisible();
        await expect(page.getByTestId('orchestrator-decision-empty')).toBeVisible();
    });

    test('marketplace orchestrator always mounts decision panel shell', async ({ page }) => {
        await waitForMarketplaceOrchestratorShell(page);

        await expect(page.getByTestId('orchestrator-live-flow-rail')).toBeVisible({ timeout: 60_000 });
        await expect(page.getByTestId('orchestrator-decision-panel')).toBeVisible();
        await expect(page.getByTestId('orchestrator-decision-empty')).toBeVisible();
    });
});

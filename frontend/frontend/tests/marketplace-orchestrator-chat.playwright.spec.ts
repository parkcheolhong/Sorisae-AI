import { expect, test } from '@playwright/test';

test.describe.configure({ timeout: 120_000 });

test.describe('Marketplace orchestrator chat SSOT (G-5-4-2)', () => {
    test('live rail and decision panel mount together', async ({ page }) => {
        await page.goto('/marketplace/orchestrator', { waitUntil: 'domcontentloaded' });
        await expect(page.getByText('마켓플레이스 오케스트레이터')).toBeVisible({ timeout: 60_000 });
        await expect(page.getByTestId('orchestrator-three-track-diagram')).toBeVisible();
        await expect(page.getByTestId('orchestrator-live-flow-rail')).toBeVisible();
        await expect(page.getByTestId('orchestrator-decision-panel')).toBeVisible();
        await expect(page.getByTestId('orchestrator-decision-empty')).toBeVisible();
    });
});

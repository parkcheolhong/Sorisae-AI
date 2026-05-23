import { expect, test } from '@playwright/test';

const MARKETPLACE_BASE_URL = process.env.PLAYWRIGHT_MARKETPLACE_BASE_URL ?? 'http://localhost:3000';

test('customer orchestrator consumes admin-llm bridge payload for ai-powerpoint product selection', async ({ page }) => {
    await page.addInitScript((bridgePayload: unknown) => {
        window.localStorage.setItem('marketplace_orchestrator_bridge_v1', JSON.stringify(bridgePayload));
    }, {
        source: 'admin-llm',
        bridgedAt: '2026-04-29T10:00:00.000Z',
        productId: 'powerpoint-deck-builder',
        projectName: 'admin-llm-ppt-bridge-project',
        task: '관리자 오케스트레이터에서 전달된 파워포인트 생성 요청입니다. KPI와 리스크 슬라이드를 우선 구성하세요.',
        note: 'playwright integration bridge test',
    });

    await page.goto(`${MARKETPLACE_BASE_URL}/marketplace/orchestrator?product=powerpoint-deck-builder`);

    await expect(page).toHaveURL(/product=powerpoint-deck-builder/);
    await expect(page.locator('input[placeholder="프로젝트명"]')).toHaveValue('admin-llm-ppt-bridge-project');
    await expect(page.locator('textarea').first()).toHaveValue('관리자 오케스트레이터에서 전달된 파워포인트 생성 요청입니다. KPI와 리스크 슬라이드를 우선 구성하세요.');

    const bridgeValue = await page.evaluate(() => window.localStorage.getItem('marketplace_orchestrator_bridge_v1'));
    expect(bridgeValue).toBeNull();
});

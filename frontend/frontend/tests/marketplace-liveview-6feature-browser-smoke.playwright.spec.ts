import { expect, test } from '@playwright/test';

const MARKETPLACE_BASE_URL = process.env.PLAYWRIGHT_MARKETPLACE_BASE_URL ?? 'http://127.0.0.1:3010';

const FEATURES: Array<{ id: string; prompt: string }> = [
    { id: 'ai-sheet', prompt: '영업 리드용 시트를 만들고 다운로드 가능한 결과를 생성한다.' },
    { id: 'ai-image', prompt: '프로모션 배너 이미지를 생성하고 결과 파일을 준비한다.' },
    { id: 'ai-video', prompt: '15초 제품 소개 영상 스토리보드를 만들고 결과 파일을 준비한다.' },
    { id: 'ai-document', prompt: '서비스 제안 문서를 생성하고 결과 파일을 준비한다.' },
    { id: 'ai-music', prompt: '브랜드 티저 음악을 생성하고 결과 파일을 준비한다.' },
    { id: 'ai-powerpoint', prompt: '분기 실적 발표용 파워포인트를 생성하고 결과 파일을 준비한다.' },
];

test('all six marketplace features are browser-runnable with preview/final/download outputs', async ({ page }) => {
    await page.goto(`${MARKETPLACE_BASE_URL}/marketplace`);

    await expect(page.getByTestId('marketplace-feature-launcher-grid')).toBeVisible({ timeout: 10000 });

    for (const feature of FEATURES) {
        await expect(page.getByTestId(`marketplace-feature-card-${feature.id}`)).toBeVisible();
        await page.getByTestId(`marketplace-feature-launch-${feature.id}`).click();

        await expect(page.getByTestId('marketplace-feature-orchestrator-popup')).toBeVisible({ timeout: 10000 });
        await page.getByTestId('marketplace-popup-project-name').fill(`browser-smoke-${feature.id}`);
        await page.getByTestId('marketplace-popup-prompt').fill(feature.prompt);
        await page.getByTestId('marketplace-popup-submit').click();

        await expect(page.getByTestId('marketplace-popup-run-id')).not.toContainText('대기', { timeout: 30000 });
        await expect(page.getByTestId('marketplace-live-view-current-state')).toContainText('완료', { timeout: 45000 });
        await expect(page.getByTestId('marketplace-spreadsheet-downloads')).toBeVisible({ timeout: 15000 });
        await expect(page.locator('a[data-testid^="marketplace-spreadsheet-download-"]').first()).toBeVisible({ timeout: 15000 });

        await page.getByRole('button', { name: '닫기' }).click();
        await expect(page.getByTestId('marketplace-feature-orchestrator-popup')).toBeHidden({ timeout: 10000 });
    }
});

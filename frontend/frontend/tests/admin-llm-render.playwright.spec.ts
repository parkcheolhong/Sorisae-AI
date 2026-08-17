import { expect, test } from '@playwright/test';

test('admin llm renders upgraded generator panels after hydration', async ({ page }) => {
    await page.goto('/admin/llm');

    await expect(page.getByRole('heading', { name: '4가지 코드생성기 고정 정의' })).toBeVisible();
    await expect(page.getByRole('button', { name: /Project Scanner/ })).toBeVisible();
    await expect(page.getByRole('button', { name: /Security Guard/ })).toBeVisible();
    await expect(page.getByRole('button', { name: /Self-Healing Engine/ })).toBeVisible();
    await expect(page.getByRole('button', { name: /Code Generator/ })).toBeVisible();
    await expect(page.getByRole('heading', { name: '관리자 제한값 직접 수정' })).toBeVisible();
    await expect(page.getByRole('heading', { name: '관리자 지시형 챗봇' })).toBeVisible();
    await page.getByRole('button', { name: '펼치기' }).click();
    await expect(page.getByRole('button', { name: '제한값 저장 및 즉시 적용' })).toBeVisible();
    await expect(page.getByRole('button', { name: '오케스트레이터 전역값 저장' })).toBeVisible();
});

test('admin llm opens generator detail modal and exposes dedicated control actions', async ({ page }) => {
    await page.goto('/admin/llm');

    await page.getByRole('button', { name: /Project Scanner/ }).click();
    await expect(page.getByTestId('admin-generator-detail-modal')).toBeVisible();
    await expect(page.getByTestId('admin-generator-detail-modal-title')).toHaveText('Project Scanner');
    await expect(page.getByTestId('admin-generator-detail-modal-directive')).toContainText('Project Scanner 주특기 활성화');
    await expect(page.getByTestId('admin-generator-action-open-capability')).toBeVisible();
    await expect(page.getByTestId('admin-generator-action-open-runtime')).toBeVisible();
    await expect(page.getByTestId('admin-generator-action-open-directive')).toBeVisible();
    await expect(page.getByTestId('admin-generator-action-apply-marketplace')).toBeVisible();
    await page.getByTestId('admin-generator-action-apply-marketplace').click();
    await expect(page.getByRole('textbox', { name: '예: 질문/명령 입력 후 Enter · /run /pass /fix /fail /verify /preset 1' })).toContainText('마켓플레이스 상품 진열');
    await page.getByTestId('admin-generator-detail-modal-close').click();
    await expect(page.getByTestId('admin-generator-detail-modal')).toBeHidden();
});

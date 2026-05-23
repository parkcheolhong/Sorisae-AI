import { expect, test } from '@playwright/test';

const targetUsername = process.env.PLAYWRIGHT_TARGET_USERNAME ?? '';
const adminUsername = process.env.PLAYWRIGHT_ADMIN_USERNAME ?? '';
const adminPassword = process.env.PLAYWRIGHT_ADMIN_PASSWORD ?? '';

function getActiveBadge(row: ReturnType<import('@playwright/test').Page['locator']>) {
    return row.locator('td').nth(7).locator('span');
}

test('ui pod marketplace + admin users operations', async ({ page }) => {
    test.skip(!targetUsername, 'PLAYWRIGHT_TARGET_USERNAME is required');
    test.skip(!adminUsername || !adminPassword, 'PLAYWRIGHT_ADMIN_USERNAME and PLAYWRIGHT_ADMIN_PASSWORD are required');

    await page.goto('/admin/login');
    await page.getByTestId('admin-login-email').fill(adminUsername);
    await page.getByTestId('admin-login-password').fill(adminPassword);
    await page.getByTestId('admin-login-submit').click();
    await page.waitForURL(/\/admin(?:\/)?(?:\?.*)?$/);

    await page.goto('/marketplace');
    await expect(page).toHaveURL(/\/marketplace/);
    await expect(page.getByTestId('marketplace-main-page')).toBeVisible();
    await expect(page.getByTestId('marketplace-stats-cards')).toBeVisible();
    await expect(page.getByPlaceholder('프로젝트 제목/설명 검색')).toBeVisible();
    await expect(page.getByText('마켓플레이스 데이터를 불러오는 중...')).toHaveCount(0, { timeout: 30_000 });
    await expect(page.getByText('마켓플레이스 데이터를 불러오지 못했습니다.')).toHaveCount(0);
    await expect(page.getByText(/상품\s+\d+개\s+노출/)).toBeVisible();

    await page.goto('/admin/users');
    await expect(page).toHaveURL(/\/admin\/users/);
    await expect(page.getByTestId('admin-users-page')).toBeVisible();
    await expect(page.getByText('회원가입 사용자 확인')).toBeVisible();
    await expect(page.getByTestId('admin-users-table')).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText('⏳ 로딩 중...')).toHaveCount(0, { timeout: 30_000 });
    await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 30_000 });

    const targetRow = page.locator('tbody tr').filter({ hasText: targetUsername });
    await expect(targetRow).toHaveCount(1, { timeout: 30_000 });

    const activeBadge = getActiveBadge(targetRow);
    const before = (await activeBadge.innerText()).trim();
    await activeBadge.click();
    await expect(activeBadge).not.toHaveText(before);

    page.once('dialog', (dialog) => dialog.accept());
    await targetRow.getByRole('button', { name: '삭제' }).click();
    await expect(targetRow).toHaveCount(0);
});

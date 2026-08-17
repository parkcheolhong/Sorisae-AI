import { expect, test } from '@playwright/test';

const adminUsername = process.env.PLAYWRIGHT_ADMIN_USERNAME ?? '';
const adminPassword = process.env.PLAYWRIGHT_ADMIN_PASSWORD ?? '';

test('admin login page enforces passkey and recovery policy', async ({ page }) => {
    test.skip(!adminUsername || !adminPassword, 'PLAYWRIGHT_ADMIN_USERNAME and PLAYWRIGHT_ADMIN_PASSWORD are required');

    await page.goto('/admin/login');
    await expect(page.getByRole('heading', { name: '관리자 대시보드' })).toBeVisible();

    await page.getByTestId('admin-login-email').fill(adminUsername);
    await page.getByTestId('admin-login-password').fill(adminPassword);
    await page.getByTestId('admin-login-submit').click();

    // Current policy keeps password login blocked; page should stay on login screen.
    await expect(page).toHaveURL(/\/admin\/login(?:\?.*)?$/);
    await expect(page.getByText('비밀번호 로그인은 정책상 비활성화되어 있습니다.')).toBeVisible();

    const recoveryLink = page.getByRole('link', { name: '비밀번호를 잊으셨나요? (이메일/문자 인증)' });
    await expect(recoveryLink).toBeVisible();
    await expect(recoveryLink).toHaveAttribute('href', '/admin/recovery');

    const passkeyRecoveryLink = page.getByRole('link', { name: '비밀번호 없이 패스키 등록 (이메일/문자 인증)' });
    await expect(passkeyRecoveryLink).toBeVisible();
    await expect(passkeyRecoveryLink).toHaveAttribute('href', '/admin/recovery?intent=passkey');

    await expect(page.getByRole('button', { name: '📱 지문/패스키 로그인' })).toBeVisible();
    await expect(page.getByRole('button', { name: '🪪 이 기기 패스키 등록' })).toBeVisible();
});
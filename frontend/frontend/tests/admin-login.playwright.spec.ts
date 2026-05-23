import { expect, test } from '@playwright/test';

test.describe('admin login regression', () => {
    test.use({ storageState: { cookies: [], origins: [] } });

    test('login screen restores remembered preferences and recovery links remain connected', async ({ page }) => {
        await page.addInitScript(() => {
            window.localStorage.setItem('admin_login_remember_id_v1', 'true');
            window.localStorage.setItem('admin_login_remember_password_v1', 'true');
            window.localStorage.setItem('admin_login_allow_passkey_v1', 'true');
            window.localStorage.setItem('admin_login_email_v1', '119cash@naver.com');
            window.localStorage.setItem('admin_login_password_v1', 'sample-password');
        });

        await page.goto('/admin/login');

        await expect(page.getByTestId('admin-login-form')).toBeVisible();
        await expect(page.getByTestId('admin-login-email')).toHaveValue('119cash@naver.com');
        await expect(page.getByTestId('admin-login-password')).toHaveValue('sample-password');
        await expect(page.getByTestId('admin-login-remember-id')).toBeChecked();
        await expect(page.getByTestId('admin-login-remember-password')).toBeChecked();
        await expect(page.getByTestId('admin-login-allow-passkey')).toBeChecked();
        await expect(page.getByTestId('admin-login-passkey-button')).toBeEnabled();
        await expect(page.getByTestId('admin-login-recovery-link')).toHaveAttribute('href', '/admin/recovery');
        await expect(page.getByTestId('admin-login-carrier-recovery-link')).toHaveAttribute('href', '/admin/recovery?mode=carrier');
    });

    test('login screen validates required credentials before proxy request', async ({ page }) => {
        await page.goto('/admin/login');

        await page.getByTestId('admin-login-submit').click();
        await expect(page.getByTestId('admin-login-error')).toContainText('이메일과 비밀번호를 모두 입력해주세요.');
    });

    test('login timeout shows stable recovery guidance when admin proxy is slow', async ({ page }) => {
        await page.route('**/api/proxy', async () => {
            await page.waitForTimeout(1000);
            throw new Error('simulated proxy disconnect');
        });

        await page.goto('/admin/login');
        await page.getByTestId('admin-login-email').fill('119cash@naver.com');
        await page.getByTestId('admin-login-password').fill('timeout-password');
        await page.getByTestId('admin-login-submit').click();

        await expect(page.getByTestId('admin-login-error')).toContainText('서버 연결에 실패했습니다. 관리자 프록시 또는 백엔드 연결 상태를 확인한 뒤 다시 시도해주세요.');
    });
});

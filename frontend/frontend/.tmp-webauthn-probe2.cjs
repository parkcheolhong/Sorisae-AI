const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ ignoreHTTPSErrors: true, baseURL: 'https://metanova1004.com' });
  const page = await context.newPage();
  await page.goto('https://metanova1004.com/admin/login', { waitUntil: 'domcontentloaded' });
  for (const ms of [0, 500, 1500, 4000]) {
    if (ms) await page.waitForTimeout(ms);
    const snap = await page.evaluate(() => ({
      t: Date.now(),
      allowFlag: localStorage.getItem('admin_login_allow_passkey_v1'),
      passkeyDisabled: document.querySelector('[data-testid="admin-login-passkey-register"]')?.disabled ?? null,
      submitDisabled: document.querySelector('[data-testid="admin-login-submit"]')?.disabled ?? null,
      emailValue: document.querySelector('[data-testid="admin-login-email"]')?.value ?? '',
      pwdDisabled: document.querySelector('[data-testid="admin-login-password"]')?.disabled ?? null,
    }));
    console.log(ms, JSON.stringify(snap));
  }
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });

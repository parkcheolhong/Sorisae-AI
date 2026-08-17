const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ ignoreHTTPSErrors: true, baseURL: 'https://metanova1004.com' });
  const page = await context.newPage();
  await page.goto('https://metanova1004.com/admin/login', { waitUntil: 'domcontentloaded' });
  const before = await page.evaluate(() => ({
    secure: window.isSecureContext,
    hasPKC: typeof window.PublicKeyCredential !== 'undefined',
    hasCreds: !!navigator.credentials,
    hasCreate: !!navigator.credentials?.create,
    hasGet: !!navigator.credentials?.get,
    allowFlag: localStorage.getItem('admin_login_allow_passkey_v1'),
    passkeyBtnDisabled: document.querySelector('[data-testid="admin-login-passkey-register"]')?.disabled ?? null,
  }));
  const client = await context.newCDPSession(page);
  await client.send('WebAuthn.enable');
  await client.send('WebAuthn.addVirtualAuthenticator', {
    options: {
      protocol: 'ctap2',
      transport: 'internal',
      hasResidentKey: true,
      hasUserVerification: true,
      isUserVerified: true,
      automaticPresenceSimulation: true,
    },
  });
  const after = await page.evaluate(() => ({
    secure: window.isSecureContext,
    hasPKC: typeof window.PublicKeyCredential !== 'undefined',
    hasCreds: !!navigator.credentials,
    hasCreate: !!navigator.credentials?.create,
    hasGet: !!navigator.credentials?.get,
    allowFlag: localStorage.getItem('admin_login_allow_passkey_v1'),
    passkeyBtnDisabled: document.querySelector('[data-testid="admin-login-passkey-register"]')?.disabled ?? null,
  }));
  console.log(JSON.stringify({ before, after }, null, 2));
  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});

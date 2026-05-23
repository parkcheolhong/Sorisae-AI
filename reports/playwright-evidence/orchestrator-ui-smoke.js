const fs = require('fs');
const path = require('path');
const { chromium } = require('@playwright/test');

(async () => {
  const outDir = 'c:/Users/WORK/source/repos/parkcheolhong/codeAI/reports/playwright-evidence';
  fs.mkdirSync(outDir, { recursive: true });

  const adminBase = process.env.PLAYWRIGHT_ADMIN_BASE_URL || 'http://127.0.0.1:3000';
  const marketBase = process.env.PLAYWRIGHT_MARKETPLACE_BASE_URL || 'http://127.0.0.1:3000';

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1600, height: 1100 } });
  const page = await context.newPage();

  const results = {
    adminBase,
    marketBase,
    adminUi: { ok: false, marker: '' },
    marketUi: { ok: false, marker: '' },
  };

  try {
    await page.goto(`${adminBase}/admin/login`, { waitUntil: 'networkidle', timeout: 120000 });
    await page.getByTestId('admin-login-email').fill('ui.admin.round@devanalysis.local');
    await page.getByTestId('admin-login-password').fill('RoundUi!20260426');
    await page.getByTestId('admin-login-submit').click();
    await page.waitForLoadState('networkidle', { timeout: 120000 });

    await page.goto(`${adminBase}/admin/llm`, { waitUntil: 'networkidle', timeout: 120000 });
    const adminInput = page.locator('textarea').first();
    await adminInput.waitFor({ timeout: 60000 });
    await adminInput.fill('UI smoke: 답변 후 역질문 1개를 해줘.');

    const sendBtn = page.getByRole('button', { name: /전송|send|요청|실행/i }).first();
    if (await sendBtn.count()) {
      await sendBtn.click();
    } else {
      await adminInput.press('Enter');
    }

    const adminMarker = page.getByText(/역질문|우선순위 1번|어떤.*원하시나요|대화를 끊지 않고/i).first();
    await adminMarker.waitFor({ timeout: 120000 });
    results.adminUi.marker = (await adminMarker.textContent() || '').trim().slice(0, 180);
    results.adminUi.ok = true;

    const adminShot = path.join(outDir, 'admin-llm-reverse-question.png');
    await page.screenshot({ path: adminShot, fullPage: true });

    await page.goto(`${marketBase}/marketplace/orchestrator`, { waitUntil: 'networkidle', timeout: 120000 });
    const marketInput = page.locator('textarea').first();
    await marketInput.waitFor({ timeout: 60000 });
    await marketInput.fill('UI smoke: 답변하고 역질문으로 이어가줘.');

    const marketSendBtn = page.getByRole('button', { name: /전송|send|요청|실행/i }).first();
    if (await marketSendBtn.count()) {
      await marketSendBtn.click();
    } else {
      await marketInput.press('Enter');
    }

    const marketMarker = page.getByText(/역질문|우선순위 1번|대화를 끊지 않고|어떤.*원하시나요/i).first();
    await marketMarker.waitFor({ timeout: 120000 });
    results.marketUi.marker = (await marketMarker.textContent() || '').trim().slice(0, 180);
    results.marketUi.ok = true;

    const marketShot = path.join(outDir, 'marketplace-orchestrator-reverse-question.png');
    await page.screenshot({ path: marketShot, fullPage: true });

    const resultPath = path.join(outDir, 'orchestrator-ui-smoke-result.json');
    fs.writeFileSync(resultPath, JSON.stringify(results, null, 2), 'utf8');

    console.log('ui_smoke_result=' + JSON.stringify(results));
    console.log('admin_screenshot=' + adminShot);
    console.log('market_screenshot=' + marketShot);
    console.log('result_json=' + resultPath);
  } finally {
    await browser.close();
  }
})();

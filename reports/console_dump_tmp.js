const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ ignoreHTTPSErrors: true });
  const urls = [
    'https://xn--114-2p7l635dz3bh5j.com/admin',
    'https://xn--114-2p7l635dz3bh5j.com/marketplace',
    'https://xn--114-2p7l635dz3bh5j.com/marketplace/orchestrator',
    'https://metanova1004.com/marketplace',
    'https://metanova1004.com/marketplace/orchestrator',
  ];
  const logs = [];

  page.on('console', (msg) => {
    logs.push({ type: msg.type(), text: msg.text(), url: page.url() });
  });
  page.on('pageerror', (err) => {
    logs.push({ type: 'pageerror', text: String(err), url: page.url() });
  });

  // Capture true CSP violations from the browser event stream.
  await page.addInitScript(() => {
    window.addEventListener('securitypolicyviolation', (e) => {
      const payload = {
        type: 'csp-violation',
        effectiveDirective: e.effectiveDirective,
        violatedDirective: e.violatedDirective,
        blockedURI: e.blockedURI,
        sourceFile: e.sourceFile,
        lineNumber: e.lineNumber,
        sample: e.sample,
      };
      console.error('[SECURITY_POLICY_VIOLATION]', JSON.stringify(payload));
    });
  });

  for (const url of urls) {
    try {
      await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
      await page.waitForTimeout(3000);
    } catch (e) {
      logs.push({ type: 'nav-error', text: String(e), url });
    }
  }

  const cspEvalOrScriptSrc = logs.filter((entry) => {
    const text = String(entry.text || '').toLowerCase();
    return (
      text.includes('content security policy') ||
      text.includes('security_policy_violation') ||
      text.includes('unsafe-eval') ||
      text.includes('script-src') ||
      text.includes('eval')
    );
  });

  console.log(
    JSON.stringify(
      {
        totalLogCount: logs.length,
        matchedCount: cspEvalOrScriptSrc.length,
        matched: cspEvalOrScriptSrc,
      },
      null,
      2,
    ),
  );
  await browser.close();
})();

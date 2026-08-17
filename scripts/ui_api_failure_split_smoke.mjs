import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { chromium } from "playwright";

const LOCAL_PAGE_FALLBACKS = {
  marketplace: "http://127.0.0.1:3000/marketplace",
  admin_3000_login: "http://127.0.0.1:3000/admin/login",
  admin_3005_login: "http://127.0.0.1:3005/admin/login",
};

function nowStamp() {
  const d = new Date();
  const p = (v) => String(v).padStart(2, "0");
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}_${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
}

function parseArgs(argv) {
  const args = {
    outDir: "",
    marketplaceUrl: "http://127.0.0.1:3000/marketplace",
    adminUrl3000: "http://127.0.0.1:3000/admin/login",
    adminUrl3005: "http://127.0.0.1:3005/admin/login",
    timeoutMs: 20000,
    harDir: "",
  };

  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    const n = argv[i + 1];
    if (a === "--out-dir" && n) {
      args.outDir = n;
      i += 1;
    } else if (a === "--marketplace-url" && n) {
      args.marketplaceUrl = n;
      i += 1;
    } else if (a === "--admin-url-3000" && n) {
      args.adminUrl3000 = n;
      i += 1;
    } else if (a === "--admin-url-3005" && n) {
      args.adminUrl3005 = n;
      i += 1;
    } else if (a === "--timeout-ms" && n) {
      args.timeoutMs = Number.parseInt(n, 10) || 20000;
      i += 1;
    } else if (a === "--har-dir" && n) {
      args.harDir = n;
      i += 1;
    }
  }

  return args;
}

function safeName(value) {
  return String(value || "").replace(/[^a-zA-Z0-9._-]+/g, "_");
}

function isLocalHttpUrl(value) {
  try {
    const parsed = new URL(String(value || ""));
    return (parsed.hostname === "127.0.0.1" || parsed.hostname === "localhost") && (parsed.protocol === "http:" || parsed.protocol === "https:");
  } catch {
    return false;
  }
}

async function canReachUrl(value, timeoutMs = 2500) {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch(value, {
        method: "GET",
        redirect: "manual",
        signal: controller.signal,
      });
      return response.status > 0;
    } finally {
      clearTimeout(timer);
    }
  } catch {
    return false;
  }
}

async function resolveProbeUrl(pageLabel, requestedUrl) {
  const fallbackUrl = LOCAL_PAGE_FALLBACKS[pageLabel];
  if (!fallbackUrl || !isLocalHttpUrl(requestedUrl) || String(requestedUrl) === fallbackUrl) {
    return {
      requestedUrl,
      effectiveUrl: requestedUrl,
      fallbackApplied: false,
      fallbackReason: "",
    };
  }

  if (await canReachUrl(requestedUrl)) {
    return {
      requestedUrl,
      effectiveUrl: requestedUrl,
      fallbackApplied: false,
      fallbackReason: "",
    };
  }

  if (await canReachUrl(fallbackUrl)) {
    return {
      requestedUrl,
      effectiveUrl: fallbackUrl,
      fallbackApplied: true,
      fallbackReason: `requested_unreachable_using_canonical_local_url:${fallbackUrl}`,
    };
  }

  return {
    requestedUrl,
    effectiveUrl: requestedUrl,
    fallbackApplied: false,
    fallbackReason: "",
  };
}

async function probePage(browser, pageLabel, url, timeoutMs, outDir, harDir) {
  const contextOptions = {};
  let harPath = "";
  if (harDir) {
    fs.mkdirSync(harDir, { recursive: true });
    harPath = path.join(harDir, `${safeName(pageLabel)}.har`);
    contextOptions.recordHar = {
      path: harPath,
      mode: "full",
      content: "attach",
    };
  }

  const context = await browser.newContext(contextOptions);
  const page = await context.newPage();
  const startedAt = Date.now();
  const probeTarget = await resolveProbeUrl(pageLabel, url);

  const result = {
    pageLabel,
    url: probeTarget.effectiveUrl,
    requestedUrl: url,
    fallbackApplied: probeTarget.fallbackApplied,
    fallbackReason: probeTarget.fallbackReason,
    ok: false,
    status: null,
    finalUrl: "",
    elapsedMs: 0,
    consoleErrors: [],
    consoleWarnings: [],
    pageErrors: [],
    requestFailed: [],
    requestFailedIgnored: [],
    apiHttpErrors: [],
    harPath,
    screenshot: "",
    htmlSnapshot: "",
  };

  page.on("console", (msg) => {
    const type = msg.type();
    const text = msg.text();
    if (type === "error") {
      result.consoleErrors.push(text);
    } else if (type === "warning") {
      result.consoleWarnings.push(text);
    }
  });

  page.on("pageerror", (err) => {
    result.pageErrors.push(String(err?.message || err));
  });

  page.on("requestfailed", (req) => {
    const row = {
      url: req.url(),
      method: req.method(),
      errorText: req.failure()?.errorText || "request_failed",
    };
    if (row.errorText.includes("ERR_ABORTED")) {
      result.requestFailedIgnored.push(row);
      return;
    }
    result.requestFailed.push(row);
  });

  page.on("response", async (res) => {
    try {
      const status = res.status();
      const rurl = res.url();
      if (status >= 400 && rurl.includes("/api/")) {
        result.apiHttpErrors.push({
          status,
          url: rurl,
          method: res.request().method(),
        });
      }
    } catch {
      // no-op
    }
  });

  try {
    const res = await page.goto(probeTarget.effectiveUrl, { waitUntil: "domcontentloaded", timeout: timeoutMs });
    result.status = res ? res.status() : null;
    result.finalUrl = page.url();

    await page.waitForTimeout(1200);

    result.ok =
      (result.status === null || (result.status >= 200 && result.status < 400)) &&
      result.pageErrors.length === 0 &&
      result.requestFailed.length === 0;
  } catch (err) {
    result.ok = false;
    result.pageErrors.push(`navigation_error: ${String(err?.message || err)}`);
  }

  result.elapsedMs = Date.now() - startedAt;

  const base = safeName(pageLabel);
  const screenshotPath = path.join(outDir, `${base}.png`);
  const htmlPath = path.join(outDir, `${base}.html`);
  try {
    await page.screenshot({ path: screenshotPath, fullPage: true });
    result.screenshot = screenshotPath;
  } catch {
    // no-op
  }

  try {
    const html = await page.content();
    fs.writeFileSync(htmlPath, html, "utf8");
    result.htmlSnapshot = htmlPath;
  } catch {
    // no-op
  }

  await page.close();
  await context.close();
  return result;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const stamp = nowStamp();
  const outDir = args.outDir || path.resolve(process.cwd(), "scripts", `ui_api_smoke_${stamp}`);
  fs.mkdirSync(outDir, { recursive: true });

  const browser = await chromium.launch({ headless: true });

  const pages = [
    { label: "marketplace", url: args.marketplaceUrl },
    { label: "admin_3000_login", url: args.adminUrl3000 },
    { label: "admin_3005_login", url: args.adminUrl3005 },
  ];

  const report = {
    startedAt: new Date().toISOString(),
    outDir,
    timeoutMs: args.timeoutMs,
    harEnabled: Boolean(args.harDir),
    harDir: args.harDir || "",
    pages: [],
    summary: {
      total: 0,
      ok: 0,
      fail: 0,
      totalConsoleErrors: 0,
      totalPageErrors: 0,
      totalRequestFailed: 0,
      totalApiHttpErrors: 0,
    },
  };

  for (const p of pages) {
    const r = await probePage(browser, p.label, p.url, args.timeoutMs, outDir, args.harDir);
    report.pages.push(r);
  }

  await browser.close();

  report.summary.total = report.pages.length;
  report.summary.ok = report.pages.filter((x) => x.ok).length;
  report.summary.fail = report.summary.total - report.summary.ok;
  report.summary.totalConsoleErrors = report.pages.reduce((acc, x) => acc + x.consoleErrors.length, 0);
  report.summary.totalPageErrors = report.pages.reduce((acc, x) => acc + x.pageErrors.length, 0);
  report.summary.totalRequestFailed = report.pages.reduce((acc, x) => acc + x.requestFailed.length, 0);
  report.summary.totalRequestFailedIgnored = report.pages.reduce((acc, x) => acc + x.requestFailedIgnored.length, 0);
  report.summary.totalApiHttpErrors = report.pages.reduce((acc, x) => acc + x.apiHttpErrors.length, 0);

  const reportPath = path.join(outDir, "ui_smoke_report.json");
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), "utf8");

  const summaryLines = [
    `out_dir=${outDir}`,
    `ui_total=${report.summary.total}`,
    `ui_ok=${report.summary.ok}`,
    `ui_fail=${report.summary.fail}`,
    `ui_console_errors=${report.summary.totalConsoleErrors}`,
    `ui_page_errors=${report.summary.totalPageErrors}`,
    `ui_request_failed=${report.summary.totalRequestFailed}`,
    `ui_request_failed_ignored=${report.summary.totalRequestFailedIgnored}`,
    `ui_api_http_errors=${report.summary.totalApiHttpErrors}`,
    `ui_report=${reportPath}`,
  ];

  const summaryPath = path.join(outDir, "ui_smoke_summary.txt");
  fs.writeFileSync(summaryPath, `${summaryLines.join("\n")}\n`, "utf8");

  for (const line of summaryLines) {
    console.log(line);
  }

  process.exit(report.summary.fail > 0 ? 2 : 0);
}

main().catch((err) => {
  console.error(`fatal: ${String(err?.message || err)}`);
  process.exit(99);
});

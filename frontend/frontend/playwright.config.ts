const fs = require('fs');
const { defineConfig, devices } = require('@playwright/test');

const orchestratorLiveFlowSpecRequested = process.argv.some((arg) =>
    String(arg).includes('orchestrator-live-flow-rail')
    || String(arg).includes('orchestrator-discuss4')
    || String(arg).includes('orchestrator-dod4')
    || String(arg).includes('orchestrator-dod5')
    || String(arg).includes('orchestrator-visual-flow-evidence')
    || String(arg).includes('marketplace-orchestrator-chat')
);
const orchestratorE2ePort = process.env.PLAYWRIGHT_ORCHESTRATOR_E2E_PORT ?? '3025';
const useOrchestratorDedicatedServer =
    orchestratorLiveFlowSpecRequested && process.env.PLAYWRIGHT_USE_WEBSERVER !== '0';

const ADMIN_REGRESSION_SCRIPT_PREFIX = 'ci:admin-regression:';
const npmLifecycleEvent = process.env.npm_lifecycle_event ?? '';
const isAdminRegressionRun = npmLifecycleEvent.startsWith(ADMIN_REGRESSION_SCRIPT_PREFIX);
const adminPort = Number(
    useOrchestratorDedicatedServer
        ? orchestratorE2ePort
        : (process.env.PLAYWRIGHT_ADMIN_PORT ?? '3005'),
);
const orchestratorWebServerUrl = `http://127.0.0.1:${orchestratorE2ePort}`;
const webServerUrl = useOrchestratorDedicatedServer
    ? orchestratorWebServerUrl
    : (process.env.PLAYWRIGHT_ADMIN_BASE_URL ?? `http://127.0.0.1:${adminPort}`);
const webServerHealthUrl = `${webServerUrl.replace(/\/$/, '')}/admin/login`;

if (useOrchestratorDedicatedServer) {
    process.env.PLAYWRIGHT_ORCHESTRATOR_E2E = '1';
    process.env.ADMIN_REGRESSION_MOCK_BACKEND = '1';
    process.env.PLAYWRIGHT_ADMIN_BASE_URL = orchestratorWebServerUrl;
    if (!process.env.PLAYWRIGHT_STORAGE_STATE) {
        process.env.PLAYWRIGHT_STORAGE_STATE = 'playwright/.auth/adminAuthState-orchestrator-e2e.json';
    }
}

const baseURL = webServerUrl;
const storageState = process.env.PLAYWRIGHT_STORAGE_STATE ?? 'playwright/.auth/adminAuthState.json';
const storageStatePath = fs.existsSync(storageState) ? storageState : undefined;

const shouldStartWebServer =
    useOrchestratorDedicatedServer
    || process.env.PLAYWRIGHT_USE_WEBSERVER === '1'
    || (!!process.env.CI && isAdminRegressionRun);
const forceFreshWebServer = process.env.PLAYWRIGHT_FORCE_FRESH_WEBSERVER === '1';
const reuseExistingWebServer = forceFreshWebServer
    ? false
    : useOrchestratorDedicatedServer
        ? true
        : (process.env.PLAYWRIGHT_USE_WEBSERVER === '1' ? false : !process.env.CI);

module.exports = defineConfig({
    testDir: './tests',
    timeout: 30000,
    expect: { timeout: 5000 },
    fullyParallel: false,
    retries: process.env.CI ? 2 : 0,
    reporter: [['list'], ['html', { open: 'never' }]],
    use: {
        baseURL,
        trace: 'on-first-retry',
        screenshot: 'only-on-failure',
        video: 'retain-on-failure',
        actionTimeout: 10000,
        ignoreHTTPSErrors: true,
    },
    webServer: shouldStartWebServer
        ? {
            command: `npm run dev -- --hostname 127.0.0.1 --port ${adminPort}`,
            url: webServerHealthUrl,
            timeout: 180000,
            reuseExistingServer: reuseExistingWebServer,
            stdout: 'pipe',
            stderr: 'pipe',
            env: {
                ...process.env,
                BACKEND_PROXY_TARGET: process.env.BACKEND_PROXY_TARGET ?? 'http://127.0.0.1:8000',
                LOCAL_API_BASE_URL: process.env.LOCAL_API_BASE_URL ?? 'http://127.0.0.1:8000',
                ...(useOrchestratorDedicatedServer
                    ? {
                        ADMIN_REGRESSION_MOCK_BACKEND: '1',
                        CI: '1',
                    }
                    : {}),
            },
        }
        : undefined,
    projects: [
        {
            name: 'setup',
            testMatch: /.*\.setup\.playwright\.spec\.ts/,
        },
        {
            name: 'chromium',
            dependencies: ['setup'],
            testIgnore: /.*\.setup\.playwright\.spec\.ts/,
            use: {
                ...devices['Desktop Chrome'],
                ...(storageStatePath ? { storageState: storageStatePath } : {}),
            },
        },
    ],
});

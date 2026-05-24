const fs = require('fs');
const { defineConfig, devices } = require('@playwright/test');

const baseURL = process.env.PLAYWRIGHT_ADMIN_BASE_URL ?? 'http://localhost:3005';
const storageState = process.env.PLAYWRIGHT_STORAGE_STATE ?? 'playwright/.auth/adminAuthState.json';
const storageStatePath = fs.existsSync(storageState) ? storageState : undefined;
const useWebServer = process.env.PLAYWRIGHT_USE_WEBSERVER === '1';
const adminPort = Number(process.env.PLAYWRIGHT_ADMIN_PORT ?? '3005');

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
    webServer: useWebServer
        ? {
            command: `npm run dev -- --hostname 127.0.0.1 --port ${adminPort}`,
            url: baseURL,
            timeout: 180000,
            reuseExistingServer: !process.env.CI,
            stdout: 'pipe',
            stderr: 'pipe',
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

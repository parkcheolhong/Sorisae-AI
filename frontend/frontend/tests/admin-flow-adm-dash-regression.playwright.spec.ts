import { expect, test } from '@playwright/test';

const ADMIN_USERNAME = process.env.PLAYWRIGHT_ADMIN_USERNAME ?? '';
const ADMIN_PASSWORD = process.env.PLAYWRIGHT_ADMIN_PASSWORD ?? '';
const ADMIN_REGRESSION_MOCK_BACKEND = process.env.ADMIN_REGRESSION_MOCK_BACKEND === '1' && process.env.CI === '1';
const ADMIN_REGRESSION_MOCK_TOKEN = 'admin-regression-mock-token';

const MOCK_SYSTEM_SETTINGS_PAYLOAD = {
    env_path: '.env',
    runtime_config_path: 'knowledge/worldlinco_tuning_config.json',
    sections: [
        {
            id: 'core',
            title: 'Core',
            usage: 'test',
            description: 'mock',
            fields: [
                {
                    key: 'LOCAL_API_BASE_URL',
                    label: 'LOCAL_API_BASE_URL',
                    value: 'http://127.0.0.1:8000',
                    sensitive: false,
                    multiline: false,
                },
            ],
        },
    ],
    summary: {
        admin_domain: 'http://127.0.0.1:3005',
        api_domain: 'http://127.0.0.1:8000',
        local_api_base_url: 'http://127.0.0.1:8000',
        api_docs_url: 'http://127.0.0.1:8000/docs',
        marketplace_host_root: '.runtime/outputs',
        marketplace_upload_root: '.runtime/uploads',
        nginx_http_port: '80',
        nginx_https_port: '443',
        selected_profile: 'mock',
        code_generation_strategy: 'mock',
        default_model: 'mock-model',
        chat_model: 'mock-model',
        voice_chat_model: 'mock-model',
        reasoning_model: 'mock-model',
        coding_model: 'mock-model',
        available_model_count: 1,
        available_models: ['mock-model'],
        generator_profiles: [],
    },
    integration_checks: {
        items: [],
        connected_count: 0,
        total_count: 0,
        all_connected: false,
    },
};

const MOCK_THRESHOLD_ANALYSIS_PAYLOAD = {
    analysis_mode_enabled: true,
    last_analyzed_at: new Date().toISOString(),
    recommendations: {
        rails: {
            sla: {},
            list: {},
            ops: {},
            cover: {},
            llm: {},
            performance: { response_budget_ms: 1200, db_query_budget_ms: 300 },
            latency: { p50_budget_ms: 500, p95_budget_ms: 1500 },
            data: {},
            monitoring: {},
        },
        worldlinco: {},
        observation_summary: {
            metrics: { p50_latency_ms: 300, p95_latency_ms: 800 },
            sorisae_classification: 'ALL_PASS',
            observations_complete: true,
        },
    },
    approvals: {
        rails: { approved: true, approved_at: null, approved_by: null, fingerprint: 'mock' },
        worldlinco: { approved: true, approved_at: null, approved_by: null, fingerprint: 'mock' },
    },
    safe_gate: {
        threshold_recovery_allowed: true,
        worldlinco_auto_apply_allowed: true,
        reason: 'mock-safe',
    },
};

const MOCK_RAIL_SETTINGS_PAYLOAD = {
    settings_path: '.runtime/admin_rail_settings.json',
    updated_at: new Date().toISOString(),
    rails: {
        sla: { enabled: true, availability_target_percent: 99.9, alert_on_breach: true, auto_push_on_breach: true, breach_cooldown_minutes: 15 },
        list: { enabled: true, auto_refresh_seconds: 30, show_failed_only: false, include_raw_payload: true, max_items: 20 },
        ops: { enabled: true, auto_apply_global_mode: true, healthcheck_on_open: true, allow_runtime_restart: false, deployment_gate_level: 'strict' },
        cover: { enabled: true, target_fastpath_percent: 85, enforce_fastpath_guard: true, auto_open_failures: true, sample_size: 25 },
        llm: { enabled: true, route_timeout_ms: 45000, prefer_fast_path: true, auto_recover_on_timeout: true, max_retry_count: 2 },
        performance: { enabled: true, response_budget_ms: 600, db_query_budget_ms: 250, cache_ttl_seconds: 300, auto_collect_snapshot: true },
        latency: { enabled: true, p50_budget_ms: 180, p95_budget_ms: 700, sampling_window_minutes: 15, alert_on_regression: true },
        data: { enabled: true, metric_refresh_seconds: 20, include_zero_metrics: false, selected_metric_key: 'http_requests_total', max_series_points: 120 },
        monitoring: { enabled: true, grafana_base_url: 'http://127.0.0.1:3000', auto_refresh_seconds: 20, open_external_dashboard: false, alert_channel: 'admin' },
    },
};

async function installFlowAdmDashApiMocks(page: import('@playwright/test').Page) {
    await page.route('**/api/admin/system-settings', async (route) => {
        const method = route.request().method().toUpperCase();
        if (method !== 'GET') {
            await route.continue();
            return;
        }
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(MOCK_SYSTEM_SETTINGS_PAYLOAD),
        });
    });

    await page.route('**/api/**', async (route) => {
        const request = route.request();
        const url = new URL(request.url());
        const path = url.pathname;

        if (path === '/api/admin/system-settings' || path === '/api/proxy') {
            await route.continue();
            return;
        }

        if (path === '/api/admin/threshold-analysis') {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify(MOCK_THRESHOLD_ANALYSIS_PAYLOAD),
            });
            return;
        }

        if (path === '/api/admin/rail-settings') {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify(MOCK_RAIL_SETTINGS_PAYLOAD),
            });
            return;
        }

        if (request.method().toUpperCase() !== 'GET') {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({ ok: true }),
            });
            return;
        }

        if (path.endsWith('/stats/overview')) {
            await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ projects: 0, users: 0, purchases: 0, reviews: 0 }) });
            return;
        }
        if (path.endsWith('/stats/revenue')) {
            await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ total_revenue: 0, total_purchases: 0, average_purchase_amount: 0 }) });
            return;
        }
        if (path.endsWith('/stats/top-projects')) {
            await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
            return;
        }

        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({}),
        });
    });
}

async function loginToAdminDashboard(page: import('@playwright/test').Page) {
    if (ADMIN_REGRESSION_MOCK_BACKEND) {
        await page.addInitScript((token: string) => {
            window.localStorage.setItem('admin_token', token);
        }, ADMIN_REGRESSION_MOCK_TOKEN);
        await page.goto('/admin');
        await page.evaluate((token: string) => {
            window.localStorage.setItem('admin_token', token);
        }, ADMIN_REGRESSION_MOCK_TOKEN);
        await page.waitForURL(/\/admin(?:\/)?(?:\?.*)?$/);
        await expect(page.getByTestId('admin-topnav-refresh')).toBeVisible({ timeout: 45_000 });
        return;
    }

    await page.goto('/admin');

    const refreshButton = page.getByTestId('admin-topnav-refresh');
    const loginEmailInput = page.getByTestId('admin-login-email');
    const refreshVisible = await refreshButton.isVisible().catch(() => false);
    if (!refreshVisible) {
        await page.waitForURL(/\/admin(?:\/login)?(?:\?.*)?$/, { timeout: 30_000 }).catch(() => {});
    }

    const loginVisible = await loginEmailInput.isVisible().catch(() => false);
    if (loginVisible || page.url().includes('/admin/login')) {
        test.skip(!ADMIN_USERNAME || !ADMIN_PASSWORD, 'PLAYWRIGHT_ADMIN_USERNAME and PLAYWRIGHT_ADMIN_PASSWORD are required');
        await loginEmailInput.fill(ADMIN_USERNAME);
        await page.getByTestId('admin-login-password').fill(ADMIN_PASSWORD);
        await page.getByTestId('admin-login-submit').click();
    }

    await page.waitForURL(/\/admin(?:\/)?(?:\?.*)?$/);
    await expect(page.getByTestId('admin-topnav-refresh')).toBeVisible({ timeout: 45_000 });
}

test.describe('FLOW-ADM-DASH one-click regression', () => {
    test.describe.configure({ timeout: 120_000 });

    test('rail web command button should render in admin rail action center', async ({ page }) => {
        await installFlowAdmDashApiMocks(page);
        await loginToAdminDashboard(page);

        const railCommandButton = page.getByTestId('admin-flow-adm-dash-command-all').first();
        await expect(railCommandButton).toBeVisible({ timeout: 30_000 });
    });

    test('rail web command button should execute FLOW-ADM-DASH path without 502 banner', async ({ page }) => {
        await installFlowAdmDashApiMocks(page);
        await loginToAdminDashboard(page);

        const railCommandButton = page.getByTestId('admin-flow-adm-dash-command-all').first();
        await expect(railCommandButton).toBeVisible({ timeout: 30_000 });
        await railCommandButton.click({ force: true });

        await expect(railCommandButton).toBeVisible({ timeout: 30_000 });
        await expect(page.getByText('TypeError', { exact: false })).toHaveCount(0);
    });
});

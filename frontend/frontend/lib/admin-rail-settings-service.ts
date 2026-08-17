export type AdminRailId = 'sla' | 'list' | 'ops' | 'cover' | 'llm' | 'performance' | 'latency' | 'data' | 'monitoring';

export interface AdminRailSlaSettings {
    enabled: boolean;
    availability_target_percent: number;
    alert_on_breach: boolean;
    auto_push_on_breach: boolean;
    breach_cooldown_minutes: number;
}

export interface AdminRailListSettings {
    enabled: boolean;
    auto_refresh_seconds: number;
    show_failed_only: boolean;
    include_raw_payload: boolean;
    max_items: number;
}

export interface AdminRailOpsSettings {
    enabled: boolean;
    auto_apply_global_mode: boolean;
    healthcheck_on_open: boolean;
    allow_runtime_restart: boolean;
    deployment_gate_level: string;
}

export interface AdminRailCoverSettings {
    enabled: boolean;
    target_fastpath_percent: number;
    enforce_fastpath_guard: boolean;
    auto_open_failures: boolean;
    sample_size: number;
}

export interface AdminRailLlmSettings {
    enabled: boolean;
    route_timeout_ms: number;
    prefer_fast_path: boolean;
    auto_recover_on_timeout: boolean;
    max_retry_count: number;
}

export interface AdminRailPerformanceSettings {
    enabled: boolean;
    response_budget_ms: number;
    db_query_budget_ms: number;
    cache_ttl_seconds: number;
    auto_collect_snapshot: boolean;
}

export interface AdminRailLatencySettings {
    enabled: boolean;
    p50_budget_ms: number;
    p95_budget_ms: number;
    sampling_window_minutes: number;
    alert_on_regression: boolean;
}

export interface AdminRailDataSettings {
    enabled: boolean;
    metric_refresh_seconds: number;
    include_zero_metrics: boolean;
    selected_metric_key: string;
    max_series_points: number;
}

export interface AdminRailMonitoringSettings {
    enabled: boolean;
    grafana_base_url: string;
    auto_refresh_seconds: number;
    open_external_dashboard: boolean;
    alert_channel: string;
}

export interface AdminRailSettingsMap {
    sla: AdminRailSlaSettings;
    list: AdminRailListSettings;
    ops: AdminRailOpsSettings;
    cover: AdminRailCoverSettings;
    llm: AdminRailLlmSettings;
    performance: AdminRailPerformanceSettings;
    latency: AdminRailLatencySettings;
    data: AdminRailDataSettings;
    monitoring: AdminRailMonitoringSettings;
}

export interface AdminRailSettingsResponse {
    settings_path: string;
    updated_at: string;
    rails: AdminRailSettingsMap;
}

export const ADMIN_RAIL_SETTINGS_DEFAULTS: AdminRailSettingsMap = {
    sla: {
        enabled: true,
        availability_target_percent: 99.9,
        alert_on_breach: true,
        auto_push_on_breach: true,
        breach_cooldown_minutes: 15,
    },
    list: {
        enabled: true,
        auto_refresh_seconds: 30,
        show_failed_only: false,
        include_raw_payload: true,
        max_items: 20,
    },
    ops: {
        enabled: true,
        auto_apply_global_mode: true,
        healthcheck_on_open: true,
        allow_runtime_restart: false,
        deployment_gate_level: 'strict',
    },
    cover: {
        enabled: true,
        target_fastpath_percent: 85,
        enforce_fastpath_guard: true,
        auto_open_failures: true,
        sample_size: 25,
    },
    llm: {
        enabled: true,
        route_timeout_ms: 45000,
        prefer_fast_path: true,
        auto_recover_on_timeout: true,
        max_retry_count: 2,
    },
    performance: {
        enabled: true,
        response_budget_ms: 600,
        db_query_budget_ms: 250,
        cache_ttl_seconds: 300,
        auto_collect_snapshot: true,
    },
    latency: {
        enabled: true,
        p50_budget_ms: 180,
        p95_budget_ms: 700,
        sampling_window_minutes: 15,
        alert_on_regression: true,
    },
    data: {
        enabled: true,
        metric_refresh_seconds: 20,
        include_zero_metrics: false,
        selected_metric_key: 'http_requests_total',
        max_series_points: 120,
    },
    monitoring: {
        enabled: true,
        grafana_base_url: 'http://127.0.0.1:3000',
        auto_refresh_seconds: 20,
        open_external_dashboard: false,
        alert_channel: 'admin',
    },
};

function buildErrorMessage(response: Response, payload: any, fallback: string) {
    return String(payload?.detail || payload?.error || fallback || `요청 실패(${response.status})`);
}

export function cloneAdminRailSettingsDefaults(): AdminRailSettingsMap {
    return JSON.parse(JSON.stringify(ADMIN_RAIL_SETTINGS_DEFAULTS)) as AdminRailSettingsMap;
}

export async function loadAdminRailSettings(options: {
    apiBaseUrl: string;
    token: string;
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const response = await fetcher(`${options.apiBaseUrl}/api/admin/rail-settings`, {
        headers: {
            Authorization: `Bearer ${options.token}`,
        },
        cache: 'no-store',
    });
    const data = await response.json().catch(() => null);
    if (response.status === 401 || response.status === 403) {
        throw new Error('__ADMIN_RAIL_UNAUTHORIZED__');
    }
    if (!response.ok || !data) {
        throw new Error(buildErrorMessage(response, data, '레일 설정 조회 실패'));
    }
    return data as AdminRailSettingsResponse;
}

export async function saveAdminRailSettings(options: {
    apiBaseUrl: string;
    token: string;
    rails: AdminRailSettingsMap;
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const response = await fetcher(`${options.apiBaseUrl}/api/admin/rail-settings`, {
        method: 'PUT',
        headers: {
            Authorization: `Bearer ${options.token}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ rails: options.rails }),
    });
    const data = await response.json().catch(() => null);
    if (response.status === 401 || response.status === 403) {
        throw new Error('__ADMIN_RAIL_UNAUTHORIZED__');
    }
    if (!response.ok || !data) {
        throw new Error(buildErrorMessage(response, data, '레일 설정 저장 실패'));
    }
    return data as AdminRailSettingsResponse;
}

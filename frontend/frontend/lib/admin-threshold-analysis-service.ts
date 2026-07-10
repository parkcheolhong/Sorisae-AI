import type { AdminRailSettingsMap } from '@/lib/admin-rail-settings-service';

export interface AdminThresholdObservationSummary {
    metrics?: Record<string, number | string | null>;
    cpu_usage_percent?: number | null;
    memory_usage_percent?: number | null;
    queue_depth?: number | null;
    health_status?: string;
    sorisae_classification?: string;
    observations_complete?: boolean;
}

export interface AdminThresholdAnalysisRecommendations {
    rails: AdminRailSettingsMap;
    worldlinco: Record<string, Record<string, number | string | boolean>>;
    observation_summary: AdminThresholdObservationSummary;
}

export interface AdminThresholdApprovalState {
    approved: boolean;
    approved_at: string | null;
    approved_by: string | null;
    fingerprint: string;
}

export interface AdminThresholdAnalysisResponse {
    analysis_mode_enabled: boolean;
    last_analyzed_at: string | null;
    recommendations: AdminThresholdAnalysisRecommendations;
    approvals: {
        rails: AdminThresholdApprovalState;
        worldlinco: AdminThresholdApprovalState;
    };
    safe_gate: {
        threshold_recovery_allowed: boolean;
        worldlinco_auto_apply_allowed: boolean;
        reason: string;
    };
    worldlinco_partial_applied?: Array<{
        group: string;
        key: string;
        value: number;
        applied_at: string;
        applied_by: string;
    }>;
}

function buildErrorMessage(response: Response, payload: any, fallback: string) {
    return String(payload?.detail || payload?.error || fallback || `요청 실패(${response.status})`);
}

export async function loadAdminThresholdAnalysis(options: {
    apiBaseUrl: string;
    token: string;
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const response = await fetcher(`${options.apiBaseUrl}/api/admin/threshold-analysis`, {
        headers: { Authorization: `Bearer ${options.token}` },
        cache: 'no-store',
    });
    const data = await response.json().catch(() => null);
    if (response.status === 401 || response.status === 403) {
        throw new Error('__ADMIN_THRESHOLD_UNAUTHORIZED__');
    }
    if (!response.ok || !data) {
        throw new Error(buildErrorMessage(response, data, '임계치 분석 상태 조회 실패'));
    }
    return data as AdminThresholdAnalysisResponse;
}

export async function analyzeAdminThresholds(options: {
    apiBaseUrl: string;
    token: string;
    health: Record<string, unknown> | null;
    sorisaeFailure: Record<string, unknown> | null;
    railSettings: AdminRailSettingsMap;
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const response = await fetcher(`${options.apiBaseUrl}/api/admin/threshold-analysis/analyze`, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${options.token}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            health: options.health,
            sorisae_failure: options.sorisaeFailure,
            rail_settings: options.railSettings,
        }),
    });
    const data = await response.json().catch(() => null);
    if (response.status === 401 || response.status === 403) {
        throw new Error('__ADMIN_THRESHOLD_UNAUTHORIZED__');
    }
    if (!response.ok || !data) {
        throw new Error(buildErrorMessage(response, data, '임계치 분석 실행 실패'));
    }
    return data as AdminThresholdAnalysisResponse;
}

export async function approveAdminThresholdTarget(options: {
    apiBaseUrl: string;
    token: string;
    target: 'rails' | 'worldlinco';
    approved: boolean;
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const response = await fetcher(`${options.apiBaseUrl}/api/admin/threshold-analysis/approve`, {
        method: 'PUT',
        headers: {
            Authorization: `Bearer ${options.token}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ target: options.target, approved: options.approved }),
    });
    const data = await response.json().catch(() => null);
    if (response.status === 401 || response.status === 403) {
        throw new Error('__ADMIN_THRESHOLD_UNAUTHORIZED__');
    }
    if (!response.ok || !data) {
        throw new Error(buildErrorMessage(response, data, '임계치 승인 상태 저장 실패'));
    }
    return data as AdminThresholdAnalysisResponse;
}

export async function applyApprovedWorldlincoRecommendations(options: {
    apiBaseUrl: string;
    token: string;
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const response = await fetcher(`${options.apiBaseUrl}/api/admin/threshold-analysis/apply-worldlinco-approved`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${options.token}` },
    });
    const data = await response.json().catch(() => null);
    if (response.status === 401 || response.status === 403) {
        throw new Error('__ADMIN_THRESHOLD_UNAUTHORIZED__');
    }
    if (!response.ok || !data) {
        throw new Error(buildErrorMessage(response, data, '승인된 월드린코 추천값 적용 실패'));
    }
    return data as {
        applied: boolean;
        applied_at: string;
        updated_by: string;
        worldlinco: Record<string, unknown>;
        safe_gate: AdminThresholdAnalysisResponse['safe_gate'];
    };
}

export async function applyWorldlincoRecommendationField(options: {
    apiBaseUrl: string;
    token: string;
    group: string;
    key: string;
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const response = await fetcher(`${options.apiBaseUrl}/api/admin/threshold-analysis/apply-worldlinco-field`, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${options.token}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            group: options.group,
            key: options.key,
        }),
    });
    const data = await response.json().catch(() => null);
    if (response.status === 401 || response.status === 403) {
        throw new Error('__ADMIN_THRESHOLD_UNAUTHORIZED__');
    }
    if (!response.ok || !data) {
        throw new Error(buildErrorMessage(response, data, '월드린코 추천값 필드 적용 실패'));
    }
    return data as {
        applied: boolean;
        group: string;
        key: string;
        value: number;
        updated_by: string;
        applied_at: string;
        worldlinco: Record<string, unknown>;
        threshold_analysis: AdminThresholdAnalysisResponse;
    };
}

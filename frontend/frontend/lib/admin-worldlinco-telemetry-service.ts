export interface AdminWorldlincoTelemetryItem {
    source: string;
    feature: string;
    metric: string;
    value: number;
    unit?: string | null;
    timestamp?: string | null;
    device_id?: string | null;
    run_id?: string | null;
    tags?: Record<string, string>;
}

export interface AdminWorldlincoTelemetrySummary {
    total_items: number;
    features: Record<string, Record<string, {
        count: number;
        avg: number;
        min: number;
        max: number;
        p95: number;
    }>>;
}

export interface AdminWorldlincoTelemetryPayload {
    updated_at: string | null;
    updated_by: string;
    note: string;
    items: AdminWorldlincoTelemetryItem[];
    summary: AdminWorldlincoTelemetrySummary;
}

export interface AdminWorldlincoCalibrationArtifactFileMeta {
    path: string;
    exists: boolean;
    size_bytes: number;
    modified_at: string | null;
    rows?: number;
}

export interface AdminWorldlincoCalibrationArtifactsPayload {
    generated_at: string;
    artifacts: {
        telemetry: AdminWorldlincoCalibrationArtifactFileMeta & {
            total_items: number;
            updated_at: string | null;
        };
        recommendation: AdminWorldlincoCalibrationArtifactFileMeta & {
            confidence?: string | null;
            warnings?: string[];
            sample_coverage?: Record<string, unknown>;
            has_test_priority_plan?: boolean;
        };
        priority_csv: AdminWorldlincoCalibrationArtifactFileMeta[];
    };
}

function buildErrorMessage(response: Response, payload: any, fallback: string) {
    return String(payload?.detail || payload?.error || fallback || `요청 실패(${response.status})`);
}

export async function loadAdminWorldlincoTelemetry(options: {
    apiBaseUrl: string;
    token: string;
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const response = await fetcher(`${options.apiBaseUrl}/api/admin/worldlinco/telemetry`, {
        headers: { Authorization: `Bearer ${options.token}` },
        cache: 'no-store',
    });
    const data = await response.json().catch(() => null);
    if (response.status === 401 || response.status === 403) {
        throw new Error('__ADMIN_THRESHOLD_UNAUTHORIZED__');
    }
    if (!response.ok || !data) {
        throw new Error(buildErrorMessage(response, data, '월드린코 텔레메트리 조회 실패'));
    }
    return data as AdminWorldlincoTelemetryPayload;
}

export async function uploadAdminWorldlincoTelemetry(options: {
    apiBaseUrl: string;
    token: string;
    note?: string;
    items: AdminWorldlincoTelemetryItem[];
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const response = await fetcher(`${options.apiBaseUrl}/api/admin/worldlinco/telemetry/upload`, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${options.token}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            note: options.note || '',
            items: options.items,
        }),
    });
    const data = await response.json().catch(() => null);
    if (response.status === 401 || response.status === 403) {
        throw new Error('__ADMIN_THRESHOLD_UNAUTHORIZED__');
    }
    if (!response.ok || !data) {
        throw new Error(buildErrorMessage(response, data, '월드린코 텔레메트리 업로드 실패'));
    }
    return data as {
        accepted: number;
        total_items: number;
        updated_at: string;
        updated_by: string;
        summary: AdminWorldlincoTelemetrySummary;
    };
}

export async function loadAdminWorldlincoCalibrationArtifacts(options: {
    apiBaseUrl: string;
    token: string;
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const response = await fetcher(`${options.apiBaseUrl}/api/admin/worldlinco/calibration-artifacts`, {
        headers: { Authorization: `Bearer ${options.token}` },
        cache: 'no-store',
    });
    const data = await response.json().catch(() => null);
    if (response.status === 401 || response.status === 403) {
        throw new Error('__ADMIN_THRESHOLD_UNAUTHORIZED__');
    }
    if (!response.ok || !data) {
        throw new Error(buildErrorMessage(response, data, '월드린코 캘리브레이션 산출물 조회 실패'));
    }
    return data as AdminWorldlincoCalibrationArtifactsPayload;
}

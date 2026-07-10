export type TravelPartnerCategory = 'hotel' | 'tour' | 'transport';

export interface AdminTravelPartner {
    partner_id: string;
    name: string;
    category: TravelPartnerCategory;
    integration_type: string;
    regions_supported: string[];
    commission_model?: string;
    base_url?: string;
    active: boolean;
    metadata: Record<string, unknown> & {
        connector_test_url?: string;
        booking_api_url?: string;
        webhook_url?: string;
    };
}

export interface AdminTravelRoutingPolicyRule {
    country_code: string;
    city_code?: string | null;
    hotel_partner_id?: string | null;
    tour_partner_id?: string | null;
    transport_partner_id?: string | null;
    fallback_partner_ids: string[];
    active: boolean;
}

export interface AdminTravelRoutingPolicy {
    updated_at?: string | null;
    updated_by?: string | null;
    version: string;
    default_hotel_partner_id?: string | null;
    default_tour_partner_id?: string | null;
    default_transport_partner_id?: string | null;
    rules: AdminTravelRoutingPolicyRule[];
}

export interface AdminTravelPartnerConfigResponse {
    partners_path: string;
    routing_policy_path: string;
    updated_at?: string | null;
    updated_by?: string | null;
    partners: AdminTravelPartner[];
    routing_policy: AdminTravelRoutingPolicy;
}

export interface AdminTravelConnectorTestResponse {
    tested: boolean;
    connector_id: string;
    partner: AdminTravelPartner;
    test_url: string;
    reachable: boolean;
    status_code?: number | null;
    response_time_ms: number;
    error?: string | null;
    tested_at: string;
    tested_by: string;
}

export interface AdminTravelWebhookTestResponse {
    tested: boolean;
    partner_id: string;
    partner: AdminTravelPartner;
    webhook_url: string;
    reachable: boolean;
    status_code?: number | null;
    response_time_ms: number;
    error?: string | null;
    event_type: string;
    request_payload: Record<string, unknown>;
    tested_at: string;
    tested_by: string;
}

export interface AdminTravelFunnelKpiCounts {
    recommendations: number;
    clicks: number;
    bookings: number;
    confirmed: number;
    completed: number;
    cancelled: number;
    refunded: number;
    trip_sessions: number;
}

export interface AdminTravelFunnelKpi {
    ctr: number;
    booking_confirm_rate: number;
    cancel_rate: number;
    commission_total: number;
    rps: number;
    counts: AdminTravelFunnelKpiCounts;
}

export interface AdminTravelPartnerSlaKpi {
    partner_id: string;
    success_rate: number;
    error_rate: number;
    p95_processing_minutes: number;
    total_events: number;
}

export interface AdminTravelFallbackKpi {
    country_rule_count: number;
    country_fallback_ratio: number;
    city_rule_count: number;
    city_fallback_ratio: number;
    default_partner_usage_ratio: number;
}

export interface AdminTravelPartnerKpiResponse {
    generated_at: string;
    funnel: AdminTravelFunnelKpi;
    sla: AdminTravelPartnerSlaKpi[];
    fallback: AdminTravelFallbackKpi;
    ops?: {
        settings?: AdminTravelKpiSettingsResponse;
        alert_summary?: {
            critical_count: number;
            warning_count: number;
            ok_count: number;
            overall: 'ok' | 'warning' | 'critical';
        };
        alerts?: AdminTravelKpiAlert[];
    };
}

export interface AdminTravelKpiThresholds {
    ctr_min: number;
    booking_confirm_rate_min: number;
    cancel_rate_max: number;
    rps_min: number;
    partner_success_rate_min: number;
    partner_error_rate_max: number;
    partner_p95_processing_minutes_max: number;
    fallback_country_ratio_max: number;
    fallback_city_ratio_max: number;
    default_partner_usage_ratio_max: number;
}

export interface AdminTravelKpiSettingsResponse {
    settings_path: string;
    updated_at?: string | null;
    updated_by?: string | null;
    thresholds: AdminTravelKpiThresholds;
}

export interface AdminTravelKpiAlert {
    id: string;
    severity: 'ok' | 'warning' | 'critical';
    label: string;
    value: number;
    threshold: number;
    operator: 'gte' | 'lte';
}

function buildErrorMessage(response: Response, payload: any, fallback: string) {
    return String(payload?.detail || payload?.error || fallback || `요청 실패(${response.status})`);
}

export async function loadAdminTravelPartners(options: {
    apiBaseUrl: string;
    token: string;
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const response = await fetcher(`${options.apiBaseUrl}/api/admin/travel-partners`, {
        headers: { Authorization: `Bearer ${options.token}` },
        cache: 'no-store',
    });
    const data = await response.json().catch(() => null);
    if (response.status === 401 || response.status === 403) {
        throw new Error('__ADMIN_TRAVEL_PARTNER_UNAUTHORIZED__');
    }
    if (!response.ok || !data) {
        throw new Error(buildErrorMessage(response, data, '여행 파트너 설정 조회 실패'));
    }
    return data as AdminTravelPartnerConfigResponse;
}

export async function createAdminTravelPartner(options: {
    apiBaseUrl: string;
    token: string;
    payload: {
        partner_id?: string;
        name: string;
        category: TravelPartnerCategory;
        integration_type?: string;
        regions_supported?: string[];
        commission_model?: string;
        base_url?: string;
        metadata?: Record<string, unknown>;
    };
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const response = await fetcher(`${options.apiBaseUrl}/api/admin/travel-partners`, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${options.token}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(options.payload),
    });
    const data = await response.json().catch(() => null);
    if (response.status === 401 || response.status === 403) {
        throw new Error('__ADMIN_TRAVEL_PARTNER_UNAUTHORIZED__');
    }
    if (!response.ok || !data) {
        throw new Error(buildErrorMessage(response, data, '여행 파트너 등록 실패'));
    }
    return data as {
        created: boolean;
        partner: AdminTravelPartner;
        partners: AdminTravelPartner[];
        routing_policy: AdminTravelRoutingPolicy;
        updated_at?: string | null;
        updated_by?: string | null;
    };
}

export async function updateAdminTravelRoutingPolicy(options: {
    apiBaseUrl: string;
    token: string;
    payload: {
        version?: string;
        default_hotel_partner_id?: string | null;
        default_tour_partner_id?: string | null;
        default_transport_partner_id?: string | null;
        rules?: AdminTravelRoutingPolicyRule[];
    };
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const response = await fetcher(`${options.apiBaseUrl}/api/admin/travel-routing-policy`, {
        method: 'PUT',
        headers: {
            Authorization: `Bearer ${options.token}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(options.payload),
    });
    const data = await response.json().catch(() => null);
    if (response.status === 401 || response.status === 403) {
        throw new Error('__ADMIN_TRAVEL_PARTNER_UNAUTHORIZED__');
    }
    if (!response.ok || !data) {
        throw new Error(buildErrorMessage(response, data, '여행 라우팅 정책 저장 실패'));
    }
    return data as {
        saved: boolean;
        routing_policy: AdminTravelRoutingPolicy;
        partners: AdminTravelPartner[];
        updated_at?: string | null;
        updated_by?: string | null;
    };
}

export async function testAdminTravelConnector(options: {
    apiBaseUrl: string;
    token: string;
    connectorId: string;
    payload?: {
        test_url?: string;
        timeout_ms?: number;
    };
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const response = await fetcher(
        `${options.apiBaseUrl}/api/admin/travel-connectors/${encodeURIComponent(options.connectorId)}/test`,
        {
            method: 'POST',
            headers: {
                Authorization: `Bearer ${options.token}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(options.payload || {}),
        }
    );
    const data = await response.json().catch(() => null);
    if (response.status === 401 || response.status === 403) {
        throw new Error('__ADMIN_TRAVEL_PARTNER_UNAUTHORIZED__');
    }
    if (!response.ok || !data) {
        throw new Error(buildErrorMessage(response, data, '여행 커넥터 연결 테스트 실패'));
    }
    return data as AdminTravelConnectorTestResponse;
}

export async function testAdminTravelPartnerWebhook(options: {
    apiBaseUrl: string;
    token: string;
    partnerId: string;
    payload?: {
        webhook_url?: string;
        timeout_ms?: number;
        event_type?: string;
        sample_data?: Record<string, unknown>;
    };
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const response = await fetcher(
        `${options.apiBaseUrl}/api/admin/travel-partners/${encodeURIComponent(options.partnerId)}/webhook/test`,
        {
            method: 'POST',
            headers: {
                Authorization: `Bearer ${options.token}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(options.payload || {}),
        }
    );
    const data = await response.json().catch(() => null);
    if (response.status === 401 || response.status === 403) {
        throw new Error('__ADMIN_TRAVEL_PARTNER_UNAUTHORIZED__');
    }
    if (!response.ok || !data) {
        throw new Error(buildErrorMessage(response, data, '여행 Webhook 테스트 발송 실패'));
    }
    return data as AdminTravelWebhookTestResponse;
}

export async function updateAdminTravelPartnerConnection(options: {
    apiBaseUrl: string;
    token: string;
    partnerId: string;
    payload: {
        base_url?: string;
        connector_test_url?: string;
        booking_api_url?: string;
        webhook_url?: string;
    };
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const response = await fetcher(
        `${options.apiBaseUrl}/api/admin/travel-partners/${encodeURIComponent(options.partnerId)}/connection`,
        {
            method: 'PUT',
            headers: {
                Authorization: `Bearer ${options.token}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(options.payload),
        }
    );
    const data = await response.json().catch(() => null);
    if (response.status === 401 || response.status === 403) {
        throw new Error('__ADMIN_TRAVEL_PARTNER_UNAUTHORIZED__');
    }
    if (!response.ok || !data) {
        throw new Error(buildErrorMessage(response, data, '여행 파트너 URL 연동 저장 실패'));
    }
    return data as {
        updated: boolean;
        partner: AdminTravelPartner;
        partners: AdminTravelPartner[];
        routing_policy: AdminTravelRoutingPolicy;
        updated_at?: string | null;
        updated_by?: string | null;
    };
}

export async function loadAdminTravelPartnerKpi(options: {
    apiBaseUrl: string;
    token: string;
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const response = await fetcher(`${options.apiBaseUrl}/api/admin/travel-partners/kpi`, {
        headers: { Authorization: `Bearer ${options.token}` },
        cache: 'no-store',
    });
    const data = await response.json().catch(() => null);
    if (response.status === 401 || response.status === 403) {
        throw new Error('__ADMIN_TRAVEL_PARTNER_UNAUTHORIZED__');
    }
    if (!response.ok || !data) {
        throw new Error(buildErrorMessage(response, data, '여행 KPI 조회 실패'));
    }
    return data as AdminTravelPartnerKpiResponse;
}

export async function loadAdminTravelPartnerKpiSettings(options: {
    apiBaseUrl: string;
    token: string;
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const response = await fetcher(`${options.apiBaseUrl}/api/admin/travel-partners/kpi-settings`, {
        headers: { Authorization: `Bearer ${options.token}` },
        cache: 'no-store',
    });
    const data = await response.json().catch(() => null);
    if (response.status === 401 || response.status === 403) {
        throw new Error('__ADMIN_TRAVEL_PARTNER_UNAUTHORIZED__');
    }
    if (!response.ok || !data) {
        throw new Error(buildErrorMessage(response, data, '여행 KPI 설정 조회 실패'));
    }
    return data as AdminTravelKpiSettingsResponse;
}

export async function updateAdminTravelPartnerKpiSettings(options: {
    apiBaseUrl: string;
    token: string;
    thresholds: AdminTravelKpiThresholds;
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const response = await fetcher(`${options.apiBaseUrl}/api/admin/travel-partners/kpi-settings`, {
        method: 'PUT',
        headers: {
            Authorization: `Bearer ${options.token}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(options.thresholds),
    });
    const data = await response.json().catch(() => null);
    if (response.status === 401 || response.status === 403) {
        throw new Error('__ADMIN_TRAVEL_PARTNER_UNAUTHORIZED__');
    }
    if (!response.ok || !data) {
        throw new Error(buildErrorMessage(response, data, '여행 KPI 설정 저장 실패'));
    }
    return data as AdminTravelKpiSettingsResponse;
}

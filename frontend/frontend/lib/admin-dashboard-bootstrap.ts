import {
    ADMIN_BOOTSTRAP_RETRYABLE_STATUSES as ADMIN_DASHBOARD_BOOTSTRAP_RETRYABLE_STATUSES,
    fetchWithAdminBootstrapRetry,
} from '@/lib/admin-bootstrap-fetch';

export type AdminDashboardBootstrapRequest = {
    key: string;
    label: string;
    url: string;
    init?: RequestInit;
    allowNoContent?: boolean;
    tolerateServerError?: boolean;
};

export type AdminDashboardBootstrapResult = {
    key: string;
    label: string;
    response: Response | null;
    error: string | null;
};

export async function runAdminDashboardBootstrapRequests(
    requests: AdminDashboardBootstrapRequest[],
): Promise<AdminDashboardBootstrapResult[]> {
    const settled = await Promise.allSettled(
        requests.map((request) => fetchWithAdminBootstrapRetry(request.url, request.init)),
    );

    return settled.map((entry, index) => {
        const request = requests[index];
        if (entry.status === 'fulfilled') {
            return {
                key: request.key,
                label: request.label,
                response: entry.value,
                error: null,
            };
        }
        return {
            key: request.key,
            label: request.label,
            response: null,
            error: entry.reason instanceof Error ? entry.reason.message : String(entry.reason || `${request.label} 요청 실패`),
        };
    });
}

export function buildAdminDashboardBootstrapRequestMap(
    apiBaseUrl: string,
    headers: HeadersInit,
    options: {
        adMonitorUnavailable: boolean;
        adSettlementUnavailable: boolean;
        includeCapabilityBootstrap?: boolean;
    },
): AdminDashboardBootstrapRequest[] {
    const includeCapabilityBootstrap = options.includeCapabilityBootstrap === true;
    return [
        {
            key: 'overview',
            label: '개요',
            url: `${apiBaseUrl}/api/marketplace/stats/overview`,
            init: { headers },
        },
        {
            key: 'revenue',
            label: '수익',
            url: `${apiBaseUrl}/api/marketplace/stats/revenue`,
            init: { headers },
        },
        {
            key: 'top-projects',
            label: '상위 프로젝트',
            url: `${apiBaseUrl}/api/marketplace/stats/top-projects?limit=8`,
            init: { headers },
        },
        {
            key: 'health',
            label: '헬스',
            url: `${apiBaseUrl}/api/health`,
        },
        {
            key: 'llm-status',
            label: 'LLM',
            url: `${apiBaseUrl}/api/llm/status`,
        },
        {
            key: 'ad-video-orders',
            label: '광고 주문',
            url: `${apiBaseUrl}/api/admin/ad-video-orders?skip=0&limit=20`,
            init: { headers },
        },
        options.adMonitorUnavailable
            ? {
                key: 'ad-video-orders-monitor-summary',
                label: '광고 주문 모니터링',
                url: '',
                allowNoContent: true,
            }
            : {
                key: 'ad-video-orders-monitor-summary',
                label: '광고 주문 모니터링',
                url: `${apiBaseUrl}/api/admin/ad-video-orders/monitor-summary`,
                init: { headers },
            },
        options.adSettlementUnavailable
            ? {
                key: 'ad-video-orders-settlement-dashboard',
                label: '광고 주문 정산',
                url: '',
                allowNoContent: true,
            }
            : {
                key: 'ad-video-orders-settlement-dashboard',
                label: '광고 주문 정산',
                url: `${apiBaseUrl}/api/admin/ad-video-orders/settlement-dashboard`,
                init: { headers },
            },
        {
            key: 'latest-self-run',
            label: '최신 self-run',
            url: `${apiBaseUrl}/api/admin/workspace-self-run-record?latest=true`,
            init: { headers },
            tolerateServerError: true,
        },
        ...(includeCapabilityBootstrap
            ? [
                {
                    key: 'capabilities-summary',
                    label: '오케스트레이터 기능군',
                    url: `${apiBaseUrl}/api/admin/orchestrator/capabilities/summary`,
                    init: { headers },
                },
                {
                    key: 'security-guard-detail',
                    label: 'Security Guard 상세',
                    url: `${apiBaseUrl}/api/admin/orchestrator/capabilities/security-guard`,
                    init: { headers },
                },
            ]
            : []),
    ];
}

export function assertAdminDashboardBootstrapContract() {
    const requests = buildAdminDashboardBootstrapRequestMap('https://example.com', { Authorization: 'Bearer sample' }, {
        adMonitorUnavailable: false,
        adSettlementUnavailable: false,
        includeCapabilityBootstrap: true,
    });
    const requiredKeys = [
        'overview',
        'revenue',
        'top-projects',
        'health',
        'llm-status',
        'ad-video-orders',
        'ad-video-orders-monitor-summary',
        'ad-video-orders-settlement-dashboard',
        'capabilities-summary',
        'latest-self-run',
        'security-guard-detail',
    ];
    const requestKeys = new Set(requests.map((request) => request.key));
    const missing = requiredKeys.filter((key) => !requestKeys.has(key));
    if (missing.length > 0) {
        throw new Error(`admin dashboard bootstrap contract 누락: ${missing.join(', ')}`);
    }
}

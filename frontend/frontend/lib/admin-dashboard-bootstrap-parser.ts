import type { OverviewStats, RevenueStats, TopProject, AdminAdOrderMonitorSummary, AdminAdOrderSettlementDashboard, AdminAdVideoOrderItem, AdminDashboardSelfRunStatus, OrchestratorCapabilityDetailResponse, OrchestratorCapabilitySummaryResponse } from '@/lib/admin-dashboard-types';
import type { HealthStatus } from '@/lib/admin-health-analysis';
import type { LlmStatus, LiveLogItem } from '@/lib/admin-runtime-types';

export type AdminDashboardBootstrapResponseMapItem = {
    key: string;
    label: string;
    response?: Response | null;
    error?: unknown;
};

export type AdminDashboardParsedBootstrapData = {
    overviewData: OverviewStats | null;
    revenueData: RevenueStats | null;
    topData: TopProject[] | null;
    healthData: HealthStatus | null;
    llmData: LlmStatus | null;
    adVideoData: { total: number; orders: AdminAdVideoOrderItem[] } | null;
    adMonitorData: AdminAdOrderMonitorSummary | null;
    adSettlementData: AdminAdOrderSettlementDashboard | null;
    capabilityData: OrchestratorCapabilitySummaryResponse | null;
    selfRunData: AdminDashboardSelfRunStatus | null;
    securityGuardDetailData: OrchestratorCapabilityDetailResponse | null;
    failedMessages: string[];
    unauthorized: boolean;
    adMonitorUnavailable: boolean;
    adSettlementUnavailable: boolean;
    liveLogEvents: Array<{ level: LiveLogItem['level']; message: string; meta?: Partial<LiveLogItem> & { capabilityId?: string } }>;
};

type ParseContext = {
    failedMessages: string[];
    unauthorized: boolean;
    adMonitorUnavailable: boolean;
    adSettlementUnavailable: boolean;
    liveLogEvents: Array<{ level: LiveLogItem['level']; message: string; meta?: Partial<LiveLogItem> & { capabilityId?: string } }>;
};

function isOptionalCapabilityBootstrapLabel(label: string) {
    return label === '오케스트레이터 기능군' || label === 'Security Guard 상세';
}

async function parseBootstrapJson<T>(options: {
    resultMap: Map<string, AdminDashboardBootstrapResponseMapItem>;
    key: string;
    label: string;
    context: ParseContext;
}) {
    const response = options.resultMap.get(options.key);
    if (!response) {
        if (options.label === '광고 주문 모니터링' || options.label === '광고 주문 정산') {
            return null;
        }
        options.context.failedMessages.push(`${options.label} 요청 실패`);
        return null;
    }
    if (response.error) {
        const errorMessage = String(response.error || '');
        if (errorMessage.includes('AbortError') || errorMessage.includes('aborted') || errorMessage.includes('The operation was aborted')) {
            return null;
        }
        if (isOptionalCapabilityBootstrapLabel(options.label)) {
            options.context.liveLogEvents.push({
                level: 'warning',
                message: `${options.label} 연결이 지연되어 이번 대시보드 로드에서는 생략했습니다.`,
                meta: {
                    capabilityId: options.label === '오케스트레이터 기능군' ? 'orchestrator-summary' : 'security-guard',
                    panel_id: 'PANEL-ADMIN-DASHBOARD',
                },
            });
            return null;
        }
        options.context.failedMessages.push(`${options.label} 요청 실패`);
        return null;
    }
    if (!response.response) {
        return null;
    }
    if (response.response.status === 401) {
        options.context.unauthorized = true;
        return null;
    }
    if (response.response.status === 404) {
        if (options.label === '광고 주문 모니터링') {
            options.context.adMonitorUnavailable = true;
            options.context.liveLogEvents.push({
                level: 'warning',
                message: '/api/admin/ad-video-orders/monitor-summary 미지원 · 백엔드 재시작 전까지 프런트 fallback 집계를 사용합니다.',
                meta: { capabilityId: 'settlement-monitor', panel_id: 'PANEL-ADMIN-SETTLEMENT' },
            });
            return null;
        }
        if (options.label === '광고 주문 정산') {
            options.context.adSettlementUnavailable = true;
            options.context.liveLogEvents.push({
                level: 'warning',
                message: '/api/admin/ad-video-orders/settlement-dashboard 미지원 · 백엔드 재시작 전까지 프런트 fallback 차트를 사용합니다.',
                meta: { capabilityId: 'settlement-dashboard', panel_id: 'PANEL-ADMIN-SETTLEMENT' },
            });
            return null;
        }
    }
    if (response.response.status === 204) {
        return null;
    }
    if (options.label === '최신 self-run' && response.response.status >= 500) {
        return null;
    }
    if (!response.response.ok) {
        if (isOptionalCapabilityBootstrapLabel(options.label)) {
            options.context.liveLogEvents.push({
                level: 'warning',
                message: `${options.label} 응답이 불안정해 기본 대시보드 카드만 먼저 표시합니다.`,
                meta: {
                    capabilityId: options.label === '오케스트레이터 기능군' ? 'orchestrator-summary' : 'security-guard',
                    panel_id: 'PANEL-ADMIN-DASHBOARD',
                },
            });
            return null;
        }
        options.context.failedMessages.push(`${options.label} 응답 오류(${response.response.status})`);
        return null;
    }
    try {
        return (await response.response.json()) as T;
    } catch {
        if (isOptionalCapabilityBootstrapLabel(options.label)) {
            options.context.liveLogEvents.push({
                level: 'warning',
                message: `${options.label} 데이터를 해석하지 못해 기본 상태로 유지합니다.`,
                meta: {
                    capabilityId: options.label === '오케스트레이터 기능군' ? 'orchestrator-summary' : 'security-guard',
                    panel_id: 'PANEL-ADMIN-DASHBOARD',
                },
            });
            return null;
        }
        options.context.failedMessages.push(`${options.label} 파싱 실패`);
        return null;
    }
}

export async function parseAdminDashboardBootstrapResults(options: {
    bootstrapResults: AdminDashboardBootstrapResponseMapItem[];
}) {
    const context: ParseContext = {
        failedMessages: [],
        unauthorized: false,
        adMonitorUnavailable: false,
        adSettlementUnavailable: false,
        liveLogEvents: [],
    };
    const resultMap = new Map(options.bootstrapResults.map((result) => [result.key, result]));

    return {
        overviewData: await parseBootstrapJson<OverviewStats>({ resultMap, key: 'overview', label: '개요', context }),
        revenueData: await parseBootstrapJson<RevenueStats>({ resultMap, key: 'revenue', label: '수익', context }),
        topData: await parseBootstrapJson<TopProject[]>({ resultMap, key: 'top-projects', label: '상위 프로젝트', context }),
        healthData: await parseBootstrapJson<HealthStatus>({ resultMap, key: 'health', label: '헬스', context }),
        llmData: await parseBootstrapJson<LlmStatus>({ resultMap, key: 'llm-status', label: 'LLM', context }),
        adVideoData: await parseBootstrapJson<{ total: number; orders: AdminAdVideoOrderItem[] }>({ resultMap, key: 'ad-video-orders', label: '광고 주문', context }),
        adMonitorData: await parseBootstrapJson<AdminAdOrderMonitorSummary>({ resultMap, key: 'ad-video-orders-monitor-summary', label: '광고 주문 모니터링', context }),
        adSettlementData: await parseBootstrapJson<AdminAdOrderSettlementDashboard>({ resultMap, key: 'ad-video-orders-settlement-dashboard', label: '광고 주문 정산', context }),
        capabilityData: await parseBootstrapJson<OrchestratorCapabilitySummaryResponse>({ resultMap, key: 'capabilities-summary', label: '오케스트레이터 기능군', context }),
        selfRunData: await parseBootstrapJson<AdminDashboardSelfRunStatus>({ resultMap, key: 'latest-self-run', label: '최신 self-run', context }),
        securityGuardDetailData: await parseBootstrapJson<OrchestratorCapabilityDetailResponse>({ resultMap, key: 'security-guard-detail', label: 'Security Guard 상세', context }),
        failedMessages: context.failedMessages,
        unauthorized: context.unauthorized,
        adMonitorUnavailable: context.adMonitorUnavailable,
        adSettlementUnavailable: context.adSettlementUnavailable,
        liveLogEvents: context.liveLogEvents,
    } satisfies AdminDashboardParsedBootstrapData;
}

export function assertAdminDashboardBootstrapParserContract() {
    const empty = new Map<string, AdminDashboardBootstrapResponseMapItem>();
    if (empty.size !== 0) {
        throw new Error('admin dashboard bootstrap parser contract 누락: result map 기본 생성 필요');
    }
}

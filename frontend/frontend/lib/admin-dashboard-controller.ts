import {
    buildAdminDashboardBootstrapRequestMap,
    runAdminDashboardBootstrapRequests,
    type AdminDashboardBootstrapRequest,
} from '@/lib/admin-dashboard-bootstrap';
import {
    parseAdminDashboardBootstrapResults,
} from '@/lib/admin-dashboard-bootstrap-parser';
import {
    assembleAdminDashboardState,
    type AdminDashboardStateAssembly,
} from '@/lib/admin-dashboard-state-assembler';
import {
    buildAdminDashboardSnapshot,
    diffAdminDashboardSnapshot,
    type AdminDashboardSnapshot,
} from '@/lib/admin-dashboard-snapshot';
import type {
    AdminAdOrderMonitorSummary,
    AdminAdOrderSettlementDashboard,
    AdminAdVideoOrderItem,
    AdminDashboardSelfRunStatus,
    OrchestratorCapabilityDetailResponse,
    OrchestratorCapabilitySummaryResponse,
    OverviewStats,
    RevenueStats,
    TopProject,
} from '@/lib/admin-dashboard-types';
import type { HealthStatus } from '@/lib/admin-health-analysis';
import type { LiveLogItem, LlmStatus } from '@/lib/admin-runtime-types';

export type AdminDashboardControllerLogEvent = {
    level: LiveLogItem['level'];
    message: string;
    meta?: Partial<LiveLogItem> & { capabilityId?: string };
};

export type AdminDashboardControllerResult = {
    unauthorized: boolean;
    overviewData: OverviewStats | null;
    revenueData: RevenueStats | null;
    topData: TopProject[] | null;
    healthData: HealthStatus | null;
    llmData: LlmStatus | null;
    assembledState: AdminDashboardStateAssembly;
    failedMessages: string[];
    adMonitorUnavailable: boolean;
    adSettlementUnavailable: boolean;
    liveLogEvents: AdminDashboardControllerLogEvent[];
    nextSnapshot: AdminDashboardSnapshot;
    lastUpdated: string;
};

async function refetchAdminAdVideoOrders(options: {
    apiBaseUrl: string;
    headers: HeadersInit;
}) {
    try {
        const response = await runAdminDashboardBootstrapRequests([
            {
                key: 'ad-video-orders-refetch',
                label: '광고 주문 재조회',
                url: `${options.apiBaseUrl}/api/admin/ad-video-orders?skip=0&limit=20`,
                init: {
                    headers: options.headers,
                    cache: 'no-store',
                },
            } satisfies AdminDashboardBootstrapRequest,
        ]).then((results) => results[0]?.response ?? null);
        if (!response) {
            return { data: null as { total: number; orders: AdminAdVideoOrderItem[] } | null, unauthorized: false };
        }
        if (response.status === 401) {
            return { data: null as { total: number; orders: AdminAdVideoOrderItem[] } | null, unauthorized: true };
        }
        if (!response.ok) {
            return { data: null as { total: number; orders: AdminAdVideoOrderItem[] } | null, unauthorized: false };
        }
        return {
            data: await response.json() as { total: number; orders: AdminAdVideoOrderItem[] },
            unauthorized: false,
        };
    } catch {
        return { data: null as { total: number; orders: AdminAdVideoOrderItem[] } | null, unauthorized: false };
    }
}

async function refetchAdminJson<T>(options: {
    apiBaseUrl: string;
    headers: HeadersInit;
    key: string;
    label: string;
    url: string;
    tolerateServerError?: boolean;
}) {
    try {
        const response = await runAdminDashboardBootstrapRequests([
            {
                key: options.key,
                label: options.label,
                url: options.url,
                init: {
                    headers: options.headers,
                    cache: 'no-store',
                },
                tolerateServerError: options.tolerateServerError,
            } satisfies AdminDashboardBootstrapRequest,
        ]).then((results) => results[0]?.response ?? null);
        if (!response) {
            return { data: null as T | null, unauthorized: false };
        }
        if (response.status === 401) {
            return { data: null as T | null, unauthorized: true };
        }
        if (options.tolerateServerError && response.status >= 500) {
            return { data: null as T | null, unauthorized: false };
        }
        if (!response.ok) {
            return { data: null as T | null, unauthorized: false };
        }
        return {
            data: await response.json() as T,
            unauthorized: false,
        };
    } catch {
        return { data: null as T | null, unauthorized: false };
    }
}

export async function loadAdminDashboardController(options: {
    apiBaseUrl: string;
    token: string;
    previousSnapshot: AdminDashboardSnapshot | null;
    currentOverview: OverviewStats;
    currentRevenue: RevenueStats;
    currentHealth: HealthStatus | null;
    currentLlmStatus: LlmStatus | null;
    adMonitorUnavailable: boolean;
    adSettlementUnavailable: boolean;
    includeCapabilityBootstrap?: boolean;
    formatCurrency: (value: number) => string;
    buildFallbackAdOrderMonitorSummary: (orders: AdminAdVideoOrderItem[]) => AdminAdOrderMonitorSummary;
    buildFallbackAdSettlementDashboard: (orders: AdminAdVideoOrderItem[]) => AdminAdOrderSettlementDashboard;
}) {
    const headers: HeadersInit = { Authorization: `Bearer ${options.token}` };
    const bootstrapRequests = buildAdminDashboardBootstrapRequestMap(options.apiBaseUrl, headers, {
        adMonitorUnavailable: options.adMonitorUnavailable,
        adSettlementUnavailable: options.adSettlementUnavailable,
        includeCapabilityBootstrap: options.includeCapabilityBootstrap,
    });
    const bootstrapResults = await runAdminDashboardBootstrapRequests(
        bootstrapRequests.filter((request) => !!request.url),
    );
    const parsedBootstrap = await parseAdminDashboardBootstrapResults({
        bootstrapResults,
    });
    if (parsedBootstrap.unauthorized) {
        return {
            unauthorized: true,
            overviewData: null,
            revenueData: null,
            topData: null,
            healthData: null,
            llmData: null,
            assembledState: assembleAdminDashboardState({
                overviewData: null,
                revenueData: null,
                topData: null,
                healthData: null,
                llmData: null,
                adVideoData: null,
                adMonitorData: null,
                adSettlementData: null,
                capabilityData: null,
                selfRunData: null,
                securityGuardDetailData: null,
                adMonitorUnavailable: options.adMonitorUnavailable,
                adSettlementUnavailable: options.adSettlementUnavailable,
                buildFallbackAdOrderMonitorSummary: options.buildFallbackAdOrderMonitorSummary,
                buildFallbackAdSettlementDashboard: options.buildFallbackAdSettlementDashboard,
            }),
            failedMessages: parsedBootstrap.failedMessages,
            adMonitorUnavailable: options.adMonitorUnavailable,
            adSettlementUnavailable: options.adSettlementUnavailable,
            liveLogEvents: [],
            nextSnapshot: options.previousSnapshot || buildAdminDashboardSnapshot({
                overviewData: null,
                revenueData: null,
                healthData: null,
                llmData: null,
                previousSnapshot: null,
                currentOverview: options.currentOverview,
                currentRevenue: options.currentRevenue,
                currentHealth: options.currentHealth,
                currentLlmStatus: options.currentLlmStatus,
            }),
            lastUpdated: new Date().toLocaleString('ko-KR'),
        } satisfies AdminDashboardControllerResult;
    }

    const finalAdMonitorUnavailable = options.adMonitorUnavailable || parsedBootstrap.adMonitorUnavailable;
    const finalAdSettlementUnavailable = options.adSettlementUnavailable || parsedBootstrap.adSettlementUnavailable;
    let adVideoData = parsedBootstrap.adVideoData;
    if (!adVideoData || Number(adVideoData.total || 0) === 0) {
        const refetchResult = await refetchAdminAdVideoOrders({
            apiBaseUrl: options.apiBaseUrl,
            headers,
        });
        if (refetchResult.unauthorized) {
            return {
                unauthorized: true,
                overviewData: null,
                revenueData: null,
                topData: null,
                healthData: null,
                llmData: null,
                assembledState: assembleAdminDashboardState({
                    overviewData: null,
                    revenueData: null,
                    topData: null,
                    healthData: null,
                    llmData: null,
                    adVideoData: null,
                    adMonitorData: null,
                    adSettlementData: null,
                    capabilityData: null,
                    selfRunData: null,
                    securityGuardDetailData: null,
                    adMonitorUnavailable: finalAdMonitorUnavailable,
                    adSettlementUnavailable: finalAdSettlementUnavailable,
                    buildFallbackAdOrderMonitorSummary: options.buildFallbackAdOrderMonitorSummary,
                    buildFallbackAdSettlementDashboard: options.buildFallbackAdSettlementDashboard,
                }),
                failedMessages: parsedBootstrap.failedMessages,
                adMonitorUnavailable: finalAdMonitorUnavailable,
                adSettlementUnavailable: finalAdSettlementUnavailable,
                liveLogEvents: parsedBootstrap.liveLogEvents,
                nextSnapshot: options.previousSnapshot || buildAdminDashboardSnapshot({
                    overviewData: null,
                    revenueData: null,
                    healthData: null,
                    llmData: null,
                    previousSnapshot: null,
                    currentOverview: options.currentOverview,
                    currentRevenue: options.currentRevenue,
                    currentHealth: options.currentHealth,
                    currentLlmStatus: options.currentLlmStatus,
                }),
                lastUpdated: new Date().toLocaleString('ko-KR'),
            } satisfies AdminDashboardControllerResult;
        }
        adVideoData = refetchResult.data || adVideoData;
    }

    let healthData = parsedBootstrap.healthData;
    if (!healthData) {
        const refetchResult = await refetchAdminJson<HealthStatus>({
            apiBaseUrl: options.apiBaseUrl,
            headers,
            key: 'health-refetch',
            label: '헬스 재조회',
            url: `${options.apiBaseUrl}/api/health`,
        });
        if (refetchResult.unauthorized) {
            return {
                unauthorized: true,
                overviewData: null,
                revenueData: null,
                topData: null,
                healthData: null,
                llmData: null,
                assembledState: assembleAdminDashboardState({
                    overviewData: null,
                    revenueData: null,
                    topData: null,
                    healthData: null,
                    llmData: null,
                    adVideoData: null,
                    adMonitorData: null,
                    adSettlementData: null,
                    capabilityData: null,
                    selfRunData: null,
                    securityGuardDetailData: null,
                    adMonitorUnavailable: finalAdMonitorUnavailable,
                    adSettlementUnavailable: finalAdSettlementUnavailable,
                    buildFallbackAdOrderMonitorSummary: options.buildFallbackAdOrderMonitorSummary,
                    buildFallbackAdSettlementDashboard: options.buildFallbackAdSettlementDashboard,
                }),
                failedMessages: parsedBootstrap.failedMessages,
                adMonitorUnavailable: finalAdMonitorUnavailable,
                adSettlementUnavailable: finalAdSettlementUnavailable,
                liveLogEvents: parsedBootstrap.liveLogEvents,
                nextSnapshot: options.previousSnapshot || buildAdminDashboardSnapshot({
                    overviewData: null,
                    revenueData: null,
                    healthData: null,
                    llmData: null,
                    previousSnapshot: null,
                    currentOverview: options.currentOverview,
                    currentRevenue: options.currentRevenue,
                    currentHealth: options.currentHealth,
                    currentLlmStatus: options.currentLlmStatus,
                }),
                lastUpdated: new Date().toLocaleString('ko-KR'),
            } satisfies AdminDashboardControllerResult;
        }
        healthData = refetchResult.data || healthData;
    }

    let llmData = parsedBootstrap.llmData;
    if (!llmData) {
        const refetchResult = await refetchAdminJson<LlmStatus>({
            apiBaseUrl: options.apiBaseUrl,
            headers,
            key: 'llm-status-refetch',
            label: 'LLM 재조회',
            url: `${options.apiBaseUrl}/api/llm/status`,
        });
        if (refetchResult.unauthorized) {
            return {
                unauthorized: true,
                overviewData: null,
                revenueData: null,
                topData: null,
                healthData: null,
                llmData: null,
                assembledState: assembleAdminDashboardState({
                    overviewData: null,
                    revenueData: null,
                    topData: null,
                    healthData: null,
                    llmData: null,
                    adVideoData: null,
                    adMonitorData: null,
                    adSettlementData: null,
                    capabilityData: null,
                    selfRunData: null,
                    securityGuardDetailData: null,
                    adMonitorUnavailable: finalAdMonitorUnavailable,
                    adSettlementUnavailable: finalAdSettlementUnavailable,
                    buildFallbackAdOrderMonitorSummary: options.buildFallbackAdOrderMonitorSummary,
                    buildFallbackAdSettlementDashboard: options.buildFallbackAdSettlementDashboard,
                }),
                failedMessages: parsedBootstrap.failedMessages,
                adMonitorUnavailable: finalAdMonitorUnavailable,
                adSettlementUnavailable: finalAdSettlementUnavailable,
                liveLogEvents: parsedBootstrap.liveLogEvents,
                nextSnapshot: options.previousSnapshot || buildAdminDashboardSnapshot({
                    overviewData: null,
                    revenueData: null,
                    healthData: null,
                    llmData: null,
                    previousSnapshot: null,
                    currentOverview: options.currentOverview,
                    currentRevenue: options.currentRevenue,
                    currentHealth: options.currentHealth,
                    currentLlmStatus: options.currentLlmStatus,
                }),
                lastUpdated: new Date().toLocaleString('ko-KR'),
            } satisfies AdminDashboardControllerResult;
        }
        llmData = refetchResult.data || llmData;
    }

    let capabilityData = parsedBootstrap.capabilityData;
    if (options.includeCapabilityBootstrap !== false && !capabilityData) {
        const refetchResult = await refetchAdminJson<OrchestratorCapabilitySummaryResponse>({
            apiBaseUrl: options.apiBaseUrl,
            headers,
            key: 'capabilities-summary-refetch',
            label: '오케스트레이터 기능군 재조회',
            url: `${options.apiBaseUrl}/api/admin/orchestrator/capabilities/summary`,
        });
        if (refetchResult.unauthorized) {
            return {
                unauthorized: true,
                overviewData: null,
                revenueData: null,
                topData: null,
                healthData: null,
                llmData: null,
                assembledState: assembleAdminDashboardState({
                    overviewData: null,
                    revenueData: null,
                    topData: null,
                    healthData: null,
                    llmData: null,
                    adVideoData: null,
                    adMonitorData: null,
                    adSettlementData: null,
                    capabilityData: null,
                    selfRunData: null,
                    securityGuardDetailData: null,
                    adMonitorUnavailable: finalAdMonitorUnavailable,
                    adSettlementUnavailable: finalAdSettlementUnavailable,
                    buildFallbackAdOrderMonitorSummary: options.buildFallbackAdOrderMonitorSummary,
                    buildFallbackAdSettlementDashboard: options.buildFallbackAdSettlementDashboard,
                }),
                failedMessages: parsedBootstrap.failedMessages,
                adMonitorUnavailable: finalAdMonitorUnavailable,
                adSettlementUnavailable: finalAdSettlementUnavailable,
                liveLogEvents: parsedBootstrap.liveLogEvents,
                nextSnapshot: options.previousSnapshot || buildAdminDashboardSnapshot({
                    overviewData: null,
                    revenueData: null,
                    healthData: null,
                    llmData: null,
                    previousSnapshot: null,
                    currentOverview: options.currentOverview,
                    currentRevenue: options.currentRevenue,
                    currentHealth: options.currentHealth,
                    currentLlmStatus: options.currentLlmStatus,
                }),
                lastUpdated: new Date().toLocaleString('ko-KR'),
            } satisfies AdminDashboardControllerResult;
        }
        capabilityData = refetchResult.data || capabilityData;
    }

    let selfRunData = parsedBootstrap.selfRunData;
    if (!selfRunData) {
        const refetchResult = await refetchAdminJson<AdminDashboardSelfRunStatus>({
            apiBaseUrl: options.apiBaseUrl,
            headers,
            key: 'latest-self-run-refetch',
            label: '최신 self-run 재조회',
            url: `${options.apiBaseUrl}/api/admin/workspace-self-run-record?latest=true`,
            tolerateServerError: true,
        });
        if (refetchResult.unauthorized) {
            return {
                unauthorized: true,
                overviewData: null,
                revenueData: null,
                topData: null,
                healthData: null,
                llmData: null,
                assembledState: assembleAdminDashboardState({
                    overviewData: null,
                    revenueData: null,
                    topData: null,
                    healthData: null,
                    llmData: null,
                    adVideoData: null,
                    adMonitorData: null,
                    adSettlementData: null,
                    capabilityData: null,
                    selfRunData: null,
                    securityGuardDetailData: null,
                    adMonitorUnavailable: finalAdMonitorUnavailable,
                    adSettlementUnavailable: finalAdSettlementUnavailable,
                    buildFallbackAdOrderMonitorSummary: options.buildFallbackAdOrderMonitorSummary,
                    buildFallbackAdSettlementDashboard: options.buildFallbackAdSettlementDashboard,
                }),
                failedMessages: parsedBootstrap.failedMessages,
                adMonitorUnavailable: finalAdMonitorUnavailable,
                adSettlementUnavailable: finalAdSettlementUnavailable,
                liveLogEvents: parsedBootstrap.liveLogEvents,
                nextSnapshot: options.previousSnapshot || buildAdminDashboardSnapshot({
                    overviewData: null,
                    revenueData: null,
                    healthData: null,
                    llmData: null,
                    previousSnapshot: null,
                    currentOverview: options.currentOverview,
                    currentRevenue: options.currentRevenue,
                    currentHealth: options.currentHealth,
                    currentLlmStatus: options.currentLlmStatus,
                }),
                lastUpdated: new Date().toLocaleString('ko-KR'),
            } satisfies AdminDashboardControllerResult;
        }
        selfRunData = refetchResult.data || selfRunData;
    }

    let securityGuardDetailData = parsedBootstrap.securityGuardDetailData;
    if (options.includeCapabilityBootstrap !== false && !securityGuardDetailData) {
        const refetchResult = await refetchAdminJson<OrchestratorCapabilityDetailResponse>({
            apiBaseUrl: options.apiBaseUrl,
            headers,
            key: 'security-guard-detail-refetch',
            label: 'Security Guard 상세 재조회',
            url: `${options.apiBaseUrl}/api/admin/orchestrator/capabilities/security-guard`,
        });
        if (refetchResult.unauthorized) {
            return {
                unauthorized: true,
                overviewData: null,
                revenueData: null,
                topData: null,
                healthData: null,
                llmData: null,
                assembledState: assembleAdminDashboardState({
                    overviewData: null,
                    revenueData: null,
                    topData: null,
                    healthData: null,
                    llmData: null,
                    adVideoData: null,
                    adMonitorData: null,
                    adSettlementData: null,
                    capabilityData: null,
                    selfRunData: null,
                    securityGuardDetailData: null,
                    adMonitorUnavailable: finalAdMonitorUnavailable,
                    adSettlementUnavailable: finalAdSettlementUnavailable,
                    buildFallbackAdOrderMonitorSummary: options.buildFallbackAdOrderMonitorSummary,
                    buildFallbackAdSettlementDashboard: options.buildFallbackAdSettlementDashboard,
                }),
                failedMessages: parsedBootstrap.failedMessages,
                adMonitorUnavailable: finalAdMonitorUnavailable,
                adSettlementUnavailable: finalAdSettlementUnavailable,
                liveLogEvents: parsedBootstrap.liveLogEvents,
                nextSnapshot: options.previousSnapshot || buildAdminDashboardSnapshot({
                    overviewData: null,
                    revenueData: null,
                    healthData: null,
                    llmData: null,
                    previousSnapshot: null,
                    currentOverview: options.currentOverview,
                    currentRevenue: options.currentRevenue,
                    currentHealth: options.currentHealth,
                    currentLlmStatus: options.currentLlmStatus,
                }),
                lastUpdated: new Date().toLocaleString('ko-KR'),
            } satisfies AdminDashboardControllerResult;
        }
        securityGuardDetailData = refetchResult.data || securityGuardDetailData;
    }

    const assembledState = assembleAdminDashboardState({
        overviewData: parsedBootstrap.overviewData,
        revenueData: parsedBootstrap.revenueData,
        topData: parsedBootstrap.topData,
        healthData,
        llmData,
        adVideoData,
        adMonitorData: parsedBootstrap.adMonitorData,
        adSettlementData: parsedBootstrap.adSettlementData,
        capabilityData,
        selfRunData,
        securityGuardDetailData,
        adMonitorUnavailable: finalAdMonitorUnavailable,
        adSettlementUnavailable: finalAdSettlementUnavailable,
        buildFallbackAdOrderMonitorSummary: options.buildFallbackAdOrderMonitorSummary,
        buildFallbackAdSettlementDashboard: options.buildFallbackAdSettlementDashboard,
    });
    const nextSnapshot = buildAdminDashboardSnapshot({
        overviewData: parsedBootstrap.overviewData,
        revenueData: parsedBootstrap.revenueData,
        healthData,
        llmData,
        previousSnapshot: options.previousSnapshot,
        currentOverview: options.currentOverview,
        currentRevenue: options.currentRevenue,
        currentHealth: options.currentHealth,
        currentLlmStatus: options.currentLlmStatus,
    });

    return {
        unauthorized: false,
        overviewData: parsedBootstrap.overviewData,
        revenueData: parsedBootstrap.revenueData,
        topData: parsedBootstrap.topData,
        healthData,
        llmData,
        assembledState,
        failedMessages: parsedBootstrap.failedMessages,
        adMonitorUnavailable: finalAdMonitorUnavailable,
        adSettlementUnavailable: finalAdSettlementUnavailable,
        liveLogEvents: [
            ...parsedBootstrap.liveLogEvents,
            ...diffAdminDashboardSnapshot({
                previousSnapshot: options.previousSnapshot,
                nextSnapshot,
                formatCurrency: options.formatCurrency,
            }),
        ],
        nextSnapshot,
        lastUpdated: new Date().toLocaleString('ko-KR'),
    } satisfies AdminDashboardControllerResult;
}

export function assertAdminDashboardControllerContract() {
    const requests = buildAdminDashboardBootstrapRequestMap('https://example.com', { Authorization: 'Bearer sample' }, {
        adMonitorUnavailable: false,
        adSettlementUnavailable: false,
    });
    if (!requests.some((request) => request.key === 'overview')) {
        throw new Error('admin dashboard controller contract 누락: overview bootstrap 요청 필요');
    }
}

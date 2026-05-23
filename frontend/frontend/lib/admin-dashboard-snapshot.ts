import type { HealthStatus } from '@/lib/admin-health-analysis';
import type { LiveLogItem, LlmStatus } from '@/lib/admin-runtime-types';
import type { OverviewStats, RevenueStats } from '@/lib/admin-dashboard-types';

export type AdminDashboardSnapshot = {
    purchases: number;
    revenue: number;
    health: string;
    llmLoaded: boolean;
    vector: string;
};

export type AdminDashboardSnapshotLogEvent = {
    level: LiveLogItem['level'];
    message: string;
};

export function buildAdminDashboardSnapshot(options: {
    overviewData: OverviewStats | null;
    revenueData: RevenueStats | null;
    healthData: HealthStatus | null;
    llmData: LlmStatus | null;
    previousSnapshot: AdminDashboardSnapshot | null;
    currentOverview: OverviewStats;
    currentRevenue: RevenueStats;
    currentHealth: HealthStatus | null;
    currentLlmStatus: LlmStatus | null;
}) {
    return {
        purchases: options.overviewData?.purchases ?? options.previousSnapshot?.purchases ?? options.currentOverview.purchases,
        revenue: options.revenueData?.total_revenue ?? options.previousSnapshot?.revenue ?? options.currentRevenue.total_revenue,
        health: options.healthData?.status ?? options.previousSnapshot?.health ?? options.currentHealth?.status ?? 'unknown',
        llmLoaded: options.llmData?.loaded ?? options.previousSnapshot?.llmLoaded ?? options.currentLlmStatus?.loaded ?? false,
        vector: options.overviewData?.vector_search?.status ?? options.previousSnapshot?.vector ?? options.currentOverview.vector_search?.status ?? 'unknown',
    } satisfies AdminDashboardSnapshot;
}

export function diffAdminDashboardSnapshot(options: {
    previousSnapshot: AdminDashboardSnapshot | null;
    nextSnapshot: AdminDashboardSnapshot;
    formatCurrency: (value: number) => string;
}) {
    if (!options.previousSnapshot) {
        return [{ level: 'info', message: '실시간 모니터링이 시작되었습니다.' }] satisfies AdminDashboardSnapshotLogEvent[];
    }

    const logs: AdminDashboardSnapshotLogEvent[] = [];
    if (options.nextSnapshot.purchases !== options.previousSnapshot.purchases) {
        logs.push({ level: 'success', message: `구매 건수 변경: ${options.previousSnapshot.purchases} → ${options.nextSnapshot.purchases}` });
    }
    if (options.nextSnapshot.revenue !== options.previousSnapshot.revenue) {
        logs.push({ level: 'info', message: `총 매출 변경: ${options.formatCurrency(options.previousSnapshot.revenue)} → ${options.formatCurrency(options.nextSnapshot.revenue)}` });
    }
    if (options.nextSnapshot.health !== options.previousSnapshot.health) {
        logs.push({ level: 'warning', message: `API 상태 변경: ${options.previousSnapshot.health} → ${options.nextSnapshot.health}` });
    }
    if (options.nextSnapshot.llmLoaded !== options.previousSnapshot.llmLoaded) {
        logs.push({ level: options.nextSnapshot.llmLoaded ? 'success' : 'warning', message: `LLM 상태 변경: ${options.nextSnapshot.llmLoaded ? 'loaded' : 'not_loaded'}` });
    }
    if (options.nextSnapshot.vector !== options.previousSnapshot.vector) {
        logs.push({ level: 'warning', message: `벡터 검색 상태 변경: ${options.previousSnapshot.vector} → ${options.nextSnapshot.vector}` });
    }
    return logs;
}

export function assertAdminDashboardSnapshotContract() {
    const next = buildAdminDashboardSnapshot({
        overviewData: { projects: 0, users: 0, purchases: 2, reviews: 0, vector_search: { status: 'ok', projects: { points_count: 0, vectors_count: 0 } } },
        revenueData: { total_revenue: 1000, total_purchases: 1, average_purchase_amount: 1000 },
        healthData: { status: 'ok' },
        llmData: { loaded: true, model_path: 'model', n_ctx: 1, n_batch: 1 },
        previousSnapshot: null,
        currentOverview: { projects: 0, users: 0, purchases: 0, reviews: 0, vector_search: { status: 'unknown', projects: { points_count: 0, vectors_count: 0 } } },
        currentRevenue: { total_revenue: 0, total_purchases: 0, average_purchase_amount: 0 },
        currentHealth: null,
        currentLlmStatus: null,
    });
    const logs = diffAdminDashboardSnapshot({ previousSnapshot: null, nextSnapshot: next, formatCurrency: (value) => `${value}` });
    if (next.purchases !== 2 || logs[0]?.message !== '실시간 모니터링이 시작되었습니다.') {
        throw new Error('admin dashboard snapshot contract 누락: snapshot 생성/초기 로그 필요');
    }
}

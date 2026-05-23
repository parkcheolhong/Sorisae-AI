import type { CompactOverviewCard } from '@/lib/admin-dashboard-ui-types';
import type { OverviewStats, RevenueStats, AdminDashboardSelfRunStatus } from '@/lib/admin-dashboard-types';
import type { HealthStatus } from '@/lib/admin-health-analysis';
import type { LlmStatus } from '@/lib/admin-runtime-types';
import { getSelfRunDisplayMeta } from '@/lib/admin-self-run-analysis';

export function isHealthyVectorStatus(status?: string | null) {
    return status === 'healthy' || status === 'ok' || status === 'ready';
}

export function buildAdminCompactOverviewCards(options: {
    overview: OverviewStats;
    revenue: RevenueStats;
    health: HealthStatus | null;
    llmStatus: LlmStatus | null;
    dashboardSelfRunStatus: AdminDashboardSelfRunStatus | null;
    formatCurrency: (value: number) => string;
}) {
    const vectorStatus = options.overview.vector_search?.status ?? 'unknown';
    const isVectorHealthy = isHealthyVectorStatus(vectorStatus);
    const llmStateLabel = options.llmStatus?.loaded ? 'loaded' : 'not_loaded';
    const dashboardSelfRunDisplayMeta = getSelfRunDisplayMeta(options.dashboardSelfRunStatus);
    const dashboardSelfRunCardValue = options.dashboardSelfRunStatus?.status === 'running'
        ? '자가 실행 활성'
        : options.dashboardSelfRunStatus?.status === 'pending_approval'
            ? '승인 대기'
            : options.dashboardSelfRunStatus?.status === 'no_changes'
                ? '재검증 완료'
                : options.dashboardSelfRunStatus?.status === 'applied_to_source'
                    ? '원본 반영 완료'
                    : options.dashboardSelfRunStatus?.status === 'failed'
                        ? dashboardSelfRunDisplayMeta.label
                        : '대기 중';
    const dashboardSelfRunCardTone: CompactOverviewCard['tone'] = options.dashboardSelfRunStatus?.status === 'running'
        ? 'emerald'
        : options.dashboardSelfRunStatus?.status === 'pending_approval'
            ? 'amber'
            : options.dashboardSelfRunStatus?.status === 'no_changes'
                ? 'emerald'
                : options.dashboardSelfRunStatus?.status === 'applied_to_source'
                    ? 'emerald'
                    : options.dashboardSelfRunStatus?.status === 'failed'
                        ? dashboardSelfRunDisplayMeta.tone
                        : 'slate';
    const dashboardSelfRunCardDetail = options.dashboardSelfRunStatus
        ? [
            `승인 ${options.dashboardSelfRunStatus.approval_id}`,
            options.dashboardSelfRunStatus.status === 'no_changes'
                ? 'clone 재검증 완료 · 반영할 diff 없음'
                : options.dashboardSelfRunStatus.status === 'applied_to_source'
                    ? '재검증 후 원본 반영 완료'
                    : options.dashboardSelfRunStatus.status === 'failed'
                        ? dashboardSelfRunDisplayMeta.detail
                        : typeof options.dashboardSelfRunStatus.running_seconds === 'number'
                            ? `${options.dashboardSelfRunStatus.running_seconds}초 경과`
                            : options.dashboardSelfRunStatus.directive_template || '자가 실행 준비 완료',
        ].join(' · ')
        : '최근 self-run 기록 없음';

    return {
        vectorStatus,
        isVectorHealthy,
        llmStateLabel,
        dashboardSelfRunDisplayMeta,
        dashboardSelfRunCardValue,
        dashboardSelfRunCardTone,
        dashboardSelfRunCardDetail,
        compactOverviewCards: [
            { key: 'projects', label: '전체 프로젝트', value: String(options.overview.projects), icon: '📦', tone: 'slate' },
            { key: 'users', label: '전체 사용자', value: String(options.overview.users), icon: '👥', tone: 'violet' },
            { key: 'purchases', label: '완료 구매', value: String(options.overview.purchases), icon: '✅', tone: 'emerald' },
            { key: 'reviews', label: '전체 리뷰', value: String(options.overview.reviews), icon: '⭐', tone: 'amber' },
            { key: 'revenue', label: '총 매출', value: options.formatCurrency(options.revenue.total_revenue), icon: '💰', tone: 'orange' },
            { key: 'average_purchase_amount', label: '평균 구매 금액', value: options.formatCurrency(options.revenue.average_purchase_amount), icon: '📊', tone: 'cyan' },
            {
                key: 'api_status',
                label: 'API 상태',
                value: options.health?.status ?? 'unknown',
                icon: '🌐',
                tone: options.health?.status === 'ok' || options.health?.status === 'healthy' ? 'emerald' : 'amber',
                detail: options.health?.status === 'ok' || options.health?.status === 'healthy' ? '정상 운영 중' : '점검 필요',
            },
            {
                key: 'llm_status',
                label: 'LLM 상태',
                value: llmStateLabel,
                icon: '🤖',
                tone: options.llmStatus?.loaded ? 'emerald' : 'amber',
                detail: options.llmStatus?.loaded ? undefined : '연결 확인 중',
            },
            {
                key: 'vector_status',
                label: '벡터 검색 상태',
                value: vectorStatus,
                icon: '🔍',
                tone: isVectorHealthy ? 'emerald' : 'amber',
                detail: `points ${options.overview.vector_search?.projects?.points_count ?? 0}`,
            },
            {
                key: 'self_run_status',
                label: 'Self-run 상태',
                value: dashboardSelfRunCardValue,
                icon: '🧪',
                tone: dashboardSelfRunCardTone,
                detail: dashboardSelfRunCardDetail,
            },
        ] satisfies CompactOverviewCard[],
    };
}

export function assertAdminDashboardOverviewAnalysisContract() {
    const result = buildAdminCompactOverviewCards({
        overview: { projects: 1, users: 2, purchases: 3, reviews: 4, vector_search: { status: 'ok', projects: { points_count: 5 } } },
        revenue: { total_revenue: 1000, total_purchases: 1, average_purchase_amount: 1000 },
        health: { status: 'ok' },
        llmStatus: { loaded: true, model_path: 'model', n_ctx: 1, n_batch: 1 },
        dashboardSelfRunStatus: null,
        formatCurrency: (value) => `${value}`,
    });
    if (result.compactOverviewCards.length < 10 || result.vectorStatus !== 'ok') {
        throw new Error('admin dashboard overview analysis contract 누락: compact overview card 조립 필요');
    }
}

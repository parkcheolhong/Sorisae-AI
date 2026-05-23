import { buildAdminOpsAlerts } from '@/lib/admin-health-dashboard-analysis';
import { buildAdminCompactOverviewCards } from '@/lib/admin-dashboard-overview-analysis';
import { buildAdminSystemResourceCards } from '@/lib/admin-health-dashboard-analysis';
import { classifySelfRunFailure } from '@/lib/admin-self-run-analysis';
import type { AdminDashboardOverviewProps } from '@/components/admin/admin-dashboard-overview';
import type { OrchestratorCapabilityState, SystemResourceCard } from '@/lib/admin-dashboard-ui-types';
import type { AdminAlertItem, AutomaticOpsActionItem, LlmStatus } from '@/lib/admin-runtime-types';
import type {
    AdminDashboardSelfRunStatus,
    OrchestratorCapabilitySummaryCard,
    OrchestratorCapabilityDetailResponse,
    OrchestratorCapabilitySummaryResponse,
    OverviewStats,
    RevenueStats,
} from '@/lib/admin-dashboard-types';
import type { HealthDiagnostics, HealthStatus } from '@/lib/admin-health-analysis';

interface BuildAdminPageHealthAnalysisInput {
    overview: OverviewStats;
    revenue: RevenueStats;
    health: HealthStatus | null;
    llmStatus: LlmStatus | null;
    orchestratorCapabilitySummary: OrchestratorCapabilitySummaryResponse | null;
    securityGuardDetail: OrchestratorCapabilityDetailResponse | null;
    dashboardSelfRunStatus: AdminDashboardSelfRunStatus | null;
    systemSettingsDisconnected: boolean;
    capabilityBootstrapEnabled: boolean;
    projectQuery: string;
    topProjects: Array<{ title: string }>;
    formatCurrency: (value: number) => string;
}

function normalizeDashboardSelfRunStatusLike(status: AdminDashboardSelfRunStatus | null) {
    if (!status) {
        return null;
    }

    return {
        approval_id: status.approval_id,
        status: status.status,
        running_seconds: status.running_seconds ?? undefined,
        python_compile_failed_files: status.python_compile_failed_files ?? undefined,
        analysis_abs_path: status.analysis_abs_path ?? undefined,
        root_cause_report_abs_path: status.root_cause_report_abs_path ?? undefined,
        runtime_diagnostic: status.runtime_diagnostic ?? undefined,
        directive_template: status.directive_template ?? undefined,
        directive_scope: status.directive_scope ?? undefined,
    };
}

function isTransientSelfRunCapabilityWarning(
    card: OrchestratorCapabilitySummaryCard,
    dashboardSelfRunStatus: AdminDashboardSelfRunStatus | null,
) {
    if (card.state !== 'warning') {
        return false;
    }
    if (!dashboardSelfRunStatus || (dashboardSelfRunStatus.status !== 'running' && dashboardSelfRunStatus.status !== 'pending_approval')) {
        return false;
    }
    const reason = String(card.state_reason || '').trim();
    return reason.includes('현재 self-run 이 진행 중이어서 결과 확정 전입니다.');
}

export function buildAdminPageHealthAnalysis(input: BuildAdminPageHealthAnalysisInput) {
    const healthDiagnostics = input.health?.diagnostics;
    const systemResourceCards: SystemResourceCard[] = buildAdminSystemResourceCards(healthDiagnostics);
    const orchestratorCapabilityGroups = input.orchestratorCapabilitySummary?.groups || [];
    const severityWeight: Record<OrchestratorCapabilityState, number> = {
        error: 3,
        warning: 2,
        active: 1,
        standby: 0,
    };
    const effectiveProblemCards = (input.orchestratorCapabilitySummary?.capabilities || [])
        .filter((card): card is OrchestratorCapabilitySummaryCard & { state: 'error' | 'warning' } => card.state === 'error' || card.state === 'warning')
        .filter((card) => !isTransientSelfRunCapabilityWarning(card, input.dashboardSelfRunStatus));
    const orchestratorProblemCards = effectiveProblemCards
        .map((card) => ({
            ...card,
            detail: card.detail ?? undefined,
        }))
        .sort((left, right) => {
            const stateDelta = severityWeight[right.state] - severityWeight[left.state];
            if (stateDelta !== 0) {
                return stateDelta;
            }
            return left.title.localeCompare(right.title, 'ko');
        })
        .slice(0, 4);
    const hasOrchestratorCapabilityError = effectiveProblemCards.some((card) => card.state === 'error');
    const hasOrchestratorCapabilityWarning = effectiveProblemCards.some((card) => card.state === 'warning');
    const filteredTopProjects = (() => {
        const query = input.projectQuery.trim().toLowerCase();
        if (!query) {
            return input.topProjects;
        }
        return input.topProjects.filter((project) => project.title.toLowerCase().includes(query));
    })();
    const opsAlerts: AdminAlertItem[] = buildAdminOpsAlerts({
        healthDiagnostics,
        hasOrchestratorCapabilityError,
        hasOrchestratorCapabilityWarning,
    });
    const {
        vectorStatus,
        dashboardSelfRunDisplayMeta,
        dashboardSelfRunCardValue,
        dashboardSelfRunCardTone,
        dashboardSelfRunCardDetail,
        compactOverviewCards,
    } = buildAdminCompactOverviewCards({
        overview: input.overview,
        revenue: input.revenue,
        health: input.health,
        llmStatus: input.llmStatus,
        dashboardSelfRunStatus: input.dashboardSelfRunStatus,
        formatCurrency: input.formatCurrency,
    });
    const normalizedDashboardSelfRunStatus = normalizeDashboardSelfRunStatusLike(input.dashboardSelfRunStatus);
    const activeDashboardSelfRun = !normalizedDashboardSelfRunStatus
        ? null
        : normalizedDashboardSelfRunStatus.status === 'running' || normalizedDashboardSelfRunStatus.status === 'pending_approval'
            ? normalizedDashboardSelfRunStatus
            : null;
    const dashboardSelfRunStatusLabel = normalizedDashboardSelfRunStatus?.status === 'running'
        ? '자가 실행 활성'
        : normalizedDashboardSelfRunStatus?.status === 'pending_approval'
            ? '승인 대기'
            : normalizedDashboardSelfRunStatus?.status === 'no_changes'
                ? '재검증 완료'
                : normalizedDashboardSelfRunStatus?.status === 'applied_to_source'
                    ? '원본 반영 완료'
                    : normalizedDashboardSelfRunStatus?.status === 'failed'
                        ? dashboardSelfRunDisplayMeta.label
                        : '대기 중';
    const dashboardSelfRunBannerDetail = activeDashboardSelfRun
        ? [
            activeDashboardSelfRun.directive_template || '기본 템플릿',
            activeDashboardSelfRun.directive_scope || '기본 범위',
            activeDashboardSelfRun.runtime_diagnostic || 'worker 가 활성 상태로 유지되고 있습니다.',
        ].filter(Boolean).join(' · ')
        : '';
    const selfRunFailureInsight = classifySelfRunFailure(input.dashboardSelfRunStatus, orchestratorProblemCards);
    const hasCapabilityBootstrapGap = !input.orchestratorCapabilitySummary || !input.securityGuardDetail;
    const capabilityBootstrapNotice = input.capabilityBootstrapEnabled && hasCapabilityBootstrapGap
        ? '오케스트레이터 기능군 상세 데이터가 잠시 지연되어 기본 건강상태 카드만 먼저 표시합니다. 새로고침 시 자동 재동기화됩니다.'
        : null;
    let automaticHealthScore = 100;
    automaticHealthScore -= opsAlerts.length * 10;
    automaticHealthScore -= orchestratorProblemCards.length * 8;
    automaticHealthScore -= dashboardSelfRunDisplayMeta.healthPenalty;
    if (input.health?.status !== 'ok' && input.health?.status !== 'healthy') automaticHealthScore -= 12;
    if (input.systemSettingsDisconnected) automaticHealthScore -= 8;
    if (hasCapabilityBootstrapGap && !selfRunFailureInsight) automaticHealthScore -= 4;
    automaticHealthScore = Math.max(0, Math.min(100, automaticHealthScore));
    const automaticHealthLabel = hasCapabilityBootstrapGap && automaticHealthScore >= 90
        ? '자동 건강상태 안정 · 기능군 재동기화 대기'
        : automaticHealthScore >= 90
            ? '자동 건강상태 안정'
            : automaticHealthScore >= 70
                ? '자동 건강상태 주의'
                : '자동 건강상태 긴급';
    const automaticOpsActions: AutomaticOpsActionItem[] = [];
    if (selfRunFailureInsight) {
        automaticOpsActions.push({
            id: `self-run-${selfRunFailureInsight.category}`,
            title: selfRunFailureInsight.title,
            summary: `${selfRunFailureInsight.reason} · ${selfRunFailureInsight.automatedActions.join(' · ')}`,
            tone: selfRunFailureInsight.severity === 'critical' ? 'red' : 'amber',
        });
    }
    if (input.systemSettingsDisconnected) {
        automaticOpsActions.push({
            id: 'system-settings-disconnected',
            title: '전역 설정 원본 미연결',
            summary: '전역 .env 원본이 비어 있거나 연결에 실패해 자동 개선 루틴이 설정 패널을 우선 개방합니다.',
            tone: 'amber',
        });
    }
    if (hasOrchestratorCapabilityError || hasOrchestratorCapabilityWarning) {
        automaticOpsActions.push({
            id: 'orchestrator-capability-watch',
            title: '오케스트레이터 기능군 자동 감시',
            summary: 'warning/error 기능군을 우선 노출하고 최신 self-run 기록을 기준으로 재진단합니다.',
            tone: hasOrchestratorCapabilityError ? 'red' : 'blue',
        });
    }
    if (hasCapabilityBootstrapGap) {
        automaticOpsActions.push({
            id: 'orchestrator-capability-bootstrap-gap',
            title: '오케스트레이터 기능군 재동기화 대기',
            summary: '요약 또는 Security Guard 상세 데이터가 지연돼도 메인 대시보드는 정상 지표를 우선 유지하고 다음 새로고침에서 재동기화합니다.',
            tone: 'blue',
        });
    }
    if ((healthDiagnostics?.alerts || []).length > 0) {
        automaticOpsActions.push({
            id: 'health-alert-watch',
            title: '헬스체크 자동 감시',
            summary: 'CPU/GPU/메모리 경고를 자동 집계해 운영 경고 목록에 반영합니다.',
            tone: 'blue',
        });
    }
    const securityGuardDetailSections = {
        pythonRules: [...((input.securityGuardDetail?.sections?.find((section) => section.id === 'python-security-validation')?.items || []).filter((item) => !['오류', '경고', '검사 파일 수'].includes(item.label)).map((item) => ({
            label: item.label,
            value: String(item.value),
            note: item.note ?? undefined,
        })))],
        findings: (input.securityGuardDetail?.sections?.find((section) => section.id === 'security-findings')?.items || []).map((item) => ({
            label: item.label,
            value: String(item.value),
            note: item.note ?? undefined,
        })),
    };

    return {
        healthDiagnostics,
        systemResourceCards,
        orchestratorCapabilityGroups,
        orchestratorProblemCards,
        hasOrchestratorCapabilityError,
        hasOrchestratorCapabilityWarning,
        filteredTopProjects,
        opsAlerts,
        vectorStatus,
        dashboardSelfRunDisplayMeta,
        dashboardSelfRunCardValue,
        dashboardSelfRunCardTone,
        dashboardSelfRunCardDetail,
        compactOverviewCards,
        activeDashboardSelfRun,
        normalizedDashboardSelfRunStatus,
        dashboardSelfRunStatusLabel,
        dashboardSelfRunBannerDetail,
        selfRunFailureInsight,
        capabilityBootstrapNotice,
        automaticHealthScore,
        automaticHealthLabel,
        automaticOpsActions: automaticOpsActions.slice(0, 4),
        securityGuardDetailSections,
    };
}

export interface BuildAdminDashboardOverviewAssemblyInput {
    error: string | null;
    dashboardAnalysis: ReturnType<typeof buildAdminPageHealthAnalysis>;
    selfRunApproving: boolean;
    onApproveWorkspaceSelfRun: () => void;
    autoOpsEnabled: boolean;
    onAutoOpsEnabledChange: (value: boolean) => void;
    autoOpsLastExecutedAt: string;
    autoRecoveryRunning: boolean;
    onExecuteAutomaticRecovery: () => void;
    onReloadDashboard: () => void;
    autoRecoveryHistory: AdminDashboardOverviewProps['autoRecoveryHistory'];
    buildCapabilityConnectionId: AdminDashboardOverviewProps['buildCapabilityConnectionId'];
    onOpenOrchestratorDetail: AdminDashboardOverviewProps['onOpenOrchestratorDetail'];
    getOrchestratorActionGuide: AdminDashboardOverviewProps['getOrchestratorActionGuide'];
    toFileHref: AdminDashboardOverviewProps['toFileHref'];
    dashboardSelfRunStatus: AdminDashboardOverviewProps['dashboardSelfRunStatus'];
    getHealthAlertMetrics: (alert: any) => Record<string, string | number>;
    getHealthAlertRootCause: AdminDashboardOverviewProps['getHealthAlertRootCause'];
    formatHealthMetricLabel: AdminDashboardOverviewProps['formatHealthMetricLabel'];
    formatHealthMetricValue: AdminDashboardOverviewProps['formatHealthMetricValue'];
    apiBaseUrl: string;
    onImmediateRefresh: () => void;
    voiceAlertEnabled: boolean;
    onToggleVoiceAlertEnabled: () => void;
    onSpeakAdminAlert: () => void;
    autoRefreshEnabled: boolean;
    onToggleAutoRefreshEnabled: () => void;
    refreshSeconds: number;
    onRefreshSecondsChange: (value: number) => void;
    refreshing: boolean;
    lastUpdated: string;
    focusedSelfHealingBusy: boolean;
    focusedSelfHealingModalOpen: boolean;
    onOpenFocusedSelfHealing: () => void;
    onCloseFocusedSelfHealing: () => void;
    focusedSelfHealingRequestedPath: string;
    onFocusedSelfHealingRequestedPathChange: (value: string) => void;
    focusedSelfHealingReason: string;
    onFocusedSelfHealingReasonChange: (value: string) => void;
    focusedSelfHealingPlan: NonNullable<AdminDashboardOverviewProps['focusedSelfHealingPlan']> | null;
    focusedSelfHealingApplyResult: NonNullable<AdminDashboardOverviewProps['focusedSelfHealingApplyResult']> | null;
    focusedSelfHealingApprovalConfirmed: boolean;
    onFocusedSelfHealingApprovalConfirmedChange: (value: boolean) => void;
    focusedSelfHealingSelectedOptionId: string;
    onFocusedSelfHealingSelectedOptionIdChange: (value: string) => void;
    onRunFocusedSelfHealingPlan: () => void;
    onApplyFocusedSelfHealing: () => void;
    focusedSelfHealingMessage: string;
}

export function buildAdminDashboardOverviewAssembly(input: BuildAdminDashboardOverviewAssemblyInput): AdminDashboardOverviewProps {
    return {
        error: input.error,
        activeDashboardSelfRun: input.dashboardAnalysis.activeDashboardSelfRun,
        dashboardSelfRunStatusLabel: input.dashboardAnalysis.dashboardSelfRunStatusLabel,
        dashboardSelfRunBannerDetail: input.dashboardAnalysis.dashboardSelfRunBannerDetail,
        selfRunApproving: input.selfRunApproving,
        onApproveWorkspaceSelfRun: input.onApproveWorkspaceSelfRun,
        autoOpsEnabled: input.autoOpsEnabled,
        onAutoOpsEnabledChange: input.onAutoOpsEnabledChange,
        automaticHealthScore: input.dashboardAnalysis.automaticHealthScore,
        automaticHealthLabel: input.dashboardAnalysis.automaticHealthLabel,
        selfRunFailureInsight: input.dashboardAnalysis.selfRunFailureInsight,
        capabilityBootstrapNotice: input.dashboardAnalysis.capabilityBootstrapNotice,
        autoOpsLastExecutedAt: input.autoOpsLastExecutedAt,
        autoRecoveryRunning: input.autoRecoveryRunning,
        onExecuteAutomaticRecovery: input.onExecuteAutomaticRecovery,
        onReloadDashboard: input.onReloadDashboard,
        automaticOpsActions: input.dashboardAnalysis.automaticOpsActions,
        autoRecoveryHistory: input.autoRecoveryHistory,
        compactOverviewCards: input.dashboardAnalysis.compactOverviewCards,
        orchestratorCapabilityGroups: input.dashboardAnalysis.orchestratorCapabilityGroups,
        orchestratorProblemCards: input.dashboardAnalysis.orchestratorProblemCards,
        securityGuardDetailSections: input.dashboardAnalysis.securityGuardDetailSections,
        buildCapabilityConnectionId: input.buildCapabilityConnectionId,
        onOpenOrchestratorDetail: input.onOpenOrchestratorDetail,
        getOrchestratorActionGuide: input.getOrchestratorActionGuide,
        toFileHref: input.toFileHref,
        dashboardSelfRunStatus: input.dashboardAnalysis.normalizedDashboardSelfRunStatus,
        systemResourceCards: input.dashboardAnalysis.systemResourceCards,
        healthAlerts: input.dashboardAnalysis.healthDiagnostics?.alerts || [],
        getHealthAlertMetrics: input.getHealthAlertMetrics,
        getHealthAlertRootCause: input.getHealthAlertRootCause,
        formatHealthMetricLabel: input.formatHealthMetricLabel,
        formatHealthMetricValue: input.formatHealthMetricValue,
        apiBaseUrl: input.apiBaseUrl,
        opsAlerts: input.dashboardAnalysis.opsAlerts,
        onImmediateRefresh: input.onImmediateRefresh,
        voiceAlertEnabled: input.voiceAlertEnabled,
        onToggleVoiceAlertEnabled: input.onToggleVoiceAlertEnabled,
        onSpeakAdminAlert: input.onSpeakAdminAlert,
        autoRefreshEnabled: input.autoRefreshEnabled,
        onToggleAutoRefreshEnabled: input.onToggleAutoRefreshEnabled,
        refreshSeconds: input.refreshSeconds,
        onRefreshSecondsChange: input.onRefreshSecondsChange,
        refreshing: input.refreshing,
        lastUpdated: input.lastUpdated,
        focusedSelfHealingBusy: input.focusedSelfHealingBusy,
        focusedSelfHealingModalOpen: input.focusedSelfHealingModalOpen,
        onOpenFocusedSelfHealing: input.onOpenFocusedSelfHealing,
        onCloseFocusedSelfHealing: input.onCloseFocusedSelfHealing,
        focusedSelfHealingRequestedPath: input.focusedSelfHealingRequestedPath,
        onFocusedSelfHealingRequestedPathChange: input.onFocusedSelfHealingRequestedPathChange,
        focusedSelfHealingReason: input.focusedSelfHealingReason,
        onFocusedSelfHealingReasonChange: input.onFocusedSelfHealingReasonChange,
        focusedSelfHealingPlan: input.focusedSelfHealingPlan,
        focusedSelfHealingApplyResult: input.focusedSelfHealingApplyResult,
        focusedSelfHealingApprovalConfirmed: input.focusedSelfHealingApprovalConfirmed,
        onFocusedSelfHealingApprovalConfirmedChange: input.onFocusedSelfHealingApprovalConfirmedChange,
        focusedSelfHealingSelectedOptionId: input.focusedSelfHealingSelectedOptionId,
        onFocusedSelfHealingSelectedOptionIdChange: input.onFocusedSelfHealingSelectedOptionIdChange,
        onRunFocusedSelfHealingPlan: input.onRunFocusedSelfHealingPlan,
        onApplyFocusedSelfHealing: input.onApplyFocusedSelfHealing,
        focusedSelfHealingMessage: input.focusedSelfHealingMessage,
    };
}

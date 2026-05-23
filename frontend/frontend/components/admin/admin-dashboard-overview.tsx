'use client';

import Link from 'next/link';
import type { AdminAlertItem, AutomaticOpsActionItem } from '@/lib/admin-runtime-types';
import type { CompactOverviewCard, SystemResourceCard } from '@/lib/admin-dashboard-ui-types';
import type { FocusedSelfHealingApplyResult, FocusedSelfHealingPlan } from '@/lib/admin-dashboard-types';

interface SelfRunFailureInsight {
    severity: 'warning' | 'critical';
    category: string;
    title: string;
    reason: string;
    automatedActions: string[];
    priorityFixPaths: string[];
    guideHref: string;
}

interface DashboardSelfRunStatusLike {
    approval_id?: string;
    running_seconds?: number;
    python_compile_failed_files?: string[];
    target_file_ids?: string[];
    failure_tags?: string[];
    analysis_abs_path?: string;
    root_cause_report_abs_path?: string;
    runtime_diagnostic?: string;
    status?: string;
}

interface AutoRecoveryHistoryItemLike {
    id: string;
    title: string;
    triggeredAt: string;
    mode: 'auto' | 'manual';
    category: string;
    summary: string;
    primaryPath?: string;
    retryStage?: string;
    retryQueued?: boolean;
    retryMessage?: string;
    normalizationAction?: string;
    normalizationMessage?: string;
    failedFiles?: string[];
}

interface OrchestratorCapabilityGroup {
    id: string;
    title: string;
    summary: string;
    state: string;
    active_count: number;
    warning_count: number;
    error_count: number;
}

interface OrchestratorProblemCard {
    id: string;
    title: string;
    summary: string;
    metric: string;
    detail?: string;
    state: 'warning' | 'error';
}

interface SecurityFindingItem {
    label: string;
    value: string;
    note?: string;
}

export interface AdminDashboardOverviewProps {
    error: string | null;
    capabilityBootstrapNotice?: string | null;
    activeDashboardSelfRun: DashboardSelfRunStatusLike | null;
    dashboardSelfRunStatusLabel: string;
    dashboardSelfRunBannerDetail: string;
    selfRunApproving: boolean;
    onApproveWorkspaceSelfRun: () => void;
    autoOpsEnabled: boolean;
    onAutoOpsEnabledChange: (value: boolean) => void;
    automaticHealthScore: number;
    automaticHealthLabel: string;
    selfRunFailureInsight: SelfRunFailureInsight | null;
    autoOpsLastExecutedAt: string;
    autoRecoveryRunning: boolean;
    onExecuteAutomaticRecovery: () => void;
    onReloadDashboard: () => void;
    automaticOpsActions: AutomaticOpsActionItem[];
    autoRecoveryHistory: AutoRecoveryHistoryItemLike[];
    compactOverviewCards: CompactOverviewCard[];
    orchestratorCapabilityGroups: OrchestratorCapabilityGroup[];
    orchestratorProblemCards: OrchestratorProblemCard[];
    securityGuardDetailSections: {
        findings: SecurityFindingItem[];
        pythonRules: SecurityFindingItem[];
    };
    buildCapabilityConnectionId: (groupId: string) => string;
    onOpenOrchestratorDetail: (capabilityId: string, detail: string, status: 'linked' | 'warning') => void;
    getOrchestratorActionGuide: (capabilityId: string) => { title: string; summary: string; href: string };
    toFileHref: (path: string) => string;
    dashboardSelfRunStatus: DashboardSelfRunStatusLike | null;
    systemResourceCards: SystemResourceCard[];
    healthAlerts: Array<{
        id: string;
        title: string;
        message: string;
        severity: string;
        action: string;
        source_path?: string;
        diagnostic_detail?: string;
    }>;
    getHealthAlertMetrics: (alert: any) => Record<string, string | number>;
    getHealthAlertRootCause: (alert: any) => string;
    formatHealthMetricLabel: (key: string) => string;
    formatHealthMetricValue: (key: string, value: string | number) => string;
    apiBaseUrl: string;
    opsAlerts: AdminAlertItem[];
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
    focusedSelfHealingPlan: FocusedSelfHealingPlan | null;
    focusedSelfHealingApplyResult: FocusedSelfHealingApplyResult | null;
    focusedSelfHealingApprovalConfirmed: boolean;
    onFocusedSelfHealingApprovalConfirmedChange: (value: boolean) => void;
    focusedSelfHealingSelectedOptionId: string;
    onFocusedSelfHealingSelectedOptionIdChange: (value: string) => void;
    onRunFocusedSelfHealingPlan: () => void;
    onApplyFocusedSelfHealing: () => void;
    focusedSelfHealingMessage: string;
}

export default function AdminDashboardOverview(props: AdminDashboardOverviewProps) {
    const dashboardErrorMessage = props.error || '';
    const showCapabilityBootstrapNotice = Boolean(props.capabilityBootstrapNotice);
    return (
        <>
            {showCapabilityBootstrapNotice && (
                <div data-testid="admin-dashboard-capability-bootstrap-notice" className="mb-6 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
                    ℹ️ {props.capabilityBootstrapNotice}
                </div>
            )}
            {props.error && !showCapabilityBootstrapNotice && (
                <div data-testid="admin-dashboard-error-banner" className="mb-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                    {`⚠️ 일부 데이터 로드에 실패했습니다: ${dashboardErrorMessage}`}
                </div>
            )}

            {props.activeDashboardSelfRun && (
                <section className="mb-6 rounded-xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-emerald-900">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                            <div className="flex flex-wrap items-center gap-2">
                                <h2 className="text-sm font-semibold">자가 실행 활성 상태가 관리자 대시보드에서 직접 감지되었습니다.</h2>
                                <span className="rounded-full border border-emerald-300 bg-white px-2 py-1 text-[11px] font-semibold text-emerald-700">
                                    {props.dashboardSelfRunStatusLabel}
                                </span>
                            </div>
                            <p className="mt-2 text-sm">
                                승인 ID {props.activeDashboardSelfRun.approval_id}
                                {typeof props.activeDashboardSelfRun.running_seconds === 'number'
                                    ? ` · ${props.activeDashboardSelfRun.running_seconds}초 경과`
                                    : ''}
                            </p>
                            <p className="mt-1 text-xs text-emerald-800/80">{props.dashboardSelfRunBannerDetail}</p>
                            {!!props.activeDashboardSelfRun.target_file_ids?.length && (
                                <p className="mt-2 break-all text-[11px] text-emerald-800/80">TARGET_FILE_IDS: {props.activeDashboardSelfRun.target_file_ids.join(', ')}</p>
                            )}
                            {!!props.activeDashboardSelfRun.failure_tags?.length && (
                                <p className="mt-1 break-all text-[11px] text-emerald-800/80">FAILURE_TAGS: {props.activeDashboardSelfRun.failure_tags.join(', ')}</p>
                            )}
                        </div>
                        <Link href="/admin/llm" className="rounded-lg border border-emerald-300 bg-white px-3 py-2 text-xs font-semibold text-emerald-800 hover:bg-emerald-100">
                            self-run 상세 제어 열기
                        </Link>
                        {props.activeDashboardSelfRun.status === 'pending_approval' && (
                            <button
                                type="button"
                                onClick={props.onApproveWorkspaceSelfRun}
                                disabled={props.selfRunApproving}
                                className={`rounded-lg px-3 py-2 text-xs font-semibold text-white ${props.selfRunApproving ? 'bg-emerald-300' : 'bg-emerald-600 hover:bg-emerald-700'}`}
                            >
                                {props.selfRunApproving ? '원본 반영 중...' : '승인 후 원본 반영'}
                            </button>
                        )}
                    </div>
                </section>
            )}

            <section className="mb-8 rounded-xl border bg-white p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h2 className="text-lg font-semibold text-gray-900">🩺 관리자 자동 건강상태 / 자가진단 / 자가개선</h2>
                        <p className="mt-1 text-sm text-gray-500">헬스체크, self-run 실패, 기능군 경고를 자동 감시하고 필요한 패널을 자동 개방합니다.</p>
                    </div>
                    <label className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-3 py-2 text-xs font-semibold text-gray-700">
                        <input type="checkbox" checked={props.autoOpsEnabled} onChange={(event) => props.onAutoOpsEnabledChange(event.target.checked)} />
                        자동 운영 모드
                    </label>
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-3">
                    <div className={`rounded-xl border p-4 ${props.automaticHealthScore >= 90 ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : props.automaticHealthScore >= 70 ? 'border-amber-200 bg-amber-50 text-amber-800' : 'border-red-200 bg-red-50 text-red-800'}`}>
                        <p className="text-xs font-semibold">자동 건강상태 점수</p>
                        <p className="mt-2 text-3xl font-bold">{props.automaticHealthScore}</p>
                        <p className="mt-2 text-xs">{props.automaticHealthLabel}</p>
                    </div>
                    <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 text-blue-900">
                        <p className="text-xs font-semibold">자동 자가진단</p>
                        <p className="mt-2 text-sm font-semibold">{props.selfRunFailureInsight?.title || '현재 self-run 실패 없음'}</p>
                        <p className="mt-2 text-xs text-blue-800/80">{props.selfRunFailureInsight?.reason || '오케스트레이터 기능군과 헬스 경고를 계속 자동 감시 중입니다.'}</p>
                    </div>
                    <div className="rounded-xl border border-[#314766] bg-[#161d27] p-4 text-[#dbeafe]">
                        <p className="text-xs font-semibold">자동 개선 실행</p>
                        <p className="mt-2 text-sm font-semibold text-[#f8fbff]">{props.autoOpsLastExecutedAt || '아직 자동 개선 실행 전'}</p>
                        <p className="mt-2 text-xs text-[#c7d2e0]">자동 운영 모드가 켜져 있으면 경고/실패 상태에 따라 로그, 설정, LLM 패널을 자동으로 개방합니다.</p>
                        <div className="mt-3 flex flex-wrap gap-2">
                            <button type="button" onClick={props.onExecuteAutomaticRecovery} disabled={props.autoRecoveryRunning} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-[11px] font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-50">
                                {props.autoRecoveryRunning ? '자동 복구 실행 중...' : '자동 복구 즉시 실행'}
                            </button>
                            <button type="button" onClick={props.onOpenFocusedSelfHealing} disabled={props.focusedSelfHealingBusy} className="rounded-lg border border-violet-300 bg-violet-50 px-3 py-2 text-[11px] font-semibold text-violet-800 hover:bg-violet-100 disabled:opacity-50">
                                {props.focusedSelfHealingBusy ? 'focused self-healing 실행 중...' : 'focused self-healing 실행'}
                            </button>
                            <button type="button" onClick={props.onReloadDashboard} disabled={props.refreshing} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-[11px] font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-50">
                                재진단 새로고침
                            </button>
                        </div>
                    </div>
                </div>
                {props.automaticOpsActions.length > 0 && (
                    <div className="mt-4 grid gap-3 lg:grid-cols-2">
                        {props.automaticOpsActions.map((item) => {
                            const toneClassName = item.tone === 'red'
                                ? 'border-red-200 bg-red-50 text-red-800'
                                : item.tone === 'amber'
                                    ? 'border-amber-200 bg-amber-50 text-amber-800'
                                    : item.tone === 'emerald'
                                        ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                                        : 'border-blue-200 bg-blue-50 text-blue-800';
                            return (
                                <div key={item.id} className={`rounded-xl border p-4 ${toneClassName}`}>
                                    <p className="text-sm font-semibold">{item.title}</p>
                                    <p className="mt-2 text-xs opacity-90">{item.summary}</p>
                                </div>
                            );
                        })}
                    </div>
                )}
                {props.autoRecoveryHistory.length > 0 && (
                    <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
                        <div className="flex items-center justify-between gap-3">
                            <div>
                                <h3 className="text-sm font-semibold text-slate-900">자동 복구 이력</h3>
                                <p className="mt-1 text-xs text-slate-600">자동/수동 복구 실행 결과를 최근 20건까지 저장합니다.</p>
                            </div>
                            <span className="rounded-full border border-slate-300 bg-white px-2 py-1 text-[11px] font-semibold text-slate-700">{props.autoRecoveryHistory.length}건</span>
                        </div>
                        <div className="mt-3 grid gap-2 lg:grid-cols-2">
                            {props.autoRecoveryHistory.slice(0, 6).map((item) => (
                                <div key={item.id} className="rounded-lg border border-slate-200 bg-white px-3 py-3 text-xs text-slate-700">
                                    <p className="font-semibold text-slate-900">{item.title}</p>
                                    <p className="mt-1">{item.triggeredAt} · {item.mode === 'auto' ? '자동' : '수동'} · {item.category}</p>
                                    <p className="mt-2 text-slate-600">{item.summary}</p>
                                    {item.primaryPath && <p className="mt-2 break-all text-[11px] text-slate-500">우선 경로: {item.primaryPath}</p>}
                                    {item.retryStage && <p className="mt-2 text-[11px] text-slate-500">retry stage: {item.retryStage}</p>}
                                    {typeof item.retryQueued === 'boolean' && <p className="mt-1 text-[11px] text-slate-500">retry queued: {item.retryQueued ? 'yes' : 'no'}</p>}
                                    {item.retryMessage && <p className="mt-1 break-all text-[11px] text-slate-500">retry message: {item.retryMessage}</p>}
                                    {item.normalizationAction && <p className="mt-1 text-[11px] text-slate-500">normalize action: {item.normalizationAction}</p>}
                                    {item.normalizationMessage && <p className="mt-1 break-all text-[11px] text-slate-500">normalize message: {item.normalizationMessage}</p>}
                                    {!!item.failedFiles?.length && (
                                        <div className="mt-2 rounded-md bg-slate-50 px-2 py-2 text-[11px] text-slate-500">
                                            <p className="font-semibold text-slate-600">retry 대상 실패 파일</p>
                                            <ul className="mt-1 list-disc space-y-1 pl-4">
                                                {item.failedFiles.slice(0, 3).map((path) => (
                                                    <li key={path} className="break-all">{path}</li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </section>

            {props.focusedSelfHealingModalOpen && (
                <section className="mb-8 rounded-xl border border-violet-200 bg-violet-50 p-5 text-violet-950">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                            <h2 className="text-lg font-semibold">🏗️ Focused Self-Healing Tower Crane</h2>
                            <p className="mt-1 text-sm text-violet-900/80">원인 범위만 좁혀 plan → 옵션 선택 → 승인 조건 확인 → apply → retry payload 확인까지 메인 화면에서 바로 실행합니다.</p>
                        </div>
                        <button type="button" onClick={props.onCloseFocusedSelfHealing} className="rounded-lg border border-violet-300 bg-white px-3 py-2 text-xs font-semibold text-violet-900 hover:bg-violet-100">
                            닫기
                        </button>
                    </div>

                    <div className="mt-4 grid gap-4 lg:grid-cols-2">
                        <label className="block">
                            <span className="mb-2 block text-xs font-semibold text-violet-900">requested_path</span>
                            <input value={props.focusedSelfHealingRequestedPath} onChange={(event) => props.onFocusedSelfHealingRequestedPathChange(event.target.value)} className="w-full rounded-lg border border-violet-300 bg-white px-3 py-2 text-sm text-slate-900" placeholder="frontend/frontend/app/admin/page.tsx" />
                        </label>
                        <label className="block">
                            <span className="mb-2 block text-xs font-semibold text-violet-900">reason</span>
                            <input value={props.focusedSelfHealingReason} onChange={(event) => props.onFocusedSelfHealingReasonChange(event.target.value)} className="w-full rounded-lg border border-violet-300 bg-white px-3 py-2 text-sm text-slate-900" placeholder="health score contract mismatch" />
                        </label>
                    </div>

                    <div className="mt-4 flex flex-wrap gap-2">
                        <button type="button" onClick={props.onRunFocusedSelfHealingPlan} disabled={props.focusedSelfHealingBusy} className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-700 disabled:bg-violet-300">
                            {props.focusedSelfHealingBusy ? 'plan 실행 중...' : '1. plan 호출'}
                        </button>
                        <button type="button" onClick={props.onApplyFocusedSelfHealing} disabled={props.focusedSelfHealingBusy || !props.focusedSelfHealingPlan || !props.focusedSelfHealingSelectedOptionId} className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:bg-emerald-300">
                            {props.focusedSelfHealingBusy ? 'apply 실행 중...' : '2. apply 호출'}
                        </button>
                    </div>

                    {props.focusedSelfHealingMessage && (
                        <div className="mt-4 rounded-lg border border-violet-300 bg-white px-4 py-3 text-sm text-violet-950">
                            {props.focusedSelfHealingMessage}
                        </div>
                    )}

                    {props.focusedSelfHealingPlan && (
                        <div className="mt-4 rounded-xl border border-violet-200 bg-white p-4 text-sm text-slate-800">
                            <div className="grid gap-2 lg:grid-cols-2">
                                <p><span className="font-semibold">issue_id:</span> {props.focusedSelfHealingPlan.issue_id}</p>
                                <p><span className="font-semibold">proposal_id:</span> {props.focusedSelfHealingPlan.proposal_id}</p>
                                <p className="break-all"><span className="font-semibold">focused_path:</span> {props.focusedSelfHealingPlan.focused_path}</p>
                                <p className="break-all"><span className="font-semibold">target_source_path:</span> {props.focusedSelfHealingPlan.target_source_path}</p>
                                <p><span className="font-semibold">category:</span> {props.focusedSelfHealingPlan.category}</p>
                                <p><span className="font-semibold">approval_required:</span> {props.focusedSelfHealingPlan.approval_required ? 'yes' : 'no'}</p>
                            </div>

                            <div className="mt-4">
                                <p className="text-xs font-semibold text-violet-900">2. selected_option_id 선택</p>
                                <div className="mt-2 grid gap-3 lg:grid-cols-3">
                                    {props.focusedSelfHealingPlan.options.map((option) => {
                                        const selected = props.focusedSelfHealingSelectedOptionId === option.option_id;
                                        return (
                                            <button key={option.option_id} type="button" onClick={() => props.onFocusedSelfHealingSelectedOptionIdChange(option.option_id)} className={`rounded-xl border p-4 text-left ${selected ? 'border-violet-500 bg-violet-50' : 'border-slate-200 bg-slate-50 hover:bg-slate-100'}`}>
                                                <div className="flex items-center justify-between gap-2">
                                                    <p className="font-semibold text-slate-900">{option.title}</p>
                                                    <span className="rounded-full border border-slate-300 bg-white px-2 py-1 text-[11px] font-semibold text-slate-700">{option.risk_level}</span>
                                                </div>
                                                <p className="mt-2 text-xs text-slate-600">{option.scope}</p>
                                                <p className="mt-2 text-[11px] text-slate-500">{option.option_id}</p>
                                                <div className="mt-3 text-[11px] text-slate-600">
                                                    <p className="font-semibold text-slate-800">validation_plan</p>
                                                    <ul className="mt-1 list-disc pl-4">
                                                        {option.validation_plan.map((plan) => <li key={`${option.option_id}-${plan}`}>{plan}</li>)}
                                                    </ul>
                                                </div>
                                            </button>
                                        );
                                    })}
                                </div>
                            </div>

                            {props.focusedSelfHealingPlan.approval_required && (
                                <label className="mt-4 inline-flex items-center gap-2 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-900">
                                    <input type="checkbox" checked={props.focusedSelfHealingApprovalConfirmed} onChange={(event) => props.onFocusedSelfHealingApprovalConfirmedChange(event.target.checked)} />
                                    4. 승인 필요 범위 확인 후 승인 스위치 활성화
                                </label>
                            )}

                            <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 text-xs text-slate-700">
                                <p className="font-semibold text-slate-900">verification loop</p>
                                <p className="mt-1">{(props.focusedSelfHealingPlan.execution_contract?.verification_loop || []).join(' → ') || 'syntax → type → runtime → domain-route'}</p>
                            </div>
                        </div>
                    )}

                    {props.focusedSelfHealingApplyResult && (
                        <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950">
                            <p className="font-semibold">apply 결과</p>
                            <div className="mt-2 grid gap-2 lg:grid-cols-2">
                                <p><span className="font-semibold">issue_id:</span> {props.focusedSelfHealingApplyResult.issue_id}</p>
                                <p><span className="font-semibold">selected_option_id:</span> {props.focusedSelfHealingApplyResult.selected_option_id || '-'}</p>
                                <p className="break-all"><span className="font-semibold">focused_path:</span> {props.focusedSelfHealingApplyResult.focused_path}</p>
                                <p className="break-all"><span className="font-semibold">target_source_path:</span> {props.focusedSelfHealingApplyResult.target_source_path}</p>
                            </div>
                            <div className="mt-3 rounded-lg border border-emerald-300 bg-white px-3 py-3 text-xs text-slate-800">
                                <p className="font-semibold text-slate-900">retry payload / verification loop</p>
                                <p className="mt-1 break-all"><span className="font-semibold">focused_path:</span> {props.focusedSelfHealingApplyResult.retry?.focused_path || '-'}</p>
                                <p className="mt-1"><span className="font-semibold">verification_loop:</span> {(props.focusedSelfHealingApplyResult.retry?.verification_loop || []).join(' → ') || '-'}</p>
                            </div>
                        </div>
                    )}
                </section>
            )}

            <section className="mb-8 grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-3">
                {props.compactOverviewCards.map((item) => {
                    const toneClasses = item.tone === 'emerald'
                        ? 'border-emerald-500/30 bg-emerald-500/8 text-emerald-300'
                        : item.tone === 'amber'
                            ? 'border-amber-500/30 bg-amber-500/8 text-amber-300'
                            : item.tone === 'violet'
                                ? 'border-violet-500/30 bg-violet-500/8 text-violet-300'
                                : item.tone === 'orange'
                                    ? 'border-orange-500/30 bg-orange-500/8 text-orange-300'
                                    : item.tone === 'cyan'
                                        ? 'border-cyan-500/30 bg-cyan-500/8 text-cyan-300'
                                        : 'border-slate-500/30 bg-slate-500/8 text-slate-300';

                    return (
                        <div key={item.key} className={`rounded-xl border px-4 py-3 transition-colors ${toneClasses}`}>
                            <div className="flex items-center gap-2 text-[11px] font-medium opacity-80">
                                <span className="text-sm">{item.icon}</span>
                                <span>{item.label}</span>
                            </div>
                            <p className="mt-2 break-all text-[clamp(1.4rem,2vw,2.15rem)] font-bold leading-none text-gray-100">{item.value}</p>
                            {item.detail && (
                                <p className="mt-2 text-[11px] text-gray-400">{item.detail}</p>
                            )}
                        </div>
                    );
                })}
            </section>

            <section className="mb-8 rounded-xl border bg-white p-5">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h2 className="text-lg font-semibold text-gray-900">🧠 오케스트레이터 기능군 상태 요약</h2>
                        <p className="mt-1 text-sm text-gray-500">/admin 에서 진단 통솔, 개선 통솔, 확장 통솔의 현재 상태를 바로 확인합니다.</p>
                    </div>
                    <Link
                        href={props.orchestratorProblemCards[0] ? `/admin/llm?capability=${encodeURIComponent(props.orchestratorProblemCards[0].id)}` : '/admin/llm'}
                        onClick={() => props.onOpenOrchestratorDetail(props.orchestratorProblemCards[0]?.id || 'summary', props.orchestratorProblemCards[0]?.title || '오케스트레이터 기능군 상세 이동', 'linked')}
                        className="rounded-lg border border-gray-300 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-50"
                    >
                        상세 제어 열기
                    </Link>
                </div>
                {props.orchestratorCapabilityGroups.length > 0 ? (
                    <div className="grid gap-3 md:grid-cols-3">
                        {props.orchestratorCapabilityGroups.map((group) => {
                            const toneClassName = group.state === 'error'
                                ? 'border-red-200 bg-red-50 text-red-700'
                                : group.state === 'warning'
                                    ? 'border-amber-200 bg-amber-50 text-amber-700'
                                    : 'border-emerald-200 bg-emerald-50 text-emerald-700';
                            return (
                                <div key={group.id} className={`rounded-xl border p-4 ${toneClassName}`}>
                                    <div className="flex items-center justify-between gap-2">
                                        <h3 className="text-sm font-semibold">{group.title}</h3>
                                        <span className="rounded-full border border-current/30 px-2 py-1 text-[11px] font-semibold">{group.state}</span>
                                    </div>
                                    <p className="mt-2 text-[11px] opacity-80">근거 API: /api/admin/orchestrator/capabilities/summary</p>
                                    <p className="mt-1 break-all text-[10px] opacity-70">{props.buildCapabilityConnectionId(group.id)}</p>
                                    <p className="mt-2 text-sm">{group.summary}</p>
                                    <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
                                        <span className="rounded-full bg-white/80 px-2 py-1">정상 {group.active_count}</span>
                                        <span className="rounded-full bg-white/80 px-2 py-1">주의 {group.warning_count}</span>
                                        <span className="rounded-full bg-white/80 px-2 py-1">오류 {group.error_count}</span>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                ) : (
                    <p className="text-sm text-gray-500">기능군 상태를 아직 수집하지 못했습니다. 새로고침 후 다시 확인하세요.</p>
                )}
                {props.orchestratorProblemCards.length > 0 && (
                    <div className="mt-5 rounded-xl border border-red-100 bg-red-50/70 p-4">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                            <div>
                                <h3 className="text-sm font-semibold text-red-800">즉시 확인할 경고 원인</h3>
                                <p className="mt-1 text-xs text-red-700/80">Python self-run 실제 기록 기준으로 오류 또는 주의 상태가 감지된 항목만 추렸습니다.</p>
                            </div>
                            <Link
                                href={props.orchestratorProblemCards[0] ? `/admin/llm?capability=${encodeURIComponent(props.orchestratorProblemCards[0].id)}` : '/admin/llm'}
                                onClick={() => props.onOpenOrchestratorDetail(props.orchestratorProblemCards[0]?.id || 'problem', props.orchestratorProblemCards[0]?.detail || props.orchestratorProblemCards[0]?.metric || '오케스트레이터 경고 상세 이동', 'warning')}
                                className="rounded-lg border border-red-200 bg-white px-3 py-2 text-[11px] font-semibold text-red-700 hover:bg-red-100"
                            >
                                상세 원인 / 개선 실행 열기
                            </Link>
                        </div>
                        <div className="mt-4 grid gap-3 lg:grid-cols-2">
                            {props.selfRunFailureInsight && (
                                <div className={`rounded-xl border p-4 ${props.selfRunFailureInsight.severity === 'critical' ? 'border-red-200 bg-white text-red-800' : 'border-amber-200 bg-white text-amber-800'}`}>
                                    <div className="flex items-start justify-between gap-3">
                                        <div>
                                            <p className="text-sm font-semibold">자동 분류된 self-run 실패 원인</p>
                                            <p className="mt-1 text-xs opacity-80">{props.selfRunFailureInsight.title}</p>
                                        </div>
                                        <span className="rounded-full border border-current/20 px-2 py-1 text-[11px] font-semibold">{props.selfRunFailureInsight.category}</span>
                                    </div>
                                    <div className="mt-3 space-y-2 text-xs">
                                        <div className="rounded-lg bg-slate-50 px-3 py-2 text-slate-700"><span className="font-semibold text-slate-900">추정 원인:</span> {props.selfRunFailureInsight.reason}</div>
                                        <div className="rounded-lg bg-slate-50 px-3 py-2 text-slate-700"><span className="font-semibold text-slate-900">자동 개선:</span> {props.selfRunFailureInsight.automatedActions.join(' · ')}</div>
                                        <div className="rounded-lg bg-slate-50 px-3 py-2 text-slate-700">
                                            <span className="font-semibold text-slate-900">우선 수정 파일 경로:</span>
                                            <ul className="mt-2 list-disc space-y-1 pl-5">
                                                {props.selfRunFailureInsight.priorityFixPaths.map((path) => (
                                                    <li key={path} className="break-all">{path}</li>
                                                ))}
                                            </ul>
                                        </div>
                                        {!!(props.dashboardSelfRunStatus?.python_compile_failed_files || []).length && (
                                            <div className="rounded-lg bg-slate-50 px-3 py-2 text-slate-700">
                                                <span className="font-semibold text-slate-900">python_compile_failed_files:</span>
                                                <ul className="mt-2 list-disc space-y-1 pl-5">
                                                    {(props.dashboardSelfRunStatus?.python_compile_failed_files || []).map((path) => (
                                                        <li key={path} className="break-all">
                                                            <a href={props.toFileHref(path)} target="_blank" rel="noreferrer" className="font-medium text-blue-700 underline underline-offset-2 hover:text-blue-800">{path}</a>
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                        {(props.dashboardSelfRunStatus?.analysis_abs_path || props.dashboardSelfRunStatus?.root_cause_report_abs_path) && (
                                            <div className="rounded-lg bg-slate-50 px-3 py-2 text-slate-700">
                                                <span className="font-semibold text-slate-900">Python 정적 진단 경로:</span>
                                                <ul className="mt-2 list-disc space-y-1 pl-5">
                                                    {props.dashboardSelfRunStatus?.analysis_abs_path && <li className="break-all">analysis: {props.dashboardSelfRunStatus.analysis_abs_path}</li>}
                                                    {props.dashboardSelfRunStatus?.root_cause_report_abs_path && <li className="break-all">root_cause: {props.dashboardSelfRunStatus.root_cause_report_abs_path}</li>}
                                                </ul>
                                            </div>
                                        )}
                                        {props.dashboardSelfRunStatus?.runtime_diagnostic && (
                                            <div className="break-all rounded-lg bg-slate-50 px-3 py-2 text-slate-700"><span className="font-semibold text-slate-900">원본 진단:</span> {props.dashboardSelfRunStatus.runtime_diagnostic}</div>
                                        )}
                                    </div>
                                    <div className="mt-3 flex flex-wrap gap-2">
                                        <Link href={props.selfRunFailureInsight.guideHref} className="inline-flex rounded-lg border border-current/20 bg-white px-3 py-2 text-[11px] font-semibold hover:bg-slate-50">자동 개선 제어 열기</Link>
                                        <button type="button" onClick={props.onExecuteAutomaticRecovery} disabled={props.autoRecoveryRunning} className="inline-flex rounded-lg border border-current/20 bg-white px-3 py-2 text-[11px] font-semibold hover:bg-slate-50 disabled:opacity-50">
                                            {props.autoRecoveryRunning ? '자동 복구 실행 중...' : '실제 자동 복구 실행'}
                                        </button>
                                        <button type="button" onClick={props.onReloadDashboard} className="inline-flex rounded-lg border border-current/20 bg-white px-3 py-2 text-[11px] font-semibold hover:bg-slate-50">즉시 재진단</button>
                                    </div>
                                </div>
                            )}
                            {props.orchestratorProblemCards.map((card) => {
                                const actionGuide = props.getOrchestratorActionGuide(card.id);
                                const toneClassName = card.state === 'error' ? 'border-red-200 bg-white text-red-800' : 'border-amber-200 bg-white text-amber-800';
                                return (
                                    <div key={card.id} className={`rounded-xl border p-4 ${toneClassName}`}>
                                        <div className="flex items-start justify-between gap-3">
                                            <div>
                                                <p className="text-sm font-semibold">{card.title}</p>
                                                <p className="mt-1 text-xs opacity-80">{card.summary}</p>
                                            </div>
                                            <span className="rounded-full border border-current/20 px-2 py-1 text-[11px] font-semibold">{card.state}</span>
                                        </div>
                                        <div className="mt-3 space-y-2 text-xs">
                                            <div className="rounded-lg bg-slate-50 px-3 py-2 text-slate-700"><span className="font-semibold text-slate-900">근거 기준:</span> {card.metric}</div>
                                            {card.detail && <div className="rounded-lg bg-slate-50 px-3 py-2 text-slate-700"><span className="font-semibold text-slate-900">직접 원인:</span> {card.detail}</div>}
                                            {card.id === 'security-guard' && props.securityGuardDetailSections.findings.length > 0 && (
                                                <div className="rounded-lg bg-slate-50 px-3 py-2 text-slate-700">
                                                    <span className="font-semibold text-slate-900">Security Guard detail:</span>
                                                    <ul className="mt-2 list-disc space-y-1 pl-5">
                                                        {props.securityGuardDetailSections.findings.slice(0, 4).map((item, index) => (
                                                            <li key={`${item.label}-${index}`} className="break-all">{String(item.value)}{item.note ? ` · ${item.note}` : ''}</li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            )}
                                            {card.id === 'security-guard' && props.securityGuardDetailSections.pythonRules.length > 0 && (
                                                <div className="rounded-lg bg-slate-50 px-3 py-2 text-slate-700">
                                                    <span className="font-semibold text-slate-900">rule/path:</span>
                                                    <ul className="mt-2 list-disc space-y-1 pl-5">
                                                        {props.securityGuardDetailSections.pythonRules.slice(0, 6).map((item, index) => (
                                                            <li key={`${item.label}-${index}`} className="break-all">
                                                                <span className="mr-2 rounded-full border border-slate-300 bg-white px-2 py-0.5 text-[10px] font-semibold text-slate-700">우선순위 {index + 1}</span>
                                                                {String(item.value)}{item.note ? ` | ${item.note}` : ''}
                                                            </li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            )}
                                            <div className="rounded-lg bg-slate-50 px-3 py-2 text-slate-700"><span className="font-semibold text-slate-900">다음 개선:</span> {actionGuide.summary}</div>
                                        </div>
                                        <div className="mt-3">
                                            <Link href={actionGuide.href} className="inline-flex rounded-lg border border-current/20 bg-white px-3 py-2 text-[11px] font-semibold hover:bg-slate-50">{actionGuide.title}</Link>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}
            </section>

            <section className="mb-8 grid grid-cols-1 gap-4 md:grid-cols-3">
                {props.systemResourceCards.map((card) => {
                    const toneClassName = card.state === 'critical'
                        ? 'border-red-200 bg-red-50 text-red-800'
                        : card.state === 'warning'
                            ? 'border-amber-200 bg-amber-50 text-amber-800'
                            : 'border-emerald-200 bg-emerald-50 text-emerald-800';
                    const badgeClassName = card.state === 'critical'
                        ? 'bg-red-100 text-red-700 border-red-200'
                        : card.state === 'warning'
                            ? 'bg-amber-100 text-amber-700 border-amber-200'
                            : 'bg-emerald-100 text-emerald-700 border-emerald-200';
                    return (
                        <div key={card.id} className={`rounded-xl border p-5 ${toneClassName}`}>
                            <div className="flex items-start justify-between gap-3">
                                <div>
                                    <p className="text-sm font-semibold">{card.icon} {card.title} 램프</p>
                                    <p className="mt-1 text-[11px] opacity-80">근거 API: {card.apiPath}</p>
                                    <p className="mt-2 text-2xl font-bold leading-none">{card.value}</p>
                                </div>
                                <span className={`rounded-full border px-2 py-1 text-[11px] font-semibold ${badgeClassName}`}>
                                    {card.state === 'critical' ? '오류' : card.state === 'warning' ? '주의' : '정상'}
                                </span>
                            </div>
                            <p className="mt-3 text-sm">원인: {card.detail}</p>
                            <div className="mt-3 rounded-lg bg-white/70 px-3 py-2 text-xs">개선 방안: {card.action}</div>
                        </div>
                    );
                })}
            </section>

            {!!props.healthAlerts.length && (
                <section className="mb-8 rounded-xl border border-amber-200 bg-amber-50 p-5 text-amber-900">
                    <div className="flex items-center justify-between gap-3">
                        <div>
                            <h2 className="text-lg font-semibold">🩺 헬스 경고 원인 분석</h2>
                            <p className="mt-1 text-sm text-amber-800/80">warning/critical 헬스 항목을 운영자 관점의 원인과 우선 조치 기준으로 다시 정리했습니다.</p>
                        </div>
                        <a href={`${props.apiBaseUrl}/api/health`} target="_blank" rel="noreferrer" className="rounded-lg border border-amber-300 bg-white px-3 py-2 text-xs font-semibold text-amber-800 hover:bg-amber-100">원본 health 열기</a>
                    </div>
                    <div className="mt-4 grid gap-3 lg:grid-cols-2">
                        {props.healthAlerts.map((alert) => {
                            const metrics = Object.entries(props.getHealthAlertMetrics(alert)).slice(0, 4);
                            return (
                                <div key={alert.id} className="rounded-xl border border-amber-200 bg-white px-4 py-3 text-sm text-amber-900">
                                    <div className="flex items-start justify-between gap-3">
                                        <div>
                                            <p className="font-semibold">{alert.title}</p>
                                            <p className="mt-1 text-xs text-amber-800/80">현재 증상: {alert.message}</p>
                                        </div>
                                        <span className="rounded-full border border-amber-300 px-2 py-1 text-[11px] font-semibold">{alert.severity}</span>
                                    </div>
                                    <div className="mt-3 space-y-2 text-xs">
                                        <div className="rounded-lg bg-amber-50 px-3 py-2"><span className="font-semibold">원인 분석:</span> {props.getHealthAlertRootCause(alert)}</div>
                                        <div className="rounded-lg bg-amber-50 px-3 py-2"><span className="font-semibold">우선 조치:</span> {alert.action}</div>
                                        {!!metrics.length && (
                                            <div className="rounded-lg bg-amber-50 px-3 py-2">
                                                <p className="font-semibold">영향 지표</p>
                                                <div className="mt-2 flex flex-wrap gap-2">
                                                    {metrics.map(([key, value]) => (
                                                        <span key={`${alert.id}-${key}`} className="rounded-full border border-amber-200 bg-white px-2 py-1 text-[11px]">
                                                            {props.formatHealthMetricLabel(key)} {props.formatHealthMetricValue(key, value)}
                                                        </span>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                        <details className="break-all rounded-lg bg-amber-50 px-3 py-2">
                                            <summary className="cursor-pointer font-semibold">기술 세부정보</summary>
                                            <div className="mt-2 space-y-2">
                                                <div><span className="font-semibold">source_path:</span> {alert.source_path || '/api/health'}</div>
                                                <div><span className="font-semibold">diagnostic_detail:</span> {alert.diagnostic_detail || alert.action}</div>
                                            </div>
                                        </details>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </section>
            )}

            <section className="mb-8 grid grid-cols-1 gap-4 lg:grid-cols-3">
                <div className="rounded-xl border bg-white p-5 lg:col-span-2">
                    <div className="mb-3 flex items-center justify-between">
                        <h2 className="text-lg font-semibold text-gray-900">🚨 운영 알림</h2>
                        <span className="text-xs text-gray-500">실시간 점검 신호</span>
                    </div>
                    {props.opsAlerts.length === 0 ? (
                        <p className="text-sm text-green-600">✅ 현재 감지된 운영 리스크가 없습니다.</p>
                    ) : (
                        <ul className="space-y-2">
                            {props.opsAlerts.map((alert) => (
                                <li key={alert.id} className={`rounded-lg border px-3 py-2 text-sm ${alert.level === 'critical' ? 'border-red-200 bg-red-50 text-red-700' : 'border-amber-200 bg-amber-50 text-amber-700'}`}>
                                    <p className="font-semibold">{alert.level === 'critical' ? '🛑' : '⚠️'} {alert.title}</p>
                                    <p className="mt-1 text-[11px] opacity-80">근거 API: {alert.apiPath}</p>
                                    <p className="mt-1">원인: {alert.message}</p>
                                    <p className="mt-1 text-xs opacity-80">개선: {alert.action}</p>
                                </li>
                            ))}
                        </ul>
                    )}
                </div>
                <div className="rounded-xl border bg-white p-5">
                    <h2 className="mb-3 text-lg font-semibold text-gray-900">🧩 관리자 액션</h2>
                    <div className="space-y-2">
                        <button type="button" onClick={props.onImmediateRefresh} className="w-full rounded-lg bg-blue-600 py-2.5 text-sm font-medium text-white hover:bg-blue-700">즉시 상태 재수집</button>
                        <Link href="/admin/users" className="block w-full rounded-lg border border-gray-300 py-2.5 text-center text-sm font-medium text-gray-700 hover:bg-gray-50">사용자 관리 이동</Link>
                        <a href={`${props.apiBaseUrl}/api/health`} target="_blank" rel="noreferrer" className="block w-full rounded-lg border border-gray-300 py-2.5 text-center text-sm font-medium text-gray-700 hover:bg-gray-50">Health API 열기</a>
                    </div>
                    <div className="mt-4 space-y-2 border-t pt-4">
                        <div className="flex items-center justify-between">
                            <span className="text-sm text-gray-600">경고 음성</span>
                            <button type="button" onClick={props.onToggleVoiceAlertEnabled} className={`rounded-full px-3 py-1 text-xs font-semibold ${props.voiceAlertEnabled ? 'bg-rose-100 text-rose-700' : 'bg-gray-100 text-gray-600'}`}>
                                {props.voiceAlertEnabled ? '음성 ON' : '음성 OFF'}
                            </button>
                        </div>
                        <button type="button" onClick={props.onSpeakAdminAlert} className="w-full rounded-lg border border-gray-300 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50">현재 경고 음성 재생</button>
                        <div className="flex items-center justify-between">
                            <span className="text-sm text-gray-600">실시간 보기</span>
                            <button type="button" onClick={props.onToggleAutoRefreshEnabled} className={`rounded-full px-3 py-1 text-xs font-semibold ${props.autoRefreshEnabled ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
                                {props.autoRefreshEnabled ? 'ON' : 'OFF'}
                            </button>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="text-xs text-gray-500">주기</span>
                            <select value={props.refreshSeconds} onChange={(event) => props.onRefreshSecondsChange(Number(event.target.value))} className="rounded-md border border-gray-300 px-2 py-1 text-xs" disabled={!props.autoRefreshEnabled} title="실시간 갱신 주기">
                                <option value={10}>10초</option>
                                <option value={20}>20초</option>
                                <option value={30}>30초</option>
                                <option value={60}>60초</option>
                            </select>
                            {props.refreshing && <span className="text-xs text-blue-600">갱신 중...</span>}
                        </div>
                        <p className="text-xs text-gray-500">마지막 동기화: {props.lastUpdated || '-'}</p>
                    </div>
                </div>
            </section>
        </>
    );
}

'use client';

import * as React from 'react';
import SharedOrchestratorFollowUpCard from '../../shared/orchestrator-follow-up-card';
import { buildFollowUpPriorityScore } from '../../shared/orchestrator-follow-up-history';

type OrchestratorCapabilityState = 'standby' | 'active' | 'warning' | 'error';
type CapabilitySyncPhase = 'live' | 'confirming' | 'stale' | 'retrying';

export type CapabilityPanelPreset = {
    id: string;
    title: string;
    mode: string;
    task: string;
    description: string;
    flowId?: string;
    stepId?: string;
    action?: string;
    autoRun?: boolean;
};

export type CapabilityPanelAction = {
    id: string;
    title: string;
    summary: string;
    presetId: string;
    task: string;
    accentClassName: string;
};

export type CapabilityPanelGroup = {
    id: string;
    title: string;
    description: string;
    accentClassName: string;
    actions: CapabilityPanelAction[];
};

export type CapabilityPanelSummaryCard = {
    id: string;
    title: string;
    group_id: string;
    state: OrchestratorCapabilityState;
    state_label?: string | null;
    state_reason?: string | null;
    summary: string;
    metric: string;
    detail?: string | null;
    attention_required?: boolean;
    staleness_label?: string | null;
    last_run_started_at?: string | null;
    last_run_finished_at?: string | null;
    last_run_age_hours?: number | null;
    evidence_digest?: {
        completion_gate_ok?: boolean | null;
        self_run_status?: string | null;
        failure_tag_count?: number;
        target_file_id_count?: number;
        operational_target_count?: number;
        operational_verified_count?: number;
        operational_warning_count?: number;
        operational_failed_count?: number;
        operational_max_latency_ms?: number | null;
        priority_average_score?: number;
        priority_peak_score?: number;
        priority_latest_score?: number;
        priority_previous_score?: number | null;
        priority_momentum?: number;
        priority_cumulative_score?: number;
        priority_approval_gate_ok?: boolean | null;
        priority_approval_failed_fields?: string[];
        priority_self_run_stage?: string | null;
        priority_hard_gate_failed_stages?: string[];
    };
};

export type CapabilityPanelGroupSummary = {
    id: string;
    title: string;
    state: OrchestratorCapabilityState;
    summary: string;
    active_count: number;
    standby_count?: number;
    warning_count: number;
    error_count: number;
};

type CapabilityPanelSectionItem = {
    label: string;
    value: string | number | boolean | null;
    note?: string | null;
};

type CapabilityPanelSection = {
    id: string;
    title: string;
    items: CapabilityPanelSectionItem[];
};

type CapabilityPanelOperationalTarget = {
    id?: string;
    status?: string;
    ok?: boolean;
    latency_ms?: number | null;
    latency_warning?: boolean;
    warning_threshold_ms?: number | null;
    verified_at?: string | null;
    target?: string | null;
    note?: string | null;
};

type CapabilityPanelOperationalEvidenceSummary = {
    verified_count?: number;
    warning_count?: number;
    failed_count?: number;
    required_count?: number;
    warning_targets?: string[];
    max_latency_ms?: number | null;
};

type CapabilityPanelOperationalLatencySummary = {
    latency_warning?: boolean;
    warning_targets?: string[];
    warning_threshold_ms?: Record<string, number>;
    max_latency_ms?: number | null;
    verified_count?: number;
    warning_count?: number;
    failed_count?: number;
    required_count?: number;
};

type CapabilityPanelTargetPatchEntry = {
    file_id?: string;
    path?: string;
    section_id?: string;
    feature_id?: string;
    chunk_id?: string;
    layer?: string;
    summary?: string;
    failure_tags?: string[];
    repair_tags?: string[];
};

type CapabilityPanelCanonicalEvidenceBindings = {
    completionGateOk: boolean | null | undefined;
    selfRunStatus: string | null | undefined;
    targetFileIds: string[];
    targetSectionIds: string[];
    targetFeatureIds: string[];
    targetChunkIds: string[];
    failureTags: string[];
    repairTags: string[];
    targetPatchEntries: CapabilityPanelTargetPatchEntry[];
    operationalSummary: CapabilityPanelOperationalEvidenceSummary;
    operationalLatency: CapabilityPanelOperationalLatencySummary;
};

function buildCanonicalEvidenceBindings(detail: CapabilityPanelDetailResponse | null): CapabilityPanelCanonicalEvidenceBindings {
    const selectiveApplyEvidence = detail?.evidence_bundle?.selective_apply;
    const executionEvidence = detail?.evidence_bundle?.execution;
    const readinessEvidence = detail?.evidence_bundle?.readiness;
    return {
        completionGateOk: executionEvidence?.completion_gate_ok,
        selfRunStatus: executionEvidence?.self_run_status,
        targetFileIds: selectiveApplyEvidence?.target_file_ids || detail?.target_file_ids || [],
        targetSectionIds: selectiveApplyEvidence?.target_section_ids || detail?.target_section_ids || [],
        targetFeatureIds: selectiveApplyEvidence?.target_feature_ids || detail?.target_feature_ids || [],
        targetChunkIds: selectiveApplyEvidence?.target_chunk_ids || detail?.target_chunk_ids || [],
        failureTags: selectiveApplyEvidence?.failure_tags || detail?.failure_tags || [],
        repairTags: selectiveApplyEvidence?.repair_tags || detail?.repair_tags || [],
        targetPatchEntries: selectiveApplyEvidence?.target_patch_entries || detail?.target_patch_entries || [],
        operationalSummary: readinessEvidence?.operational_evidence_summary || {},
        operationalLatency: readinessEvidence?.operational_latency_summary || {},
    };
}

export type CapabilityPanelValidationFinding = {
    id: string;
    severity: string;
    title: string;
    problem: string;
    wrong_expression: string;
    improvement: string;
    source_path: string;
    file_evidence?: Array<{
        path: string;
        line_start: number;
        line_end: number;
        summary: string;
        snippet: string;
    }>;
};

export type CapabilityPanelCodeExample = {
    id: string;
    title: string;
    language: string;
    path: string;
    summary: string;
    code: string;
};

export type CapabilityPanelDetailResponse = {
    generated_at: string;
    capability: CapabilityPanelSummaryCard;
    highlights: string[];
    suggested_actions: string[];
    sections: CapabilityPanelSection[];
    evidence_bundle?: {
        contract?: {
            evidence_schema_version?: string;
            profile_id?: string;
            [key: string]: unknown;
        };
        execution?: {
            evidence_run_id?: string;
            evidence_generated_at?: string;
            completion_gate_ok?: boolean | null;
            self_run_status?: string | null;
            semantic_audit_ok?: boolean | null;
            [key: string]: unknown;
        };
        readiness?: {
            final_readiness_checklist_path?: string;
            automatic_validation_result_path?: string;
            output_audit_path?: string;
            operational_evidence_snapshot?: {
                targets?: CapabilityPanelOperationalTarget[];
                verified_target_count?: number;
                required_target_count?: number;
                warning_target_count?: number;
                failed_target_count?: number;
                summary?: CapabilityPanelOperationalEvidenceSummary;
                [key: string]: unknown;
            };
            operational_targets_by_id?: Record<string, CapabilityPanelOperationalTarget>;
            operational_evidence_summary?: CapabilityPanelOperationalEvidenceSummary;
            operational_latency_summary?: CapabilityPanelOperationalLatencySummary;
            documentation_sync?: Record<string, unknown>;
            [key: string]: unknown;
        };
        operations?: {
            canonical_source?: string;
            operational_evidence_deprecated?: boolean;
            [key: string]: unknown;
        };
        selective_apply?: {
            target_file_ids?: string[];
            target_section_ids?: string[];
            target_feature_ids?: string[];
            target_chunk_ids?: string[];
            failure_tags?: string[];
            repair_tags?: string[];
            target_patch_entries?: CapabilityPanelTargetPatchEntry[];
        };
    };
    target_file_ids?: string[];
    target_section_ids?: string[];
    target_feature_ids?: string[];
    target_chunk_ids?: string[];
    failure_tags?: string[];
    repair_tags?: string[];
    target_patch_entries?: CapabilityPanelTargetPatchEntry[];
    validation_findings: CapabilityPanelValidationFinding[];
    improvement_code_examples: CapabilityPanelCodeExample[];
    expansion_experiment?: {
        work_document_title?: string;
        work_document?: string;
        focus_path?: string;
        proposal_id?: string;
        tower_crane_options?: Array<Record<string, unknown>>;
        web_research?: Array<{ title?: string; url?: string; snippet?: string }>;
        recommended_self_run?: {
            mode?: string;
            execution_mode?: string;
            directive_template?: string;
            directive_scope?: string;
            directive_request?: string;
            endpoint?: string;
        };
    } | null;
};

export type CapabilityPanelExecutionComparison = {
    capabilityId: string;
    capturedAt: string;
    beforeDetail: CapabilityPanelDetailResponse | null;
    afterDetail: CapabilityPanelDetailResponse | null;
    runResult: {
        applied?: boolean;
        apply_error?: string | null;
        output_dir?: string | null;
        failed_output_dir?: string | null;
        pipeline?: string[];
        state_history?: string[];
        completion_gate_ok?: boolean | null;
        semantic_audit_ok?: boolean | null;
    } | null;
    selfRunResult?: {
        status: string;
        experiment_clone_path?: string | null;
        execution_mode?: string | null;
        orchestration_error?: string | null;
    } | null;
};

interface CapabilityPanelProps {
    presets: CapabilityPanelPreset[];
    selectedPresetId: string;
    onApplyPreset: (preset: CapabilityPanelPreset) => void;
    capabilityGroups: CapabilityPanelGroup[];
    capabilityGroupSummaryLookup: Map<string, CapabilityPanelGroupSummary>;
    capabilitySummaryLookup: Map<string, CapabilityPanelSummaryCard>;
    selectedCapabilityActionId: string;
    getLinkedPresetTitle: (presetId: string) => string;
    getCapabilityStateClassName: (state: OrchestratorCapabilityState | undefined) => string;
    getCapabilityStateText: (capability: CapabilityPanelSummaryCard | undefined) => string;
    onSelectCapabilityAction: (action: CapabilityPanelAction) => Promise<void>;
    onApplyCapabilityAction: (action: CapabilityPanelAction, execution: 'prepare' | 'run') => Promise<void>;
    loading: boolean;
    selfRunBusy: boolean;
    capabilityVoiceAlertEnabled: boolean;
    onToggleCapabilityVoiceAlert: () => void;
    onSpeakCapabilityAlert: () => void;
    onRefreshCapabilitySummary: () => Promise<unknown>;
    capabilityLoading: boolean;
    capabilityMessage: string;
    capabilitySyncPhase: CapabilitySyncPhase;
    capabilityLastLiveRefreshElapsedSec: number;
    capabilitySummaryGeneratedAt: string;
    capabilityDetail: CapabilityPanelDetailResponse | null;
    detailCapabilityAction: CapabilityPanelAction | null;
    activeCapabilityComparison: CapabilityPanelExecutionComparison | null;
    beforeComparisonErrors: number;
    beforeComparisonWarnings: number;
    afterComparisonErrors: number;
    afterComparisonWarnings: number;
    comparisonResolvedTitles: string[];
    comparisonNewTitles: string[];
    getCapabilityFindingRenderKey: (finding: CapabilityPanelValidationFinding, index: number) => string;
    getCapabilityCodeExampleRenderKey: (example: CapabilityPanelCodeExample, index: number) => string;
    buildSelfRunStatusLabel: (status: string) => string;
}

export default function CapabilityPanel({
    presets,
    selectedPresetId,
    onApplyPreset,
    capabilityGroups,
    capabilityGroupSummaryLookup,
    capabilitySummaryLookup,
    selectedCapabilityActionId,
    getLinkedPresetTitle,
    getCapabilityStateClassName,
    getCapabilityStateText,
    onSelectCapabilityAction,
    onApplyCapabilityAction,
    loading,
    selfRunBusy,
    capabilityVoiceAlertEnabled,
    onToggleCapabilityVoiceAlert,
    onSpeakCapabilityAlert,
    onRefreshCapabilitySummary,
    capabilityLoading,
    capabilityMessage,
    capabilitySyncPhase,
    capabilityLastLiveRefreshElapsedSec,
    capabilitySummaryGeneratedAt,
    capabilityDetail,
    detailCapabilityAction,
    activeCapabilityComparison,
    beforeComparisonErrors,
    beforeComparisonWarnings,
    afterComparisonErrors,
    afterComparisonWarnings,
    comparisonResolvedTitles,
    comparisonNewTitles,
    getCapabilityFindingRenderKey,
    getCapabilityCodeExampleRenderKey,
    buildSelfRunStatusLabel,
}: CapabilityPanelProps) {
    const canonicalEvidenceBindings = buildCanonicalEvidenceBindings(capabilityDetail);
    const completionGateOk = canonicalEvidenceBindings.completionGateOk;
    const selfRunStatus = canonicalEvidenceBindings.selfRunStatus;
    const targetFileIds = canonicalEvidenceBindings.targetFileIds;
    const targetSectionIds = canonicalEvidenceBindings.targetSectionIds;
    const targetFeatureIds = canonicalEvidenceBindings.targetFeatureIds;
    const targetChunkIds = canonicalEvidenceBindings.targetChunkIds;
    const failureTags = canonicalEvidenceBindings.failureTags;
    const repairTags = canonicalEvidenceBindings.repairTags;
    const contractEvidence = capabilityDetail?.evidence_bundle?.contract || {};
    const executionEvidence = capabilityDetail?.evidence_bundle?.execution || {};
    const readinessEvidence = capabilityDetail?.evidence_bundle?.readiness || {};
    const operationsEvidence = capabilityDetail?.evidence_bundle?.operations || {};
    const operationalEvidenceSummary = canonicalEvidenceBindings.operationalSummary;
    const operationalLatencySummary = canonicalEvidenceBindings.operationalLatency;
    const targetPatchEntries = canonicalEvidenceBindings.targetPatchEntries;
    const pythonSecurityFindings = capabilityDetail?.validation_findings.filter(
        (finding) => finding.id.includes('python-policy') || finding.title.includes('Python 보안'),
    ) || [];
    const pythonSecurityErrors = pythonSecurityFindings.filter((finding) => finding.severity === 'error').length;
    const pythonSecurityWarnings = pythonSecurityFindings.filter((finding) => finding.severity === 'warning').length;
    const priorityScore = Math.max(0, Math.min(100,
        (beforeComparisonErrors * 25)
        + (beforeComparisonWarnings * 10)
        + (failureTags.length * 8)
        + (targetFileIds.length * 5)
        - (comparisonResolvedTitles.length * 12)
        - Math.max(0, beforeComparisonErrors - afterComparisonErrors) * 18,
    ));
    const sharedRecommendations = capabilityDetail?.suggested_actions.slice(0, 4).map((item, index) => ({
        id: `admin-follow-up-${index}`,
        label: `후속 제안 ${index + 1}`,
        detail: item,
    })) || [];
    const historyStats = {
        averageScore: capabilityDetail?.capability?.evidence_digest?.priority_average_score ?? priorityScore,
        peakScore: capabilityDetail?.capability?.evidence_digest?.priority_peak_score ?? priorityScore,
        latestScore: capabilityDetail?.capability?.evidence_digest?.priority_latest_score ?? priorityScore,
        previousScore: capabilityDetail?.capability?.evidence_digest?.priority_previous_score ?? null,
        momentum: capabilityDetail?.capability?.evidence_digest?.priority_momentum ?? 0,
        cumulativeScore: capabilityDetail?.capability?.evidence_digest?.priority_cumulative_score ?? priorityScore,
    };
    const approvalFailedFields = capabilityDetail?.capability?.evidence_digest?.priority_approval_failed_fields || [];
    const hardGateFailedStages = capabilityDetail?.capability?.evidence_digest?.priority_hard_gate_failed_stages || [];
    const followUpPriority = buildFollowUpPriorityScore({
        severity: Math.min(100, (beforeComparisonErrors * 28) + (failureTags.length * 10)),
        recency: capabilityDetail?.capability?.evidence_digest?.priority_latest_score ?? priorityScore,
        approvalRisk: Math.min(100, approvalFailedFields.length * 25),
        hardGateImpact: Math.min(100, hardGateFailedStages.length * 25),
        operationalRisk: Math.min(100, ((capabilityDetail?.capability?.evidence_digest?.operational_failed_count ?? 0) * 22) + ((capabilityDetail?.capability?.evidence_digest?.operational_warning_count ?? 0) * 12)),
        selfRunPriority: capabilityDetail?.capability?.evidence_digest?.priority_self_run_stage ? 80 : 20,
    });
    const syncPhaseBadge = (() => {
        if (capabilitySyncPhase === 'confirming') {
            return {
                label: 'confirming',
                description: 'pending_approval 해제 확인 중',
                className: 'border-[#d29922] bg-[rgba(210,153,34,0.14)] text-[#f2cc60]',
            };
        }
        if (capabilitySyncPhase === 'stale') {
            return {
                label: 'stale',
                description: 'live 응답 지연 감지',
                className: 'border-[#f78166] bg-[rgba(248,81,73,0.14)] text-[#ffb3ad]',
            };
        }
        if (capabilitySyncPhase === 'retrying') {
            return {
                label: 'retrying',
                description: '재조회 실패 후 재시도 중',
                className: 'border-[#8b949e] bg-[rgba(139,148,158,0.18)] text-[#c9d1d9]',
            };
        }
        return {
            label: 'live',
            description: 'live API 기준 최신 상태',
            className: 'border-[#238636] bg-[rgba(35,134,54,0.16)] text-[#9be9a8]',
        };
    })();
    const liveElapsedLabel = capabilityLastLiveRefreshElapsedSec > 0
        ? `${capabilityLastLiveRefreshElapsedSec}초 전`
        : '방금';
    const serverSnapshotLabel = String(capabilitySummaryGeneratedAt || '').trim() || '-';
    const expansionExperiment = capabilityDetail?.expansion_experiment || null;
    const showExpansionExperimentPanel = detailCapabilityAction?.id === 'code-generator' && Boolean(expansionExperiment?.work_document);

    return (
        <div className="mb-4 rounded-xl border border-[#30363d] bg-[#161b22] p-5">
            <div className="mb-[14px]">
                <div className="mb-4 rounded-lg border border-[#30363d] bg-[#0d1117] p-4">
                    <div className="mb-3 flex flex-wrap items-center gap-2">
                        {presets.map((preset) => (
                            <button
                                key={preset.id}
                                type="button"
                                onClick={() => onApplyPreset(preset)}
                                className={`rounded-lg px-4 py-2 text-sm font-semibold ${selectedPresetId === preset.id ? 'bg-[#1f6feb] text-white' : 'bg-[#21262d] text-[#8b949e]'}`}
                            >
                                {preset.title}
                            </button>
                        ))}
                    </div>
                    <p className="text-xs text-[#8b949e]">
                        {selectedPresetId
                            ? `${presets.find((preset) => preset.id === selectedPresetId)?.title}: ${presets.find((preset) => preset.id === selectedPresetId)?.description || ''}`
                            : '자가진단, 자가개선, 자가확장 중 하나를 선택해 프리셋을 적용할 수 있습니다.'}
                    </p>
                    <div className="mt-4 grid gap-3 xl:grid-cols-3">
                        {capabilityGroups.map((group) => {
                            const groupSummary = capabilityGroupSummaryLookup.get(group.id);
                            const groupStateClassName = getCapabilityStateClassName(groupSummary?.state);
                            return (
                                <div key={group.id} className={`rounded-xl border p-4 ${group.accentClassName}`}>
                                    <div className={`mb-3 rounded-lg border px-3 py-2 text-xs ${groupStateClassName}`}>
                                        <div className="flex items-center justify-between gap-2">
                                            <span className="font-semibold">{groupSummary?.title || group.title}</span>
                                            <span>{groupSummary?.state || 'standby'}</span>
                                        </div>
                                        <p className="mt-1 opacity-90">{groupSummary?.summary || '기능군 상태 수집 대기 중'}</p>
                                    </div>
                                    <div className="mb-3 flex items-start justify-between gap-3">
                                        <div>
                                            <p className="text-sm font-semibold text-[#e6edf3]">{group.title}</p>
                                            <p className="mt-1 text-xs text-[#8b949e]">{group.description}</p>
                                        </div>
                                        <span className="rounded-full border border-[#30363d] px-2 py-1 text-[10px] font-semibold text-[#8b949e]">
                                            기능별 분리
                                        </span>
                                    </div>
                                    <div className="space-y-3">
                                        {group.actions.map((action) => {
                                            const active = selectedCapabilityActionId === action.id;
                                            const capabilityStatus = capabilitySummaryLookup.get(action.id);
                                            const capabilityStateClassName = getCapabilityStateClassName(capabilityStatus?.state);
                                            return (
                                                <div
                                                    key={action.id}
                                                    className={`rounded-lg border bg-[#0d1117] p-3 ${active ? action.accentClassName : 'border-[#30363d] text-[#e6edf3]'}`}
                                                >
                                                    <div className="flex items-start justify-between gap-3">
                                                        <div>
                                                            <p className="text-sm font-semibold text-[#e6edf3]">{action.title}</p>
                                                            <p className="mt-1 text-xs text-[#8b949e]">{action.summary}</p>
                                                        </div>
                                                        <span className="rounded-full border border-[#30363d] px-2 py-1 text-[10px] font-semibold text-[#8b949e]">
                                                            {getLinkedPresetTitle(action.presetId)}
                                                        </span>
                                                    </div>
                                                    <div className={`mt-3 rounded-lg border px-3 py-2 text-[11px] ${capabilityStateClassName}`}>
                                                        <div className="flex items-center justify-between gap-2">
                                                            <span className="font-semibold">{getCapabilityStateText(capabilityStatus)}</span>
                                                            <span>{capabilityStatus?.metric || '구조화 결과 대기'}</span>
                                                        </div>
                                                        <div className="mt-2 flex flex-wrap gap-2 text-[10px]">
                                                            <span className="rounded-full border border-[#30363d] bg-[#11161d] px-2 py-1 text-[#c9d1d9]">
                                                                completion_gate_ok {typeof capabilityStatus?.evidence_digest?.completion_gate_ok === 'boolean' ? (capabilityStatus.evidence_digest.completion_gate_ok ? 'pass' : 'fail') : 'unknown'}
                                                            </span>
                                                            <span className="rounded-full border border-[#30363d] bg-[#11161d] px-2 py-1 text-[#c9d1d9]">
                                                                self_run_status {capabilityStatus?.evidence_digest?.self_run_status || 'unknown'}
                                                            </span>
                                                            <span className="rounded-full border border-[#30363d] bg-[#11161d] px-2 py-1 text-[#c9d1d9]">
                                                                failure_tags {capabilityStatus?.evidence_digest?.failure_tag_count ?? 0}
                                                            </span>
                                                            <span className="rounded-full border border-[#30363d] bg-[#11161d] px-2 py-1 text-[#c9d1d9]">
                                                                target_file_ids {capabilityStatus?.evidence_digest?.target_file_id_count ?? 0}
                                                            </span>
                                                            <span className="rounded-full border border-[#30363d] bg-[#11161d] px-2 py-1 text-[#c9d1d9]">
                                                                operational_evidence {(capabilityStatus?.evidence_digest?.operational_verified_count ?? 0)}/{capabilityStatus?.evidence_digest?.operational_target_count ?? 0}
                                                            </span>
                                                            <span className="rounded-full border border-[#30363d] bg-[#11161d] px-2 py-1 text-[#c9d1d9]">
                                                                operational_warning {capabilityStatus?.evidence_digest?.operational_warning_count ?? 0}
                                                            </span>
                                                            <span className="rounded-full border border-[#30363d] bg-[#11161d] px-2 py-1 text-[#c9d1d9]">
                                                                operational_failed {capabilityStatus?.evidence_digest?.operational_failed_count ?? 0}
                                                            </span>
                                                        </div>
                                                        <p className="mt-1">{capabilityStatus?.summary || '백엔드 능력 API를 아직 조회하지 않았습니다.'}</p>
                                                        {capabilityStatus?.detail && (
                                                            <p className="mt-1 opacity-90">{capabilityStatus.detail}</p>
                                                        )}
                                                        {(capabilityStatus?.state_reason || capabilityStatus?.staleness_label) && (
                                                            <p className="mt-1 opacity-80">
                                                                {[capabilityStatus?.state_reason, capabilityStatus?.staleness_label].filter(Boolean).join(' · ')}
                                                            </p>
                                                        )}
                                                    </div>
                                                    <div className="mt-3 flex flex-wrap gap-2">
                                                        <button
                                                            type="button"
                                                            onClick={() => void onSelectCapabilityAction(action)}
                                                            className={`rounded-lg border px-3 py-2 text-xs font-semibold ${active ? 'border-[#1f6feb] bg-[rgba(31,111,235,0.16)] text-[#9ecbff]' : 'border-[#30363d] bg-[#161b22] text-[#c9d1d9]'}`}
                                                        >
                                                            {active ? '상세 선택됨' : '상세 보기'}
                                                        </button>
                                                        <button
                                                            type="button"
                                                            onClick={() => void onApplyCapabilityAction(action, 'prepare')}
                                                            className="rounded-lg border border-[#30363d] bg-[#161b22] px-3 py-2 text-xs font-semibold text-[#e6edf3]"
                                                        >
                                                            작업문 적용
                                                        </button>
                                                        <button
                                                            type="button"
                                                            onClick={() => void onApplyCapabilityAction(action, 'run')}
                                                            disabled={loading || selfRunBusy}
                                                            className={`rounded-lg px-3 py-2 text-xs font-semibold text-white ${(loading || selfRunBusy) && selectedCapabilityActionId === action.id ? 'bg-[#21262d]' : 'bg-[#238636]'}`}
                                                        >
                                                            {(loading || selfRunBusy) && selectedCapabilityActionId === action.id ? '실행 중...' : '즉시 실행'}
                                                        </button>
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                    <div className="mt-4 rounded-lg border border-[#30363d] bg-[#11161d] p-4">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                            <div>
                                <p className="text-sm font-semibold text-[#e6edf3]">기능별 구조화 결과</p>
                                <p className="mt-1 text-xs text-[#8b949e]">선택한 기능 카드의 실제 백엔드 능력 응답을 섹션형으로 표시합니다.</p>
                            </div>
                            <div className="flex flex-wrap items-center gap-2">
                                <div className={`rounded-full border px-3 py-1 text-[11px] font-semibold ${syncPhaseBadge.className}`}>
                                    <span>{syncPhaseBadge.label}</span>
                                    <span className="ml-2 opacity-90">{syncPhaseBadge.description}</span>
                                    <span className="ml-2 opacity-75">(client {liveElapsedLabel} · server {serverSnapshotLabel})</span>
                                </div>
                                <button
                                    type="button"
                                    onClick={onToggleCapabilityVoiceAlert}
                                    className={`rounded-lg px-3 py-2 text-xs font-semibold ${capabilityVoiceAlertEnabled ? 'bg-[rgba(248,81,73,0.15)] text-[#ffb3ad]' : 'bg-[#161b22] text-[#8b949e]'}`}
                                >
                                    {capabilityVoiceAlertEnabled ? '경고 음성 ON' : '경고 음성 OFF'}
                                </button>
                                <button
                                    type="button"
                                    onClick={onSpeakCapabilityAlert}
                                    className="rounded-lg border border-[#30363d] bg-[#161b22] px-3 py-2 text-xs font-semibold text-[#e6edf3]"
                                >
                                    현재 경고 음성 재생
                                </button>
                                <button
                                    type="button"
                                    onClick={() => void onRefreshCapabilitySummary()}
                                    disabled={capabilityLoading}
                                    className={`rounded-lg px-3 py-2 text-xs font-semibold text-white ${capabilityLoading ? 'bg-[#21262d]' : 'bg-[#1f6feb]'}`}
                                >
                                    {capabilityLoading ? '수집 중...' : '요약 새로고침'}
                                </button>
                            </div>
                        </div>
                        {capabilityMessage && (
                            <p className="mt-3 text-sm text-[#f78166]">{capabilityMessage}</p>
                        )}
                        {capabilityDetail ? (
                            <div className="mt-4 space-y-4">
                                {showExpansionExperimentPanel && detailCapabilityAction && (
                                    <div className="rounded-lg border border-[#1f6feb] bg-[rgba(31,111,235,0.08)] p-4">
                                        <div className="flex flex-wrap items-start justify-between gap-3">
                                            <div>
                                                <p className="text-sm font-semibold text-[#9ecbff]">
                                                    {expansionExperiment?.work_document_title || '확장 실험 작업문'}
                                                </p>
                                                <p className="mt-1 text-xs text-[#8b949e]">
                                                    PowerShell 명령이 아닙니다. 아래 버튼으로 API(self-expansion / full)를 호출합니다.
                                                </p>
                                                <p className="mt-2 text-xs text-[#c9d1d9]">
                                                    focus: {expansionExperiment?.focus_path || '-'}
                                                    {' · '}
                                                    Tower {(expansionExperiment?.tower_crane_options || []).length}옵션
                                                    {' · '}
                                                    웹 {(expansionExperiment?.web_research || []).length}건
                                                </p>
                                            </div>
                                            <div className="flex flex-wrap gap-2">
                                                <button
                                                    type="button"
                                                    onClick={() => void onApplyCapabilityAction(detailCapabilityAction, 'prepare')}
                                                    className="rounded-lg border border-[#30363d] bg-[#161b22] px-3 py-2 text-xs font-semibold text-[#e6edf3]"
                                                >
                                                    작업문만 적용
                                                </button>
                                                <button
                                                    type="button"
                                                    onClick={() => void onApplyCapabilityAction(detailCapabilityAction, 'run')}
                                                    disabled={loading || selfRunBusy}
                                                    className={`rounded-lg px-3 py-2 text-xs font-semibold text-white ${(loading || selfRunBusy) ? 'bg-[#21262d]' : 'bg-[#1f6feb]'}`}
                                                >
                                                    {(loading || selfRunBusy) ? 'self-expansion 실행 중...' : '확장 실험 self-expansion 실행'}
                                                </button>
                                            </div>
                                        </div>
                                        <pre className="mt-3 max-h-48 overflow-auto whitespace-pre-wrap rounded-lg border border-[#30363d] bg-[#0d1117] p-3 text-[11px] leading-5 text-[#c9d1d9]">
                                            {String(expansionExperiment?.work_document || '').slice(0, 2400)}
                                        </pre>
                                    </div>
                                )}
                                {pythonSecurityFindings.length > 0 && (
                                    <div className="rounded-lg border border-[#f78166] bg-[#2d1412] p-4">
                                        <div className="flex flex-wrap items-center justify-between gap-3">
                                            <div>
                                                <p className="text-sm font-semibold text-[#ffb4a1]">Python Security Validation 경광판</p>
                                                <p className="mt-1 text-xs text-[#ffd8cc]">검출된 보안 위반 원인을 즉시 개선 실행 작업문에 함께 전달합니다.</p>
                                            </div>
                                            <div className="text-right text-xs text-[#ffd8cc]">
                                                <p>오류 {pythonSecurityErrors}건</p>
                                                <p className="mt-1">경고 {pythonSecurityWarnings}건</p>
                                            </div>
                                        </div>
                                        <ul className="mt-3 space-y-2 text-xs text-[#ffe2d8]">
                                            {pythonSecurityFindings.slice(0, 3).map((finding, index) => (
                                                <li key={`${finding.id}-alarm-${index}`}>• {finding.title} · {finding.problem}</li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                                <div className="rounded-lg border border-[#30363d] bg-[#0d1117] p-4">
                                    <div className="flex flex-wrap items-center justify-between gap-3">
                                        <div>
                                            <p className="text-sm font-semibold text-[#e6edf3]">{capabilityDetail.capability.title}</p>
                                            <p className="mt-1 text-xs text-[#8b949e]">{capabilityDetail.capability.summary}</p>
                                        </div>
                                        <div className="text-right text-xs text-[#8b949e]">
                                            <p>{capabilityDetail.capability.metric}</p>
                                            {capabilityDetail.capability.detail && <p className="mt-1">{capabilityDetail.capability.detail}</p>}
                                        </div>
                                    </div>
                                    <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
                                        <span className="rounded-full border border-[#30363d] bg-[#11161d] px-3 py-1 text-[#c9d1d9]">
                                            completion_gate_ok {typeof completionGateOk === 'boolean' ? (completionGateOk ? 'pass' : 'fail') : 'unknown'}
                                        </span>
                                        <span className="rounded-full border border-[#30363d] bg-[#11161d] px-3 py-1 text-[#c9d1d9]">
                                            self_run_status {String(selfRunStatus || 'unknown')}
                                        </span>
                                        <span className="rounded-full border border-[#30363d] bg-[#11161d] px-3 py-1 text-[#c9d1d9]">
                                            failure_tags {failureTags.length}
                                        </span>
                                        <span className="rounded-full border border-[#30363d] bg-[#11161d] px-3 py-1 text-[#c9d1d9]">
                                            target_file_ids {targetFileIds.length}
                                        </span>
                                        <span className="rounded-full border border-[#30363d] bg-[#11161d] px-3 py-1 text-[#c9d1d9]">
                                            target_feature_ids {targetFeatureIds.length}
                                        </span>
                                        <span className="rounded-full border border-[#30363d] bg-[#11161d] px-3 py-1 text-[#c9d1d9]">
                                            repair_tags {repairTags.length}
                                        </span>
                                    </div>
                                    {detailCapabilityAction && (
                                        <div className="mt-3 flex flex-wrap gap-2">
                                            <button
                                                type="button"
                                                onClick={() => void onApplyCapabilityAction(detailCapabilityAction, 'prepare')}
                                                disabled={loading}
                                                className={`rounded-lg px-3 py-2 text-xs font-semibold ${loading && selectedCapabilityActionId === detailCapabilityAction.id ? 'bg-[#161b22] text-[#8b949e]' : 'border border-[#30363d] bg-[#11161d] text-[#c9d1d9]'}`}
                                            >
                                                작업문 반영
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => void onApplyCapabilityAction(detailCapabilityAction, 'run')}
                                                disabled={loading || selfRunBusy}
                                                className={`rounded-lg px-3 py-2 text-xs font-semibold text-white ${(loading || selfRunBusy) && selectedCapabilityActionId === detailCapabilityAction.id ? 'bg-[#21262d]' : 'bg-[#238636]'}`}
                                            >
                                                {(loading || selfRunBusy) && selectedCapabilityActionId === detailCapabilityAction.id ? '실행 중...' : '즉시 개선 실행'}
                                            </button>
                                        </div>
                                    )}
                                    <div className="mt-3 grid gap-2 lg:grid-cols-2">
                                        <div className="rounded-lg border border-[#30363d] bg-[#11161d] p-3">
                                            <p className="text-xs font-semibold text-[#79c0ff]">핵심 하이라이트</p>
                                            <ul className="mt-2 space-y-2 text-xs text-[#c9d1d9]">
                                                {capabilityDetail.highlights.map((item, index) => (
                                                    <li key={`${capabilityDetail.capability.id}-highlight-${index}`}>• {item}</li>
                                                ))}
                                            </ul>
                                        </div>
                                        <div className="rounded-lg border border-[#30363d] bg-[#11161d] p-3">
                                            <p className="text-xs font-semibold text-[#3fb950]">권장 후속 조치</p>
                                            <ul className="mt-2 space-y-2 text-xs text-[#c9d1d9]">
                                                {capabilityDetail.suggested_actions.map((item, index) => (
                                                    <li key={`${capabilityDetail.capability.id}-action-${index}`}>• {item}</li>
                                                ))}
                                            </ul>
                                        </div>
                                    </div>
                                    <SharedOrchestratorFollowUpCard
                                        tone="admin"
                                        title="공통 후속 제안 카드"
                                        summary="관리자/고객 오케스트레이터가 같은 기준으로 후속 제안과 우선순위를 표시합니다."
                                        scoreLabel="우선순위"
                                        scoreValue={historyStats.cumulativeScore}
                                        scoreAxes={[
                                            { id: 'severity', label: 'severity', score: followUpPriority.axes.severity, detail: `errors=${beforeComparisonErrors}, failure_tags=${failureTags.length}`, tone: beforeComparisonErrors > 0 || failureTags.length > 0 ? 'warning' : 'good' },
                                            { id: 'recency', label: 'recency', score: followUpPriority.axes.recency, detail: `latest score=${historyStats.latestScore}`, tone: historyStats.latestScore >= historyStats.averageScore ? 'warning' : 'neutral' },
                                            { id: 'approval_risk', label: 'approval_risk', score: followUpPriority.axes.approvalRisk, detail: `approval failed fields=${approvalFailedFields.join(', ') || '없음'}`, tone: approvalFailedFields.length > 0 ? 'warning' : 'good' },
                                            { id: 'hard_gate_impact', label: 'hard_gate_impact', score: followUpPriority.axes.hardGateImpact, detail: `hard gate failed stages=${hardGateFailedStages.join(', ') || '없음'}`, tone: hardGateFailedStages.length > 0 ? 'warning' : 'good' },
                                            { id: 'operational_risk', label: 'operational_risk', score: followUpPriority.axes.operationalRisk, detail: `operational failed=${capabilityDetail?.capability?.evidence_digest?.operational_failed_count ?? 0}, warning=${capabilityDetail?.capability?.evidence_digest?.operational_warning_count ?? 0}`, tone: ((capabilityDetail?.capability?.evidence_digest?.operational_failed_count ?? 0) > 0 || (capabilityDetail?.capability?.evidence_digest?.operational_warning_count ?? 0) > 0) ? 'warning' : 'good' },
                                            { id: 'self_run_priority', label: 'self_run_priority', score: followUpPriority.axes.selfRunPriority, detail: `priority stage=${capabilityDetail?.capability?.evidence_digest?.priority_self_run_stage || '없음'}`, tone: capabilityDetail?.capability?.evidence_digest?.priority_self_run_stage ? 'warning' : 'good' },
                                        ]}
                                        recommendations={sharedRecommendations}
                                        metrics={[
                                            { label: '에러 변화량', value: `${beforeComparisonErrors} → ${afterComparisonErrors}`, tone: afterComparisonErrors < beforeComparisonErrors ? 'good' : 'warning' },
                                            { label: '경고 변화량', value: `${beforeComparisonWarnings} → ${afterComparisonWarnings}`, tone: afterComparisonWarnings < beforeComparisonWarnings ? 'good' : 'warning' },
                                            { label: 'failure tags', value: `${failureTags.length}건`, tone: failureTags.length > 0 ? 'warning' : 'good' },
                                            { label: 'target file ids', value: `${targetFileIds.length}건`, tone: targetFileIds.length > 0 ? 'neutral' : 'good' },
                                            { label: '누적 평균', value: `${historyStats.averageScore}점`, tone: historyStats.averageScore >= historyStats.latestScore ? 'warning' : 'good' },
                                            { label: '직전 대비', value: `${historyStats.momentum >= 0 ? '+' : ''}${historyStats.momentum}점`, tone: historyStats.momentum > 0 ? 'warning' : 'good' },
                                            { label: 'priority stage', value: capabilityDetail?.capability?.evidence_digest?.priority_self_run_stage || '없음', tone: capabilityDetail?.capability?.evidence_digest?.priority_self_run_stage ? 'warning' : 'good' },
                                            { label: 'approval failed fields', value: approvalFailedFields.join(', ') || '없음', tone: approvalFailedFields.length > 0 ? 'warning' : 'good' },
                                            { label: 'hard gate failed stages', value: hardGateFailedStages.join(', ') || '없음', tone: hardGateFailedStages.length > 0 ? 'warning' : 'good' },
                                        ]}
                                        trendPoints={[
                                            { label: '직전', value: historyStats.previousScore ?? historyStats.latestScore },
                                            { label: '현재', value: historyStats.latestScore },
                                            { label: '평균', value: historyStats.averageScore },
                                            { label: '피크', value: historyStats.peakScore },
                                        ]}
                                        actionLabel="후속 개선 실행"
                                        actionBusyLabel="실행 중..."
                                        actionDisabled={(loading || selfRunBusy) && selectedCapabilityActionId === detailCapabilityAction?.id}
                                        onAction={detailCapabilityAction ? () => void onApplyCapabilityAction(detailCapabilityAction, 'run') : undefined}
                                    />
                                    {capabilityDetail.suggested_actions.length > 0 && detailCapabilityAction && (
                                        <div className="mt-3 rounded-lg border border-[#3fb950] bg-[rgba(35,134,54,0.08)] p-3">
                                            <div className="flex flex-wrap items-center justify-between gap-3">
                                                <div>
                                                    <p className="text-xs font-semibold text-[#3fb950]">AI 후속 실행 연결</p>
                                                    <p className="mt-1 text-[11px] text-[#c9d1d9]">권장 후속 조치가 현재 관리자 실행 액션에 직접 연결된 상태입니다. 아래 버튼으로 동일 capability를 즉시 재실행할 수 있습니다.</p>
                                                </div>
                                                <button
                                                    type="button"
                                                    onClick={() => void onApplyCapabilityAction(detailCapabilityAction, 'run')}
                                                    disabled={loading || selfRunBusy}
                                                    className={`rounded-lg px-3 py-2 text-xs font-semibold text-white ${(loading || selfRunBusy) && selectedCapabilityActionId === detailCapabilityAction.id ? 'bg-[#21262d]' : 'bg-[#238636]'}`}
                                                >
                                                    {(loading || selfRunBusy) && selectedCapabilityActionId === detailCapabilityAction.id ? '실행 중...' : '후속 개선 실행'}
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                    <div className="mt-3 rounded-lg border border-[#30363d] bg-[#11161d] p-3">
                                        <p className="text-xs font-semibold text-[#79c0ff]">증거 스냅샷 / 실행 상관관계</p>
                                        <div className="mt-2 grid gap-2 lg:grid-cols-2">
                                            <div>
                                                <p className="text-[11px] font-semibold text-[#8b949e]">EVIDENCE_SCHEMA_VERSION</p>
                                                <p className="mt-1 text-xs text-[#c9d1d9] break-all">{String(contractEvidence.evidence_schema_version || '-')}</p>
                                            </div>
                                            <div>
                                                <p className="text-[11px] font-semibold text-[#8b949e]">PROFILE_ID</p>
                                                <p className="mt-1 text-xs text-[#c9d1d9] break-all">{String(contractEvidence.profile_id || '-')}</p>
                                            </div>
                                            <div>
                                                <p className="text-[11px] font-semibold text-[#8b949e]">EVIDENCE_RUN_ID</p>
                                                <p className="mt-1 text-xs text-[#c9d1d9] break-all">{String(executionEvidence?.evidence_run_id || '-')}</p>
                                            </div>
                                            <div>
                                                <p className="text-[11px] font-semibold text-[#8b949e]">GENERATED_AT</p>
                                                <p className="mt-1 text-xs text-[#c9d1d9] break-all">{String(executionEvidence?.evidence_generated_at || '-')}</p>
                                            </div>
                                            <div>
                                                <p className="text-[11px] font-semibold text-[#8b949e]">READINESS_CHECKLIST</p>
                                                <p className="mt-1 text-xs text-[#c9d1d9] break-all">{String(readinessEvidence.final_readiness_checklist_path || '-')}</p>
                                            </div>
                                            <div>
                                                <p className="text-[11px] font-semibold text-[#8b949e]">AUTOMATIC_VALIDATION_RESULT</p>
                                                <p className="mt-1 text-xs text-[#c9d1d9] break-all">{String(readinessEvidence.automatic_validation_result_path || '-')}</p>
                                            </div>
                                            <div>
                                                <p className="text-[11px] font-semibold text-[#8b949e]">OPERATIONAL_CANONICAL_SOURCE</p>
                                                <p className="mt-1 text-xs text-[#c9d1d9] break-all">{String(operationsEvidence.canonical_source || 'evidence_bundle.readiness.operational_evidence_snapshot')}</p>
                                            </div>
                                            <div>
                                                <p className="text-[11px] font-semibold text-[#8b949e]">OPERATIONAL_EVIDENCE</p>
                                                <p className="mt-1 text-xs text-[#c9d1d9] break-all">{String(operationalEvidenceSummary?.verified_count ?? capabilityDetail?.capability?.evidence_digest?.operational_verified_count ?? 0)}/{String(operationalEvidenceSummary?.required_count ?? capabilityDetail?.capability?.evidence_digest?.operational_target_count ?? 0)}</p>
                                            </div>
                                            <div>
                                                <p className="text-[11px] font-semibold text-[#8b949e]">OPERATIONAL_WARNING / FAILED</p>
                                                <p className="mt-1 text-xs text-[#c9d1d9] break-all">{String(operationalEvidenceSummary?.warning_count ?? capabilityDetail?.capability?.evidence_digest?.operational_warning_count ?? 0)}/{String(operationalEvidenceSummary?.failed_count ?? capabilityDetail?.capability?.evidence_digest?.operational_failed_count ?? 0)}</p>
                                            </div>
                                            <div>
                                                <p className="text-[11px] font-semibold text-[#8b949e]">OPERATIONAL_MAX_LATENCY_MS</p>
                                                <p className="mt-1 text-xs text-[#c9d1d9] break-all">{String(operationalLatencySummary?.max_latency_ms ?? operationalEvidenceSummary?.max_latency_ms ?? capabilityDetail?.capability?.evidence_digest?.operational_max_latency_ms ?? '-')}</p>
                                            </div>
                                            <div>
                                                <p className="text-[11px] font-semibold text-[#8b949e]">OUTPUT_AUDIT_PATH</p>
                                                <p className="mt-1 text-xs text-[#c9d1d9] break-all">{String(readinessEvidence.output_audit_path || '-')}</p>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="mt-3 rounded-lg border border-[#30363d] bg-[#11161d] p-3">
                                        <p className="text-xs font-semibold text-[#f2cc60]">정밀 수정 ID / 실패 꼬리표</p>
                                        <div className="mt-2 grid gap-2 lg:grid-cols-2">
                                            <div>
                                                <p className="text-[11px] font-semibold text-[#8b949e]">TARGET_FILE_IDS</p>
                                                <p className="mt-1 text-xs text-[#c9d1d9] break-all">{targetFileIds.join(', ') || '없음'}</p>
                                            </div>
                                            <div>
                                                <p className="text-[11px] font-semibold text-[#8b949e]">FAILURE_TAGS</p>
                                                <p className="mt-1 text-xs text-[#c9d1d9] break-all">{failureTags.join(', ') || '없음'}</p>
                                            </div>
                                            <div>
                                                <p className="text-[11px] font-semibold text-[#8b949e]">TARGET_SECTION_IDS</p>
                                                <p className="mt-1 text-xs text-[#8b949e] break-all">{targetSectionIds.join(', ') || '없음'}</p>
                                            </div>
                                            <div>
                                                <p className="text-[11px] font-semibold text-[#8b949e]">TARGET_FEATURE_IDS</p>
                                                <p className="mt-1 text-xs text-[#8b949e] break-all">{targetFeatureIds.join(', ') || '없음'}</p>
                                            </div>
                                            <div>
                                                <p className="text-[11px] font-semibold text-[#8b949e]">TARGET_CHUNK_IDS</p>
                                                <p className="mt-1 text-xs text-[#8b949e] break-all">{targetChunkIds.join(', ') || '없음'}</p>
                                            </div>
                                            <div>
                                                <p className="text-[11px] font-semibold text-[#8b949e]">REPAIR_TAGS</p>
                                                <p className="mt-1 text-xs text-[#8b949e] break-all">{repairTags.join(', ') || '없음'}</p>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="mt-3 rounded-lg border border-[#30363d] bg-[#11161d] p-3">
                                        <p className="text-xs font-semibold text-[#79c0ff]">섹션/기능/라우터/레이어 식별 맵</p>
                                        {targetPatchEntries.length > 0 ? (
                                            <div className="mt-3 space-y-2">
                                                {targetPatchEntries.map((entry, index) => (
                                                    <div key={`${entry.file_id || entry.path || 'entry'}-${entry.chunk_id || index}`} className="rounded-lg border border-[#30363d] bg-[#0b0f14] p-3">
                                                        <div className="grid gap-2 lg:grid-cols-2">
                                                            <div>
                                                                <p className="text-[11px] font-semibold text-[#8b949e]">FILE / PATH</p>
                                                                <p className="mt-1 text-xs text-[#c9d1d9] break-all">{entry.file_id || '-'} · {entry.path || '-'}</p>
                                                            </div>
                                                            <div>
                                                                <p className="text-[11px] font-semibold text-[#8b949e]">SECTION / FEATURE / CHUNK</p>
                                                                <p className="mt-1 text-xs text-[#c9d1d9] break-all">{entry.section_id || '-'} · {entry.feature_id || '-'} · {entry.chunk_id || '-'}</p>
                                                            </div>
                                                            <div>
                                                                <p className="text-[11px] font-semibold text-[#8b949e]">LAYER</p>
                                                                <p className="mt-1 text-xs text-[#c9d1d9] break-all">{entry.layer || '미기록'}</p>
                                                            </div>
                                                            <div>
                                                                <p className="text-[11px] font-semibold text-[#8b949e]">FAILURE / REPAIR TAGS</p>
                                                                <p className="mt-1 text-xs text-[#c9d1d9] break-all">{(entry.failure_tags || []).join(', ') || '없음'} / {(entry.repair_tags || []).join(', ') || '없음'}</p>
                                                            </div>
                                                        </div>
                                                        {entry.summary && (
                                                            <p className="mt-2 text-xs text-[#8b949e] whitespace-pre-wrap">{entry.summary}</p>
                                                        )}
                                                    </div>
                                                ))}
                                            </div>
                                        ) : (
                                            <p className="mt-2 text-xs text-[#8b949e]">현재 실행 근거에는 target patch registry 기반 식별 맵이 아직 연결되지 않았습니다.</p>
                                        )}
                                    </div>
                                </div>
                                {(capabilityDetail.validation_findings.length > 0 || capabilityDetail.improvement_code_examples.length > 0) && (
                                    <div className="grid gap-3 xl:grid-cols-2">
                                        <div className="rounded-lg border border-[#30363d] bg-[#0d1117] p-4">
                                            <p className="text-sm font-semibold text-[#e6edf3]">프로그램 검증 결과</p>
                                            <div className="mt-3 space-y-3">
                                                {capabilityDetail.validation_findings.length > 0 ? capabilityDetail.validation_findings.map((finding, findingIndex) => {
                                                    const findingRenderKey = getCapabilityFindingRenderKey(finding, findingIndex);
                                                    return (
                                                        <div key={findingRenderKey} className="rounded-lg border border-[#30363d] bg-[#11161d] p-3">
                                                            <div className="flex items-center justify-between gap-3">
                                                                <p className="text-xs font-semibold text-[#f2cc60]">{finding.title}</p>
                                                                <span className="rounded-full border border-[#30363d] px-2 py-0.5 text-[10px] uppercase tracking-[0.2em] text-[#8b949e]">{finding.severity}</span>
                                                            </div>
                                                            <p className="mt-2 text-xs text-[#c9d1d9]">문제 내용: {finding.problem}</p>
                                                            <p className="mt-2 text-xs text-[#f78166]">잘못 구현된 상태 표현: {finding.wrong_expression}</p>
                                                            <p className="mt-2 text-xs text-[#3fb950]">개선 방향: {finding.improvement}</p>
                                                            <p className="mt-2 text-[11px] text-[#8b949e]">근거 경로: {finding.source_path}</p>
                                                            {(finding.file_evidence || []).length > 0 && (
                                                                <div className="mt-3 space-y-2">
                                                                    {(finding.file_evidence || []).map((evidence, evidenceIndex) => (
                                                                        <div key={`${findingRenderKey}-evidence-${evidenceIndex}`} className="rounded-lg border border-[#30363d] bg-[#0b0f14] p-3">
                                                                            <p className="text-[11px] font-semibold text-[#79c0ff]">실제 문제 코드 조각: {evidence.path}:{evidence.line_start}-{evidence.line_end}</p>
                                                                            <p className="mt-1 text-[11px] text-[#8b949e]">{evidence.summary}</p>
                                                                            <pre className="mt-2 overflow-x-auto text-[11px] leading-5 text-[#c9d1d9]">
                                                                                <code>{evidence.snippet}</code>
                                                                            </pre>
                                                                        </div>
                                                                    ))}
                                                                </div>
                                                            )}
                                                        </div>
                                                    );
                                                }) : (
                                                    <p className="text-xs text-[#8b949e]">현재 선택한 기능에는 표시할 검증 결과가 없습니다.</p>
                                                )}
                                            </div>
                                        </div>
                                        <div className="rounded-lg border border-[#30363d] bg-[#0d1117] p-4">
                                            <p className="text-sm font-semibold text-[#e6edf3]">개선 코드 예시</p>
                                            <div className="mt-3 space-y-3">
                                                {capabilityDetail.improvement_code_examples.length > 0 ? capabilityDetail.improvement_code_examples.map((example, exampleIndex) => (
                                                    <div key={getCapabilityCodeExampleRenderKey(example, exampleIndex)} className="rounded-lg border border-[#30363d] bg-[#11161d] p-3">
                                                        <div className="flex items-center justify-between gap-3">
                                                            <p className="text-xs font-semibold text-[#79c0ff]">{example.title}</p>
                                                            <span className="rounded-full border border-[#30363d] px-2 py-0.5 text-[10px] uppercase tracking-[0.2em] text-[#8b949e]">{example.language}</span>
                                                        </div>
                                                        <p className="mt-2 text-xs text-[#c9d1d9]">{example.summary}</p>
                                                        <p className="mt-2 text-[11px] text-[#8b949e]">적용 위치: {example.path}</p>
                                                        <pre className="mt-3 overflow-x-auto rounded-lg border border-[#30363d] bg-[#0b0f14] p-3 text-[11px] leading-5 text-[#c9d1d9]">
                                                            <code>{example.code}</code>
                                                        </pre>
                                                    </div>
                                                )) : (
                                                    <p className="text-xs text-[#8b949e]">현재 선택한 기능에는 표시할 개선 코드 예시가 없습니다.</p>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                )}
                                {activeCapabilityComparison && (
                                    <div className="grid gap-3 xl:grid-cols-2">
                                        <div className="rounded-lg border border-[#30363d] bg-[#0d1117] p-4">
                                            <p className="text-sm font-semibold text-[#e6edf3]">즉시 개선 실행 전후 비교</p>
                                            <p className="mt-1 text-[11px] text-[#8b949e]">회수 시각: {new Date(activeCapabilityComparison.capturedAt).toLocaleString('ko-KR')}</p>
                                            <div className="mt-3 grid gap-2 md:grid-cols-2">
                                                <div className="rounded-lg border border-[#30363d] bg-[#11161d] p-3">
                                                    <p className="text-xs font-semibold text-[#f78166]">실행 전</p>
                                                    <p className="mt-2 text-xs text-[#c9d1d9]">상태: {activeCapabilityComparison.beforeDetail?.capability.state || '-'}</p>
                                                    <p className="mt-1 text-xs text-[#c9d1d9]">에러 {beforeComparisonErrors}건 / 경고 {beforeComparisonWarnings}건</p>
                                                    <p className="mt-1 text-xs text-[#8b949e]">{activeCapabilityComparison.beforeDetail?.capability.detail || activeCapabilityComparison.beforeDetail?.capability.metric || '-'}</p>
                                                </div>
                                                <div className="rounded-lg border border-[#30363d] bg-[#11161d] p-3">
                                                    <p className="text-xs font-semibold text-[#3fb950]">실행 후</p>
                                                    <p className="mt-2 text-xs text-[#c9d1d9]">상태: {activeCapabilityComparison.afterDetail?.capability.state || '-'}</p>
                                                    <p className="mt-1 text-xs text-[#c9d1d9]">에러 {afterComparisonErrors}건 / 경고 {afterComparisonWarnings}건</p>
                                                    <p className="mt-1 text-xs text-[#8b949e]">{activeCapabilityComparison.afterDetail?.capability.detail || activeCapabilityComparison.afterDetail?.capability.metric || '-'}</p>
                                                </div>
                                            </div>
                                            <div className="mt-3 grid gap-2 md:grid-cols-2">
                                                <div className="rounded-lg border border-[#30363d] bg-[#11161d] p-3">
                                                    <p className="text-xs font-semibold text-[#79c0ff]">해소된 항목</p>
                                                    {comparisonResolvedTitles.length > 0 ? (
                                                        <ul className="mt-2 space-y-1 text-xs text-[#c9d1d9]">
                                                            {comparisonResolvedTitles.map((title, index) => (
                                                                <li key={`resolved-${index}`}>• {title}</li>
                                                            ))}
                                                        </ul>
                                                    ) : (
                                                        <p className="mt-2 text-xs text-[#8b949e]">자동 비교에서 해소된 항목이 아직 감지되지 않았습니다.</p>
                                                    )}
                                                </div>
                                                <div className="rounded-lg border border-[#30363d] bg-[#11161d] p-3">
                                                    <p className="text-xs font-semibold text-[#f2cc60]">새로 남은 항목</p>
                                                    {comparisonNewTitles.length > 0 ? (
                                                        <ul className="mt-2 space-y-1 text-xs text-[#c9d1d9]">
                                                            {comparisonNewTitles.map((title, index) => (
                                                                <li key={`new-${index}`}>• {title}</li>
                                                            ))}
                                                        </ul>
                                                    ) : (
                                                        <p className="mt-2 text-xs text-[#8b949e]">새로 추가된 실패 항목은 감지되지 않았습니다.</p>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                        <div className="rounded-lg border border-[#30363d] bg-[#0d1117] p-4">
                                            <p className="text-sm font-semibold text-[#e6edf3]">자동 회수된 실행 결과</p>
                                            <div className="mt-3 space-y-2 text-xs text-[#c9d1d9]">
                                                <div className="rounded-lg border border-[#30363d] bg-[#11161d] p-3">
                                                    <p>적용 상태: {activeCapabilityComparison.selfRunResult ? buildSelfRunStatusLabel(activeCapabilityComparison.selfRunResult.status) : (activeCapabilityComparison.runResult?.applied ? '1차 검증 반영 완료' : (activeCapabilityComparison.runResult?.apply_error ? '적용 실패' : '응답만 생성'))}</p>
                                                    <p className="mt-1">출력 경로: {activeCapabilityComparison.selfRunResult?.experiment_clone_path || activeCapabilityComparison.runResult?.output_dir || activeCapabilityComparison.runResult?.failed_output_dir || '-'}</p>
                                                    <p className="mt-1">파이프라인: {activeCapabilityComparison.selfRunResult ? `self-run / ${activeCapabilityComparison.selfRunResult.execution_mode || '-'}` : ((activeCapabilityComparison.runResult?.pipeline || []).join(' -> ') || '-')}</p>
                                                </div>
                                                <div className="rounded-lg border border-[#30363d] bg-[#11161d] p-3">
                                                    <p>완료 게이트: {typeof activeCapabilityComparison.runResult?.completion_gate_ok === 'boolean' ? (activeCapabilityComparison.runResult?.completion_gate_ok ? '1차 검증 통과' : '실패') : '미보고'}</p>
                                                    <p className="mt-1">의미 감사: {typeof activeCapabilityComparison.runResult?.semantic_audit_ok === 'boolean' ? (activeCapabilityComparison.runResult?.semantic_audit_ok ? '1차 검증 통과' : '실패') : '미보고'}</p>
                                                    <p className="mt-1 text-[#e3b341]">최종 통과는 사용자 직접 실험 후 인정</p>
                                                    <p className="mt-1">적용 오류: {activeCapabilityComparison.selfRunResult?.orchestration_error || activeCapabilityComparison.runResult?.apply_error || '-'}</p>
                                                </div>
                                                <div className="rounded-lg border border-[#30363d] bg-[#11161d] p-3">
                                                    <p className="text-xs font-semibold text-[#79c0ff]">상태 이력</p>
                                                    <p className="mt-2 text-xs text-[#8b949e]">{(activeCapabilityComparison.runResult?.state_history || []).join(' -> ') || '-'}</p>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                )}
                                <div className="grid gap-3 xl:grid-cols-2">
                                    {capabilityDetail.sections.map((section) => (
                                        <div key={section.id} className="rounded-lg border border-[#30363d] bg-[#0d1117] p-4">
                                            <p className="text-sm font-semibold text-[#e6edf3]">{section.title}</p>
                                            <div className="mt-3 space-y-2">
                                                {section.items.map((item, index) => (
                                                    <div key={`${section.id}-${index}`} className="rounded-lg border border-[#30363d] bg-[#11161d] px-3 py-2">
                                                        <div className="flex items-start justify-between gap-3">
                                                            <span className="text-xs font-semibold text-[#8b949e]">{item.label}</span>
                                                            <span className="text-xs text-[#e6edf3] text-right">{String(item.value ?? '-')}</span>
                                                        </div>
                                                        {item.note && (
                                                            <p className="mt-1 text-[11px] text-[#8b949e]">{item.note}</p>
                                                        )}
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ) : (
                            <p className="mt-4 text-xs text-[#8b949e]">기능 카드를 선택하면 project scan, dependency graph, model control 등 구조화된 결과가 여기에 표시됩니다.</p>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

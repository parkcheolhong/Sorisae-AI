import type { OrchestratorAgentKey, RoutedTextFeatureKey } from '@/lib/use-orchestrator-chat';

export type LiveApplyState = 'idle' | 'running' | 'applied' | 'response-only' | 'failed';

interface LiveSemanticAuditSnapshotLike {
    passed?: boolean;
    error?: string;
    summary?: string;
    score?: number;
    maxScore?: number;
    threshold?: number;
    checklist?: any[];
}

interface ProductReadinessHardGateLike {
    ok?: boolean;
    summary?: string | null;
    failed_stages?: string[];
    stages?: Array<{
        id: string;
        ok: boolean;
        summary: string;
        evidence?: Record<string, unknown> | null;
    }>;
    archive_path?: string | null;
}

interface OrchestrateResponseLike {
    pipeline?: string[];
    state_history?: string[];
    output_dir?: string;
    failed_output_dir?: string;
    apply_error?: string | null;
    applied?: boolean;
    orchestration_spec?: any;
    completion_gate_ok?: boolean | null;
    completion_gate_error?: string | null;
    completion_summary?: string | null;
    semantic_audit_ok?: boolean | null;
    semantic_audit_error?: string | null;
    semantic_audit_summary?: string | null;
    semantic_audit_score?: number | null;
    semantic_audit_max_score?: number | null;
    semantic_audit_threshold?: number | null;
    semantic_audit_checklist?: any[];
    semantic_audit_report_path?: string | null;
    completion_judge?: {
        product_readiness_hard_gate?: ProductReadinessHardGateLike;
        [key: string]: unknown;
    };
}

export function buildAdminLivePanelSummary(options: {
    liveStateHistory: string[];
    liveCurrentState: string;
    livePipeline: string[];
    runtimeDraft?: { code_generation_strategy?: string | null } | null;
    runtimeConfig?: { code_generation_strategy?: string | null } | null;
    result?: OrchestrateResponseLike | null;
    chatAgentKey: OrchestratorAgentKey;
    voiceAgentKey: OrchestratorAgentKey;
    textFeatureAgents: Record<RoutedTextFeatureKey, OrchestratorAgentKey>;
    requiredReasonerTargets: readonly string[];
    expansionReasonerTargets: readonly string[];
    liveOrchestrationSpec: any;
    liveOutputDir: string;
    liveApplyError: string;
    liveSemanticAudit?: LiveSemanticAuditSnapshotLike | null;
    liveApplyState: LiveApplyState;
    loading: boolean;
    liveLogs: Array<unknown>;
    liveRunId: string;
}) {
    const effectiveStateHistory = options.liveStateHistory.length > 0
        ? options.liveStateHistory
        : (options.result?.state_history || []);
    const effectiveCurrentState = options.liveCurrentState || effectiveStateHistory[effectiveStateHistory.length - 1] || '';
    const effectivePipeline = options.livePipeline.length > 0 ? options.livePipeline : (options.result?.pipeline || []);
    const effectiveCodeGenerationStrategy = options.runtimeDraft?.code_generation_strategy
        || options.runtimeConfig?.code_generation_strategy
        || 'auto_generator';
    const effectiveConversationAgents = {
        text: options.chatAgentKey,
        voice: options.voiceAgentKey,
        question: options.textFeatureAgents.question,
        research: options.textFeatureAgents.research,
        action: options.textFeatureAgents.action,
    };
    const reasonerRequiredCoverage = options.requiredReasonerTargets
        .filter((target) => (effectiveConversationAgents as any)[target] === 'reasoner')
        .length;
    const reasonerExpansionCoverage = options.expansionReasonerTargets
        .filter((target) => (effectiveConversationAgents as any)[target] === 'reasoner')
        .length;
    const reasonerConversationCoverage = reasonerRequiredCoverage + reasonerExpansionCoverage;
    const reasonerCoverageState = reasonerRequiredCoverage === options.requiredReasonerTargets.length
        ? (reasonerExpansionCoverage > 0 ? '강화됨' : '기본 적용')
        : '부분 적용';
    const reasonerCoverageClassName = reasonerRequiredCoverage === options.requiredReasonerTargets.length
        ? 'text-[#3fb950]'
        : 'text-[#f2cc60]';
    const effectiveOrchestrationSpec = options.liveOrchestrationSpec || options.result?.orchestration_spec || null;
    const effectiveOutputDir = options.liveOutputDir || options.result?.output_dir || options.result?.failed_output_dir || '';
    const effectiveFailedOutputDir = options.result?.failed_output_dir || (!options.result?.applied ? options.liveOutputDir : '');
    const effectiveApplyError = options.liveApplyError || options.result?.apply_error || '';
    const hasCompletionGateResult = typeof options.result?.completion_gate_ok === 'boolean';
    const effectiveCompletionGateOk = options.result?.completion_gate_ok ?? false;
    const effectiveCompletionGateError = options.result?.completion_gate_error || '';
    const effectiveCompletionSummary = options.result?.completion_summary || '';
    const hasSemanticAuditResult = typeof options.result?.semantic_audit_ok === 'boolean'
        || typeof options.liveSemanticAudit?.passed === 'boolean'
        || ((options.liveSemanticAudit?.checklist?.length || 0) > 0);
    const effectiveSemanticAuditOk = options.result?.semantic_audit_ok ?? options.liveSemanticAudit?.passed ?? false;
    const effectiveSemanticAuditError = options.result?.semantic_audit_error || options.liveSemanticAudit?.error || '';
    const effectiveSemanticAuditSummary = options.result?.semantic_audit_summary || options.liveSemanticAudit?.summary || '';
    const effectiveSemanticAuditScore = options.result?.semantic_audit_score ?? options.liveSemanticAudit?.score;
    const effectiveSemanticAuditMaxScore = options.result?.semantic_audit_max_score ?? options.liveSemanticAudit?.maxScore ?? 100;
    const effectiveSemanticAuditThreshold = options.result?.semantic_audit_threshold ?? options.liveSemanticAudit?.threshold ?? 0;
    const effectiveSemanticAuditChecklist = options.result?.semantic_audit_checklist || options.liveSemanticAudit?.checklist || [];
    const effectiveSemanticAuditReportPath = options.result?.semantic_audit_report_path || '';
    const effectiveProductReadinessHardGate = options.result?.completion_judge?.product_readiness_hard_gate || null;
    const effectiveApplyState: LiveApplyState = options.result
        ? (options.result.applied ? 'applied' : (options.result.apply_error ? 'failed' : 'response-only'))
        : options.liveApplyState;
    const shouldShowLivePanel = options.loading || options.liveLogs.length > 0 || effectiveStateHistory.length > 0 || !!options.liveRunId;
    const shouldShowExecutionSummary = !!options.result || shouldShowLivePanel || !!effectiveOrchestrationSpec;
    const applyStateLabel = effectiveApplyState === 'applied'
        ? '적용 완료'
        : effectiveApplyState === 'running'
            ? '실행 중'
            : effectiveApplyState === 'failed'
                ? '실패'
                : effectiveApplyState === 'response-only'
                    ? '응답만 생성'
                    : '대기';

    return {
        effectiveStateHistory,
        effectiveCurrentState,
        effectivePipeline,
        effectiveCodeGenerationStrategy,
        effectiveConversationAgents,
        reasonerRequiredCoverage,
        reasonerExpansionCoverage,
        reasonerConversationCoverage,
        reasonerCoverageState,
        reasonerCoverageClassName,
        effectiveOrchestrationSpec,
        effectiveOutputDir,
        effectiveFailedOutputDir,
        effectiveApplyError,
        hasCompletionGateResult,
        effectiveCompletionGateOk,
        effectiveCompletionGateError,
        effectiveCompletionSummary,
        hasSemanticAuditResult,
        effectiveSemanticAuditOk,
        effectiveSemanticAuditError,
        effectiveSemanticAuditSummary,
        effectiveSemanticAuditScore,
        effectiveSemanticAuditMaxScore,
        effectiveSemanticAuditThreshold,
        effectiveSemanticAuditChecklist,
        effectiveSemanticAuditReportPath,
        effectiveProductReadinessHardGate,
        effectiveApplyState,
        shouldShowLivePanel,
        shouldShowExecutionSummary,
        applyStateLabel,
    };
}

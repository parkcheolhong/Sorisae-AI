import type { SharedOrchestratorStageRun } from '@/shared/orchestrator-stage-card-panel';
import type { OrchestratorDecisionItem } from '@/shared/orchestrator-decision-card';
import {
    mergeProgressIntoDiagnostics,
    type OrchestratorLiveProgressSnapshot,
} from '@/lib/orchestrator-live-progress';

export type LiveFlowStageStatus =
    | 'pending'
    | 'running'
    | 'completed'
    | 'awaiting_approval'
    | 'discuss'
    | 'failed';

export type LiveFlowAgentResult = {
    agent: string;
    status: string;
};

export type LiveFlowProgressLog = {
    id: string;
    message: string;
    timestamp: string;
    severity?: 'info' | 'success' | 'warning' | 'error';
};

export type LiveFlowSubstep = {
    id: string;
    status: string;
    message?: string;
    at?: string;
};

export type OrchestratorLiveFlowStage = {
    id: string;
    number: number;
    label: string;
    status: LiveFlowStageStatus;
};

export type OrchestratorLiveFlowSnapshot = {
    orchestratorCore?: string | null;
    autonomousIntent?: string | null;
    stageCommand?: string | null;
    stageNumber?: number | null;
    stagesCompleted: number;
    stagesTotal: number;
    currentStage?: string | null;
    executionState?: string | null;
    approvalState?: string | null;
    requiresApproval: boolean;
    stageCommandHint?: string | null;
    llmConnected?: boolean | null;
    agentResults: LiveFlowAgentResult[];
    chatLoading: boolean;
    activeStageIndex: number;
    stages: OrchestratorLiveFlowStage[];
    discussLocked?: boolean;
    commandRules?: string[];
    progressStatus?: 'idle' | 'running' | 'success' | 'failed' | null;
    progressUpdatedAt?: string | null;
    progressPolling?: boolean;
    progressLogs?: LiveFlowProgressLog[];
    activeSubstep?: string | null;
    substeps?: LiveFlowSubstep[];
    voiceEntry?: boolean;
    voiceSpeaker?: string | null;
};

export const ORCHESTRATOR_LIVE_FLOW_STAGE_DEFS: Array<{ id: string; number: number; label: string }> = [
    { id: 'STAGE-01', number: 1, label: '구조 설계' },
    { id: 'STAGE-02', number: 2, label: '폴더·기초' },
    { id: 'STAGE-03', number: 3, label: '골조 구현' },
    { id: 'STAGE-04', number: 4, label: '핵심 엔진' },
    { id: 'STAGE-045', number: 4.5, label: 'Refiner' },
    { id: 'STAGE-05', number: 5, label: '로직' },
    { id: 'STAGE-06', number: 6, label: '데이터' },
    { id: 'STAGE-07', number: 7, label: '서비스' },
    { id: 'STAGE-08', number: 8, label: 'API' },
    { id: 'STAGE-09', number: 9, label: '프론트' },
    { id: 'STAGE-10', number: 10, label: '운영 검증' },
];

const ARCH_TO_STAGE_INDEX: Record<string, number> = {
    'ARCH-001': 0,
    'ARCH-002': 1,
    'ARCH-003': 2,
    'ARCH-004': 3,
    'ARCH-0045': 4,
    'ARCH-005': 5,
    'ARCH-006': 6,
    'ARCH-007': 7,
    'ARCH-008': 8,
    'ARCH-009': 9,
    'ARCH-010': 10,
};

const STAGE_ID_TO_INDEX: Record<string, number> = Object.fromEntries(
    ORCHESTRATOR_LIVE_FLOW_STAGE_DEFS.map((stage, index) => [stage.id, index]),
);

const STAGE_NUMBER_TO_ARCH: Record<number, string> = {
    1: 'ARCH-001',
    2: 'ARCH-002',
    3: 'ARCH-003',
    4: 'ARCH-004',
    4.5: 'ARCH-0045',
    5: 'ARCH-005',
    6: 'ARCH-006',
    7: 'ARCH-007',
    8: 'ARCH-008',
    9: 'ARCH-009',
    10: 'ARCH-010',
};

export function resolveLiveFlowLabelForArchId(archId?: string | null): string | null {
    const normalized = String(archId || '').trim().toUpperCase();
    const index = ARCH_TO_STAGE_INDEX[normalized];
    if (index === undefined) {
        return null;
    }
    const stage = ORCHESTRATOR_LIVE_FLOW_STAGE_DEFS[index];
    if (!stage) {
        return null;
    }
    return `${stage.number}단계 · ${stage.label}`;
}

export function isDiscussIntent(autonomousIntent?: string | null): boolean {
    return String(autonomousIntent || '').includes('discuss');
}

export function isDiscussLockedIntent(autonomousIntent?: string | null): boolean {
    return String(autonomousIntent || '') === 'stage_discuss_locked';
}

export function resolveCommandRules(
    diagnostics?: Record<string, unknown> | null,
    fallback: string[] = [],
): string[] {
    const rules = diagnostics?.command_rules;
    if (Array.isArray(rules) && rules.length > 0) {
        return rules.map((item) => String(item));
    }
    return fallback;
}

export function resolveDiscussArchId(
    snapshot: Pick<OrchestratorLiveFlowSnapshot, 'autonomousIntent' | 'stageNumber' | 'currentStage'>,
    stageRun?: SharedOrchestratorStageRun | null,
): string | null {
    if (!isDiscussIntent(snapshot.autonomousIntent)) {
        return null;
    }
    const runArch = String(stageRun?.current_stage_id || '').trim().toUpperCase();
    if (runArch.startsWith('ARCH-')) {
        return runArch;
    }
    const currentStage = String(snapshot.currentStage || '').trim().toUpperCase();
    if (currentStage.startsWith('ARCH-')) {
        return currentStage;
    }
    if (snapshot.stageNumber !== null && snapshot.stageNumber !== undefined) {
        return STAGE_NUMBER_TO_ARCH[snapshot.stageNumber] || null;
    }
    return null;
}

function resolveActiveStageIndex(options: {
    stagesCompleted: number;
    currentStage?: string | null;
    stageNumber?: number | null;
    stageRun?: SharedOrchestratorStageRun | null;
}): number {
    const currentStage = String(options.currentStage || '').trim().toUpperCase();
    if (currentStage.startsWith('STAGE-') && STAGE_ID_TO_INDEX[currentStage] !== undefined) {
        return STAGE_ID_TO_INDEX[currentStage];
    }
    if (currentStage.startsWith('ARCH-') && ARCH_TO_STAGE_INDEX[currentStage] !== undefined) {
        return ARCH_TO_STAGE_INDEX[currentStage];
    }
    if (options.stageRun?.current_stage_id) {
        const archIndex = ARCH_TO_STAGE_INDEX[String(options.stageRun.current_stage_id).toUpperCase()];
        if (archIndex !== undefined) {
            return archIndex;
        }
    }
    if (options.stageNumber !== null && options.stageNumber !== undefined) {
        const matched = ORCHESTRATOR_LIVE_FLOW_STAGE_DEFS.findIndex(
            (stage) => stage.number === options.stageNumber,
        );
        if (matched >= 0) {
            return matched;
        }
    }
    const completed = Math.max(0, options.stagesCompleted);
    if (completed >= ORCHESTRATOR_LIVE_FLOW_STAGE_DEFS.length) {
        return ORCHESTRATOR_LIVE_FLOW_STAGE_DEFS.length - 1;
    }
    return Math.min(completed, ORCHESTRATOR_LIVE_FLOW_STAGE_DEFS.length - 1);
}

function buildStageStatuses(options: {
    stagesCompleted: number;
    activeStageIndex: number;
    autonomousIntent?: string | null;
    requiresApproval: boolean;
    chatLoading: boolean;
}): OrchestratorLiveFlowStage[] {
    const discuss = String(options.autonomousIntent || '').includes('discuss');
    return ORCHESTRATOR_LIVE_FLOW_STAGE_DEFS.map((stage, index) => {
        let status: LiveFlowStageStatus = 'pending';
        if (index < options.stagesCompleted) {
            status = 'completed';
        } else if (index === options.activeStageIndex) {
            if (discuss) {
                status = 'discuss';
            } else if (options.requiresApproval) {
                status = 'awaiting_approval';
            } else if (options.chatLoading) {
                status = 'running';
            } else {
                status = 'running';
            }
        }
        return { ...stage, status };
    });
}

export function buildLiveFlowSnapshotFromDiagnostics(
    diagnostics?: Record<string, unknown> | null,
    options?: {
        chatLoading?: boolean;
        stageRun?: SharedOrchestratorStageRun | null;
    },
): OrchestratorLiveFlowSnapshot {
    const diag = diagnostics || {};
    const stagesCompleted = Number(diag.stages_completed ?? 0) || 0;
    const stagesTotal = Number(diag.stages_total ?? ORCHESTRATOR_LIVE_FLOW_STAGE_DEFS.length) || ORCHESTRATOR_LIVE_FLOW_STAGE_DEFS.length;
    const requiresApproval = Boolean(diag.requires_approval);
    const chatLoading = Boolean(options?.chatLoading);
    const autonomousIntent = typeof diag.autonomous_intent === 'string' ? diag.autonomous_intent : null;
    const stageNumberRaw = diag.stage_number;
    const stageNumber = stageNumberRaw === null || stageNumberRaw === undefined
        ? null
        : Number(stageNumberRaw);
    const activeStageIndex = resolveActiveStageIndex({
        stagesCompleted,
        currentStage: typeof diag.current_stage === 'string' ? diag.current_stage : null,
        stageNumber: Number.isFinite(stageNumber) ? stageNumber : null,
        stageRun: options?.stageRun,
    });
    const agentResultsRaw = Array.isArray(diag.agent_results) ? diag.agent_results : [];
    const agentResults: LiveFlowAgentResult[] = agentResultsRaw
        .map((item) => {
            if (!item || typeof item !== 'object') {
                return null;
            }
            const record = item as Record<string, unknown>;
            const agent = String(record.agent || '').trim();
            if (!agent) {
                return null;
            }
            return {
                agent,
                status: String(record.status || 'unknown'),
            };
        })
        .filter((item): item is LiveFlowAgentResult => item !== null);

    const commandRules = resolveCommandRules(diag, []);
    const progressLogsRaw = Array.isArray(diag.progress_logs) ? diag.progress_logs : [];
    const progressLogs: LiveFlowProgressLog[] = progressLogsRaw
        .flatMap((item) => {
            if (!item || typeof item !== 'object') {
                return [];
            }
            const record = item as Record<string, unknown>;
            const message = String(record.message || '').trim();
            if (!message) {
                return [];
            }
            const severity = record.severity;
            const normalizedSeverity = severity === 'error'
                || severity === 'warning'
                || severity === 'success'
                || severity === 'info'
                ? severity
                : undefined;
            return [{
                id: String(record.id || message.slice(0, 24)),
                message,
                timestamp: String(record.timestamp || record.at || ''),
                severity: normalizedSeverity,
            }];
        });
    const substepsRaw = Array.isArray(diag.progress_substeps) ? diag.progress_substeps : [];
    const substeps: LiveFlowSubstep[] = substepsRaw
        .flatMap((item) => {
            if (!item || typeof item !== 'object') {
                return [];
            }
            const record = item as Record<string, unknown>;
            const id = String(record.id || '').trim();
            if (!id) {
                return [];
            }
            return [{
                id,
                status: String(record.status || 'info'),
                message: record.message ? String(record.message) : undefined,
                at: record.at ? String(record.at) : undefined,
            }];
        });
    const progressStatusRaw = typeof diag.progress_status === 'string' ? diag.progress_status : null;
    const progressStatus = progressStatusRaw === 'running'
        || progressStatusRaw === 'success'
        || progressStatusRaw === 'failed'
        || progressStatusRaw === 'idle'
        ? progressStatusRaw
        : null;
    const progressPolling = Boolean(diag.progress_polling) || progressStatus === 'running' || chatLoading;
    const voiceEntry = Boolean(diag.voice_entry);
    const voiceSpeaker = typeof diag.voice_speaker === 'string' ? diag.voice_speaker : null;

    return {
        orchestratorCore: typeof diag.orchestrator_core === 'string' ? diag.orchestrator_core : null,
        autonomousIntent,
        stageCommand: typeof diag.stage_command === 'string' ? diag.stage_command : null,
        stageNumber: Number.isFinite(stageNumber) ? stageNumber : null,
        stagesCompleted,
        stagesTotal,
        currentStage: typeof diag.current_stage === 'string' ? diag.current_stage : null,
        executionState: typeof diag.execution_state === 'string' ? diag.execution_state : null,
        approvalState: typeof diag.approval_state === 'string' ? diag.approval_state : null,
        requiresApproval,
        stageCommandHint: typeof diag.stage_command_hint === 'string' ? diag.stage_command_hint : null,
        llmConnected: typeof diag.llm_connected === 'boolean' ? diag.llm_connected : null,
        agentResults,
        chatLoading,
        activeStageIndex,
        discussLocked: Boolean(diag.discuss_locked) || isDiscussLockedIntent(autonomousIntent),
        commandRules,
        stages: buildStageStatuses({
            stagesCompleted,
            activeStageIndex,
            autonomousIntent,
            requiresApproval,
            chatLoading: chatLoading || progressPolling,
        }),
        progressStatus,
        progressUpdatedAt: typeof diag.progress_updated_at === 'string' ? diag.progress_updated_at : null,
        progressPolling,
        progressLogs,
        activeSubstep: typeof diag.progress_active_substep === 'string' ? diag.progress_active_substep : null,
        substeps,
        voiceEntry,
        voiceSpeaker,
    };
}

export function mergeLiveFlowWithProgress(
    snapshot: OrchestratorLiveFlowSnapshot,
    progress: OrchestratorLiveProgressSnapshot | null | undefined,
    options?: { chatLoading?: boolean; stageRun?: SharedOrchestratorStageRun | null },
): OrchestratorLiveFlowSnapshot {
    if (!progress) {
        return snapshot;
    }
    const mergedDiagnostics = mergeProgressIntoDiagnostics(
        {
            orchestrator_core: snapshot.orchestratorCore,
            stages_completed: snapshot.stagesCompleted,
            stages_total: snapshot.stagesTotal,
            autonomous_intent: snapshot.autonomousIntent,
            stage_command: snapshot.stageCommand,
            stage_number: snapshot.stageNumber,
            execution_state: snapshot.executionState,
            approval_state: snapshot.approvalState,
            requires_approval: snapshot.requiresApproval,
            stage_command_hint: snapshot.stageCommandHint,
            llm_connected: snapshot.llmConnected,
            agent_results: snapshot.agentResults,
            discuss_locked: snapshot.discussLocked,
            voice_entry: snapshot.voiceEntry,
            voice_speaker: snapshot.voiceSpeaker,
        },
        progress,
    );
    const next = buildLiveFlowSnapshotFromDiagnostics(mergedDiagnostics, {
        chatLoading: options?.chatLoading ?? snapshot.chatLoading,
        stageRun: options?.stageRun,
    });
    return {
        ...next,
        voiceEntry: next.voiceEntry ?? snapshot.voiceEntry,
        voiceSpeaker: next.voiceSpeaker ?? snapshot.voiceSpeaker,
        progressPolling: progress.status === 'running' || Boolean(next.progressPolling),
    };
}

export function mergeLiveFlowWithStageRun(
    snapshot: OrchestratorLiveFlowSnapshot,
    stageRun?: SharedOrchestratorStageRun | null,
): OrchestratorLiveFlowSnapshot {
    if (!stageRun?.stages?.length) {
        return snapshot;
    }
    const activeStageIndex = resolveActiveStageIndex({
        stagesCompleted: snapshot.stagesCompleted,
        currentStage: snapshot.currentStage,
        stageNumber: snapshot.stageNumber,
        stageRun,
    });
    const passedCount = stageRun.stages.filter((stage) => stage.status === 'passed').length;
    const stagesCompleted = Math.max(snapshot.stagesCompleted, passedCount);
    return {
        ...snapshot,
        stagesCompleted,
        activeStageIndex,
        stages: buildStageStatuses({
            stagesCompleted,
            activeStageIndex,
            autonomousIntent: snapshot.autonomousIntent,
            requiresApproval: snapshot.requiresApproval,
            chatLoading: snapshot.chatLoading,
        }),
    };
}

export const LIVE_FLOW_STATUS_LABELS: Record<LiveFlowStageStatus, string> = {
    pending: '대기',
    running: '진행 중',
    completed: '완료',
    awaiting_approval: '승인 대기',
    discuss: '협업 Q&A',
    failed: '실패',
};

type DecisionProposalItem = {
    title: string;
    category?: string;
    detail: string;
    benefit?: string | null;
    tradeoff?: string | null;
};

type DecisionTechnologyRecommendation = {
    title: string;
    source?: string;
    adoption_risk?: string;
    implementation_difficulty?: string;
    operating_cost?: string;
    alternative?: string;
    rationale?: string;
};

type DecisionNextAction = {
    title: string;
    action_type?: string;
    detail: string;
};

export function buildDecisionItems(options: {
    proposalItems?: DecisionProposalItem[];
    technologyRecommendations?: DecisionTechnologyRecommendation[];
    nextActionSuggestions?: DecisionNextAction[];
    newTechnologyCandidates?: string[];
    stageNumber?: number | null;
}): OrchestratorDecisionItem[] {
    const items: OrchestratorDecisionItem[] = [];
    const stageNumber = options.stageNumber ?? null;

    for (const [index, proposal] of (options.proposalItems || []).entries()) {
        items.push({
            id: `proposal-${proposal.title}-${index}`,
            title: proposal.title,
            summary: [proposal.detail, proposal.benefit ? `효과: ${proposal.benefit}` : '', proposal.tradeoff ? `트레이드오프: ${proposal.tradeoff}` : '']
                .filter(Boolean)
                .join('\n'),
            category: proposal.category || 'proposal',
            stageNumber,
            source: 'proposal',
        });
    }

    for (const [index, tech] of (options.technologyRecommendations || []).entries()) {
        items.push({
            id: `tech-${tech.title}-${index}`,
            title: tech.title,
            summary: [
                tech.rationale,
                tech.adoption_risk ? `도입 리스크: ${tech.adoption_risk}` : '',
                tech.implementation_difficulty ? `구현 난이도: ${tech.implementation_difficulty}` : '',
                tech.operating_cost ? `운영비: ${tech.operating_cost}` : '',
                tech.alternative ? `대체안: ${tech.alternative}` : '',
            ].filter(Boolean).join('\n'),
            category: 'technology',
            stageNumber,
            recommendedAction: tech.alternative,
            source: 'technology',
        });
    }

    for (const [index, candidate] of (options.newTechnologyCandidates || []).slice(0, 3).entries()) {
        if (items.some((item) => item.title === candidate)) {
            continue;
        }
        items.push({
            id: `candidate-${index}-${candidate}`,
            title: candidate,
            summary: '신기술 후보 — 반영 여부를 선택하세요.',
            category: 'technology',
            stageNumber,
            source: 'technology',
        });
    }

    for (const [index, action] of (options.nextActionSuggestions || []).entries()) {
        if (action.action_type === 'stage_hint') {
            continue;
        }
        items.push({
            id: `action-${action.title}-${index}`,
            title: action.title,
            summary: action.detail,
            category: action.action_type || 'next_action',
            stageNumber,
            recommendedAction: action.detail,
            source: 'next_action',
        });
    }

    return items.slice(0, 8);
}

export function mapEvidenceHighlights(
    raw?: Array<{
        title?: string;
        source_label?: string;
        why_it_matters?: string;
        url?: string | null;
        trust_score?: number;
    }> | null,
): Array<{
    title: string;
    sourceLabel: string;
    whyItMatters: string;
    url?: string | null;
    trustScore?: number;
}> {
    return (raw || []).map((item) => ({
        title: String(item.title || '근거'),
        sourceLabel: String(item.source_label || 'source'),
        whyItMatters: String(item.why_it_matters || ''),
        url: item.url || null,
        trustScore: typeof item.trust_score === 'number' ? item.trust_score : undefined,
    })).filter((item) => item.whyItMatters || item.title);
}

export function buildDecisionApplyMessage(item: {
    title: string;
    stageNumber?: number | null;
}): string {
    if (item.stageNumber) {
        return `${item.stageNumber}단계 진행해줘`;
    }
    return `「${item.title}」 반영하고 진행해줘`;
}

export function buildDecisionSaveMessage(item: { title: string; summary: string }): string {
    return `아이디어만 저장: ${item.title} — ${item.summary.slice(0, 200)}`;
}

export function buildDecisionReviseMessage(item: { title: string }): string {
    return `/revise ${item.title} 관련 설계를 수정하고 싶습니다.`;
}

export function buildApprovalProceedMessage(stageNumber?: number | null): string {
    if (stageNumber) {
        return `${stageNumber}단계 진행해줘`;
    }
    return '진행해';
}

export function buildApprovalReviseMessage(): string {
    return '수정: 설계를 변경하고 다시 제안해줘';
}

export function buildApprovalRejectMessage(): string {
    return '거절: 현재 설계안은 보류합니다';
}

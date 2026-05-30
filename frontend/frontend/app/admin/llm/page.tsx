'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import CapabilityPanel from '@/components/ui/CapabilityPanel';
import RuntimeConfigPanel from '@/components/ui/RuntimeConfigPanel';
import AdminDirectivePanel from '@/components/ui/AdminDirectivePanel';
import AdminExternalSearchPanel, {
    type AdminExternalSearchEndpoint,
    type AdminExternalSearchResponse,
} from '@/components/ui/AdminExternalSearchPanel';
import AdminGeneratorDetailModal from '@/components/admin/admin-generator-detail-modal';
import { resolveApiBaseUrl } from '@/lib/api';
import {
    buildSuggestedSelfRunDirectiveRequest,
    inferSuggestedSelfRunDirectiveTemplate,
    useOrchestratorChat,
    type AdvisoryEvidenceItem as ChatAdvisoryEvidenceItem,
    type AdvisoryNextAction as ChatAdvisoryNextAction,
    type AdvisoryQuestion as ChatAdvisoryQuestion,
    type ChatFunctionMode,
    type CompanionMode,
    type OrchestratorAgentKey,
    type OrchestratorChatResponse,
    type OrchestratorConversationMessage as ChatConversationMessage,
    type ProposalItem as ChatProposalItem,
    type RoutedTextFeatureKey,
    type SuggestedSelfRunPreview,
    type TargetPatchHint as ChatTargetPatchHint,
    type VoiceResponse,
} from '@/lib/use-orchestrator-chat';
import { useAdminWorkspace } from '@/lib/use-admin-workspace';
import { useAdminSelfRun } from '@/lib/use-admin-self-run';
import {
    applyGeneratorControlOrchestration,
    applyGeneratorModalActionOrchestration,
    buildGeneratorMarketplaceAppendix,
} from '@/lib/admin-generator-adapter';
import {
    MARKETPLACE_ORCHESTRATOR_BRIDGE_KEY,
    buildMarketplaceOrchestratorAdminLlmBridgePayload,
} from '@/lib/admin-orchestrator-bridge';
import {
    createAdminSessionExpiryChecker,
    extractApiErrorMessage,
    readJsonSafely,
    verifyAdminBootstrap,
} from '@/lib/admin-auth-session';
import {
    applyCapabilityActionOrchestration,
    buildCapabilityDirectiveRequest,
    inferCapabilityDirectiveTemplate,
} from '@/lib/admin-capability-orchestration';
import { createCapabilityDataHelpers } from '@/lib/admin-capability-data';
import { buildAdminCapabilityPanelData } from '@/lib/admin-capability-panel-data';
import { buildActiveAdminGeneratorData } from '@/lib/admin-generator-active-data';
import { buildAdminHeaderIntroData } from '@/lib/admin-header-intro-data';
import { buildAdminLlmStatusSectionData } from '@/lib/admin-llm-status-section';
import { buildAdminGeneratorModalBindings } from '@/lib/admin-generator-modal-bindings';
import { buildAdminGeneratorStatusSectionData } from '@/lib/admin-generator-status-section';
import { buildAdminResultSummarySectionData } from '@/lib/admin-result-summary-section';
import { buildAdminStageCardBindings } from '@/lib/admin-stage-card-bindings';
import { restoreAdminPresetTask, runPostAuthBootstrap } from '@/lib/admin-bootstrap-effects';
import { buildAdminLivePanelSummary } from '@/lib/admin-live-panel-summary';
import { bindAdminLiveWebSocket } from '@/lib/admin-live-websocket';
import {
    loadOrchestratorSystemSettingsBundle,
    saveOrchestratorSystemSettingsBundle,
} from '@/lib/admin-orchestrator-system-settings';
import {
    applyAdminRunFailureState,
    applyAdminRunOptions,
    applyAdminRunSuccessState,
    buildAdminOrchestrateRequestBody,
    normalizeAdminRunResult,
    resetAdminRunLifecycleState,
} from '@/lib/admin-run-lifecycle';
import { buildCapabilityPanelBindings } from '@/lib/admin-capability-panel-bindings';
import { buildCapabilityPanelDataProps } from '@/lib/admin-capability-panel-data-props';
import { createSelfRunDraftFlow } from '@/lib/admin-self-run-draft';
import {
    fetchLatestQuantCompareSummaryBundle,
    parseQuantCompareReport,
} from '@/lib/admin-quant-compare';
import {
    fetchRuntimeConfigBundle,
    saveRuntimeConfigBundle,
} from '@/lib/admin-runtime-config-data';
import { buildRuntimeConfigPanelData } from '@/lib/admin-runtime-panel-data';
import { buildRuntimeConfigPanelHelpers } from '@/lib/admin-runtime-panel-helpers';
import { buildRuntimeConfigPanelBindings } from '@/lib/admin-runtime-panel-bindings';
import { buildAdminRunResultNotice } from '@/lib/admin-run-result-notice';
import { createRuntimeConfigMutationHelpers } from '@/lib/admin-runtime-config-mutations';
import {
    applyAdminStageCommand as applyAdminStageCommandAdapter,
    applyStageIdeaPresetValue,
    DEFAULT_STAGE_IDEA_PRESETS,
} from '@/lib/admin-stage-command-adapter';
import {
    buildSuggestedSelfRunPreview,
    getSelfRunDirectiveScopeOption,
    getSelfRunDirectiveTemplateOption,
} from '@/lib/admin-self-run-presets';
import OrchestratorStageCardPanel, { type SharedOrchestratorStageRun } from '@shared/orchestrator-stage-card-panel';
import { fetchWithAdminBootstrapRetry } from '@/lib/admin-bootstrap-fetch';
import { hasSpeechSynthesisActivation } from '@/lib/admin-alert-speech';
import {
    ADMIN_SESSION_CHECK_INTERVAL_MS,
    ADMIN_SESSION_WARNING_WINDOW_MS,
    clearAdminToken,
    extendAdminSessionToken,
    getAdminToken,
    getAdminTokenExpiryMs,
    getRemainingSessionMinutes,
    setAdminToken,
} from '@/lib/admin-session';

type BrowserSpeechRecognition = {
    lang: string;
    interimResults: boolean;
    maxAlternatives: number;
    onresult: ((event: any) => void) | null;
    onerror: ((event: any) => void) | null;
    onend: (() => void) | null;
    start: () => void;
    stop: () => void;
};

declare global {
    interface Window {
        SpeechRecognition?: new () => BrowserSpeechRecognition;
        webkitSpeechRecognition?: new () => BrowserSpeechRecognition;
    }
}

const ORCHESTRATOR_CHAT_ABORT_MS = 90_000;

interface AgentResult { agent: string; role: string; model: string; output: string; }
interface AdminLLMPreset {
    id: string;
    title: string;
    mode: string;
    task: string;
    description: string;
}
interface OrchestratorCapabilityAction {
    id: string;
    title: string;
    summary: string;
    presetId: string;
    task: string;
    accentClassName: string;
}
interface OrchestratorCapabilityGroup {
    id: string;
    title: string;
    description: string;
    accentClassName: string;
    actions: OrchestratorCapabilityAction[];
}
type OrchestratorCapabilityState = 'standby' | 'active' | 'warning' | 'error';
interface OrchestratorCapabilitySummaryCard {
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
        evidence_snapshot_version?: string;
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
}
interface OrchestratorCapabilityGroupSummary {
    id: string;
    title: string;
    state: OrchestratorCapabilityState;
    summary: string;
    active_count: number;
    standby_count?: number;
    warning_count: number;
    error_count: number;
}
interface OrchestratorCapabilitySectionItem {
    label: string;
    value: string | number | boolean | null;
    note?: string | null;
}
interface OrchestratorCapabilitySection {
    id: string;
    title: string;
    items: OrchestratorCapabilitySectionItem[];
}
interface OrchestratorCapabilityValidationFinding {
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
}
interface OrchestratorCapabilityCodeExample {
    id: string;
    title: string;
    language: string;
    path: string;
    summary: string;
    code: string;
}
interface OrchestratorCapabilitySummaryResponse {
    generated_at: string;
    evidence_snapshot_version?: string;
    groups: OrchestratorCapabilityGroupSummary[];
    capabilities: OrchestratorCapabilitySummaryCard[];
}
interface OrchestratorCapabilityDetailResponse {
    generated_at: string;
    debug_signature?: string | null;
    sections_count?: number | null;
    capability: OrchestratorCapabilitySummaryCard;
    highlights: string[];
    suggested_actions: string[];
    sections: OrchestratorCapabilitySection[];
    evidence_bundle?: {
        contract?: {
            evidence_schema_version?: string;
            profile_id?: string;
            [key: string]: unknown;
        };
        execution?: {
            evidence_run_id?: string;
            evidence_generated_at?: string;
            self_run_status?: string | null;
            completion_gate_ok?: boolean | null;
            semantic_audit_ok?: boolean | null;
            [key: string]: unknown;
        };
        readiness?: {
            final_readiness_checklist_path?: string;
            automatic_validation_result_path?: string;
            output_audit_path?: string;
            operational_evidence_snapshot?: {
                targets?: Array<Record<string, unknown>>;
                verified_target_count?: number;
                required_target_count?: number;
                warning_target_count?: number;
                failed_target_count?: number;
                summary?: Record<string, unknown>;
                [key: string]: unknown;
            };
            operational_targets_by_id?: Record<string, Record<string, unknown>>;
            operational_evidence_summary?: {
                verified_count?: number;
                warning_count?: number;
                failed_count?: number;
                required_count?: number;
                warning_targets?: string[];
                max_latency_ms?: number | null;
                [key: string]: unknown;
            };
            operational_latency_summary?: {
                latency_warning?: boolean;
                warning_targets?: string[];
                warning_threshold_ms?: Record<string, number>;
                max_latency_ms?: number | null;
                verified_count?: number;
                warning_count?: number;
                failed_count?: number;
                required_count?: number;
                [key: string]: unknown;
            };
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
            target_patch_entries?: Array<{
                file_id?: string;
                path?: string;
                section_id?: string;
                feature_id?: string;
                chunk_id?: string;
                layer?: string;
                summary?: string;
                failure_tags?: string[];
                repair_tags?: string[];
            }>;
        };
    };
    target_file_ids?: string[];
    target_section_ids?: string[];
    target_feature_ids?: string[];
    target_chunk_ids?: string[];
    failure_tags?: string[];
    repair_tags?: string[];
    target_patch_entries?: Array<{
        file_id?: string;
        path?: string;
        section_id?: string;
        feature_id?: string;
        chunk_id?: string;
        layer?: string;
        summary?: string;
        failure_tags?: string[];
        repair_tags?: string[];
    }>;
    validation_findings: OrchestratorCapabilityValidationFinding[];
    improvement_code_examples: OrchestratorCapabilityCodeExample[];
}

type ProductReadinessGateStage = {
    id: string;
    ok: boolean;
    summary: string;
    evidence?: Record<string, unknown> | null;
};

type ProductReadinessHardGate = {
    ok?: boolean;
    summary?: string | null;
    failed_stages?: string[];
    stages?: ProductReadinessGateStage[];
    archive_path?: string | null;
};
interface OrchestratorCapabilityExecutionComparison {
    capabilityId: string;
    capturedAt: string;
    beforeDetail: OrchestratorCapabilityDetailResponse | null;
    afterDetail: OrchestratorCapabilityDetailResponse | null;
    runResult: OrchestrateResponse | null;
    selfRunResult?: AdminWorkspaceSelfRunResponse | null;
}

interface PendingCapabilityExecution {
    capabilityId: string;
    capturedAt: string;
    beforeDetail: OrchestratorCapabilityDetailResponse | null;
}

type GeneratorCapabilityDefinition = {
    id: string;
    title: string;
    summary: string;
    modalKey: 'capability' | 'runtime' | 'directive' | 'verification';
    finalStage: string;
    presetId: SelfPrepareMode;
    featureMode: ChatFunctionMode;
    defaultDirective: string;
    marketplaceOfferId: string;
};

type GeneratorDetailModalActionId = 'open-capability' | 'open-runtime' | 'open-directive' | 'apply-marketplace';

const normalizeCapabilityIdentityPart = (value: unknown): string => String(value ?? '')
    .trim()
    .replace(/\s+/g, ' ')
    .toLowerCase();

const getCapabilityFindingCompareKey = (finding: OrchestratorCapabilityValidationFinding): string => [
    finding.id,
    finding.severity,
    finding.title,
    finding.problem,
    finding.wrong_expression,
    finding.improvement,
    finding.source_path,
].map(normalizeCapabilityIdentityPart).join('::');

const getCapabilityFindingRenderKey = (
    finding: OrchestratorCapabilityValidationFinding,
    index: number,
): string => `${getCapabilityFindingCompareKey(finding)}::${index}`;

const getCapabilityCodeExampleRenderKey = (
    example: OrchestratorCapabilityCodeExample,
    index: number,
): string => [
    example.id,
    example.language,
    example.title,
    example.path,
    example.summary,
    String(index),
].map(normalizeCapabilityIdentityPart).join('::');

const buildCapabilityComparisonTitles = (
    sourceFindings: OrchestratorCapabilityValidationFinding[],
    targetFindings: OrchestratorCapabilityValidationFinding[],
): string[] => {
    const remainingCounts = new Map<string, number>();

    targetFindings.forEach((finding) => {
        const compareKey = getCapabilityFindingCompareKey(finding);
        remainingCounts.set(compareKey, (remainingCounts.get(compareKey) || 0) + 1);
    });

    return sourceFindings
        .filter((finding) => {
            const compareKey = getCapabilityFindingCompareKey(finding);
            const remaining = remainingCounts.get(compareKey) || 0;
            if (remaining <= 0) {
                return true;
            }
            remainingCounts.set(compareKey, remaining - 1);
            return false;
        })
        .map((finding) => finding.title)
        .slice(0, 4);
};

const GENERATOR_CAPABILITY_DEFINITIONS: GeneratorCapabilityDefinition[] = [
    {
        id: 'project-scanner',
        title: 'Project Scanner',
        summary: '구조 스캔과 진입점 식별을 수행하는 진단 코드생성기',
        modalKey: 'capability',
        finalStage: 'DESIGN',
        presetId: 'self-diagnosis',
        featureMode: 'research',
        defaultDirective: '프로젝트 구조를 스캔하고 상품화 가능한 엔진/템플릿 후보를 추려 관리자 작업문에 반영합니다.',
        marketplaceOfferId: 'project-scanner-starter',
    },
    {
        id: 'security-guard',
        title: 'Security Guard',
        summary: '권한·보안 경계와 노출 위험을 교정하는 보안 코드생성기',
        modalKey: 'verification',
        finalStage: 'TEST',
        presetId: 'self-diagnosis',
        featureMode: 'question',
        defaultDirective: '보안 경계, 인증, 권한 정책, 노출 리스크를 먼저 점검하고 바로 수정 가능한 상품형 가드를 제안합니다.',
        marketplaceOfferId: 'security-guard-bundle',
    },
    {
        id: 'self-healing-engine',
        title: 'Self-Healing Engine',
        summary: '실패 루프를 복구하고 마지막 단계까지 self-run을 연결하는 복구 코드생성기',
        modalKey: 'directive',
        finalStage: 'FIX',
        presetId: 'self-improvement',
        featureMode: 'action',
        defaultDirective: '실패 루프를 복구하고 9단계 self-run 기준으로 끝까지 밀어붙일 복구 지시문을 구성합니다.',
        marketplaceOfferId: 'self-healing-ops-suite',
    },
    {
        id: 'code-generator',
        title: 'Code Generator',
        summary: '생성 범위와 런타임 정책을 고정해 최종 산출물까지 밀어붙이는 구현 코드생성기',
        modalKey: 'runtime',
        finalStage: 'DONE',
        presetId: 'self-expansion',
        featureMode: 'action',
        defaultDirective: '실배포형 상품 생성 기준으로 코드, 런타임, 산출물 패키징까지 한 번에 완성하도록 작업문을 구성합니다.',
        marketplaceOfferId: 'code-generator-deployment-kit',
    },
];

type GeneratorMarketplaceOffer = {
    id: string;
    title: string;
    subtitle: string;
    description: string;
    priceLabel: string;
    badge: string;
    tags: string[];
    primaryActionLabel: string;
    secondaryActionLabel: string;
    generatorId: string;
};

const GENERATOR_MARKETPLACE_OFFERS: GeneratorMarketplaceOffer[] = [
    {
        id: 'project-scanner-starter',
        title: 'Project Scanner Starter Pack',
        subtitle: '구조 스캔 · 엔트리포인트 맵 · 상품화 후보 추출',
        description: '레거시/신규 프로젝트를 스캔해 폴더 구조, 엔진 후보, 진입점, 상품화 가능 모듈을 정리하는 분석형 상품입니다.',
        priceLabel: '₩189,000',
        badge: '진단형',
        tags: ['scanner', 'architecture', 'inventory', 'starter'],
        primaryActionLabel: '작업문에 반영',
        secondaryActionLabel: '스캔 결과를 관리자 지시문과 마켓 진열 설명으로 동시 반영',
        generatorId: 'project-scanner',
    },
    {
        id: 'security-guard-bundle',
        title: 'Security Guard Hardening Bundle',
        subtitle: '인증 · 권한 · 노출 차단 · 운영 가드',
        description: '관리자 권한, 동적 실행 경계, 노출 위험을 점검하고 상품화 가능한 보안형 상품입니다.',
        priceLabel: '₩249,000',
        badge: '보안형',
        tags: ['security', 'auth', 'policy', 'guard'],
        primaryActionLabel: '보안 상품화',
        secondaryActionLabel: '보안 점검 기준을 즉시 지시문과 검증 흐름에 반영',
        generatorId: 'security-guard',
    },
    {
        id: 'self-healing-ops-suite',
        title: 'Self-Healing Ops Suite',
        subtitle: '자동 복구 · 장애 루프 제거 · 운영 안정화',
        description: '실패 루프 분석, 자동 재시도, self-run 복구, 운영 메모 누적을 상품 형태로 제공하는 운영 복구형 상품입니다.',
        priceLabel: '₩279,000',
        badge: '복구형',
        tags: ['self-run', 'healing', 'ops', 'recovery'],
        primaryActionLabel: '복구 상품화',
        secondaryActionLabel: '복구 지시문과 단계 카드 흐름을 동시에 강화',
        generatorId: 'self-healing-engine',
    },
    {
        id: 'code-generator-deployment-kit',
        title: 'Code Generator Deployment Kit',
        subtitle: '완성형 생성 · 패키징 · 배포 스모크 기준',
        description: '실배포 가능한 코드 생성, 런타임 정책, 배포 패키징, 최종 스모크 기준까지 포함한 구현형 상품입니다.',
        priceLabel: '₩329,000',
        badge: '구현형',
        tags: ['generator', 'deployment', 'packaging', 'delivery'],
        primaryActionLabel: '구현 상품화',
        secondaryActionLabel: '배포 기준 작업문과 마켓 진열 문구를 즉시 생성',
        generatorId: 'code-generator',
    },
];

interface OrchestrationSpec {
    mode?: string;
    pipeline?: string[];
    required_files?: string[];
    validation_profile?: string;
    dod_targets?: string[];
    reasoning?: string;
    spec_source?: string;
    fallback_reason?: string | null;
    manual_steps?: string[];
}
type ConversationMessage = ChatConversationMessage;
type AdvisoryQuestion = ChatAdvisoryQuestion;
type AdvisoryEvidenceItem = ChatAdvisoryEvidenceItem;
type AdvisoryNextAction = ChatAdvisoryNextAction;
type ProposalItem = ChatProposalItem;
type TargetPatchHint = ChatTargetPatchHint;
interface FeatureOrchestrateActionPayload {
    feature_id: string;
    project_name: string;
    prompt: string;
    template_id?: string;
    photo_reference?: string;
    photo_content_type?: string;
    photo_size?: number;
    final_enabled?: boolean;
    context_tags?: string[];
}

const parseFeatureOrchestrateActionPayload = (payload: unknown): FeatureOrchestrateActionPayload | null => {
    if (!payload || typeof payload !== 'object') return null;
    const source = payload as Record<string, unknown>;
    const featureId = String(source.feature_id || '').trim();
    const projectName = String(source.project_name || '').trim();
    const prompt = String(source.prompt || '').trim();
    if (!featureId || !projectName || !prompt) {
        return null;
    }
    const contextTags = Array.isArray(source.context_tags)
        ? source.context_tags.map((item) => String(item || '').trim()).filter(Boolean)
        : [];
    return {
        feature_id: featureId,
        project_name: projectName,
        prompt,
        template_id: source.template_id ? String(source.template_id).trim() : undefined,
        photo_reference: source.photo_reference ? String(source.photo_reference).trim() : undefined,
        photo_content_type: source.photo_content_type ? String(source.photo_content_type).trim() : undefined,
        photo_size: typeof source.photo_size === 'number' ? source.photo_size : undefined,
        final_enabled: typeof source.final_enabled === 'boolean' ? source.final_enabled : true,
        context_tags: contextTags,
    };
};
interface SemanticAuditChecklistItem {
    id: string;
    label: string;
    passed: boolean;
    critical?: boolean;
    score: number;
    max_score: number;
    reason?: string | null;
    evidence?: string | null;
}
interface OrchestrateResponse {
    task: string;
    mode: string;
    run_id?: string;
    pipeline: string[];
    results: AgentResult[];
    final_output: string;
    applied?: boolean;
    output_dir?: string;
    failed_output_dir?: string;
    output_audit_path?: string;
    output_archive_path?: string;
    completion_gate_ok?: boolean;
    completion_gate_error?: string | null;
    completion_summary?: string | null;
    semantic_audit_ran?: boolean;
    semantic_audit_ok?: boolean;
    semantic_audit_error?: string | null;
    semantic_audit_summary?: string | null;
    semantic_audit_score?: number | null;
    semantic_audit_max_score?: number | null;
    semantic_audit_threshold?: number | null;
    semantic_audit_checklist?: SemanticAuditChecklistItem[];
    semantic_audit_report_path?: string | null;
    apply_error?: string | null;
    state_history?: string[];
    orchestration_spec?: OrchestrationSpec;
    conversation?: ConversationMessage[];
    completion_judge?: {
        product_readiness_hard_gate?: ProductReadinessHardGate;
        [key: string]: unknown;
    };
}

type AccelerationMode = 'cpu_only' | 'gpu_only';
type ModelRouteKey =
    | 'default'
    | 'reasoning'
    | 'coding'
    | 'chat'
    | 'voice_chat'
    | 'planner'
    | 'coder'
    | 'reviewer'
    | 'designer'
    | 'smart_planner'
    | 'smart_executor'
    | 'smart_designer';
type ModelGradeKey = 'light' | 'balanced' | 'quality';

interface ModelGradeChoice {
    key: ModelGradeKey;
    label: string;
    description: string;
    targets: Partial<Record<ModelRouteKey, string>>;
}

interface FeaturedModelAction {
    label: string;
    description: string;
    targets: Partial<Record<ModelRouteKey, string>>;
}

interface FunctionalModelGradeRow {
    key: string;
    title: string;
    description: string;
    routeKeys: ModelRouteKey[];
    grades: ModelGradeChoice[];
    featuredAction?: FeaturedModelAction;
}

interface GpuRuntimeDevice {
    name: string;
    memory_total_mb: number;
    memory_used_mb: number;
    utilization_gpu: number;
}

const CONVERSATION_STAGE_LABELS: Record<string, string> = {
    general: '일반 협업',
    discovery: '요구 정제',
    research: '근거 조사',
    implementation: '구현 설계',
};

const ROUTED_TEXT_FEATURES: Array<{
    key: RoutedTextFeatureKey;
    title: string;
    description: string;
    lockedMode: CompanionMode;
    lockedLogics: string[];
}> = [
        {
            key: 'question',
            title: '질문 응답',
            description: '무엇이든 궁금한 내용을 바로 묻는 일반 질문 흐름입니다.',
            lockedMode: 'hybrid',
            lockedLogics: ['핵심 답변 우선', '웹조사 자동 비활성', '되묻기 최소화'],
        },
        {
            key: 'research',
            title: '정보 수집',
            description: '비교, 조사, 최신 동향, 공식 문서 확인 같은 탐색 흐름입니다.',
            lockedMode: 'research',
            lockedLogics: ['외부 근거 탐색 우선', '근거 등급 분리', '요약 후 상세 근거 정리'],
        },
        {
            key: 'action',
            title: '작업 지시',
            description: '수정, 구현, 자가진단, 적용처럼 바로 행동해야 하는 흐름입니다.',
            lockedMode: 'project',
            lockedLogics: ['구현 단계 우선', '되묻기 최소화', '실행 또는 실행계획 우선'],
        },
    ];

type AdminTerminalCoreMode = 'implementation' | 'pass_review' | 'feature_innovation';

const ADMIN_TERMINAL_CORE_MODES: Array<{
    id: AdminTerminalCoreMode;
    label: string;
    description: string;
}> = [
        {
            id: 'implementation',
            label: '구현 모드',
            description: '코드/수정/적용 중심으로 즉시 실행합니다.',
        },
        {
            id: 'pass_review',
            label: '통과 모드',
            description: '검증 기준 확인과 통과 판정을 우선합니다.',
        },
        {
            id: 'feature_innovation',
            label: '신기술 모드',
            description: '신기술 탐색과 확장 제안을 중심으로 진행합니다.',
        },
    ];

const DEFAULT_ROUTED_TEXT_AGENTS: Record<RoutedTextFeatureKey, OrchestratorAgentKey> = {
    question: 'chat',
    research: 'reasoner',
    action: 'chat',
};

const REASONER_REQUIRED_AGENT_TARGETS = ['voice', 'research'] as const;
const REASONER_EXPANSION_AGENT_TARGETS = ['text', 'question', 'action'] as const;

const detectRoutedTextFeature = (content: string): RoutedTextFeatureKey | null => {
    const normalized = content.trim().toLowerCase();
    if (!normalized) {
        return null;
    }
    const researchMarkers = ['정보수집', '정보 수집', '조사', '검색', '찾아', '수집', '자료', '근거', '공식문서', '트렌드', '최신'];
    if (researchMarkers.some((marker) => normalized.includes(marker))) {
        return 'research';
    }
    const actionMarkers = ['자가진단', '자가개선', '자가확장', '실행', '수정', '적용', '구현', '만들어', '고쳐', '바꿔', '처리해', '즉시', '바로'];
    if (actionMarkers.some((marker) => normalized.includes(marker))) {
        return 'action';
    }
    const questionMarkers = ['?', '왜', '뭐', '무엇', '어떻게', '어떤', '설명', '알려', '궁금', '차이'];
    if (normalized.endsWith('?') || questionMarkers.some((marker) => normalized.includes(marker))) {
        return 'question';
    }
    return null;
};


const normalizeCapabilitySpeechText = (text: string) => (
    text
        .replace(/·/g, ', ')
        .replace(/=/g, ' ')
        .replace(/\//g, ' 중 ')
        .replace(/\s+/g, ' ')
        .trim()
);

const buildCapabilitySpeechReason = (
    capability: OrchestratorCapabilitySummaryCard,
) => {
    if (capability.id === 'project-scanner') {
        return `프로젝트 스캐너. ${normalizeCapabilitySpeechText(capability.metric)}. ${normalizeCapabilitySpeechText(capability.detail || '')}`;
    }
    if (capability.id === 'code-generator') {
        return `코드 생성 기준 미달. ${normalizeCapabilitySpeechText(capability.metric)}. ${normalizeCapabilitySpeechText(capability.detail || '')}`;
    }
    if (capability.id === 'self-healing-engine') {
        return `자가 복구 경고. ${normalizeCapabilitySpeechText(capability.detail || capability.metric)}`;
    }
    if (capability.id === 'security-guard') {
        return `파이썬 보안 경광판. ${normalizeCapabilitySpeechText(capability.metric)}. ${normalizeCapabilitySpeechText(capability.detail || '')}`;
    }
    return `${capability.title}. ${normalizeCapabilitySpeechText(capability.metric)}. ${normalizeCapabilitySpeechText(capability.detail || '')}`;
};

const buildCapabilityAlertSpeech = (
    summary: OrchestratorCapabilitySummaryResponse | null,
    detail: OrchestratorCapabilityDetailResponse | null,
) => {
    const problemCards = (summary?.capabilities || []).filter(
        (capability) => capability.attention_required || capability.state === 'error' || capability.state === 'warning'
    );
    const speechParts: string[] = [];
    const scannerCard = problemCards.find(
        (capability) => capability.id === 'project-scanner'
    );
    if (scannerCard) {
        speechParts.push(buildCapabilitySpeechReason(scannerCard));
    }
    const topProblem = problemCards.find(
        (capability) => capability.id !== 'project-scanner'
    ) || problemCards[0];
    if (topProblem && topProblem !== scannerCard) {
        speechParts.push(buildCapabilitySpeechReason(topProblem));
    }
    if (detail) {
        speechParts.push(
            `현재 선택 기능. ${buildCapabilitySpeechReason(detail.capability)}`
        );
        if (detail.suggested_actions.length > 0) {
            speechParts.push(
                `권장 조치. ${normalizeCapabilitySpeechText(detail.suggested_actions[0])}`
            );
        }
    }
    if (speechParts.length === 0) {
        return '';
    }
    return `관리자 오케스트레이터 경고 알림입니다. ${speechParts.join('. ')}. 즉시 실행 또는 작업문 적용으로 개선을 시작하세요.`;
};

const getCapabilityStateClassName = (state: OrchestratorCapabilityState | undefined) => {
    if (state === 'error') {
        return 'border-[#f85149] bg-[rgba(248,81,73,0.12)] text-[#ffb3ad]';
    }
    if (state === 'warning') {
        return 'border-[#d29922] bg-[rgba(210,153,34,0.12)] text-[#f2cc60]';
    }
    if (state === 'active') {
        return 'border-[#238636] bg-[rgba(35,134,54,0.12)] text-[#3fb950]';
    }
    return 'border-[#6e7681] bg-[rgba(110,118,129,0.12)] text-[#c9d1d9]';
};

const getCapabilityStateText = (capability: OrchestratorCapabilitySummaryCard | undefined) => (
    capability?.state_label || capability?.state || 'standby'
);

const getCapabilityPriorityScore = (capability: OrchestratorCapabilitySummaryCard) => {
    if (capability.state === 'error') {
        return 300;
    }
    if (capability.state === 'warning') {
        return 200;
    }
    if (capability.attention_required) {
        return 100;
    }
    if (capability.state === 'active') {
        return 50;
    }
    return 0;
};

const pickPrimaryCapability = (
    capabilities: OrchestratorCapabilitySummaryCard[],
) => [...capabilities].sort((left, right) => {
    const scoreDiff = getCapabilityPriorityScore(right) - getCapabilityPriorityScore(left);
    if (scoreDiff !== 0) {
        return scoreDiff;
    }
    const leftAge = typeof left.last_run_age_hours === 'number' ? left.last_run_age_hours : Number.MAX_SAFE_INTEGER;
    const rightAge = typeof right.last_run_age_hours === 'number' ? right.last_run_age_hours : Number.MAX_SAFE_INTEGER;
    if (leftAge !== rightAge) {
        return leftAge - rightAge;
    }
    return left.title.localeCompare(right.title, 'ko');
})[0] || null;

const advisoryActionTypeLabel = (actionType: string) => {
    if (actionType === 'self-expansion') return '자가확장 추천';
    if (actionType === 'self-improvement') return '자가개선 추천';
    if (actionType === 'research') return '근거 조사';
    return '대화 보강';
};

interface GpuRuntimeInfo {
    available: boolean;
    devices: GpuRuntimeDevice[];
    error?: string;
}

interface RuntimeProfileSettings {
    selected_profile?: string;
    max_tokens_per_step?: number;
    default_request_max_tokens?: number;
    chat_request_max_tokens?: number;
    default_agent_max_tokens?: number;
    planner_max_tokens?: number;
    coder_max_tokens?: number;
    reviewer_max_tokens?: number;
    step_timeout_sec?: number;
    job_timeout_sec?: number;
    agent_http_timeout_sec?: number;
    forensic_max_inventory?: number;
    max_force_retries?: number;
    force_complete?: boolean;
    allow_synthetic_fallback?: boolean;
    min_files?: number;
    min_dirs?: number;
    model_tuning_level?: number;
    token_tuning_level?: number;
    timeout_tuning_level?: number;
}

interface RuntimeExecutionControl {
    acceleration_mode?: AccelerationMode;
    num_gpu?: number;
    num_thread?: number;
}

interface RuntimeProfile {
    key: string;
    label: string;
    description: string;
    hardware_hint: string;
    model_routes: Record<ModelRouteKey, string>;
    execution_controls?: Partial<Record<ModelRouteKey, RuntimeExecutionControl>>;
    settings: RuntimeProfileSettings;
}

interface AdvisoryControls {
    clarification_questions_enabled: boolean;
    max_clarification_questions: number;
    evidence_panel_enabled: boolean;
    max_evidence_items: number;
    next_action_suggestions_enabled: boolean;
    max_next_actions: number;
    scientific_reasoning_enabled?: boolean;
    systems_thinking_enabled?: boolean;
    future_tech_expansion_enabled?: boolean;
    cross_domain_synthesis_enabled?: boolean;
    innovation_scenarios_enabled?: boolean;
    max_innovation_scenarios?: number;
    max_system_design_alternatives?: number;
}

interface OrchestratorRuntimeConfig {
    max_tokens_per_step: number;
    default_request_max_tokens: number;
    chat_request_max_tokens?: number;
    default_agent_max_tokens: number;
    planner_max_tokens: number;
    coder_max_tokens: number;
    reviewer_max_tokens: number;
    step_timeout_sec: number;
    job_timeout_sec: number;
    agent_http_timeout_sec: number;
    planner_agent_timeout_sec?: number;
    coder_agent_timeout_sec?: number;
    reviewer_agent_timeout_sec?: number;
    index_context_timeout_sec?: number;
    planner_prompt_char_limit?: number;
    coder_prompt_char_limit?: number;
    reviewer_prompt_char_limit?: number;
    planner_context_char_limit?: number;
    coder_context_char_limit?: number;
    reviewer_context_char_limit?: number;
    experience_memory_char_limit?: number;
    forensic_max_inventory: number;
    max_force_retries: number;
    force_complete: boolean;
    allow_synthetic_fallback: boolean;
    code_generation_strategy?: string;
    min_files: number;
    min_dirs: number;
    model_tuning_level?: number;
    token_tuning_level?: number;
    timeout_tuning_level?: number;
    selected_profile?: string;
    gpu_only_preferred?: boolean;
    model_routes: Record<ModelRouteKey, string>;
    execution_controls?: Partial<Record<ModelRouteKey, RuntimeExecutionControl>>;
    advisory_controls?: AdvisoryControls;
    available_models: string[];
    gpu_runtime?: GpuRuntimeInfo;
    runtime_profiles?: RuntimeProfile[];
    config_path: string;
}

interface LiveLogEntry {
    id: string;
    event: string;
    stage?: string;
    message: string;
    timestamp: string;
    severity?: 'info' | 'success' | 'warning' | 'error';
}

interface LiveProgressSnapshot {
    runId: string;
    task: string;
    mode: string;
    pipeline: string[];
    status: 'idle' | 'running' | 'success' | 'failed';
    currentState: string;
    stateHistory: string[];
    logs: LiveLogEntry[];
    wsConnected: boolean;
    updatedAt: string;
}

interface LiveSemanticAuditSnapshot {
    passed?: boolean;
    error?: string;
    summary?: string;
    score?: number;
    maxScore?: number;
    threshold?: number;
    checklist: SemanticAuditChecklistItem[];
}

interface AdminWorkspaceTextEntry {
    name: string;
    path: string;
    kind: 'dir' | 'file';
    size_bytes?: number | null;
    modified_at?: number | null;
}

interface AdminWorkspaceTextListing {
    root_path: string;
    current_path: string;
    parent_path?: string | null;
    entries: AdminWorkspaceTextEntry[];
}

interface AdminWorkspaceTextFileResponse {
    path: string;
    size_bytes: number;
    content: string;
}

interface AdminSystemSettingField {
    key: string;
    label: string;
    value: string;
    sensitive: boolean;
    multiline: boolean;
}

interface AdminSystemSettingSection {
    id: string;
    title: string;
    usage: string;
    description: string;
    fields: AdminSystemSettingField[];
}

interface AdminSystemSettingsSummary {
    admin_domain: string;
    api_domain: string;
    local_api_base_url: string;
    marketplace_host_root: string;
    marketplace_upload_root: string;
    nginx_http_port: string;
    nginx_https_port: string;
    selected_profile: string;
    default_model: string;
    chat_model: string;
    voice_chat_model: string;
}

interface AdminSystemSettingsResponse {
    env_path: string;
    runtime_config_path: string;
    sections: AdminSystemSettingSection[];
    summary: AdminSystemSettingsSummary;
}

interface QuantCompareRow {
    grade: string;
    model: string;
    status: string;
    elapsedSeconds: number | null;
    responseChars: number | null;
    gpuUtilMax: number | null;
    gpuUtilAvg: number | null;
    gpuVramMaxMib: number | null;
}

interface QuantCompareSummary {
    path: string;
    reportDate: string;
    prompt: string;
    maxTokens: string;
    rows: QuantCompareRow[];
    previewLines: string[];
    issues: string[];
}

interface AdminWorkspaceSelfPrepareResponse {
    source_path: string;
    requested_mode: string;
    suggested_mode: string;
    recommended_work_dir?: string | null;
    experiment_clone_path?: string | null;
    clone_copied_files?: number | null;
    analysis_summary: {
        total_directories: number;
        total_files: number;
        total_text_files: number;
        included_text_files: number;
        content_chars: number;
        tree_truncated: boolean;
    };
    skipped_directories: string[];
    tree_preview: string;
    key_text_files: AdminWorkspaceTextEntry[];
    suggested_task: string;
}

interface AdminWorkspaceSelfRunResponse {
    approval_id: string;
    status: 'running' | 'pending_approval' | 'failed' | 'no_changes' | 'applied_to_source';
    requested_mode?: string;
    execution_mode?: string;
    directive_template?: string;
    directive_scope?: string;
    directive_request?: string;
    source_path: string;
    experiment_clone_path: string;
    analysis_summary: {
        total_directories: number;
        total_files: number;
        total_text_files: number;
        included_text_files: number;
        content_chars: number;
        tree_truncated: boolean;
    };
    tree_preview: string;
    key_text_files: AdminWorkspaceTextEntry[];
    diff_summary: {
        added_files: string[];
        modified_files: string[];
        deleted_files: string[];
        total_changed_files: number;
    };
    orchestration_result: OrchestrateResponse;
    report_preview: string;
    report_path: string;
    executed_task: string;
    started_at?: string;
    finished_at?: string;
    orchestration_error?: string;
    worker_pid?: number | null;
    worker_log_path?: string;
    worker_alive?: boolean | null;
    running_seconds?: number | null;
    runtime_diagnostic?: string;
    stage_run?: SharedOrchestratorStageRun | null;
}

type ImportTarget = 'task' | 'chat';
type ImportMode = 'append' | 'replace';
type SelfPrepareMode = 'self-diagnosis' | 'self-improvement' | 'self-expansion';
type SelfRunDirectiveTemplate = '' | 'debug_remediation_loop' | 'video_ad_clarity' | 'video_ad_conversion' | 'video_ad_speed_optimization' | 'video_ad_storytelling' | 'video_ad_quality_upgrade' | 'video_ad_new_tech' | 'admin_ops_efficiency' | 'marketplace_conversion' | 'llm_cost_latency';
type SelfRunDirectiveScope = 'preset_default' | 'diagnosis_only' | 'targeted_implementation' | 'feature_expansion' | 'modernization';
type CapabilitySyncPhase = 'live' | 'confirming' | 'stale' | 'retrying';

type LiveApplyState = 'idle' | 'running' | 'applied' | 'response-only' | 'failed';

const ADMIN_LLM_PRESET_TASK_KEY = 'admin_llm_preset_task_v1';
const ADMIN_ORCHESTRATOR_LIVE_PROGRESS_KEY = 'admin_orchestrator_live_progress_v1';
const ADMIN_ORCHESTRATOR_WORK_DIR_KEY = 'admin_orchestrator_work_dir_v1';
const ADMIN_SELF_RUN_RECORD_KEY = 'admin_self_run_record_v1';
const ADMIN_CAPABILITY_ALERT_VOICE_ENABLED_KEY = 'admin_capability_alert_voice_enabled_v1';
const ADMIN_CAPABILITY_AUTO_REFRESH_MS = 60000;
const ADMIN_CAPABILITY_STALE_THRESHOLD_SEC = 45;
const ADMIN_CAPABILITY_PENDING_CLEAR_CONFIRMATIONS = 2;
const ADMIN_CAPABILITY_FOCUS_REFRESH_DEBOUNCE_MS = 3000;
const ORCHESTRATOR_STAGE_ORDER = ['DESIGN', 'PLAN', 'GENERATE', 'BUILD', 'REFINER_FIXER', 'TEST', 'REFLEXION', 'FIX', 'DONE'];
const ORCHESTRATOR_AGENT_OPTIONS: Array<{
    key: OrchestratorAgentKey;
    label: string;
    summary: string;
    modelKey: 'chat' | 'voice_chat' | 'reasoning' | 'coding';
}> = [
        {
            key: 'chat',
            label: '챗봇',
            summary: '일반 질의와 관리자 협업 대화',
            modelKey: 'chat',
        },
        {
            key: 'voice_chat',
            label: '음성',
            summary: '음성 입력용 응답 모델',
            modelKey: 'voice_chat',
        },
        {
            key: 'reasoner',
            label: '추론',
            summary: '판단 근거와 해석 중심 응답',
            modelKey: 'reasoning',
        },
        {
            key: 'coder',
            label: '코딩',
            summary: '구현안과 코드 중심 응답',
            modelKey: 'coding',
        },
    ];

const ORCHESTRATOR_RUNTIME_FIELDS: Array<[keyof OrchestratorRuntimeConfig, string]> = [
    ['max_tokens_per_step', '단계 최대 토큰'],
    ['default_request_max_tokens', '기본 요청 토큰'],
    ['chat_request_max_tokens', '대화 전용 토큰'],
    ['default_agent_max_tokens', '기본 에이전트 토큰'],
    ['planner_max_tokens', 'planner 전용 토큰'],
    ['coder_max_tokens', 'coder 전용 토큰'],
    ['reviewer_max_tokens', 'reviewer 전용 토큰'],
    ['step_timeout_sec', '단계 제한 시간(초)'],
    ['job_timeout_sec', '전체 작업 시간(초)'],
    ['agent_http_timeout_sec', 'LLM HTTP 시간(초)'],
    ['forensic_max_inventory', '포렌식 파일 최대 개수'],
    ['max_force_retries', '최대 재시도 횟수'],
    ['min_files', '최소 파일 개수'],
    ['min_dirs', '최소 폴더 개수'],
];

const ORCHESTRATOR_MODEL_ROUTE_FIELDS: Array<[ModelRouteKey, string]> = [
    ['default', '기본'],
    ['reasoning', '추론'],
    ['coding', '코딩'],
    ['chat', '챗봇'],
    ['voice_chat', '음성'],
    ['planner', 'planner'],
    ['coder', 'coder'],
    ['reviewer', 'reviewer'],
    ['designer', 'designer'],
    ['smart_planner', 'smart planner'],
    ['smart_executor', 'smart executor'],
    ['smart_designer', 'smart designer'],
];

const CODING_Q4_TAG = 'qwen2.5-coder:32b-q4km';
const CODING_Q5_TAG = 'qwen2.5-coder:32b-q5km';
const CODING_Q6_TAG = 'qwen2.5-coder:32b-q6k';
const CODING_Q8_TAG = 'qwen2.5-coder:32b-q8';

const FUNCTIONAL_MODEL_GRADE_ROWS: FunctionalModelGradeRow[] = [
    {
        key: 'conversation',
        title: '협업 대화',
        description: '관리자 텍스트/음성 대화 응답을 q4/q5/q6/q8 양자화 등급으로 맞춥니다.',
        routeKeys: ['chat', 'voice_chat'],
        grades: [
            {
                key: 'light',
                label: '경량',
                description: 'Q4_K_M 속도 우선',
                targets: {
                    chat: CODING_Q4_TAG,
                    voice_chat: CODING_Q4_TAG,
                },
            },
            {
                key: 'balanced',
                label: '균형',
                description: 'Q5_K_M 균형형 선택지',
                targets: {
                    chat: CODING_Q5_TAG,
                    voice_chat: CODING_Q5_TAG,
                },
            },
            {
                key: 'quality',
                label: '고품질',
                description: 'Q6_K 고품질 선택지',
                targets: {
                    chat: CODING_Q6_TAG,
                    voice_chat: CODING_Q6_TAG,
                },
            },
        ],
        featuredAction: {
            label: '최상위 품질 (Q8)',
            description: '협업 대화 라우트를 Q8 실험 라인으로 즉시 전환',
            targets: {
                chat: CODING_Q8_TAG,
                voice_chat: CODING_Q8_TAG,
            },
        },
    },
    {
        key: 'reasoning',
        title: '추론 / 계획',
        description: 'reasoning, planner, smart planner 를 q4/q5/q6/q8 양자화 등급으로 맞춥니다.',
        routeKeys: ['reasoning', 'planner', 'smart_planner'],
        grades: [
            {
                key: 'light',
                label: '경량',
                description: 'Q4_K_M 속도 우선',
                targets: {
                    reasoning: CODING_Q4_TAG,
                    planner: CODING_Q4_TAG,
                    smart_planner: CODING_Q4_TAG,
                },
            },
            {
                key: 'balanced',
                label: '균형',
                description: 'Q5_K_M 균형형 선택지',
                targets: {
                    reasoning: CODING_Q5_TAG,
                    planner: CODING_Q5_TAG,
                    smart_planner: CODING_Q5_TAG,
                },
            },
            {
                key: 'quality',
                label: '고품질',
                description: 'Q6_K 고품질 선택지',
                targets: {
                    reasoning: CODING_Q6_TAG,
                    planner: CODING_Q6_TAG,
                    smart_planner: CODING_Q6_TAG,
                },
            },
        ],
        featuredAction: {
            label: '최상위 품질 (Q8)',
            description: '추론 / 계획 라우트를 Q8 실험 라인으로 즉시 전환',
            targets: {
                reasoning: CODING_Q8_TAG,
                planner: CODING_Q8_TAG,
                smart_planner: CODING_Q8_TAG,
            },
        },
    },
    {
        key: 'coding',
        title: '코딩 / 생성',
        description: 'coding, coder, smart executor 를 양자화 등급으로 맞춥니다.',
        routeKeys: ['coding', 'coder', 'smart_executor'],
        grades: [
            {
                key: 'light',
                label: '경량',
                description: 'Q4_K_M 속도 우선',
                targets: {
                    coding: CODING_Q4_TAG,
                    coder: CODING_Q4_TAG,
                    smart_executor: CODING_Q4_TAG,
                },
            },
            {
                key: 'balanced',
                label: '균형',
                description: 'Q5_K_M 균형형 선택지',
                targets: {
                    coding: CODING_Q5_TAG,
                    coder: CODING_Q5_TAG,
                    smart_executor: CODING_Q5_TAG,
                },
            },
            {
                key: 'quality',
                label: '고품질',
                description: 'Q6_K 고품질 선택지',
                targets: {
                    coding: CODING_Q6_TAG,
                    coder: CODING_Q6_TAG,
                    smart_executor: CODING_Q6_TAG,
                },
            },
        ],
        featuredAction: {
            label: '최상위 품질 (Q8)',
            description: '수동 드롭다운 없이 Q8 실험 라인으로 즉시 전환',
            targets: {
                coding: CODING_Q8_TAG,
                coder: CODING_Q8_TAG,
                smart_executor: CODING_Q8_TAG,
            },
        },
    },
    {
        key: 'review',
        title: '리뷰 / 검증',
        description: 'reviewer 라우트를 q4/q5/q6/q8 양자화 등급으로 맞춥니다.',
        routeKeys: ['reviewer'],
        grades: [
            {
                key: 'light',
                label: '경량',
                description: 'Q4_K_M 속도 우선',
                targets: {
                    reviewer: CODING_Q4_TAG,
                },
            },
            {
                key: 'balanced',
                label: '균형',
                description: 'Q5_K_M 균형형 선택지',
                targets: {
                    reviewer: CODING_Q5_TAG,
                },
            },
            {
                key: 'quality',
                label: '고품질',
                description: 'Q6_K 고품질 선택지',
                targets: {
                    reviewer: CODING_Q6_TAG,
                },
            },
        ],
        featuredAction: {
            label: '최상위 품질 (Q8)',
            description: 'reviewer 라우트를 Q8 실험 라인으로 즉시 전환',
            targets: {
                reviewer: CODING_Q8_TAG,
            },
        },
    },
    {
        key: 'design',
        title: '디자인 / 보조',
        description: 'designer, smart designer 를 q4/q5/q6/q8 양자화 등급으로 맞춥니다.',
        routeKeys: ['designer', 'smart_designer'],
        grades: [
            {
                key: 'light',
                label: '경량',
                description: 'Q4_K_M 속도 우선',
                targets: {
                    designer: CODING_Q4_TAG,
                    smart_designer: CODING_Q4_TAG,
                },
            },
            {
                key: 'balanced',
                label: '균형',
                description: 'Q5_K_M 균형형 선택지',
                targets: {
                    designer: CODING_Q5_TAG,
                    smart_designer: CODING_Q5_TAG,
                },
            },
            {
                key: 'quality',
                label: '고품질',
                description: 'Q6_K 고품질 선택지',
                targets: {
                    designer: CODING_Q6_TAG,
                    smart_designer: CODING_Q6_TAG,
                },
            },
        ],
        featuredAction: {
            label: '최상위 품질 (Q8)',
            description: 'designer 계열을 Q8 실험 라인으로 즉시 전환',
            targets: {
                designer: CODING_Q8_TAG,
                smart_designer: CODING_Q8_TAG,
            },
        },
    },
];

const EXECUTION_MODE_LABELS: Record<AccelerationMode, string> = {
    cpu_only: 'CPU 전용',
    gpu_only: 'GPU 전용',
};

const DEFAULT_HYBRID_NUM_GPU = 32;

const RUNTIME_POLICY_HINTS: Record<AccelerationMode, string> = {
    cpu_only: '현재 초안 값을 그대로 저장합니다.',
    gpu_only: '현재 초안 값을 그대로 저장합니다.',
};

const QUANT_COMPARE_REPORT_PREFIX = 'ollama_quant_compare_';
const ORCHESTRATOR_SYSTEM_SECTION_IDS = ['llm_defaults', 'orchestrator_self_engine'];
const DEFAULT_ADVISORY_CONTROLS: AdvisoryControls = {
    clarification_questions_enabled: true,
    max_clarification_questions: 3,
    evidence_panel_enabled: true,
    max_evidence_items: 5,
    next_action_suggestions_enabled: true,
    max_next_actions: 3,
    scientific_reasoning_enabled: true,
    systems_thinking_enabled: true,
    future_tech_expansion_enabled: true,
    cross_domain_synthesis_enabled: true,
    innovation_scenarios_enabled: true,
    max_innovation_scenarios: 5,
    max_system_design_alternatives: 4,
};

const parseNullableNumber = (value: string) => {
    const trimmed = value.trim();
    if (!trimmed || trimmed === '-' || trimmed.toLowerCase() === 'n/a') {
        return null;
    }
    const parsed = Number(trimmed);
    return Number.isFinite(parsed) ? parsed : null;
};

const resolveHybridExecutionNumGpu = (control?: RuntimeExecutionControl) => {
    const candidate = control?.num_gpu;
    if (typeof candidate === 'number' && Number.isFinite(candidate) && candidate > 0) {
        return candidate;
    }
    return DEFAULT_HYBRID_NUM_GPU;
};

const formatMetricNumber = (value: number | null, digits = 0, suffix = '') => {
    if (value == null) {
        return '-';
    }
    return `${value.toFixed(digits)}${suffix}`;
};

const getMissingGradeModels = (
    availableModels: string[],
    targets: Partial<Record<ModelRouteKey, string>>,
) => {
    const availableSet = new Set(availableModels);
    return Array.from(new Set(Object.values(targets).filter((modelName): modelName is string => Boolean(modelName) && !availableSet.has(modelName))));
};

const isGradeActive = (
    modelRoutes: Record<ModelRouteKey, string>,
    targets: Partial<Record<ModelRouteKey, string>>,
) => Object.entries(targets).every(([routeKey, modelName]) => modelRoutes[routeKey as ModelRouteKey] === modelName);

const RUNTIME_PROFILE_CUSTOM_KEY = 'custom';
const RUNTIME_TUNING_LEVELS = [-1, 0, 1] as const;

type RuntimeTuningLevel = typeof RUNTIME_TUNING_LEVELS[number];

const CORE_RUNTIME_MODEL_ROUTE_KEYS: ModelRouteKey[] = [
    'default',
    'reasoning',
    'coding',
    'planner',
    'coder',
    'reviewer',
    'smart_planner',
    'smart_executor',
];

const EXPERIENCE_RUNTIME_MODEL_ROUTE_KEYS: ModelRouteKey[] = [
    'chat',
    'voice_chat',
    'designer',
    'smart_designer',
];

const TOKEN_TUNING_PRESETS: Record<RuntimeTuningLevel, Partial<OrchestratorRuntimeConfig>> = {
    '-1': {
        max_tokens_per_step: 4096,
        default_request_max_tokens: 4096,
        chat_request_max_tokens: 768,
        default_agent_max_tokens: 1024,
        planner_max_tokens: 1024,
        coder_max_tokens: 1024,
        reviewer_max_tokens: 1024,
        planner_prompt_char_limit: 2200,
        coder_prompt_char_limit: 2600,
        reviewer_prompt_char_limit: 2200,
        planner_context_char_limit: 700,
        coder_context_char_limit: 900,
        reviewer_context_char_limit: 700,
        experience_memory_char_limit: 400,
    },
    '0': {
        max_tokens_per_step: 4096,
        default_request_max_tokens: 4096,
        chat_request_max_tokens: 1024,
        default_agent_max_tokens: 2048,
        planner_max_tokens: 2048,
        coder_max_tokens: 2048,
        reviewer_max_tokens: 2048,
        planner_prompt_char_limit: 3200,
        coder_prompt_char_limit: 3600,
        reviewer_prompt_char_limit: 3200,
        planner_context_char_limit: 1400,
        coder_context_char_limit: 1800,
        reviewer_context_char_limit: 1400,
        experience_memory_char_limit: 800,
    },
    '1': {
        max_tokens_per_step: 6144,
        default_request_max_tokens: 6144,
        chat_request_max_tokens: 1536,
        default_agent_max_tokens: 3072,
        planner_max_tokens: 3072,
        coder_max_tokens: 3072,
        reviewer_max_tokens: 3072,
        planner_prompt_char_limit: 4200,
        coder_prompt_char_limit: 4800,
        reviewer_prompt_char_limit: 4200,
        planner_context_char_limit: 1800,
        coder_context_char_limit: 2400,
        reviewer_context_char_limit: 1800,
        experience_memory_char_limit: 1200,
    },
};

const TIMEOUT_TUNING_PRESETS: Record<RuntimeTuningLevel, Partial<OrchestratorRuntimeConfig>> = {
    '-1': {
        step_timeout_sec: 300,
        job_timeout_sec: 1200,
        agent_http_timeout_sec: 180,
        planner_agent_timeout_sec: 60,
        coder_agent_timeout_sec: 60,
        reviewer_agent_timeout_sec: 60,
        index_context_timeout_sec: 10,
    },
    '0': {
        step_timeout_sec: 420,
        job_timeout_sec: 1800,
        agent_http_timeout_sec: 180,
        planner_agent_timeout_sec: 60,
        coder_agent_timeout_sec: 90,
        reviewer_agent_timeout_sec: 60,
        index_context_timeout_sec: 15,
    },
    '1': {
        step_timeout_sec: 600,
        job_timeout_sec: 2400,
        agent_http_timeout_sec: 240,
        planner_agent_timeout_sec: 90,
        coder_agent_timeout_sec: 120,
        reviewer_agent_timeout_sec: 90,
        index_context_timeout_sec: 20,
    },
};

const getRuntimeProfileByKey = (
    runtimeDraft: OrchestratorRuntimeConfig,
    profileKey?: string,
) => runtimeDraft.runtime_profiles?.find((profile) => profile.key === profileKey);

const pickAvailableRuntimeModel = (
    availableModels: string[],
    candidates: Array<string | undefined>,
    fallback: string,
) => {
    const availableSet = new Set(availableModels);
    for (const candidate of candidates) {
        if (candidate && availableSet.has(candidate)) {
            return candidate;
        }
    }
    return fallback;
};

const buildTunedModelRoutes = (
    runtimeDraft: OrchestratorRuntimeConfig,
    level: RuntimeTuningLevel,
) => {
    const baseProfile = getRuntimeProfileByKey(
        runtimeDraft,
        runtimeDraft.selected_profile && runtimeDraft.selected_profile !== RUNTIME_PROFILE_CUSTOM_KEY
            ? runtimeDraft.selected_profile
            : runtimeDraft.runtime_profiles?.[0]?.key,
    );
    const nextRoutes: Record<ModelRouteKey, string> = {
        ...runtimeDraft.model_routes,
    };

    if (level === 0 && baseProfile) {
        return {
            ...nextRoutes,
            ...baseProfile.model_routes,
        };
    }

    const lowCoreModel = pickAvailableRuntimeModel(
        runtimeDraft.available_models,
        ['qwen2.5-coder:7b', CODING_Q4_TAG],
        runtimeDraft.model_routes.coder,
    );
    const balancedCoreModel = pickAvailableRuntimeModel(
        runtimeDraft.available_models,
        [CODING_Q4_TAG, CODING_Q5_TAG, 'qwen2.5-coder:7b'],
        runtimeDraft.model_routes.coder,
    );
    const highCoreModel = pickAvailableRuntimeModel(
        runtimeDraft.available_models,
        [CODING_Q5_TAG, CODING_Q6_TAG, CODING_Q8_TAG, CODING_Q4_TAG],
        runtimeDraft.model_routes.coder,
    );
    const lowExperienceModel = pickAvailableRuntimeModel(
        runtimeDraft.available_models,
        [CODING_Q4_TAG, 'qwen2.5-coder:7b'],
        runtimeDraft.model_routes.chat,
    );
    const highExperienceModel = pickAvailableRuntimeModel(
        runtimeDraft.available_models,
        [CODING_Q6_TAG, CODING_Q5_TAG, CODING_Q8_TAG, CODING_Q4_TAG],
        runtimeDraft.model_routes.chat,
    );

    const selectedCoreModel = level < 0 ? lowCoreModel : level > 0 ? highCoreModel : balancedCoreModel;
    const selectedExperienceModel = level < 0 ? lowExperienceModel : level > 0 ? highExperienceModel : (baseProfile?.model_routes.chat || lowExperienceModel);

    CORE_RUNTIME_MODEL_ROUTE_KEYS.forEach((routeKey) => {
        nextRoutes[routeKey] = selectedCoreModel;
    });
    EXPERIENCE_RUNTIME_MODEL_ROUTE_KEYS.forEach((routeKey) => {
        nextRoutes[routeKey] = selectedExperienceModel;
    });
    return nextRoutes;
};

const mergeStageHistory = (history: string[], stage?: string) => {
    if (!stage || !ORCHESTRATOR_STAGE_ORDER.includes(stage)) {
        return history;
    }
    if (history.includes(stage)) {
        return history;
    }
    return [...history, stage].sort(
        (left, right) => ORCHESTRATOR_STAGE_ORDER.indexOf(left) - ORCHESTRATOR_STAGE_ORDER.indexOf(right),
    );
};

const formatFileSize = (sizeBytes?: number | null) => {
    if (!sizeBytes || sizeBytes <= 0) {
        return '-';
    }
    if (sizeBytes >= 1024 * 1024) {
        return `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`;
    }
    if (sizeBytes >= 1024) {
        return `${(sizeBytes / 1024).toFixed(1)} KB`;
    }
    return `${sizeBytes} B`;
};

const presetForSelfPrepareMode = (requestedMode: SelfPrepareMode) => {
    if (requestedMode === 'self-improvement') {
        return getOrchestratorPresetById('self-improvement');
    }
    if (requestedMode === 'self-expansion') {
        return getOrchestratorPresetById('self-expansion');
    }
    return getOrchestratorPresetById('self-diagnosis');
};

const ORCHESTRATOR_PRESETS: AdminLLMPreset[] = [
    {
        id: 'self-diagnosis',
        title: '자가진단',
        mode: 'review',
        description: '상태머신, Reflexion, 메모리, 동적 도구 경계를 진단합니다.',
        task: `오케스트레이터 자가진단 실행

1. detect_mode와 planner 기반 orchestration_spec 결정 흐름 점검
2. Reflexion 단계와 Root Cause Analysis 주입 경로 점검
3. knowledge 경험 메모리 누적/재주입 흐름 점검
4. dynamic_python_tool 권한과 보안 경계 점검
5. 관리자 UI 연결 누락 여부 점검`,
    },
    {
        id: 'self-improvement',
        title: '자가개선',
        mode: 'full',
        description: '실패 루프 품질과 생성 품질을 개선하는 작업 프리셋입니다.',
        task: `오케스트레이터 자가개선 적용

1. planner가 mode/pipeline/required_files/validation_profile/dod_targets를 JSON으로 먼저 결정하도록 유지/보강
2. reviewer Root Cause Analysis를 다음 GENERATE 프롬프트 최상단에 강제 주입하도록 유지/보강
3. Reflexion -> FIX -> GENERATE 재시도 품질을 높이기
4. knowledge 경험 메모리 재사용 품질을 높이기
5. 관리자 UI 결과 가시성을 개선`,
    },
    {
        id: 'self-expansion',
        title: '자가확장',
        mode: 'plan',
        description: 'React, Go, Rust, 런타임 도구 확장까지 포함한 확장 계획 프리셋입니다.',
        task: `오케스트레이터 자가확장 계획 수립

1. React/Next.js, Go, Rust 작업에서 required_files와 validation_profile을 동적으로 설계하는 확장안 제시
2. dynamic_python_tool 기반의 보안/성능/API 검증 도구 확장 전략 제시
3. 프레임워크별 경험 메모리 분류 저장 구조 제시
4. 관리자 UI에서 자가진단 -> 자가개선 -> 자가확장 순차 운영 흐름 제시`,
    },
];

const getOrchestratorPresetById = (presetId: string) => (
    ORCHESTRATOR_PRESETS.find((preset) => preset.id === presetId) || null
);

const getOrchestratorCapabilityActionById = (capabilityId: string) => (
    ORCHESTRATOR_CAPABILITY_GROUPS.flatMap((group) => group.actions).find((action) => action.id === capabilityId) || null
);

const ORCHESTRATOR_CAPABILITY_GROUPS: OrchestratorCapabilityGroup[] = [
    {
        id: 'diagnosis-control',
        title: '진단 통솔',
        description: '현재 프로젝트 상태와 연결 구조, 보안 경계를 기능 단위로 바로 점검합니다.',
        accentClassName: 'border-[#1f6feb] bg-[rgba(31,111,235,0.08)]',
        actions: [
            {
                id: 'project-scanner',
                title: 'Project Scanner',
                summary: '워크스페이스 구조, 핵심 파일, 누락 위험 지점을 스캔합니다.',
                presetId: 'self-diagnosis',
                task: `project scanner 실행\n\n1. 현재 워크스페이스의 핵심 디렉터리와 실행 진입점 정리\n2. 최근 변경 위험이 큰 파일과 설정 누락 가능성 점검\n3. 운영상 치명도 기준으로 즉시 확인할 항목 5개 이내 요약`,
                accentClassName: 'border-[#1f6feb] text-[#79c0ff]',
            },
            {
                id: 'dependency-graph',
                title: 'Dependency Graph',
                summary: '프런트엔드, 백엔드, 라우터, 런타임 의존관계를 추적합니다.',
                presetId: 'self-diagnosis',
                task: `dependency graph 분석\n\n1. admin/frontend/backend/orchestrator 연결 흐름을 의존관계 기준으로 도식화\n2. 고정 연결로 취급해야 하는 라우터, 프록시, API 결합점 식별\n3. 변경 시 파급 범위가 큰 의존성 순서대로 정리`,
                accentClassName: 'border-[#58a6ff] text-[#58a6ff]',
            },
            {
                id: 'security-guard',
                title: 'Security Guard',
                summary: '관리자 권한, 동적 실행 경계, 노출 위험을 점검합니다.',
                presetId: 'self-diagnosis',
                task: `security guard 점검\n\n1. 관리자 인증 경로와 권한 검증 누락 여부 점검\n2. dynamic tool, self-run, runtime 설정 저장 경계 검토\n3. 즉시 차단이 필요한 보안/오동작 위험과 완화 조치 제시`,
                accentClassName: 'border-[#d29922] text-[#f2cc60]',
            },
        ],
    },
    {
        id: 'improvement-control',
        title: '개선 통솔',
        description: '실패 복구와 생성 품질 보강 작업을 목적별로 분리해 실행합니다.',
        accentClassName: 'border-[#238636] bg-[rgba(35,134,54,0.08)]',
        actions: [
            {
                id: 'self-healing-engine',
                title: 'Self-Healing Engine',
                summary: '실패 원인 분석과 복구 순서를 실행형 작업으로 정리합니다.',
                presetId: 'self-improvement',
                task: `self-healing engine 적용\n\n1. 최근 실패 루프와 apply_error, build/test 차단 원인을 우선순위로 분류\n2. 복구 순서를 즉시 수정 가능한 단계로 세분화\n3. 재발 방지용 검증 포인트와 로그 보강 항목을 함께 제시`,
                accentClassName: 'border-[#238636] text-[#3fb950]',
            },
            {
                id: 'code-generator',
                title: 'Code Generator',
                summary: '필요한 코드 생성과 수정 범위를 실무형 지시문으로 준비합니다.',
                presetId: 'self-improvement',
                task: `code generator 준비\n\n1. 요청 목표를 만족하는 최소 변경 파일과 구현 순서 확정\n2. 기존 연결을 깨지 않는 코드 생성/수정 범위를 정의\n3. 변경 직후 필요한 검증과 기록 항목까지 포함해 실행안 작성`,
                accentClassName: 'border-[#2ea043] text-[#56d364]',
            },
        ],
    },
    {
        id: 'expansion-control',
        title: '확장 통솔',
        description: '관리 명령과 모델 운용을 분리해 확장/운영 준비를 수행합니다.',
        accentClassName: 'border-[#8957e5] bg-[rgba(137,87,229,0.08)]',
        actions: [
            {
                id: 'admin-command-interface',
                title: 'Admin Command Interface',
                summary: '관리자 명령 흐름과 운영 절차를 지시형 태스크로 분리합니다.',
                presetId: 'self-expansion',
                task: `admin command interface 설계\n\n1. 관리자 대시보드에서 분리해야 할 명령군과 목적 정의\n2. 자가진단/개선/확장 흐름에 맞는 명령 인터페이스 제안\n3. 각 명령이 어떤 실행 결과와 로그를 남겨야 하는지 정리`,
                accentClassName: 'border-[#a371f7] text-[#d2a8ff]',
            },
            {
                id: 'ollama-model-controller',
                title: 'Ollama Model Controller',
                summary: '모델 라우팅, 프로필, GPU 운용을 분리된 제어 주제로 다룹니다.',
                presetId: 'self-expansion',
                task: `ollama model controller 계획\n\n1. 현재 모델 라우트와 권장 프로필을 운영 목적별로 정리\n2. q4/q5/q6/q8 계층을 어떤 작업군에 배치할지 제안\n3. 관리자 화면에서 즉시 제어해야 할 모델/프로필 항목을 우선순위로 정리`,
                accentClassName: 'border-[#8957e5] text-[#d2a8ff]',
            },
        ],
    },
];

const MANDATORY_ORCHESTRATOR_RULES = [
    'Planner가 mode/pipeline/required_files/DoD를 JSON으로 먼저 결정',
    'Reflexion: reviewer Root Cause Analysis 강제 작성',
    'RCA를 다음 GENERATE 프롬프트 최상단에 주입',
    '성공/실패 경험 메모리 knowledge/ 폴더 누적',
    'dynamic_python_tool로 backend/llm/tools 런타임 도구 생성 허용',
    '파일 수 27개 이상',
    '빈 파일/빈 폴더 금지 (세밀 검증)',
    'TODO/pass/추후구현 제한',
    'file_manifest 선생성',
    '상태머신: DESIGN→PLAN→GENERATE→BUILD→TEST→REFLEXION→FIX→DONE',
    '동일 실패 최대 3회 재시도',
    '실패 보고서 docs/failure_report.md 생성',
    '단계별 아티팩트 로그 기록',
    'docs 스냅샷을 knowledge/runs로 복사',
];

const OPTIONAL_ORCHESTRATOR_RULES = [
    '상태머신: DESIGN→PLAN→GENERATE→BUILD→TEST→REFLEXION→FIX→DONE',
    '동일 실패 최대 3회 재시도',
    '실패 보고서 docs/failure_report.md 생성',
    '단계별 아티팩트 로그 기록',
    'orchestration_spec 응답 상세 표시',
];

const parseApprovalIdTimestamp = (approvalId?: string | null) => {
    const raw = String(approvalId || '').trim();
    const match = raw.match(/^(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})_/);
    if (!match) {
        return null;
    }
    const [, year, month, day, hour, minute, second] = match;
    const timestamp = new Date(
        Number(year),
        Number(month) - 1,
        Number(day),
        Number(hour),
        Number(minute),
        Number(second),
    ).getTime();
    return Number.isFinite(timestamp) ? timestamp : null;
};

export default function AdminLLMPage() {
    const router = useRouter();
    const api = resolveApiBaseUrl();
    const frameRootRef = useRef<HTMLDivElement | null>(null);
    const [authChecked, setAuthChecked] = useState(false);
    const [embeddedMode, setEmbeddedMode] = useState(false);
    const [authStatusMessage, setAuthStatusMessage] = useState('관리자 인증 확인 중...');
    const [task, setTask] = useState('');
    const [mode, setMode] = useState('review');
    const manualMode = false;
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<OrchestrateResponse | null>(null);
    const [error, setError] = useState('');
    const [llmStatus, setLlmStatus] = useState<any>(null);
    const [activeResult, setActiveResult] = useState(0);
    const [enabledRules, setEnabledRules] = useState<string[]>(OPTIONAL_ORCHESTRATOR_RULES);
    const [selectedPreset, setSelectedPreset] = useState<AdminLLMPreset | null>(null);
    const [selectedCapabilityActionId, setSelectedCapabilityActionId] = useState('');
    const [capabilitySummary, setCapabilitySummary] = useState<OrchestratorCapabilitySummaryResponse | null>(null);
    const [capabilityDetail, setCapabilityDetail] = useState<OrchestratorCapabilityDetailResponse | null>(null);
    const [capabilityExecutionComparison, setCapabilityExecutionComparison] = useState<OrchestratorCapabilityExecutionComparison | null>(null);
    const [capabilityLoading, setCapabilityLoading] = useState(false);
    const [capabilityMessage, setCapabilityMessage] = useState('');
    const [capabilitySyncPhase, setCapabilitySyncPhase] = useState<CapabilitySyncPhase>('live');
    const [capabilityLastLiveRefreshAt, setCapabilityLastLiveRefreshAt] = useState<number | null>(null);
    const [capabilityLastLiveRefreshElapsedSec, setCapabilityLastLiveRefreshElapsedSec] = useState<number>(0);
    const [capabilityVoiceAlertEnabled, setCapabilityVoiceAlertEnabled] = useState(true);
    const capabilityRefreshInFlightRef = useRef(false);
    const capabilityLastRefreshAtRef = useRef(0);
    const capabilityPendingClearTrackerRef = useRef<Record<string, { pendingLatched: boolean; clearConfirmations: number; lastPendingVersion: string }>>({});
    const [capabilityBootstrapReady, setCapabilityBootstrapReady] = useState(false);
    const [requestedCapabilityId, setRequestedCapabilityId] = useState('');
    const [activeGeneratorModal, setActiveGeneratorModal] = useState<'capability' | 'runtime' | 'directive' | 'verification' | null>(null);
    const [activeGeneratorId, setActiveGeneratorId] = useState('');
    const [runtimeConfig, setRuntimeConfig] = useState<OrchestratorRuntimeConfig | null>(null);
    const [runtimeDraft, setRuntimeDraft] = useState<OrchestratorRuntimeConfig | null>(null);
    const [runtimeLoading, setRuntimeLoading] = useState(false);
    const [runtimeSaving, setRuntimeSaving] = useState(false);
    const [runtimeMessage, setRuntimeMessage] = useState('');
    const [runtimeEditorOpen, setRuntimeEditorOpen] = useState(false);
    const [externalSearchEndpoint, setExternalSearchEndpoint] = useState<AdminExternalSearchEndpoint>('news');
    const [externalSearchQuery, setExternalSearchQuery] = useState('');
    const [externalSearchPlaceId, setExternalSearchPlaceId] = useState('');
    const [externalSearchLoading, setExternalSearchLoading] = useState(false);
    const [externalSearchMessage, setExternalSearchMessage] = useState('');
    const [externalSearchResult, setExternalSearchResult] = useState<AdminExternalSearchResponse | null>(null);
    const [quantCompareLoading, setQuantCompareLoading] = useState(false);
    const [quantCompareMessage, setQuantCompareMessage] = useState('');
    const [quantCompareSummary, setQuantCompareSummary] = useState<QuantCompareSummary | null>(null);
    const [orchestratorSystemSettings, setOrchestratorSystemSettings] = useState<AdminSystemSettingsResponse | null>(null);
    const [orchestratorSystemDraft, setOrchestratorSystemDraft] = useState<Record<string, string>>({});
    const [orchestratorSystemOpen, setOrchestratorSystemOpen] = useState<Record<string, boolean>>({});
    const [orchestratorSystemLoading, setOrchestratorSystemLoading] = useState(false);
    const [orchestratorSystemSaving, setOrchestratorSystemSaving] = useState(false);
    const [orchestratorSystemMessage, setOrchestratorSystemMessage] = useState('');
    const pendingCapabilityExecutionRef = useRef<PendingCapabilityExecution | null>(null);
    const detailCapabilityAction = capabilityDetail
        ? getOrchestratorCapabilityActionById(capabilityDetail.capability.id)
        : null;
    const [wsConnected, setWsConnected] = useState(false);
    const [liveRunId, setLiveRunId] = useState('');
    const [liveTask, setLiveTask] = useState('');
    const [liveMode, setLiveMode] = useState('');
    const [livePipeline, setLivePipeline] = useState<string[]>([]);
    const [liveStatus, setLiveStatus] = useState<'idle' | 'running' | 'success' | 'failed'>('idle');
    const [liveCurrentState, setLiveCurrentState] = useState('');
    const [featureActionRunning, setFeatureActionRunning] = useState(false);
    const hardNavigate = (path: string) => {
        if (typeof window !== 'undefined') {
            window.location.assign(path);
            return;
        }
        router.push(path);
    };
    useEffect(() => {
        if (typeof window === 'undefined') {
            return;
        }
        setEmbeddedMode(new URLSearchParams(window.location.search).get('embedded') === '1');
    }, []);

    useEffect(() => {
        if (!embeddedMode || typeof window === 'undefined' || window.parent === window || !frameRootRef.current) {
            return;
        }

        let isMounted = true;

        // 관리자 대시보드 iframe 높이를 실제 컨텐츠 높이에 맞춰 동기화한다.
        const postHeight = () => {
            if (!isMounted || !frameRootRef.current || !window.parent) {
                return;
            }
            try {
                const rootHeight = frameRootRef.current.scrollHeight || 0;
                const documentHeight = Math.max(
                    document.documentElement?.scrollHeight || 0,
                    document.body?.scrollHeight || 0,
                    rootHeight,
                );
                // Check if parent window is still accessible before posting
                if (window.parent !== window && window.parent.location) {
                    window.parent.postMessage(
                        {
                            type: 'admin-llm-frame-height',
                            height: documentHeight,
                        },
                        window.location.origin,
                    );
                }
            } catch (error) {
                // Silently ignore errors from iframe communication (e.g., parent window closed)
                if (error instanceof Error && !error.message.includes('closed')) {
                    console.debug('postHeight error:', error);
                }
            }
        };

        const resizeObserver = new ResizeObserver(() => {
            if (isMounted) {
                window.requestAnimationFrame(postHeight);
            }
        });
        resizeObserver.observe(frameRootRef.current);

        const immediateTimer = window.setTimeout(() => {
            if (isMounted) postHeight();
        }, 0);
        const delayedTimer = window.setTimeout(() => {
            if (isMounted) postHeight();
        }, 400);
        postHeight();

        return () => {
            isMounted = false;
            window.clearTimeout(immediateTimer);
            window.clearTimeout(delayedTimer);
            resizeObserver.disconnect();
        };
    }, [embeddedMode]);

    const [liveStateHistory, setLiveStateHistory] = useState<string[]>([]);
    const [liveLogs, setLiveLogs] = useState<LiveLogEntry[]>([]);
    const [liveUpdatedAt, setLiveUpdatedAt] = useState('');
    const [liveSemanticAudit, setLiveSemanticAudit] = useState<LiveSemanticAuditSnapshot | null>(null);
    const [liveOrchestrationSpec, setLiveOrchestrationSpec] = useState<OrchestrationSpec | null>(null);
    const [liveOutputDir, setLiveOutputDir] = useState('');
    const [workOutputDir, setWorkOutputDir] = useState('');
    const [generatorProjectName, setGeneratorProjectName] = useState('my-project');
    const [continueInPlace, setContinueInPlace] = useState(true);
    const [liveApplyState, setLiveApplyState] = useState<LiveApplyState>('idle');
    const [liveApplyError, setLiveApplyError] = useState('');
    const [importTarget, setImportTarget] = useState<ImportTarget>('chat');
    const [adminStageNoteDraft, setAdminStageNoteDraft] = useState('');
    const [adminStageSubstepChecks, setAdminStageSubstepChecks] = useState<Record<string, boolean>>({});
    const [adminStageRevisionNote, setAdminStageRevisionNote] = useState('');
    const liveRunIdRef = useRef('');
    const sessionWarningExpRef = useRef<number | null>(null);
    const capabilityAlertSignatureRef = useRef('');
    const adminFinalPassGuide = 'Copilot의 1차 검증 결과는 내부 확인용이며, 최종 통과는 사용자가 오케스트레이터에서 직접 실험한 뒤 인정합니다.';

    const handleAdminUnauthorized = (message = '관리자 인증 정보가 유효하지 않습니다. 다시 로그인해 주세요.') => {
        clearAdminToken();
        setAuthChecked(false);
        setAuthStatusMessage(message);
        setRuntimeMessage('');
        setWorkspaceMessage('');
        setSelfPrepareMessage('');
        setSelfRunMessage('');
        setWorkspaceListing(null);
        setRuntimeConfig(null);
        setRuntimeDraft(null);
        router.replace('/admin/login');
    };

    const token = () => getAdminToken() || localStorage.getItem('token') || '';

    const logBootstrapMetric = useCallback((metric: {
        name: string;
        elapsedMs: number;
        status?: number;
        outcome: 'fulfilled' | 'rejected' | 'sync';
        error?: string;
    }) => {
        console.info('[admin-llm-bootstrap-metric]', metric);
    }, []);

    const normalizeMetricUrl = useCallback((value: string) => {
        const raw = String(value || '').trim();
        if (!raw) {
            return raw;
        }
        try {
            const url = new URL(raw, typeof window !== 'undefined' ? window.location.origin : undefined);
            const currentOrigin = typeof window !== 'undefined' ? window.location.origin : '';
            const isLocalOrigin = url.hostname === 'localhost' || url.hostname === '127.0.0.1';
            if (!url.origin || url.origin === 'null' || url.origin === currentOrigin || isLocalOrigin) {
                return `${url.pathname}${url.search}${url.hash}`;
            }
            return url.toString();
        } catch {
            return raw;
        }
    }, []);

    const adminFetch = async (input: RequestInfo | URL, init?: RequestInit) => {
        const accessToken = token();
        if (!accessToken) {
            handleAdminUnauthorized('관리자 인증 정보가 없습니다. 다시 로그인해 주세요.');
            throw new Error('관리자 인증 정보가 없습니다.');
        }

        const headers = new Headers(init?.headers || {});
        if (!headers.has('Authorization')) {
            headers.set('Authorization', `Bearer ${accessToken}`);
        }

        const requestUrl = typeof input === 'string' ? input : String(input);
        const metricUrl = normalizeMetricUrl(requestUrl);
        const response = await fetchWithAdminBootstrapRetry(input, {
            ...init,
            headers,
        }, {
            traceLabel: `admin-fetch:${metricUrl}`,
            onMetric: (metric) => {
                // Suppress abort noise for self-run-record (ERR_ABORTED on page reload is expected)
                const isAbortError =
                    metric.outcome === 'error' &&
                    (metric as any).error != null &&
                    String((metric as any).error).includes('AbortError');
                const isSelfRunRecordEndpoint =
                    String(metric.input || '').includes('workspace-self-run-record');
                if (isAbortError && isSelfRunRecordEndpoint) return;
                console.info('[admin-fetch-metric]', {
                    ...metric,
                    input: normalizeMetricUrl(String(metric.input || '')),
                    traceLabel: String(metric.traceLabel || '').replace(requestUrl, metricUrl),
                });
            },
        });

        if (response.status === 401 || response.status === 403) {
            const payload = await readJsonSafely(response.clone());
            const detail = extractApiErrorMessage(payload, response.status);
            handleAdminUnauthorized(detail);
            throw new Error(detail);
        }

        return response;
    };

    const speakText = (text: string) => {
        if (!text || typeof window === 'undefined' || !window.speechSynthesis || !hasSpeechSynthesisActivation()) {
            return false;
        }
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'ko-KR';
        window.speechSynthesis.speak(utterance);
        return true;
    };

    const {
        conversation,
        chatInput,
        chatLoading,
        voiceListening,
        chatAgentKey,
        voiceAgentKey,
        textFeatureAgents,
        chatFunctionMode,
        lastGroundingMode,
        lastGroundingNote,
        companionMode,
        lastWebResults,
        suggestedCompanionMode,
        suggestedCompanionReason,
        lastConversationStage,
        clarificationQuestions,
        evidenceHighlights,
        nextActionSuggestions,
        inferredGoal,
        proposalItems,
        newTechnologyCandidates,
        technologyRecommendations,
        targetPatchHints,
        conversationAssistExpanded,
        suggestedSelfRunPreview,
        recognitionRef,
        setConversation,
        setChatInput,
        setVoiceListening,
        setChatAgentKey,
        setVoiceAgentKey,
        setTextFeatureAgents,
        setChatFunctionMode,
        setCompanionMode,
        setConversationAssistExpanded,
        setSuggestedSelfRunPreview,
        appendConversationMessage,
        pushAssistantNotice,
        setUnifiedPrompt,
        appendUnifiedPrompt,
        getEffectiveTaskInput,
        getLatestUserConversationRequest,
        resolveReusableOutputDir,
        sendChatMessage,
        pushUserMessage,
        startVoiceInput,
    } = useOrchestratorChat({
        apiBaseUrl: api,
        adminFetch,
        getAdminToken: token,
        task,
        setTask,
        mode,
        manualMode,
        liveRunIdRef,
        runtimeDraft,
        runtimeConfig,
        workOutputDir,
        liveOutputDir,
        setWorkOutputDir,
        setLiveOutputDir,
        speakText,
    });
    const adminTerminalFocusedView = true;
    const miniConsoleLayout = true;
    const [adminCoreMode, setAdminCoreMode] = useState<AdminTerminalCoreMode>('implementation');

    useEffect(() => {
        if (adminCoreMode === 'implementation') {
            if (chatFunctionMode !== 'action') setChatFunctionMode('action');
            if (companionMode !== 'project') setCompanionMode('project');
            if (chatAgentKey !== 'coder') setChatAgentKey('coder');
            return;
        }
        if (adminCoreMode === 'pass_review') {
            if (chatFunctionMode !== 'question') setChatFunctionMode('question');
            if (companionMode !== 'hybrid') setCompanionMode('hybrid');
            if (chatAgentKey !== 'reasoner') setChatAgentKey('reasoner');
            return;
        }
        if (chatFunctionMode !== 'research') setChatFunctionMode('research');
        if (companionMode !== 'research') setCompanionMode('research');
        if (chatAgentKey !== 'reasoner') setChatAgentKey('reasoner');
    }, [adminCoreMode, chatAgentKey, chatFunctionMode, companionMode, setChatAgentKey, setChatFunctionMode, setCompanionMode]);
    const {
        workspaceListing,
        workspaceBrowsePath,
        workspaceLoading,
        workspaceMessage,
        importMode,
        setWorkspaceListing,
        setWorkspaceBrowsePath,
        setWorkspaceMessage,
        setImportMode,
        importWorkspaceFile,
        fetchWorkspaceListing,
        resolveWorkspacePath,
        syncWorkspacePath,
    } = useAdminWorkspace({
        apiBaseUrl: api,
        adminFetch,
        getEffectiveTaskInput,
        setUnifiedPrompt,
    });
    const {
        selfPrepareLoading,
        selfPrepareMessage,
        selfPrepareResult,
        selfRunLoading,
        selfRunApproveLoading,
        selfRunMessage,
        selfRunResult,
        selfRunDirectiveTemplate,
        selfRunDirectiveScope,
        selfRunDirectiveRequest,
        selfRunBusy,
        setSelfPrepareMessage,
        setSelfRunMessage,
        setSelfRunResult,
        setSelfRunDirectiveTemplate,
        setSelfRunDirectiveScope,
        setSelfRunDirectiveRequest,
        fetchSelfRunRecord,
        persistSelfRunRecord,
        restoreLatestSelfRunRecord,
        buildSelfRunStatusMessage,
        buildSelfRunStatusLabel,
        buildSelfRunPreview,
        buildSelfRunComparisonRows,
        prepareSelfWorkspace,
        createExperimentCloneOnly,
        executeSelfWorkflow,
        updateAdminStageStatus,
        runAdminOperationalVerification,
        approveSelfWorkflow,
    } = useAdminSelfRun({
        apiBaseUrl: api,
        adminFetch,
        adminFinalPassGuide,
        selfRunRecordStorageKey: ADMIN_SELF_RUN_RECORD_KEY,
        parseApprovalIdTimestamp,
        getEffectiveTaskInput,
        setUnifiedPrompt,
        pushAssistantNotice,
        resolveWorkspacePath,
        syncWorkspacePath,
        workOutputDir,
        liveOutputDir,
        setWorkOutputDir,
        setLiveOutputDir,
        applyPreparedMode: (requestedMode, prepared) => {
            setMode(prepared.suggested_mode || 'review');
            setSelectedPreset(presetForSelfPrepareMode(requestedMode));
        },
        applyExecutedMode: (requestedMode, executed) => {
            setResult(executed.orchestration_result || null);
            setSelectedPreset(presetForSelfPrepareMode(requestedMode));
            setMode(executed.orchestration_result?.mode || 'full');
        },
        getDirectiveTemplateLabel: (value) => getSelfRunDirectiveTemplateOption(value).label,
        getDirectiveScopeLabel: (value) => getSelfRunDirectiveScopeOption(value).label,
    });

    const fetchCapabilitySummary = async (options?: { silent?: boolean }) => {
        const silent = options?.silent === true;
        if (!silent) {
            setCapabilityLoading(true);
            setCapabilityMessage('');
        }
        try {
            const liveUrl = new URL(`${api}/api/admin/orchestrator/capabilities/summary`);
            liveUrl.searchParams.set('_live', '1');
            liveUrl.searchParams.set('_ts', String(Date.now()));
            const response = await adminFetch(liveUrl.toString(), {
                cache: 'no-store',
                headers: {
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    Pragma: 'no-cache',
                    Expires: '0',
                },
            });
            const payload = await response.json() as OrchestratorCapabilitySummaryResponse;
            const generatedAtText = String(payload?.generated_at || '').trim();
            const generatedAt = generatedAtText ? new Date(generatedAtText).getTime() : NaN;
            const ageSec = Number.isFinite(generatedAt)
                ? Math.max(0, Math.floor((Date.now() - generatedAt) / 1000))
                : null;
            const trackers = capabilityPendingClearTrackerRef.current;
            const capabilities = (payload?.capabilities || []).map((capability) => {
                const tracker = trackers[capability.id] || {
                    pendingLatched: false,
                    clearConfirmations: 0,
                    lastPendingVersion: '',
                };
                const selfRunStatus = String(capability?.evidence_digest?.self_run_status || '').trim();
                const isPendingApproval = selfRunStatus === 'pending_approval';

                if (isPendingApproval) {
                    tracker.pendingLatched = true;
                    tracker.clearConfirmations = 0;
                    tracker.lastPendingVersion = generatedAtText;
                } else if (tracker.pendingLatched) {
                    const versionAdvanced = Boolean(generatedAtText) && tracker.lastPendingVersion !== generatedAtText;
                    if (versionAdvanced) {
                        tracker.pendingLatched = false;
                        tracker.clearConfirmations = 0;
                        tracker.lastPendingVersion = '';
                    } else {
                        tracker.clearConfirmations += 1;
                        if (tracker.clearConfirmations < ADMIN_CAPABILITY_PENDING_CLEAR_CONFIRMATIONS) {
                            const confirmationText = `${tracker.clearConfirmations}/${ADMIN_CAPABILITY_PENDING_CLEAR_CONFIRMATIONS}`;
                            const nextStalenessLabel = [capability.staleness_label, `live 재확인 ${confirmationText}`]
                                .filter(Boolean)
                                .join(' · ');
                            trackers[capability.id] = tracker;
                            return {
                                ...capability,
                                state: 'warning' as OrchestratorCapabilityState,
                                attention_required: true,
                                state_reason: `pending_approval 해제 확인 중 (${confirmationText})`,
                                staleness_label: nextStalenessLabel || null,
                                evidence_digest: {
                                    ...(capability.evidence_digest || {}),
                                    self_run_status: 'pending_approval_verifying',
                                },
                            };
                        }
                        tracker.pendingLatched = false;
                        tracker.clearConfirmations = 0;
                        tracker.lastPendingVersion = '';
                    }
                }

                trackers[capability.id] = tracker;

                if (ageSec != null && ageSec > ADMIN_CAPABILITY_STALE_THRESHOLD_SEC) {
                    const staleText = `live 응답 지연 ${ageSec}초`;
                    return {
                        ...capability,
                        staleness_label: [capability.staleness_label, staleText].filter(Boolean).join(' · '),
                    };
                }
                return capability;
            });

            const normalizedPayload: OrchestratorCapabilitySummaryResponse = {
                ...payload,
                capabilities,
            };
            const hasConfirming = capabilities.some((capability) => {
                const selfRunStatus = String(capability?.evidence_digest?.self_run_status || '').trim();
                return selfRunStatus === 'pending_approval_verifying' || String(capability?.state_reason || '').includes('해제 확인 중');
            });
            const hasStale = capabilities.some((capability) => String(capability?.staleness_label || '').includes('live 응답 지연'));
            setCapabilitySyncPhase(hasConfirming ? 'confirming' : (hasStale ? 'stale' : 'live'));
            setCapabilitySummary(normalizedPayload);
            const refreshedAt = Date.now();
            capabilityLastRefreshAtRef.current = refreshedAt;
            setCapabilityLastLiveRefreshAt(refreshedAt);
            setCapabilityLastLiveRefreshElapsedSec(0);
            return payload;
        } catch (error: any) {
            const hasLatchedPending = Object.values(capabilityPendingClearTrackerRef.current).some((item) => item.pendingLatched);
            const message = hasLatchedPending
                ? 'live 상태 재조회 실패: 기존 경고를 유지한 채 재시도합니다.'
                : (error?.message || '기능군 상태 요약을 불러오지 못했습니다.');
            setCapabilitySyncPhase('retrying');
            setCapabilityMessage(message);
            return null;
        } finally {
            if (!silent) {
                setCapabilityLoading(false);
            }
        }
    };

    const fetchCapabilityDetail = async (capabilityId: string, options?: { silent?: boolean }) => {
        const silent = options?.silent === true;
        if (!silent) {
            setCapabilityLoading(true);
            setCapabilityMessage('');
        }
        try {
            const liveUrl = new URL(`${api}/api/admin/orchestrator/capabilities/${capabilityId}`);
            liveUrl.searchParams.set('_live', '1');
            liveUrl.searchParams.set('_ts', String(Date.now()));
            const response = await adminFetch(liveUrl.toString(), {
                cache: 'no-store',
                headers: {
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    Pragma: 'no-cache',
                    Expires: '0',
                },
            });
            const payload = await response.json() as OrchestratorCapabilityDetailResponse;
            setCapabilityDetail(payload);
            return payload;
        } catch (error: any) {
            const message = error?.message || '기능 상세 결과를 불러오지 못했습니다.';
            if (!silent) {
                setCapabilityMessage(message);
            }
            return null;
        } finally {
            if (!silent) {
                setCapabilityLoading(false);
            }
        }
    };

    useEffect(() => {
        if (capabilityLastLiveRefreshAt == null) {
            setCapabilityLastLiveRefreshElapsedSec(0);
            return;
        }
        const tick = () => {
            setCapabilityLastLiveRefreshElapsedSec(
                Math.max(0, Math.floor((Date.now() - capabilityLastLiveRefreshAt) / 1000)),
            );
        };
        tick();
        const intervalId = window.setInterval(tick, 1000);
        return () => {
            window.clearInterval(intervalId);
        };
    }, [capabilityLastLiveRefreshAt]);

    const capabilityDataHelpers = createCapabilityDataHelpers({
        fetchCapabilitySummary,
        fetchCapabilityDetail,
    });

    useEffect(() => {
        if (typeof window === 'undefined') {
            return;
        }
        setRequestedCapabilityId((new URLSearchParams(window.location.search).get('capability') || '').trim());
    }, []);

    const appendLiveLog = (
        event: string,
        message: string,
        stage?: string,
        timestamp?: string,
        severity: 'info' | 'success' | 'warning' | 'error' = 'info',
    ) => {
        const createdAt = timestamp || new Date().toISOString();
        setLiveLogs((prev) => ([
            {
                id: `${createdAt}-${event}-${Math.random().toString(36).slice(2, 8)}`,
                event,
                stage,
                message,
                timestamp: createdAt,
                severity,
            },
            ...prev,
        ].slice(0, 40)));
        setLiveUpdatedAt(createdAt);
    };

    const buildWsUrl = () => {
        const toWsUrl = (base: string) => {
            const url = new URL(base);
            url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
            url.pathname = '/api/llm/ws';
            url.search = '';
            url.hash = '';
            return url.toString();
        };

        if (typeof window !== 'undefined') {
            const isLocalHost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
            const isFrontendDevPort = window.location.port === '3000' || window.location.port === '3005';
            const configured = (process.env.NEXT_PUBLIC_API_URL || '').trim();
            const normalized = configured.toLowerCase();
            const pointsToLocalBackend = normalized.startsWith('http://localhost:8000') || normalized.startsWith('http://127.0.0.1:8000');

            // Local dev: bypass Next.js catch-all API rewrite for WS upgrades.
            if (isLocalHost && isFrontendDevPort) {
                try {
                    if (pointsToLocalBackend) {
                        return toWsUrl(configured);
                    }

                    const backendOrigin = `http://${window.location.hostname}:8000`;
                    return toWsUrl(backendOrigin);
                } catch {
                }
            }
        }

        try {
            return toWsUrl(api);
        } catch {
            if (typeof window === 'undefined') return '';
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            return `${protocol}//${window.location.host}/api/llm/ws`;
        }
    };

    const buildWsUrls = () => {
        const candidates: string[] = [];
        const push = (value: string) => {
            const normalized = String(value || '').trim();
            if (!normalized || candidates.includes(normalized)) return;
            candidates.push(normalized);
        };

        push(buildWsUrl());

        if (typeof window !== 'undefined') {
            const isLocalHost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
            const isFrontendDevPort = window.location.port === '3000' || window.location.port === '3005';

            // Local dev에서는 프론트(3000/3005) 자체 WS 경로가 아니라 백엔드(8000)만 후보로 사용한다.
            if (isLocalHost && isFrontendDevPort) {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                push(`${protocol}//${window.location.hostname}:8000/api/llm/ws`);
                if (window.location.hostname === 'localhost') {
                    push(`${protocol}//127.0.0.1:8000/api/llm/ws`);
                } else if (window.location.hostname === '127.0.0.1') {
                    push(`${protocol}//localhost:8000/api/llm/ws`);
                }
                return candidates;
            }

            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            push(`${protocol}//${window.location.host}/api/llm/ws`);
        }

        return candidates;
    };

    useEffect(() => {
        try {
            const raw = localStorage.getItem(ADMIN_ORCHESTRATOR_LIVE_PROGRESS_KEY);
            if (!raw) return;
            const snapshot = JSON.parse(raw) as LiveProgressSnapshot;
            if (!snapshot || typeof snapshot !== 'object') return;
            liveRunIdRef.current = snapshot.runId || '';
            setLiveRunId(snapshot.runId || '');
            setLiveTask(snapshot.task || '');
            setLiveMode(snapshot.mode || '');
            setLivePipeline(Array.isArray(snapshot.pipeline) ? snapshot.pipeline : []);
            setLiveStatus(snapshot.status || 'idle');
            setLiveCurrentState(snapshot.currentState || '');
            setLiveStateHistory(Array.isArray(snapshot.stateHistory) ? snapshot.stateHistory : []);
            setLiveLogs(Array.isArray(snapshot.logs) ? snapshot.logs.slice(0, 40) : []);
            setLiveUpdatedAt(snapshot.updatedAt || '');
        } catch {
        }
        try {
            const storedWorkDir = localStorage.getItem(ADMIN_ORCHESTRATOR_WORK_DIR_KEY) || '';
            if (storedWorkDir) {
                setWorkOutputDir(storedWorkDir);
                setLiveOutputDir(storedWorkDir);
            }
        } catch {
        }
        try {
            const storedVoiceAlertEnabled = localStorage.getItem(
                ADMIN_CAPABILITY_ALERT_VOICE_ENABLED_KEY
            );
            if (storedVoiceAlertEnabled === 'false') {
                setCapabilityVoiceAlertEnabled(false);
            }
        } catch {
        }
    }, []);

    useEffect(() => {
        if (typeof window === 'undefined') {
            return;
        }

        // Browser extensions can emit this rejected promise globally even when app logic is healthy.
        // Keep the console focused on actionable app/runtime errors.
        const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
            const reason = event.reason;
            const message = typeof reason === 'string'
                ? reason
                : (reason && typeof reason.message === 'string' ? reason.message : '');

            if (
                message.includes('A listener indicated an asynchronous response by returning true')
                && message.includes('message channel closed before a response was received')
            ) {
                event.preventDefault();
            }
        };

        window.addEventListener('unhandledrejection', handleUnhandledRejection);
        return () => {
            window.removeEventListener('unhandledrejection', handleUnhandledRejection);
        };
    }, []);

    useEffect(() => {
        try {
            if (workOutputDir.trim()) {
                localStorage.setItem(ADMIN_ORCHESTRATOR_WORK_DIR_KEY, workOutputDir.trim());
            } else {
                localStorage.removeItem(ADMIN_ORCHESTRATOR_WORK_DIR_KEY);
            }
        } catch {
        }
    }, [workOutputDir]);

    useEffect(() => {
        try {
            localStorage.setItem(
                ADMIN_CAPABILITY_ALERT_VOICE_ENABLED_KEY,
                capabilityVoiceAlertEnabled ? 'true' : 'false'
            );
        } catch {
        }
    }, [capabilityVoiceAlertEnabled]);

    useEffect(() => {
        const snapshot: LiveProgressSnapshot = {
            runId: liveRunId,
            task: liveTask,
            mode: liveMode,
            pipeline: livePipeline,
            status: liveStatus,
            currentState: liveCurrentState,
            stateHistory: liveStateHistory,
            logs: liveLogs,
            wsConnected,
            updatedAt: liveUpdatedAt,
        };
        try {
            localStorage.setItem(
                ADMIN_ORCHESTRATOR_LIVE_PROGRESS_KEY,
                JSON.stringify(snapshot),
            );
            window.dispatchEvent(
                new CustomEvent('admin-orchestrator-progress', { detail: snapshot }),
            );
        } catch {
        }
    }, [
        liveCurrentState,
        liveLogs,
        liveMode,
        livePipeline,
        liveRunId,
        liveStateHistory,
        liveStatus,
        liveTask,
        liveUpdatedAt,
        wsConnected,
    ]);

    useEffect(() => bindAdminLiveWebSocket({
        buildWsUrl,
        buildWsUrls,
        setWsConnected,
        liveRunIdRef,
        appendConversationMessage,
        setLiveStatus,
        setLiveApplyState,
        setLiveMode,
        setLivePipeline,
        setLiveTask,
        setLiveOrchestrationSpec,
        setLiveOutputDir,
        setLiveSemanticAudit,
        setLiveCurrentState,
        setLiveStateHistory,
        appendLiveLog,
        mergeStageHistory,
        onConnectionMetric: (metric: {
            stage: 'open' | 'close' | 'error';
            elapsedMs: number;
            reconnectDelayMs: number;
            url: string;
        }) => {
            console.info('[admin-llm-websocket-metric]', {
                ...metric,
                url: normalizeMetricUrl(metric.url),
            });
        },
    }), [api]);

    const fetchRuntimeConfig = async () => {
        setRuntimeLoading(true);
        try {
            const normalizedData = await fetchRuntimeConfigBundle<OrchestratorRuntimeConfig>({
                apiBaseUrl: api,
                adminFetch,
                defaultAdvisoryControls: DEFAULT_ADVISORY_CONTROLS,
            });
            setRuntimeConfig(normalizedData);
            setRuntimeDraft(normalizedData);
            setRuntimeMessage('');
            return { ok: true, status: 200 };
        } catch (e: any) {
            setRuntimeMessage(`설정 조회 실패: ${e.message}`);
            return { ok: false, status: 0, error: e?.message || '설정 조회 실패' };
        } finally {
            setRuntimeLoading(false);
        }
    };

    const loadOrchestratorSystemSettings = async () => {
        setOrchestratorSystemLoading(true);
        setOrchestratorSystemMessage('');
        try {
            const normalized = await loadOrchestratorSystemSettingsBundle<AdminSystemSettingsResponse>({
                apiBaseUrl: api,
                adminFetch,
                sectionIds: ORCHESTRATOR_SYSTEM_SECTION_IDS,
                previousOpen: orchestratorSystemOpen,
            });
            setOrchestratorSystemSettings(normalized.settings);
            setOrchestratorSystemDraft(normalized.draft);
            setOrchestratorSystemOpen(normalized.openState);
            return { ok: true, status: 200 };
        } catch (e: any) {
            setOrchestratorSystemMessage(`오케스트레이터 전역 설정 조회 실패: ${e.message}`);
            return { ok: false, status: 0, error: e?.message || '오케스트레이터 전역 설정 조회 실패' };
        } finally {
            setOrchestratorSystemLoading(false);
        }
    };

    const updateOrchestratorSystemSettingValue = (key: string, value: string) => {
        setOrchestratorSystemDraft((prev) => ({
            ...prev,
            [key]: value,
        }));
    };

    const toggleOrchestratorSystemSection = (sectionId: string) => {
        setOrchestratorSystemOpen((prev) => ({
            ...prev,
            [sectionId]: !prev[sectionId],
        }));
    };

    const saveOrchestratorSystemSettings = async () => {
        setOrchestratorSystemSaving(true);
        setOrchestratorSystemMessage('');
        try {
            const normalized = await saveOrchestratorSystemSettingsBundle<AdminSystemSettingsResponse>({
                apiBaseUrl: api,
                adminFetch,
                sectionIds: ORCHESTRATOR_SYSTEM_SECTION_IDS,
                values: orchestratorSystemDraft,
            });
            setOrchestratorSystemSettings(normalized.settings);
            setOrchestratorSystemDraft(normalized.draft);
            setOrchestratorSystemMessage('오케스트레이터 전역 환경값이 저장되었습니다.');
        } catch (e: any) {
            setOrchestratorSystemMessage(`오케스트레이터 전역 설정 저장 실패: ${e.message}`);
        } finally {
            setOrchestratorSystemSaving(false);
        }
    };

    const fetchLatestQuantCompareSummary = async () => {
        setQuantCompareLoading(true);
        setQuantCompareMessage('');
        try {
            const bundle = await fetchLatestQuantCompareSummaryBundle({
                apiBaseUrl: api,
                adminFetch,
                reportPrefix: QUANT_COMPARE_REPORT_PREFIX,
            });
            setQuantCompareSummary(bundle.summary as QuantCompareSummary | null);
            setQuantCompareMessage(bundle.message);
            return { ok: true, status: 200 };
        } catch (e: any) {
            setQuantCompareSummary(null);
            setQuantCompareMessage(`양자화 비교 리포트 조회 실패: ${e.message}`);
            return { ok: false, status: 0, error: e?.message || '양자화 비교 리포트 조회 실패' };
        } finally {
            setQuantCompareLoading(false);
        }
    };

    const applyAdminStageCommand = async (input: string) => applyAdminStageCommandAdapter(
        input,
        {
            stageNote: adminStageNoteDraft,
            substepChecks: adminStageSubstepChecks,
            revisionNote: adminStageRevisionNote,
        },
        {
            run: () => run(),
            runWithTask: (task: string) => run({ task }),
            updateStageStatus: (status, payload) => updateAdminStageStatus(status, {
                ...payload,
                onSuccess: () => setAdminStageRevisionNote(''),
            }),
            verify: () => runAdminOperationalVerification(),
            applyIdeaPreset: (value) => setAdminStageRevisionNote((prev) => applyStageIdeaPresetValue(prev, value)),
        },
    );

    useEffect(() => {
        const controller = new AbortController();
        const accessToken = token();
        if (!accessToken) {
            handleAdminUnauthorized('관리자 로그인 정보가 없어 로그인 페이지로 이동합니다.');
            return () => {
                controller.abort();
            };
        }

        verifyAdminBootstrap({
            accessToken,
            setAdminToken,
        })
            .then(() => {
                setAuthChecked(true);
                setAuthStatusMessage('');
            })
            .catch((error: any) => {
                const message = error instanceof DOMException && error.name === 'AbortError'
                    ? '관리자 인증 확인이 지연되어 로그인 페이지로 이동합니다.'
                    : (error?.message || '관리자 인증 확인에 실패했습니다.');
                handleAdminUnauthorized(message);
            });

        return () => {
            controller.abort();
        };
    }, [router]);

    useEffect(() => {
        if (!authChecked) {
            sessionWarningExpRef.current = null;
            return;
        }

        const checkSessionExpiry = createAdminSessionExpiryChecker({
            token,
            getAdminTokenExpiryMs,
            warningWindowMs: ADMIN_SESSION_WARNING_WINDOW_MS,
            getRemainingSessionMinutes,
            sessionWarningExpRef,
            onUnauthorized: handleAdminUnauthorized,
            onAppendLiveLog: appendLiveLog,
            onRuntimeMessage: setRuntimeMessage,
            onPushAssistantNotice: pushAssistantNotice,
            extendAdminSessionToken,
        });

        void checkSessionExpiry();
        const intervalId = window.setInterval(() => {
            void checkSessionExpiry();
        }, ADMIN_SESSION_CHECK_INTERVAL_MS);

        return () => {
            window.clearInterval(intervalId);
        };
    }, [authChecked]);

    useEffect(() => {
        if (!authChecked) {
            return;
        }
        void runPostAuthBootstrap({
            apiBaseUrl: api,
            adminFetch,
            fetchRuntimeConfig,
            fetchWorkspaceListing: async () => {
                const listing = await fetchWorkspaceListing();
                return {
                    ok: !!listing,
                    status: listing ? 200 : 0,
                    error: listing ? undefined : 'workspace listing unavailable',
                };
            },
            fetchLatestQuantCompareSummary,
            loadOrchestratorSystemSettings,
            restoreLatestSelfRunRecord,
            restorePresetTask: () => restoreAdminPresetTask<AdminLLMPreset>({
                storageKey: ADMIN_LLM_PRESET_TASK_KEY,
                task,
                setUnifiedPrompt,
                setMode,
                setSelectedPreset,
                setSelectedCapabilityActionId,
            }),
            setLlmStatus,
            logBootstrapMetric,
        });
    }, [authChecked]);

    useEffect(() => {
        if (!authChecked || capabilityBootstrapReady) {
            return;
        }
        const timerId = window.setTimeout(() => {
            setCapabilityBootstrapReady(true);
        }, 15000);
        return () => {
            window.clearTimeout(timerId);
        };
    }, [authChecked, capabilityBootstrapReady]);

    useEffect(() => {
        if (!authChecked || !requestedCapabilityId) {
            return;
        }
        if (selectedCapabilityActionId !== requestedCapabilityId) {
            setSelectedCapabilityActionId(requestedCapabilityId);
        }
        if (capabilityDetail?.capability.id === requestedCapabilityId) {
            if (!capabilityBootstrapReady) {
                setCapabilityBootstrapReady(true);
            }
            return;
        }

        void fetchCapabilityDetail(requestedCapabilityId, { silent: true });
        if (!capabilityBootstrapReady) {
            setCapabilityBootstrapReady(true);
        }
    }, [authChecked, requestedCapabilityId, selectedCapabilityActionId, capabilityDetail?.capability.id, capabilityBootstrapReady]);

    useEffect(() => {
        if (!authChecked || !selectedCapabilityActionId) {
            return;
        }
        if (capabilityDetail?.capability.id === selectedCapabilityActionId) {
            return;
        }

        void fetchCapabilityDetail(selectedCapabilityActionId, { silent: true });
        if (!capabilityBootstrapReady) {
            setCapabilityBootstrapReady(true);
        }
    }, [authChecked, selectedCapabilityActionId, capabilityDetail?.capability.id, capabilityBootstrapReady]);

    useEffect(() => {
        if (!authChecked || !capabilityBootstrapReady) {
            return;
        }

        const refreshCapabilityState = async () => {
            if (capabilityRefreshInFlightRef.current) {
                return;
            }
            capabilityRefreshInFlightRef.current = true;
            try {
                await capabilityDataHelpers.refreshCapabilityState({
                    selectedCapabilityActionId,
                    pickPrimaryCapability,
                    getCards: (summary) => (summary?.capabilities || []),
                    setSelectedCapabilityActionId,
                    currentDetailCapabilityId: capabilityDetail?.capability.id || '',
                });
            } finally {
                capabilityRefreshInFlightRef.current = false;
            }
        };

        void refreshCapabilityState();
        const intervalId = window.setInterval(() => {
            void refreshCapabilityState();
        }, ADMIN_CAPABILITY_AUTO_REFRESH_MS);

        const refreshOnFocus = () => {
            const now = Date.now();
            if ((now - capabilityLastRefreshAtRef.current) < ADMIN_CAPABILITY_FOCUS_REFRESH_DEBOUNCE_MS) {
                return;
            }
            void refreshCapabilityState();
        };

        const refreshOnVisibility = () => {
            if (document.visibilityState === 'visible') {
                refreshOnFocus();
            }
        };

        window.addEventListener('focus', refreshOnFocus);
        document.addEventListener('visibilitychange', refreshOnVisibility);

        return () => {
            window.clearInterval(intervalId);
            window.removeEventListener('focus', refreshOnFocus);
            document.removeEventListener('visibilitychange', refreshOnVisibility);
        };
    }, [authChecked, capabilityBootstrapReady, selectedCapabilityActionId]);

    const applyPreset = (preset: AdminLLMPreset) => {
        setSelectedPreset(preset);
        setSelectedCapabilityActionId('');
        setUnifiedPrompt(preset.task);
        setMode(preset.mode);
    };

    const getGeneratorDefinition = (generatorId: string) => GENERATOR_CAPABILITY_DEFINITIONS.find((item) => item.id === generatorId) || null;

    const applyGeneratorControl = (generatorId: string) => {
        applyGeneratorControlOrchestration({
            generatorId,
            getGeneratorDefinition,
            getPresetById: getOrchestratorPresetById,
            setActiveGeneratorId,
            setActiveGeneratorModal,
            setSelectedPreset: (preset) => setSelectedPreset(preset as AdminLLMPreset | null),
            setSelectedCapabilityActionId,
            setChatFunctionMode,
            setUnifiedPrompt,
            setSelfRunDirectiveTemplate,
            setSelfRunDirectiveScope,
            setSelfRunDirectiveRequest,
            setMode,
            setRuntimeEditorOpen,
        });
    };

    const applyGeneratorMarketplaceOffer = (offerId: string) => {
        const offer = GENERATOR_MARKETPLACE_OFFERS.find((item) => item.id === offerId);
        if (!offer) {
            return;
        }
        applyGeneratorControl(offer.generatorId);
        const marketplaceTask = `${getEffectiveTaskInput() || task || buildGeneratorMarketplaceAppendix(offer)}${buildGeneratorMarketplaceAppendix(offer)}`.trim();
        appendUnifiedPrompt(buildGeneratorMarketplaceAppendix(offer));
        try {
            localStorage.setItem(
                MARKETPLACE_ORCHESTRATOR_BRIDGE_KEY,
                JSON.stringify(buildMarketplaceOrchestratorAdminLlmBridgePayload({
                    productId: offer.id,
                    projectName: activeGeneratorDefinition?.title || offer.title,
                    task: marketplaceTask,
                    capabilityId: activeGeneratorDefinition?.id || undefined,
                    presetId: selectedPreset?.id || undefined,
                    note: 'admin-llm generator marketplace bridge',
                })),
            );
        } catch {
        }
        hardNavigate(`/marketplace/orchestrator?product=${encodeURIComponent(offer.id)}`);
    };

    const runFeatureOrchestrateAction = useCallback(async (action: AdvisoryNextAction) => {
        const payload = parseFeatureOrchestrateActionPayload(action.action_payload);
        if (!payload) {
            pushAssistantNotice('실행 불가', 'feature-orchestrate payload가 없어 액션을 실행할 수 없습니다.');
            return;
        }
        setFeatureActionRunning(true);
        try {
            const response = await adminFetch(`${api}/api/marketplace/feature-orchestrate/accepted`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const accepted = await response.json();
            const runId = String(accepted?.run_id || '').trim();
            if (!runId) {
                throw new Error('run_id 누락');
            }
            pushAssistantNotice('feature-orchestrate 실행', `${payload.feature_id} 실행을 수락했습니다. run_id=${runId}`);
            try {
                localStorage.setItem(
                    MARKETPLACE_ORCHESTRATOR_BRIDGE_KEY,
                    JSON.stringify(buildMarketplaceOrchestratorAdminLlmBridgePayload({
                        productId: payload.feature_id,
                        projectName: payload.project_name,
                        task: payload.prompt,
                        note: `admin-llm web grounded action ${runId}`,
                    })),
                );
            } catch {
            }
            hardNavigate(`/marketplace/orchestrator?feature=${encodeURIComponent(payload.feature_id)}&run_id=${encodeURIComponent(runId)}`);
        } catch (error: any) {
            pushAssistantNotice('feature-orchestrate 실패', `검색 기반 실행 요청이 실패했습니다: ${error?.message || 'unknown error'}`);
        } finally {
            setFeatureActionRunning(false);
        }
    }, [adminFetch, api, hardNavigate, pushAssistantNotice]);

    const runExternalSearch = useCallback(async () => {
        const query = externalSearchQuery.trim();
        const placeId = externalSearchPlaceId.trim();
        if (externalSearchEndpoint === 'maps-reviews') {
            if (!query && !placeId) {
                pushAssistantNotice('입력 필요', '지도 리뷰는 검색어 또는 place_id 중 하나가 필요합니다.');
                return;
            }
        } else if (!query) {
            pushAssistantNotice('입력 필요', '검색어를 입력해 주세요.');
            return;
        }

        setExternalSearchLoading(true);
        setExternalSearchMessage('');
        try {
            const params = new URLSearchParams();
            if (query) {
                params.set('q', query);
            }
            params.set('limit', '5');
            if (externalSearchEndpoint === 'maps-reviews' && placeId) {
                params.set('place_id', placeId);
            }
            const response = await adminFetch(`${api}/api/external-search/${externalSearchEndpoint}?${params.toString()}`);
            const payload = await response.json() as AdminExternalSearchResponse;
            setExternalSearchResult(payload);
            if (!response.ok || payload.status === 'error') {
                const errorMessage = payload.error?.message || `HTTP ${response.status}`;
                setExternalSearchMessage(`호출 실패: ${errorMessage}`);
                pushAssistantNotice('외부 검색 실패', `${externalSearchEndpoint} 호출이 실패했습니다: ${errorMessage}`);
                return;
            }
            const resultCount = Array.isArray(payload.data) ? payload.data.length : 0;
            const provider = payload.meta?.provider || '-';
            const engine = payload.meta?.engine || '-';
            setExternalSearchMessage(`${externalSearchEndpoint} 호출 완료: ${resultCount}건, provider=${provider}, engine=${engine}`);
            pushAssistantNotice('외부 검색 완료', `${externalSearchEndpoint} 결과 ${resultCount}건을 불러왔습니다.`);
        } catch (error: any) {
            const message = error?.message || 'unknown error';
            setExternalSearchMessage(`호출 실패: ${message}`);
            pushAssistantNotice('외부 검색 실패', `${externalSearchEndpoint} 호출 중 오류가 발생했습니다: ${message}`);
        } finally {
            setExternalSearchLoading(false);
        }
    }, [adminFetch, api, externalSearchEndpoint, externalSearchPlaceId, externalSearchQuery, pushAssistantNotice]);

    const handleGeneratorModalAction = (actionId: GeneratorDetailModalActionId) => {
        applyGeneratorModalActionOrchestration({
            actionId,
            activeGeneratorId,
            getGeneratorDefinition,
            applyGeneratorControl,
            applyGeneratorMarketplaceOffer,
            setActiveGeneratorModal,
            setRuntimeEditorOpen,
        });
    };

    const buildCapabilityTask = (action: OrchestratorCapabilityAction, preset: AdminLLMPreset | null) => {
        const baseTask = preset?.task?.trim() || '';
        const actionTask = action.task.trim();
        if (!baseTask) {
            return actionTask;
        }
        return `${baseTask}\n\n[기능별 통솔: ${action.title}]\n${actionTask}`;
    };

    const isImmediateSelfRunCapability = (action: OrchestratorCapabilityAction) => action.presetId === 'self-improvement';

    const finalizeCapabilityExecutionComparison = async (
        capabilityId: string,
        beforeDetail: OrchestratorCapabilityDetailResponse | null,
        runResult: OrchestrateResponse | null,
        selfRunResult?: AdminWorkspaceSelfRunResponse | null,
        capturedAt?: string,
    ) => {
        const comparison = await capabilityDataHelpers.finalizeCapabilityExecutionComparison({
            capabilityId,
            beforeDetail,
            runResult,
            selfRunResult,
            capturedAt,
        });
        setCapabilityExecutionComparison(comparison);
    };

    const applyCapabilityAction = async (
        action: OrchestratorCapabilityAction,
        execution: 'prepare' | 'run' = 'prepare',
    ) => applyCapabilityActionOrchestration({
        action,
        execution,
        getPresetById: getOrchestratorPresetById,
        buildCapabilityTask: (nextAction, preset) => buildCapabilityTask(
            nextAction as OrchestratorCapabilityAction,
            (preset || null) as AdminLLMPreset | null,
        ),
        setSelectedPreset: (preset) => setSelectedPreset((preset || null) as AdminLLMPreset | null),
        setSelectedCapabilityActionId,
        setUnifiedPrompt,
        setMode,
        refreshCapabilityDetail: capabilityDataHelpers.refreshCapabilityDetail,
        isImmediateSelfRunCapability,
        pendingCapabilityExecutionRef,
        executeSelfWorkflow,
        runWorkflow: (runOptions) => run({
            ...runOptions,
            nextPreset: (runOptions.nextPreset || null) as AdminLLMPreset | null,
        }),
        setCapabilityExecutionComparison,
    });

    const selectCapabilityAction = async (action: OrchestratorCapabilityAction) => {
        setSelectedCapabilityActionId(action.id);
        await fetchCapabilityDetail(action.id);
    };

    const inferSuggestionDirectiveTemplate = (
        action: AdvisoryNextAction,
    ): SelfRunDirectiveTemplate => {
        return inferSuggestedSelfRunDirectiveTemplate(
            action,
            selfRunDirectiveTemplate,
            getLatestUserConversationRequest(),
        );
    };

    const buildSuggestionDirectiveRequest = (action: AdvisoryNextAction) => {
        return buildSuggestedSelfRunDirectiveRequest({
            action,
            directiveTemplate: inferSuggestionDirectiveTemplate(action),
            baseRequest: getLatestUserConversationRequest(),
        });
    };

    const {
        runSuggestedSelfWorkflow,
        confirmSuggestedSelfWorkflow,
        cancelSuggestedSelfWorkflow,
        applySuggestedSelfWorkflowDraft,
    } = createSelfRunDraftFlow({
        inferSuggestionDirectiveTemplate,
        buildSuggestionDirectiveRequest,
        buildSuggestedSelfRunPreview,
        setSuggestedSelfRunPreview,
        executeSelfWorkflow,
        setSelfRunDirectiveTemplate,
        setSelfRunDirectiveScope,
        setSelfRunDirectiveRequest,
    });

    const updateTextFeatureAgent = (featureKey: RoutedTextFeatureKey, agentKey: OrchestratorAgentKey) => {
        setTextFeatureAgents((prev) => ({
            ...prev,
            [featureKey]: agentKey,
        }));
    };

    const getFeatureAgentOption = (featureKey: RoutedTextFeatureKey | null) => {
        if (!featureKey) {
            return ORCHESTRATOR_AGENT_OPTIONS.find((option) => option.key === chatAgentKey) || null;
        }
        const mappedAgentKey = textFeatureAgents[featureKey];
        return ORCHESTRATOR_AGENT_OPTIONS.find((option) => option.key === mappedAgentKey) || null;
    };

    const {
        updateRuntimeField,
        updateRuntimeToggle,
        updateGlobalExecutionPreference,
        updateGlobalExecutionNumeric,
        updateAdvisoryToggle,
        updateAdvisoryNumeric,
        updateRuntimeModelRoute,
        updateRuntimeExecutionMode,
        updateRuntimeExecutionNumeric,
        applyRuntimeProfile,
        applyFunctionalModelGrade,
        applyFeaturedModelAction,
        applyModelTuningLevel,
        applyTokenTuningLevel,
        applyTimeoutTuningLevel,
    } = createRuntimeConfigMutationHelpers({
        setRuntimeDraft: setRuntimeDraft as React.Dispatch<React.SetStateAction<any>>,
        setRuntimeMessage,
        defaultAdvisoryControls: DEFAULT_ADVISORY_CONTROLS,
        modelRouteFields: ORCHESTRATOR_MODEL_ROUTE_FIELDS,
        resolveHybridExecutionNumGpu,
        buildTunedModelRoutes: buildTunedModelRoutes as any,
        tokenTuningPresets: TOKEN_TUNING_PRESETS as any,
        timeoutTuningPresets: TIMEOUT_TUNING_PRESETS as any,
    });
    const saveRuntimeConfig = async () => {
        if (!runtimeDraft) return;
        setRuntimeSaving(true);
        setRuntimeMessage('');
        try {
            const normalizedData = await saveRuntimeConfigBundle<OrchestratorRuntimeConfig>({
                apiBaseUrl: api,
                adminFetch,
                runtimeDraft,
                defaultAdvisoryControls: DEFAULT_ADVISORY_CONTROLS,
            });
            setRuntimeConfig(normalizedData);
            setRuntimeDraft(normalizedData);
            setRuntimeMessage('관리자 제한값이 저장되어 즉시 반영됐습니다.');
        } catch (e: any) {
            setRuntimeMessage(`설정 저장 실패: ${e.message}`);
        } finally {
            setRuntimeSaving(false);
        }
    };

    const runtimeConfigPanelActions = buildRuntimeConfigPanelBindings({
        setRuntimeEditorOpen,
        fetchRuntimeConfig,
        saveRuntimeConfig,
        saveOrchestratorSystemSettings,
        applyModelTuningLevel: (level) => applyModelTuningLevel(level as RuntimeTuningLevel),
        applyTokenTuningLevel: (level) => applyTokenTuningLevel(level as RuntimeTuningLevel),
        applyTimeoutTuningLevel: (level) => applyTimeoutTuningLevel(level as RuntimeTuningLevel),
        updateRuntimeField: (field, value) => updateRuntimeField(field as keyof OrchestratorRuntimeConfig, value),
        updateGlobalExecutionPreference,
        updateRuntimeToggle: (field, value) => updateRuntimeToggle(field as 'force_complete' | 'allow_synthetic_fallback', value),
        updateAdvisoryToggle: (field, value) => updateAdvisoryToggle(field as keyof Pick<AdvisoryControls, 'clarification_questions_enabled' | 'evidence_panel_enabled' | 'next_action_suggestions_enabled'>, value),
        updateAdvisoryNumeric: (field, value) => updateAdvisoryNumeric(field as keyof Pick<AdvisoryControls, 'max_clarification_questions' | 'max_evidence_items' | 'max_next_actions'>, value),
        applyRuntimeProfile,
        applyFeaturedModelAction,
        applyFunctionalModelGrade,
        fetchLatestQuantCompareSummary,
        updateRuntimeModelRoute,
        updateGlobalExecutionNumeric,
        updateRuntimeExecutionMode,
        updateRuntimeExecutionNumeric,
        loadOrchestratorSystemSettings,
        toggleOrchestratorSystemSection,
        updateOrchestratorSystemSettingValue,
    });
    const runtimeConfigPanelHelpers = buildRuntimeConfigPanelHelpers({
        runtimeTuningLevels: RUNTIME_TUNING_LEVELS,
        runtimeFields: ORCHESTRATOR_RUNTIME_FIELDS as Array<[string, string]>,
        defaultAdvisoryControls: DEFAULT_ADVISORY_CONTROLS,
        modelGradeRows: FUNCTIONAL_MODEL_GRADE_ROWS,
        getMissingGradeModels: (availableModels, targets) => getMissingGradeModels(availableModels, targets as Partial<Record<ModelRouteKey, string>>),
        isGradeActive: (modelRoutes, targets) => isGradeActive(modelRoutes as Record<ModelRouteKey, string>, targets as Partial<Record<ModelRouteKey, string>>),
        codingQ4Tag: CODING_Q4_TAG,
        codingQ5Tag: CODING_Q5_TAG,
        codingQ6Tag: CODING_Q6_TAG,
        codingQ8Tag: CODING_Q8_TAG,
        formatMetricNumber,
        modelRouteFields: ORCHESTRATOR_MODEL_ROUTE_FIELDS as Array<[string, string]>,
        runtimePolicyHints: RUNTIME_POLICY_HINTS,
        executionModeLabels: EXECUTION_MODE_LABELS,
        resolveHybridExecutionNumGpu,
    });
    const runtimeConfigPanelData = buildRuntimeConfigPanelData({
        runtimeEditorOpen,
        runtimeDraft,
        runtimeLoading,
        runtimeSaving,
        orchestratorSystemSaving,
        runtimeMessage,
        runtimeConfig,
        quantCompareLoading,
        quantCompareMessage,
        quantCompareSummary,
        orchestratorSystemLoading,
        orchestratorSystemSettings,
        orchestratorSystemMessage,
        orchestratorSystemOpen,
    });
    const run = async (options?: {
        task?: string;
        nextMode?: string;
        nextPreset?: AdminLLMPreset | null;
        nextCapabilityActionId?: string;
    }) => {
        const nextRunOptions = applyAdminRunOptions({
            incomingOptions: options,
            currentMode: mode,
            getEffectiveTaskInput,
            setUnifiedPrompt,
            setSelectedPreset,
            setSelectedCapabilityActionId,
            setMode,
            setTask,
        });
        if (!nextRunOptions) return null;
        const {
            effectiveTaskInput,
            effectiveModeState,
        } = nextRunOptions;
        const nextRunId = typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
            ? crypto.randomUUID()
            : `run-${Date.now()}`;
        liveRunIdRef.current = nextRunId;
        resetAdminRunLifecycleState({
            nextRunId,
            effectiveTaskInput,
            effectiveModeState,
            continueInPlace,
            workOutputDir,
            liveOutputDir,
            setLiveRunId,
            setLiveTask,
            setLiveMode,
            setLivePipeline,
            setLiveStatus,
            setLiveCurrentState,
            setLiveStateHistory,
            setLiveLogs,
            setLiveUpdatedAt,
            setLiveSemanticAudit,
            setLiveOrchestrationSpec,
            setLiveOutputDir,
            setLiveApplyState,
            setLiveApplyError,
            setLoading,
            setError,
            setResult,
        });
        pushAssistantNotice('오케스트레이션 실행', `챗봇 입력 기준 오케스트레이션을 ${effectiveModeState} 모드로 시작합니다.`);
        appendLiveLog('client', '오케스트레이터 실행 요청 전송', 'DESIGN');
        try {
            const r = await adminFetch(`${api}/api/llm/orchestrate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(buildAdminOrchestrateRequestBody({
                    effectiveTaskInput,
                    effectiveModeState,
                    companionMode,
                    continueInPlace,
                    outputDir: resolveReusableOutputDir(),
                    nextRunId,
                    maxTokens: runtimeDraft?.default_request_max_tokens,
                    conversation,
                    enabledRules,
                    mandatoryRules: MANDATORY_ORCHESTRATOR_RULES,
                }))
            });
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            const data = await r.json();
            const normalizedRunResult = normalizeAdminRunResult(data);
            applyAdminRunSuccessState({
                normalizedRunResult,
                liveRunIdRef,
                setLiveRunId,
                setLiveOrchestrationSpec,
                setLiveOutputDir,
                setWorkOutputDir,
                setLiveApplyError,
                setLivePipeline,
                setLiveStateHistory,
                setLiveCurrentState,
                setLiveSemanticAudit,
                setLiveStatus,
                setLiveApplyState,
                appendLiveLog,
                setConversation,
                setResult,
                setActiveResult,
            });
            pushAssistantNotice(
                '오케스트레이션 결과',
                buildAdminRunResultNotice({
                    applyError: data.apply_error,
                    applied: data.applied,
                    outputDir: data.output_dir,
                    adminFinalPassGuide,
                }),
            );
            return normalizedRunResult.result as OrchestrateResponse;
        } catch (e: any) {
            applyAdminRunFailureState({
                errorMessage: e.message,
                fallbackState: liveCurrentState,
                setLiveStatus,
                setLiveApplyState,
                setLiveApplyError,
                appendLiveLog,
                setError,
            });
            return null;
        } finally {
            setLoading(false);
        }
    };

    const submitPrimaryPrompt = async (rawPrompt?: string) => {
        const prompt = String(rawPrompt ?? chatInput).trim();
        if (!prompt) {
            pushAssistantNotice('입력 필요', '태스크 설명을 입력해 주세요.');
            return null;
        }

        const handled = await applyAdminStageCommand(prompt);
        if (handled) {
            return null;
        }

        await sendChatMessage(prompt);
        return null;
    };

    const EXAMPLES = [
        'FastAPI로 JWT 인증 미들웨어 작성',
        'React 쇼핑카트 컴포넌트 디자인',
        'PostgreSQL 쿼리 성능 최적화',
        'Next.js 다크모드 구현',
    ];

    const toggleRule = (rule: string) => {
        if (!OPTIONAL_ORCHESTRATOR_RULES.includes(rule)) {
            return;
        }
        setEnabledRules(prev => (
            prev.includes(rule)
                ? prev.filter(item => item !== rule)
                : [...prev, rule]
        ));
    };

    const {
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
    } = buildAdminLivePanelSummary({
        liveStateHistory,
        liveCurrentState,
        livePipeline,
        runtimeDraft,
        runtimeConfig,
        result,
        chatAgentKey,
        voiceAgentKey,
        textFeatureAgents,
        requiredReasonerTargets: REASONER_REQUIRED_AGENT_TARGETS,
        expansionReasonerTargets: REASONER_EXPANSION_AGENT_TARGETS,
        liveOrchestrationSpec,
        liveOutputDir,
        liveApplyError,
        liveSemanticAudit,
        liveApplyState,
        loading,
        liveLogs,
        liveRunId,
    });
    const {
        capabilitySummaryLookup,
        capabilityGroupSummaryLookup,
        capabilityProblemCards,
        activeCapabilityComparison,
        beforeComparisonErrors,
        afterComparisonErrors,
        beforeComparisonWarnings,
        afterComparisonWarnings,
        comparisonResolvedTitles,
        comparisonNewTitles,
        capabilityAlertSpeech,
        generatorCapabilityStatusRows,
    } = buildAdminCapabilityPanelData({
        capabilitySummary,
        capabilityExecutionComparison,
        capabilityDetail,
        generatorDefinitions: GENERATOR_CAPABILITY_DEFINITIONS,
        buildCapabilityComparisonTitles,
        buildCapabilityAlertSpeech,
    });
    const {
        activeGeneratorDefinition,
        activeGeneratorOffer,
        activeGeneratorStatus,
        activeGeneratorPreset,
        activeGeneratorFeature,
        activeGeneratorDetailModalData,
    } = buildActiveAdminGeneratorData({
        activeGeneratorId,
        getGeneratorDefinition,
        generatorOffers: GENERATOR_MARKETPLACE_OFFERS,
        generatorStatusRows: generatorCapabilityStatusRows,
        getPresetById: getOrchestratorPresetById,
        features: ROUTED_TEXT_FEATURES,
    });
    const capabilityPanelBindings = buildCapabilityPanelBindings({
        getPresetTitle: (presetId) => getOrchestratorPresetById(presetId)?.title || '연결 없음',
        getCapabilityStateClassName,
        getCapabilityStateText,
        selectCapabilityAction: async (action) => {
            await selectCapabilityAction(action as OrchestratorCapabilityAction);
        },
        applyCapabilityAction: async (action, execution) => {
            await applyCapabilityAction(action as OrchestratorCapabilityAction, execution);
        },
        toggleCapabilityVoiceAlert: () => setCapabilityVoiceAlertEnabled((prev) => !prev),
        speakCapabilityAlert: () => speakText(capabilityAlertSpeech || '현재 발성할 관리자 경고가 없습니다.'),
        refreshCapabilitySummary: async () => {
            await fetchCapabilitySummary();
            const nextTargetId = selectedCapabilityActionId || capabilityDetail?.capability.id || capabilityProblemCards[0]?.id || '';
            if (nextTargetId) {
                await fetchCapabilityDetail(nextTargetId);
            }
        },
        activeCapabilityComparison: activeCapabilityComparison as any,
        getCapabilityFindingRenderKey: getCapabilityFindingRenderKey as any,
        getCapabilityCodeExampleRenderKey: getCapabilityCodeExampleRenderKey as any,
        buildSelfRunStatusLabel: (status) => buildSelfRunStatusLabel(status as AdminWorkspaceSelfRunResponse['status']),
    });
    const capabilityPanelDataProps = buildCapabilityPanelDataProps({
        capabilityLoading,
        capabilityMessage,
        capabilityDetail,
        detailCapabilityAction,
        beforeComparisonErrors,
        beforeComparisonWarnings,
        afterComparisonErrors,
        afterComparisonWarnings,
        comparisonResolvedTitles,
        comparisonNewTitles,
    });
    const headerIntroData = buildAdminHeaderIntroData({
        embeddedMode,
    });
    const llmStatusSectionData = buildAdminLlmStatusSectionData({
        llmStatus,
        agentOptions: ORCHESTRATOR_AGENT_OPTIONS,
    });
    const generatorStatusSectionData = buildAdminGeneratorStatusSectionData({
        activeGeneratorModal,
        generatorCapabilityStatusRows,
        effectiveCodeGenerationStrategy,
        effectivePipeline,
        effectiveOrchestrationSpec,
        effectiveConversationAgents,
        reasonerCoverageClassName,
        reasonerCoverageState,
        reasonerRequiredCoverage,
        requiredReasonerTargetCount: REASONER_REQUIRED_AGENT_TARGETS.length,
        reasonerConversationCoverage,
    });
    const generatorModalBindings = buildAdminGeneratorModalBindings({
        modal: activeGeneratorDetailModalData,
        onClose: () => {
            setActiveGeneratorId('');
            setActiveGeneratorModal(null);
        },
        onSelectAction: (actionId) => handleGeneratorModalAction(actionId as GeneratorDetailModalActionId),
    });
    const stageCardBindings = buildAdminStageCardBindings({
        selfRunResult,
        adminStageNoteDraft,
        setAdminStageNoteDraft,
        adminStageSubstepChecks,
        setAdminStageSubstepChecks,
        adminStageRevisionNote,
        setAdminStageRevisionNote,
        selfRunBusy,
        updateAdminStageStatus,
        runAdminOperationalVerification,
        ideaPresets: DEFAULT_STAGE_IDEA_PRESETS,
        applyStageIdeaPresetValue,
    });
    const resultSummarySectionData = buildAdminResultSummarySectionData({
        effectiveProductReadinessHardGate,
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
        effectiveApplyState,
        applyStateLabel,
        effectiveOutputDir,
        effectiveFailedOutputDir,
        effectiveApplyError,
    });

    useEffect(() => {
        if (!authChecked || !capabilityVoiceAlertEnabled) {
            return;
        }
        const signature = `${capabilityProblemCards.map((card) => `${card.id}:${card.state}:${card.detail || card.metric}`).join('|')}__${capabilityDetail?.capability.id || ''}__${capabilityDetail?.capability.detail || capabilityDetail?.capability.metric || ''}`;
        if (!capabilityAlertSpeech || !signature) {
            return;
        }
        if (capabilityAlertSignatureRef.current === signature) {
            return;
        }
        if (speakText(capabilityAlertSpeech)) {
            capabilityAlertSignatureRef.current = signature;
        }
    }, [
        authChecked,
        capabilityAlertSpeech,
        capabilityDetail,
        capabilityProblemCards,
        capabilityVoiceAlertEnabled,
    ]);

    if (!authChecked) {
        return (
            <div className="min-h-screen bg-[#0d1117] p-6 text-[#e6edf3]">
                <div className="mx-auto flex min-h-[70vh] max-w-[720px] items-center justify-center">
                    <div className="w-full rounded-2xl border border-[#30363d] bg-[#161b22] p-8 text-center">
                        <h1 className="mb-3 text-2xl font-bold text-[#58a6ff]">관리자 LLM 연결 확인 중</h1>
                        <p className="text-sm text-[#8b949e]">{authStatusMessage || '관리자 인증을 확인하고 있습니다.'}</p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div
            ref={frameRootRef}
            className={embeddedMode ? 'bg-[#0d1117] p-4 text-[#e6edf3]' : 'min-h-screen bg-[#0d1117] p-6 text-[#e6edf3]'}
        >
            <div className={`mx-auto ${miniConsoleLayout ? 'max-w-[980px]' : 'max-w-[1200px]'}`}>
                {!miniConsoleLayout && (headerIntroData.embeddedMode ? (
                    <div className="mb-4 rounded-xl border border-[#30363d] bg-[#161b22] p-4">
                        <h1 className="text-lg font-bold text-[#58a6ff]">{headerIntroData.embeddedTitle}</h1>
                        <p className="mt-1 text-xs text-[#8b949e]">{headerIntroData.embeddedDescription}</p>
                    </div>
                ) : (
                    <>
                        <div className="sticky top-0 z-30 mb-6 rounded-2xl border border-[#30363d] bg-[#0d1117]/95 px-4 py-3 backdrop-blur">
                            <div className="flex flex-wrap items-center justify-between gap-4">
                                <div>
                                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#79c0ff]">{headerIntroData.stickyEyebrow}</p>
                                    <p className="mt-1 text-xs text-[#8b949e]">{headerIntroData.stickyDescription}</p>
                                </div>
                                <div className="flex flex-wrap gap-2">
                                    <button type="button" data-testid="admin-llm-topnav-dashboard" onClick={() => hardNavigate('/admin')} className="rounded-xl border border-[#30363d] bg-[#21262d] px-4 py-2.5 text-sm font-semibold text-[#e6edf3] shadow-[0_0_0_1px_rgba(255,255,255,0.02)]">
                                        ← 대시보드로 돌아가기
                                    </button>
                                    <button type="button" data-testid="admin-llm-topnav-marketplace-orchestrator" onClick={() => hardNavigate('/marketplace/orchestrator')} className="rounded-xl border border-[#8957e5] bg-[#1f1630] px-4 py-2.5 text-sm font-semibold text-[#e9d5ff] shadow-[0_0_0_1px_rgba(255,255,255,0.02)]">
                                        고객 오케스트레이터 공간 →
                                    </button>
                                </div>
                            </div>
                        </div>
                        <div className="mb-6 flex items-center justify-between">
                            <div>
                                <h1 className="text-2xl font-bold text-[#58a6ff]">{headerIntroData.pageTitle}</h1>
                                <p className="text-sm text-[#8b949e]">{headerIntroData.pageSubtitle}</p>
                                <p className="mt-2 text-xs text-[#e3b341]">{headerIntroData.pageDescription}</p>
                            </div>
                        </div>
                    </>
                ))}

                {!miniConsoleLayout && llmStatusSectionData && (
                    <div className="mb-6 flex flex-wrap gap-6 rounded-xl border border-[#30363d] bg-[#161b22] p-4">
                        <div>
                            <span className="text-xs text-[#8b949e]">상태</span>
                            <br />
                            <span className={`font-semibold ${llmStatusSectionData.statusClassName}`}>{llmStatusSectionData.statusLabel}</span>
                        </div>
                        <div>
                            <span className="text-xs text-[#8b949e]">모드</span>
                            <br />
                            <span className="text-[#58a6ff]">{llmStatusSectionData.modeLabel}</span>
                        </div>
                        <div>
                            <span className="text-xs text-[#8b949e]">모델 수</span>
                            <br />
                            <span>{llmStatusSectionData.modelCountLabel}</span>
                        </div>
                        <div>
                            <span className="text-xs text-[#8b949e]">기본 모델</span>
                            <br />
                            <span className="text-[#e3b341]">{llmStatusSectionData.primaryModelLabel}</span>
                        </div>
                        {llmStatusSectionData.configuredModelRows.map((row) => (
                            <div key={row.key}>
                                <span className="text-xs text-[#8b949e]">{row.label} 모델</span>
                                <br />
                                <span className="text-[#79c0ff]">
                                    {row.value}
                                </span>
                            </div>
                        ))}
                    </div>
                )}

                {!miniConsoleLayout && <div className="mb-6 rounded-xl border border-[#30363d] bg-[#161b22] p-5">
                    <div className="mb-4 flex items-center justify-between gap-3">
                        <div>
                            <h2 className="text-lg font-semibold text-[#58a6ff]">4가지 코드생성기 고정 정의</h2>
                            <p className="text-xs text-[#8b949e]">Project Scanner, Security Guard, Self-Healing Engine, Code Generator를 관리자 최종 제어 기능으로 고정하고 마지막 단계까지 연결 상태를 추적합니다.</p>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                            <div className="rounded-lg border border-[#30363d] bg-[#21262d] px-3 py-2 text-xs text-[#8b949e]">
                                모달 멀티 사용 상태: {generatorStatusSectionData.modalStatusLabel}
                            </div>
                            <div className="rounded-lg border border-[#1f6feb] bg-[rgba(31,111,235,0.16)] px-3 py-2 text-xs text-[#9ecbff]">
                                evidence snapshot: {String(capabilitySummary?.evidence_snapshot_version || capabilityDetail?.evidence_bundle?.contract?.evidence_schema_version || 'v1')}
                            </div>
                        </div>
                    </div>
                    <div className="mb-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                        {generatorStatusSectionData.generatorCapabilityStatusRows.map((item) => (
                            <button
                                key={item.id}
                                type="button"
                                onClick={() => applyGeneratorControl(item.id)}
                                className="rounded-xl border border-[#30363d] bg-[#0d1117] p-4 text-left hover:border-[#1f6feb]"
                            >
                                <div className="flex items-center justify-between gap-2">
                                    <span className="text-sm font-semibold text-[#e6edf3]">{item.title}</span>
                                    <span className={`rounded-full px-2 py-1 text-[11px] font-semibold ${getCapabilityStateClassName(item.state as OrchestratorCapabilityState)}`}>{item.state}</span>
                                </div>
                                <p className="mt-2 text-xs text-[#8b949e]">{item.summary}</p>
                                <p className="mt-2 text-[11px] text-[#79c0ff]">최종 단계 {item.finalStage}</p>
                                <p className="mt-2 text-[11px] text-[#c9d1d9]">{item.metric}</p>
                            </button>
                        ))}
                    </div>
                    <div className="flex flex-wrap items-start justify-between gap-4">
                        <div>
                            <h2 className="text-lg font-semibold text-[#58a6ff]">현재 오케스트레이터 연결 상태</h2>
                            <p className="mt-1 text-xs text-[#8b949e]">관리자 UI에서 실시간 파이프라인과 전략 연결을 확인하고, 1차 검증 결과와 사용자 최종 통과를 분리해서 봅니다.</p>
                        </div>
                        <div className={`rounded-full border px-3 py-1 text-xs font-semibold ${generatorStatusSectionData.effectiveCodeGenerationStrategy === 'auto_generator' ? 'border-[#3fb950] text-[#3fb950]' : 'border-[#f78166] text-[#f78166]'}`}>
                            code generation: {generatorStatusSectionData.effectiveCodeGenerationStrategy}
                        </div>
                    </div>
                    <div className="mt-4 grid gap-3 lg:grid-cols-3">
                        <div className="rounded-lg border border-[#30363d] bg-[#0d1117] p-4">
                            <p className="text-xs font-semibold text-[#8b949e]">유효 파이프라인</p>
                            <p className="mt-2 text-sm text-[#e6edf3]">{generatorStatusSectionData.effectivePipelineText}</p>
                            <p className="mt-2 text-[11px] text-[#79c0ff]">spec pipeline: {generatorStatusSectionData.specPipelineText}</p>
                        </div>
                        <div className="rounded-lg border border-[#30363d] bg-[#0d1117] p-4">
                            <p className="text-xs font-semibold text-[#8b949e]">대화 응답 기본 연결</p>
                            <p className="mt-2 text-sm text-[#e6edf3]">텍스트 {generatorStatusSectionData.effectiveConversationAgents.text} / 음성 {generatorStatusSectionData.effectiveConversationAgents.voice}</p>
                            <p className="mt-2 text-[11px] text-[#79c0ff]">질문 {generatorStatusSectionData.effectiveConversationAgents.question} · 조사 {generatorStatusSectionData.effectiveConversationAgents.research} · 작업 {generatorStatusSectionData.effectiveConversationAgents.action}</p>
                        </div>
                        <div className="rounded-lg border border-[#30363d] bg-[#0d1117] p-4">
                            <p className="text-xs font-semibold text-[#8b949e]">reasoner 직접 개입</p>
                            <p className={`mt-2 text-sm font-semibold ${generatorStatusSectionData.reasonerCoverageClassName}`}>
                                {generatorStatusSectionData.reasonerCoverageState}
                            </p>
                            <p className="mt-2 text-[11px] text-[#8b949e]">{generatorStatusSectionData.reasonerCoverageSummary}</p>
                        </div>
                    </div>
                </div>}

                {!miniConsoleLayout && <RuntimeConfigPanel
                    data={runtimeConfigPanelData}
                    actions={runtimeConfigPanelActions}
                    helpers={runtimeConfigPanelHelpers}
                />}

                {!miniConsoleLayout && <AdminGeneratorDetailModal {...generatorModalBindings} />}

                {!miniConsoleLayout && <CapabilityPanel
                    presets={ORCHESTRATOR_PRESETS}
                    selectedPresetId={selectedPreset?.id || ''}
                    onApplyPreset={applyPreset}
                    capabilityGroups={ORCHESTRATOR_CAPABILITY_GROUPS}
                    capabilityGroupSummaryLookup={capabilityGroupSummaryLookup}
                    capabilitySummaryLookup={capabilitySummaryLookup}
                    selectedCapabilityActionId={selectedCapabilityActionId}
                    getLinkedPresetTitle={capabilityPanelBindings.getLinkedPresetTitle}
                    getCapabilityStateClassName={capabilityPanelBindings.getCapabilityStateClassName}
                    getCapabilityStateText={capabilityPanelBindings.getCapabilityStateText}
                    onSelectCapabilityAction={capabilityPanelBindings.onSelectCapabilityAction}
                    onApplyCapabilityAction={capabilityPanelBindings.onApplyCapabilityAction}
                    loading={loading}
                    selfRunBusy={selfRunBusy}
                    capabilityVoiceAlertEnabled={capabilityVoiceAlertEnabled}
                    onToggleCapabilityVoiceAlert={capabilityPanelBindings.onToggleCapabilityVoiceAlert}
                    onSpeakCapabilityAlert={capabilityPanelBindings.onSpeakCapabilityAlert}
                    onRefreshCapabilitySummary={capabilityPanelBindings.onRefreshCapabilitySummary}
                    capabilityLoading={capabilityPanelDataProps.capabilityLoading}
                    capabilityMessage={capabilityPanelDataProps.capabilityMessage}
                    capabilitySyncPhase={capabilitySyncPhase}
                    capabilityLastLiveRefreshElapsedSec={capabilityLastLiveRefreshElapsedSec}
                    capabilitySummaryGeneratedAt={capabilitySummary?.generated_at || ''}
                    capabilityDetail={capabilityPanelDataProps.capabilityDetail}
                    detailCapabilityAction={capabilityPanelDataProps.detailCapabilityAction}
                    activeCapabilityComparison={capabilityPanelBindings.activeCapabilityComparison}
                    beforeComparisonErrors={capabilityPanelDataProps.beforeComparisonErrors}
                    beforeComparisonWarnings={capabilityPanelDataProps.beforeComparisonWarnings}
                    afterComparisonErrors={capabilityPanelDataProps.afterComparisonErrors}
                    afterComparisonWarnings={capabilityPanelDataProps.afterComparisonWarnings}
                    comparisonResolvedTitles={capabilityPanelDataProps.comparisonResolvedTitles}
                    comparisonNewTitles={capabilityPanelDataProps.comparisonNewTitles}
                    getCapabilityFindingRenderKey={capabilityPanelBindings.getCapabilityFindingRenderKey}
                    getCapabilityCodeExampleRenderKey={capabilityPanelBindings.getCapabilityCodeExampleRenderKey}
                    buildSelfRunStatusLabel={capabilityPanelBindings.buildSelfRunStatusLabel}
                />}

                {!miniConsoleLayout && resultSummarySectionData.hardGate && (
                    <div className="mb-4 rounded-xl border border-[#30363d] bg-[#161b22] p-5">
                        <div className="mb-3 flex items-start justify-between gap-3">
                            <div>
                                <h2 className="text-lg font-semibold text-[#58a6ff]">출고 hard gate 결과</h2>
                                <p className="mt-1 text-xs text-[#8b949e]">의존성 설치, 단독 기동, API 스모크, pytest, 프레임워크 계약, 외부 연동, ZIP 재현을 단일 증거 체계로 표기합니다.</p>
                            </div>
                            <span className={`rounded-full px-3 py-1 text-xs font-semibold ${resultSummarySectionData.hardGate.statusClassName}`}>
                                {resultSummarySectionData.hardGate.statusLabel}
                            </span>
                        </div>
                        <p className="mb-3 text-xs text-[#8b949e]">{resultSummarySectionData.hardGate.summary}</p>
                        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                            {resultSummarySectionData.hardGate.stages.map((stage) => (
                                <div key={stage.id} className="rounded-lg border border-[#30363d] bg-[#0d1117] p-4">
                                    <div className="flex items-center justify-between gap-2">
                                        <p className="text-sm font-semibold text-[#e6edf3]">{stage.id}</p>
                                        <span className={`rounded-full px-2 py-1 text-[11px] font-semibold ${stage.ok ? 'border border-[#238636] bg-[rgba(35,134,54,0.16)] text-[#9be9a8]' : 'border border-[#da3633] bg-[rgba(218,54,51,0.18)] text-[#ffb3ad]'}`}>
                                            {stage.ok ? 'pass' : 'fail'}
                                        </span>
                                    </div>
                                    <p className="mt-2 text-[11px] text-[#8b949e]">{stage.summary}</p>
                                </div>
                            ))}
                        </div>
                        <div className="mt-3 rounded-lg border border-[#30363d] bg-[#0d1117] p-4 text-xs text-[#8b949e] space-y-1">
                            <p>archive: {resultSummarySectionData.hardGate.archivePath}</p>
                            <p>failed stages: {resultSummarySectionData.hardGate.failedStagesText}</p>
                            <p>운영 실도메인 동일 evidence 대상: `/api/llm/ws`, `/admin/llm`, `/marketplace/orchestrator`</p>
                        </div>
                    </div>
                )}

                {!miniConsoleLayout && (resultSummarySectionData.completionGate || resultSummarySectionData.semanticAudit) && (
                    <div className="mb-4 grid gap-4 xl:grid-cols-2">
                        {resultSummarySectionData.completionGate && (
                            <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-5">
                                <div className="mb-3 flex items-start justify-between gap-3">
                                    <div>
                                        <h2 className="text-lg font-semibold text-[#58a6ff]">completion gate 결과</h2>
                                        <p className="mt-1 text-xs text-[#8b949e]">최종 완료 판정과 차단 사유를 같은 summary helper 데이터로 렌더링합니다.</p>
                                    </div>
                                    <span className={`rounded-full px-3 py-1 text-xs font-semibold ${resultSummarySectionData.completionGate.statusClassName}`}>
                                        {resultSummarySectionData.completionGate.statusLabel}
                                    </span>
                                </div>
                                <div className="space-y-3 rounded-lg border border-[#30363d] bg-[#0d1117] p-4 text-xs text-[#8b949e]">
                                    <p>summary: {resultSummarySectionData.completionGate.summary}</p>
                                    <p>error: {resultSummarySectionData.completionGate.error}</p>
                                    <p>apply state: {resultSummarySectionData.execution.applyStateLabel} ({resultSummarySectionData.execution.applyState})</p>
                                    <p>output: {resultSummarySectionData.execution.outputDir}</p>
                                    <p>failed output: {resultSummarySectionData.execution.failedOutputDir}</p>
                                    <p>apply error: {resultSummarySectionData.execution.applyError}</p>
                                </div>
                            </div>
                        )}
                        {resultSummarySectionData.semanticAudit && (
                            <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-5">
                                <div className="mb-3 flex items-start justify-between gap-3">
                                    <div>
                                        <h2 className="text-lg font-semibold text-[#58a6ff]">semantic audit 결과</h2>
                                        <p className="mt-1 text-xs text-[#8b949e]">점수, 기준치, 체크리스트 수, 리포트 경로를 같은 summary helper 데이터로 렌더링합니다.</p>
                                    </div>
                                    <span className={`rounded-full px-3 py-1 text-xs font-semibold ${resultSummarySectionData.semanticAudit.statusClassName}`}>
                                        {resultSummarySectionData.semanticAudit.statusLabel}
                                    </span>
                                </div>
                                <div className="space-y-3 rounded-lg border border-[#30363d] bg-[#0d1117] p-4 text-xs text-[#8b949e]">
                                    <p>summary: {resultSummarySectionData.semanticAudit.summary}</p>
                                    <p>error: {resultSummarySectionData.semanticAudit.error}</p>
                                    <p>score: {resultSummarySectionData.semanticAudit.scoreLabel}</p>
                                    <p>threshold: {resultSummarySectionData.semanticAudit.thresholdLabel}</p>
                                    <p>checklist count: {resultSummarySectionData.semanticAudit.checklistCount}</p>
                                    <p>report: {resultSummarySectionData.semanticAudit.reportPath}</p>
                                </div>
                            </div>
                        )}
                    </div>
                )}

                <div className="mb-4 rounded-xl border border-[#30363d] bg-[#161b22] p-5">
                    {!miniConsoleLayout && <div className="mb-3 rounded-lg border border-[#30363d] bg-[#0d1117] p-4">
                        <label htmlFor="admin-work-output-dir" className="mb-2 block text-xs text-[#8b949e]">현재 작업 폴더</label>
                        <input
                            id="admin-work-output-dir"
                            name="workOutputDir"
                            type="text"
                            value={workOutputDir}
                            onChange={(e) => setWorkOutputDir(e.target.value)}
                            placeholder="예: C:\\...\\uploads\\projects\\project_20260309_xxxxxx"
                            className="w-full rounded-lg border border-[#30363d] bg-[#161b22] px-3 py-2 text-sm text-[#e6edf3]"
                        />
                        <p className="mt-2 text-xs text-[#8b949e]">챗봇이 현재 작업 폴더를 기준으로 바로 수정/실행하도록 유지합니다.</p>
                    </div>}
                    {!miniConsoleLayout && <div className="rounded-lg border border-[#30363d] bg-[#0d1117] p-4">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                            <div>
                                <p className="text-sm font-semibold text-[#e6edf3]">자동 · 반자동 오케스트레이션 이동</p>
                                <p className="mt-2 text-xs text-[#8b949e]">자가진단, 자가개선, 자가확장 같은 자동·반자동 실행 패널은 관리자 화면에서 빼고 마켓플레이스 오케스트레이터로 넘깁니다. 관리자 화면은 챗봇 지시와 즉시 실행에 집중합니다.</p>
                            </div>
                            <div className="rounded-lg border border-[#30363d] bg-[#161b22] px-3 py-2 text-xs text-[#8b949e] space-y-1">
                                <p>이동 경로 안내</p>
                                <p>/marketplace/orchestrator · /marketplace</p>
                            </div>
                        </div>
                    </div>}
                    <div className="mb-3">
                        <div className="mb-2 flex flex-wrap items-center gap-2">
                            <span className="text-[11px] font-semibold tracking-[0.28em] text-[#79c0ff]">CODE GENERATOR</span>
                            <h2 className="text-2xl font-bold text-[#e6edf3]">AI 코드 제너레이터</h2>
                            <span className="rounded-full bg-[#12381f] px-2 py-1 text-[11px] text-[#3fb950]">Enter 실행형</span>
                            {adminTerminalFocusedView && <span className="rounded-full bg-[#0f2747] px-2 py-1 text-[11px] text-[#9ecbff]">기능만 표시</span>}
                        </div>
                        <p className="text-xs text-[#8b949e]">프로젝트 설정 후 핵심 3모드를 고르고, 수동 체크 카드 없이 오케스트레이터가 역질문식으로 바로 진행합니다.</p>
                        <div className="mt-4 grid gap-4 xl:grid-cols-[220px_1fr]">
                            <div className="rounded-xl border border-[#25304a] bg-[#0f1726] p-4">
                                <p className="mb-3 text-sm font-semibold text-[#e6edf3]">프로필</p>
                                <div className="space-y-2">
                                    {ADMIN_TERMINAL_CORE_MODES.map((modeOption) => {
                                        const active = adminCoreMode === modeOption.id;
                                        return (
                                            <button
                                                key={modeOption.id}
                                                type="button"
                                                onClick={() => setAdminCoreMode(modeOption.id)}
                                                className={`w-full rounded-lg border px-3 py-3 text-left text-xs transition ${active ? 'border-[#79c0ff] bg-[#132846] text-[#e6edf3]' : 'border-[#30363d] bg-[#111827] text-[#8b949e]'}`}
                                            >
                                                <p className="text-sm font-semibold">{modeOption.label}</p>
                                                <p className="mt-1 leading-5">{modeOption.description}</p>
                                            </button>
                                        );
                                    })}
                                </div>
                                <div className="mt-4 border-t border-[#2b3548] pt-4 text-xs text-[#9fb0c2]">
                                    말투는 버튼 선택 없이 오케스트레이터가 대화 중 3종(자유대화/간결/실행형)을 먼저 질문해 자동 확정합니다.
                                </div>
                            </div>
                            <div className="rounded-xl border border-[#25304a] bg-[#0f1726] p-4">
                                <p className="text-sm font-semibold text-[#e6edf3]">프로젝트 설정</p>
                                <div className="mt-3 space-y-3">
                                    <label htmlFor="admin-generator-project-name" className="block text-xs font-medium text-[#9fb0c2]">프로젝트 이름</label>
                                    <input
                                        id="admin-generator-project-name"
                                        name="generatorProjectName"
                                        type="text"
                                        value={generatorProjectName}
                                        onChange={(event) => setGeneratorProjectName(event.target.value)}
                                        placeholder="my-project"
                                        className="w-full rounded-lg border border-[#2b3548] bg-[#0b1220] px-3 py-2 text-sm text-[#e6edf3]"
                                    />
                                    <label htmlFor="admin-generator-task-input" className="block text-xs font-medium text-[#9fb0c2]">태스크 설명</label>
                                    <textarea
                                        id="admin-generator-task-input"
                                        name="generatorTaskInput"
                                        value={chatInput}
                                        onChange={(event) => setUnifiedPrompt(event.target.value)}
                                        rows={4}
                                        placeholder="태스크 설명 (예: REST API 사용자 관리 시스템 생성)"
                                        className="w-full rounded-lg border border-[#2b3548] bg-[#0b1220] px-3 py-3 text-sm text-[#e6edf3] placeholder:text-[#6b7280]"
                                    />
                                    <button
                                        type="button"
                                        disabled={chatLoading || loading}
                                        onClick={async () => {
                                            await submitPrimaryPrompt(chatInput);
                                        }}
                                        className="w-full rounded-xl bg-[#2f6f99] px-4 py-3 text-sm font-semibold text-[#041018]"
                                    >
                                        {(chatLoading || loading) ? '실행 중...' : '코드 생성'}
                                    </button>
                                </div>
                            </div>
                        </div>
                        {!adminTerminalFocusedView && <div className="mt-3 grid gap-3 xl:grid-cols-2">
                            <div className="rounded-lg border border-[#30363d] bg-[#0d1117] p-4 text-xs text-[#8b949e] space-y-2">
                                <p className="text-sm font-semibold text-[#e6edf3]">대화 AI 추론</p>
                                <p>stage: {lastConversationStage || '-'}</p>
                                <p>suggested companion: {suggestedCompanionMode || '-'}</p>
                                <p>reason: {suggestedCompanionReason || '-'}</p>
                                <p>inferred goal: {inferredGoal || '-'}</p>
                            </div>
                            <div className="rounded-lg border border-[#30363d] bg-[#0d1117] p-4 text-xs text-[#8b949e] space-y-2">
                                <p className="text-sm font-semibold text-[#e6edf3]">신규 기술 / 타겟 수정 힌트</p>
                                <div className="space-y-2">
                                    {(technologyRecommendations.length > 0 ? technologyRecommendations : []).map((item) => (
                                        <div key={`${item.title}-${item.source || 'llm'}`} className="rounded-md border border-[#244766] bg-[#101826] px-3 py-2 text-[#c9d1d9]">
                                            <p className="font-semibold text-[#9ecbff]">{item.title}</p>
                                            <p className="mt-1 text-[11px] text-[#ffcf8a]">도입 리스크: {item.adoption_risk}</p>
                                            <p className="text-[11px] text-[#d2d9e3]">구현 난이도: {item.implementation_difficulty}</p>
                                            <p className="text-[11px] text-[#d2d9e3]">운영비: {item.operating_cost}</p>
                                            <p className="text-[11px] text-[#8fb0d4]">대체안: {item.alternative}</p>
                                        </div>
                                    ))}
                                </div>
                                <div className="space-y-1">
                                    {(newTechnologyCandidates.length > 0 ? newTechnologyCandidates : ['후보 없음']).map((item) => (
                                        <p key={item} className="rounded-md border border-[#30363d] bg-[#161b22] px-3 py-2 text-[#c9d1d9]">{item}</p>
                                    ))}
                                </div>
                                <div className="space-y-1 pt-1">
                                    {(targetPatchHints.length > 0 ? targetPatchHints : [{ file_id: '-', reason: '타겟 수정 힌트 없음' } as TargetPatchHint]).map((item, index) => (
                                        <div key={`${item.file_id}-${index}`} className="rounded-md border border-[#30363d] bg-[#161b22] px-3 py-2 text-[#c9d1d9]">
                                            <p>{item.file_id}</p>
                                            <p className="text-[11px] text-[#8b949e]">{[item.section_id, item.feature_id, item.chunk_id].filter(Boolean).join(' / ') || 'section/feature/chunk 없음'}</p>
                                            <p className="text-[11px] text-[#79c0ff]">{item.reason}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>}
                        {!adminTerminalFocusedView && <div className="mt-3 grid gap-3 xl:grid-cols-3">
                            <div className="rounded-lg border border-[#30363d] bg-[#0d1117] p-4 text-xs text-[#8b949e] space-y-2">
                                <p className="text-sm font-semibold text-[#e6edf3]">제안형 응답</p>
                                {(proposalItems.length > 0 ? proposalItems : [{ title: '제안 없음', detail: '아직 제안형 응답이 수집되지 않았습니다.' } as ProposalItem]).map((item) => (
                                    <div key={`${item.title}-${item.category || 'proposal'}`} className="rounded-md border border-[#30363d] bg-[#161b22] px-3 py-2">
                                        <p className="text-[#e6edf3]">{item.title}</p>
                                        <p className="mt-1 text-[#8b949e]">{item.detail}</p>
                                        {item.benefit && <p className="mt-1 text-[#79c0ff]">benefit: {item.benefit}</p>}
                                        {item.tradeoff && <p className="mt-1 text-[#f2cc60]">tradeoff: {item.tradeoff}</p>}
                                    </div>
                                ))}
                            </div>
                            <div className="rounded-lg border border-[#30363d] bg-[#0d1117] p-4 text-xs text-[#8b949e] space-y-2">
                                <p className="text-sm font-semibold text-[#e6edf3]">추가 확인 질문</p>
                                {(clarificationQuestions.length > 0 ? clarificationQuestions : [{ prompt: '추가 확인 질문 없음' } as AdvisoryQuestion]).map((item, index) => (
                                    <div key={`${item.prompt}-${index}`} className="rounded-md border border-[#30363d] bg-[#161b22] px-3 py-2">
                                        <p className="text-[#e6edf3]">{item.prompt}</p>
                                        {item.reason && <p className="mt-1 text-[#8b949e]">{item.reason}</p>}
                                    </div>
                                ))}
                            </div>
                            <div className="rounded-lg border border-[#30363d] bg-[#0d1117] p-4 text-xs text-[#8b949e] space-y-2">
                                <p className="text-sm font-semibold text-[#e6edf3]">다음 액션 / 근거</p>
                                {(nextActionSuggestions.length > 0 ? nextActionSuggestions : [{ title: '다음 액션 없음', detail: '현재 추천된 후속 액션이 없습니다.' } as AdvisoryNextAction]).map((item, index) => (
                                    <div key={`${item.title}-${index}`} className="rounded-md border border-[#30363d] bg-[#161b22] px-3 py-2">
                                        <p className="text-[#e6edf3]">{item.title}</p>
                                        <p className="mt-1 text-[#8b949e]">{item.detail}</p>
                                        {item.action_type === 'feature_orchestrate' && item.action_payload && (
                                            <button
                                                type="button"
                                                onClick={() => {
                                                    void runFeatureOrchestrateAction(item);
                                                }}
                                                disabled={featureActionRunning || chatLoading}
                                                className="mt-2 rounded-lg border border-[#1f6feb] bg-[#0f2747] px-3 py-1.5 text-[11px] font-semibold text-[#9ecbff] disabled:cursor-not-allowed disabled:opacity-60"
                                            >
                                                {featureActionRunning ? '실행 준비 중...' : '검색 근거로 feature-orchestrate 실행'}
                                            </button>
                                        )}
                                    </div>
                                ))}
                                {(evidenceHighlights.length > 0 ? evidenceHighlights : [{ title: '근거 없음', source_label: '-', why_it_matters: '아직 수집된 대화 근거가 없습니다.' } as AdvisoryEvidenceItem]).map((item, index) => (
                                    <div key={`${item.title}-${index}`} className="rounded-md border border-[#1f6feb] bg-[#0f2747] px-3 py-2">
                                        <p className="text-[#e6edf3]">{item.title}</p>
                                        <p className="mt-1 text-[#9ecbff]">source: {item.source_label}</p>
                                        <p className="mt-1 text-[#c9d1d9]">{item.why_it_matters}</p>
                                    </div>
                                ))}
                            </div>
                        </div>}
                    </div>
                    {lastWebResults.length > 0 && (
                        <div className="mb-3 rounded-lg border border-[#1f6feb] bg-[#0f2747] p-4 text-xs text-[#9ecbff]">
                            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                                <p className="text-sm font-semibold text-[#e6edf3]">웹 검색 근거 {lastWebResults.length}건</p>
                                <span className="rounded-full border border-[#79c0ff] px-2 py-1 text-[10px] font-semibold text-[#79c0ff]">
                                    grounding: {lastGroundingMode || 'internal'}
                                </span>
                            </div>
                            <div className="space-y-2">
                                {lastWebResults.map((item, index) => (
                                    <div key={`${item.url || item.title}-${index}`} className="rounded-md border border-[#2f81f7] bg-[#0d223f] px-3 py-2 text-[#c9d1d9]">
                                        <p className="font-semibold text-[#e6edf3]">{index + 1}. {item.title}</p>
                                        <p className="mt-1 text-[#9ecbff]">{item.domain || item.source_type || '-'}</p>
                                        <p className="mt-1">{item.snippet}</p>
                                        {item.url && (
                                            <a href={item.url} target="_blank" rel="noreferrer" className="mt-1 inline-block text-[#79c0ff] underline">
                                                {item.url}
                                            </a>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                    <AdminExternalSearchPanel
                        endpoint={externalSearchEndpoint}
                        query={externalSearchQuery}
                        placeId={externalSearchPlaceId}
                        loading={externalSearchLoading}
                        message={externalSearchMessage}
                        result={externalSearchResult}
                        onChangeEndpoint={setExternalSearchEndpoint}
                        onChangeQuery={setExternalSearchQuery}
                        onChangePlaceId={setExternalSearchPlaceId}
                        onRun={runExternalSearch}
                    />
                    <div className="mb-3 max-h-[460px] space-y-3 overflow-y-auto rounded-lg border border-[#30363d] bg-[#0d1117] p-4">
                        {conversation.map((message, index) => (
                            <div
                                key={`${message.timestamp || 'msg'}-${index}`}
                                className={`rounded-lg border px-4 py-3 ${message.role === 'user' ? 'ml-10 border-[#1f6feb] bg-[#0f2747]' : 'mr-10 border-[#30363d] bg-[#161b22]'}`}
                            >
                                <div className="mb-1 flex items-center justify-between gap-3 text-[11px] text-[#8b949e]">
                                    <span>{message.speaker || message.role}</span>
                                    <span>{message.timestamp ? new Date(message.timestamp).toLocaleTimeString('ko-KR') : ''}</span>
                                </div>
                                <p className="whitespace-pre-wrap break-words text-sm text-[#e6edf3]">{message.content}</p>
                            </div>
                        ))}
                    </div>
                    <div className="rounded-lg border border-[#30363d] bg-[#11161d] p-3">
                        <label htmlFor="admin-llm-chat-input" className="mb-2 block text-xs font-semibold text-[#79c0ff]">역질문 입력</label>
                        <textarea
                            id="admin-llm-chat-input"
                            name="adminLlmChatInput"
                            value={chatInput}
                            onChange={(e) => setUnifiedPrompt(e.target.value)}
                            onKeyDown={async (e) => {
                                if (e.key !== 'Enter' || e.shiftKey) return;
                                e.preventDefault();
                                const handled = await applyAdminStageCommand(chatInput);
                                if (!handled) {
                                    await submitPrimaryPrompt(chatInput);
                                }
                            }}
                            placeholder="예: 이 기능을 운영형으로 닫으려면 먼저 어떤 구현 조건을 확인해야 하나요?"
                            className="box-border min-h-[108px] w-full resize-y rounded-lg border border-[#4b5563] bg-[#f8fafc] p-3 text-sm text-[#0f172a] placeholder:text-[#64748b]"
                        />
                        <p className="mt-3 text-xs text-[#8b949e]">Enter 실행, Shift+Enter 줄바꿈. 현재 모드: {ADMIN_TERMINAL_CORE_MODES.find((item) => item.id === adminCoreMode)?.label}</p>
                    </div>
                </div>

                {error && <div className="mb-4 rounded-lg border border-[#f78166] bg-[#2d1f1f] p-3 text-[#f78166]">{error}</div>}

                {false && shouldShowLivePanel && null}

                {false && shouldShowExecutionSummary && null}
            </div>
        </div>
    );
}
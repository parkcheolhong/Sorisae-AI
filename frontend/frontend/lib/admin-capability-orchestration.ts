import type { MutableRefObject } from 'react';

import type { SelfRunDirectiveScope, SelfRunDirectiveTemplate } from '@/lib/use-admin-self-run';

import { buildExpansionExperimentRunOverrides } from '@/lib/admin-expansion-experiment-run';

export interface CapabilityActionLike {
    id: string;
    title: string;
    summary: string;
    presetId: string;
    task: string;
    accentClassName: string;
}

export interface CapabilityPresetLike {
    id?: string;
    title?: string;
    mode?: string;
    task?: string;
    description?: string;
}

export interface CapabilityValidationFindingLike {
    severity: string;
    title: string;
    problem: string;
    improvement: string;
}

export interface CapabilityDetailLike {
    expansion_experiment?: {
        work_document?: string;
        work_document_title?: string;
        focus_path?: string;
        recommended_self_run?: {
            directive_template?: string;
            directive_scope?: string;
            directive_request?: string;
            mode?: string;
            execution_mode?: string;
        };
    } | null;
    capability?: {
        detail?: string | null;
        metric?: string | null;
    } | null;
    target_file_ids?: string[];
    target_section_ids?: string[];
    target_feature_ids?: string[];
    target_chunk_ids?: string[];
    failure_tags?: string[];
    repair_tags?: string[];
    validation_findings?: CapabilityValidationFindingLike[];
    suggested_actions?: string[];
}

export interface PendingCapabilityExecutionLike<TDetail> {
    capabilityId: string;
    capturedAt: string;
    beforeDetail: TDetail | null;
}

export interface CapabilityExecutionComparisonLike<TDetail, TRunResult, TSelfRunResult> {
    capabilityId: string;
    capturedAt: string;
    beforeDetail: TDetail | null;
    afterDetail: TDetail | null;
    runResult: TRunResult | null;
    selfRunResult?: TSelfRunResult | null;
}

interface SelfRunExecutionResultLike<TRunResult> {
    status?: string;
    orchestration_result?: TRunResult | null;
}

export const inferCapabilityDirectiveTemplate = (
    action: CapabilityActionLike,
    detail: CapabilityDetailLike | null,
): SelfRunDirectiveTemplate => {
    const failureCount = (detail?.validation_findings || []).length;
    const mergedText = [
        action.summary,
        ...(detail?.suggested_actions || []),
        ...(detail?.validation_findings || []).map((finding) => `${finding.title} ${finding.problem}`),
    ].join(' ');

    if (failureCount > 0 && /보안|security|runtime|validation|approval|semantic|worker|python/i.test(mergedText)) {
        return 'debug_remediation_loop';
    }

    if (/ollama|timeout|readtimeout|latency|응답 대기 시간 초과/i.test(mergedText)) {
        return 'llm_cost_latency';
    }

    return 'admin_ops_efficiency';
};

export const buildCapabilityDirectiveRequest = (
    action: CapabilityActionLike,
    detail: CapabilityDetailLike | null,
) => {
    const failureFindings = (detail?.validation_findings || []).slice(0, 8);
    const suggestedActions = (detail?.suggested_actions || []).slice(0, 6);
    const targetFileIds = (detail?.target_file_ids || []).slice(0, 8);
    const targetSectionIds = (detail?.target_section_ids || []).slice(0, 8);
    const targetFeatureIds = (detail?.target_feature_ids || []).slice(0, 8);
    const targetChunkIds = (detail?.target_chunk_ids || []).slice(0, 8);
    const failureTags = (detail?.failure_tags || []).slice(0, 8);
    const repairTags = (detail?.repair_tags || []).slice(0, 8);
    const detailSummary = detail?.capability?.detail || detail?.capability?.metric || action.summary;
    const defectCommands = failureFindings.length > 0
        ? failureFindings.map((finding, index) => {
            const severity = finding.severity === 'error' ? '즉시 수정' : '정리 후 재검증';
            return `${index + 1}. ${severity} | ${finding.title} | 원인=${finding.problem} | 조치=${finding.improvement}`;
        }).join('\n')
        : '1. 현재 상세 패널의 실패 근거를 기준으로 실제 결함을 재식별하고 즉시 수정할 것';

    const systemUnderstandingLines = failureFindings.length > 0
        ? failureFindings.map((finding, index) => `${index + 1}. ${finding.title} 가 연결된 파일/상태/호출 체인을 설명하고 수정 영향 범위를 기록`).join('\n')
        : '1. 결함과 연결된 호출 체인, 상태 저장 경로, 승인 게이트 영향 범위를 정리할 것';

    const riskLines = suggestedActions.length > 0
        ? suggestedActions.map((item, index) => `${index + 1}. ${item}`).join('\n')
        : '1. 수정 후 남는 리스크와 미검증 항목을 분리 기록할 것';

    const targetedScopeLines = [
        `1. TARGET_FILE_IDS=${targetFileIds.join(', ') || '없음'}`,
        `2. TARGET_SECTION_IDS=${targetSectionIds.join(', ') || '없음'}`,
        `3. TARGET_FEATURE_IDS=${targetFeatureIds.join(', ') || '없음'}`,
        `4. TARGET_CHUNK_IDS=${targetChunkIds.join(', ') || '없음'}`,
        `5. FAILURE_TAGS=${failureTags.join(', ') || '없음'} / REPAIR_TAGS=${repairTags.join(', ') || '없음'}`,
    ].join('\n');

    const performanceLines = [
        '1. 결함 제거 후 남는 지연, 자원 점유, 반복 작업만 최적화할 것',
        '2. 성능 최적화 때문에 기능 회귀나 검증 우회가 생기면 실패로 남길 것',
    ].join('\n');

    return [
        `[디버깅 기반 corrective command] ${action.title}`,
        `현재 상태 요약: ${detailSummary}`,
        '',
        '[목표]',
        '- 검출된 결함을 수정 조치 명령으로 되돌려 오케스트레이터가 코드 자동생성기로 실제 개선을 수행하게 할 것',
        '- 이번 실행은 분석 보고서 작성이 아니라 수정, 검증, 승인 대기 결과 생성까지 완료할 것',
        '- 해결되지 않은 결함은 숨기지 말고 차단 원인과 미해결 상태를 그대로 남길 것',
        '',
        '[1단계 결함 식별 및 제거]',
        defectCommands,
        '',
        '[2단계 시스템 이해도 향상]',
        systemUnderstandingLines,
        '',
        '[3단계 리스크 관리]',
        riskLines,
        '',
        '[4단계 타겟 범위 고정]',
        targetedScopeLines,
        '',
        '[5단계 성능 최적화]',
        performanceLines,
        '',
        '[완료 조건]',
        '- 수정 파일, 수정 이유, 검증 결과, 남은 리스크, 후속 과제를 모두 기록할 것',
        '- validation_findings 수치가 실제로 줄었는지 before/after 로 비교할 것',
    ].join('\n');
};

export async function applyCapabilityActionOrchestration<
    TDetail extends CapabilityDetailLike,
    TRunResult,
    TSelfRunResult extends SelfRunExecutionResultLike<TRunResult>,
>(options: {
    action: CapabilityActionLike;
    execution?: 'prepare' | 'run';
    getPresetById: (presetId: string) => CapabilityPresetLike | null;
    buildCapabilityTask: (action: CapabilityActionLike, preset: CapabilityPresetLike | null) => string;
    setSelectedPreset: (preset: CapabilityPresetLike | null) => void;
    setSelectedCapabilityActionId: (capabilityId: string) => void;
    setUnifiedPrompt: (value: string) => void;
    setMode: (value: string) => void;
    refreshCapabilityDetail: (capabilityId: string) => Promise<TDetail | null>;
    isImmediateSelfRunCapability: (action: CapabilityActionLike) => boolean;
    pendingCapabilityExecutionRef: MutableRefObject<PendingCapabilityExecutionLike<TDetail> | null>;
    executeSelfWorkflow: (
        requestedMode: 'self-improvement' | 'self-expansion',
        overrides: {
            directiveTemplate: SelfRunDirectiveTemplate;
            directiveScope: SelfRunDirectiveScope;
            directiveRequest: string;
        },
    ) => Promise<TSelfRunResult | null>;
    runWorkflow: (options: {
        task: string;
        nextMode: string;
        nextPreset: CapabilityPresetLike | null;
        nextCapabilityActionId: string;
    }) => Promise<TRunResult | null>;
    setCapabilityExecutionComparison: (comparison: CapabilityExecutionComparisonLike<TDetail, TRunResult, TSelfRunResult>) => void;
}) {
    const execution = options.execution || 'prepare';
    const preset = options.getPresetById(options.action.presetId);
    const nextTask = options.buildCapabilityTask(options.action, preset);
    const nextMode = preset?.mode || 'review';

    options.setSelectedPreset(preset);
    options.setSelectedCapabilityActionId(options.action.id);
    options.setUnifiedPrompt(nextTask);
    options.setMode(nextMode);

    const beforeDetail = await options.refreshCapabilityDetail(options.action.id);
    if (execution !== 'run') {
        if (options.action.id === 'code-generator') {
            const expansionOverrides = buildExpansionExperimentRunOverrides(beforeDetail);
            options.setUnifiedPrompt(expansionOverrides.unifiedPrompt);
        }
        return null;
    }

    if (options.action.id === 'code-generator') {
        const capturedAt = new Date().toISOString();
        options.pendingCapabilityExecutionRef.current = {
            capabilityId: options.action.id,
            capturedAt,
            beforeDetail,
        };
        const expansionOverrides = buildExpansionExperimentRunOverrides(beforeDetail);
        options.setUnifiedPrompt(expansionOverrides.unifiedPrompt);
        const selfRunExecution = await options.executeSelfWorkflow('self-expansion', expansionOverrides);

        if (selfRunExecution && selfRunExecution.status !== 'running') {
            options.pendingCapabilityExecutionRef.current = null;
            const afterDetail = await options.refreshCapabilityDetail(options.action.id);
            options.setCapabilityExecutionComparison({
                capabilityId: options.action.id,
                capturedAt,
                beforeDetail,
                afterDetail,
                runResult: selfRunExecution.orchestration_result || null,
                selfRunResult: selfRunExecution,
            });
        }
        return selfRunExecution;
    }

    if (options.isImmediateSelfRunCapability(options.action)) {
        const capturedAt = new Date().toISOString();
        options.pendingCapabilityExecutionRef.current = {
            capabilityId: options.action.id,
            capturedAt,
            beforeDetail,
        };

        const selfRunExecution = await options.executeSelfWorkflow('self-improvement', {
            directiveTemplate: inferCapabilityDirectiveTemplate(options.action, beforeDetail),
            directiveScope: 'targeted_implementation',
            directiveRequest: buildCapabilityDirectiveRequest(options.action, beforeDetail),
        });

        if (selfRunExecution && selfRunExecution.status !== 'running') {
            options.pendingCapabilityExecutionRef.current = null;
            const afterDetail = await options.refreshCapabilityDetail(options.action.id);
            options.setCapabilityExecutionComparison({
                capabilityId: options.action.id,
                capturedAt,
                beforeDetail,
                afterDetail,
                runResult: selfRunExecution.orchestration_result || null,
                selfRunResult: selfRunExecution,
            });
        }
        return selfRunExecution;
    }

    const runResult = await options.runWorkflow({
        task: nextTask,
        nextMode,
        nextPreset: preset,
        nextCapabilityActionId: options.action.id,
    });
    const afterDetail = await options.refreshCapabilityDetail(options.action.id);
    options.setCapabilityExecutionComparison({
        capabilityId: options.action.id,
        capturedAt: new Date().toISOString(),
        beforeDetail,
        afterDetail,
        runResult,
        selfRunResult: null,
    });
    return runResult;
}

interface RunLifecycleSemanticAuditLike {
    passed?: boolean;
    error?: string;
    summary?: string;
    score?: number;
    maxScore?: number;
    threshold?: number;
    checklist: any[];
}

export function buildAdminOrchestrateRequestBody(options: {
    effectiveTaskInput: string;
    effectiveModeState: string;
    companionMode: string;
    continueInPlace: boolean;
    outputDir?: string;
    nextRunId: string;
    maxTokens?: number;
    conversation: any[];
    enabledRules: string[];
    mandatoryRules: string[];
}) {
    const appliedRules = [...options.mandatoryRules, ...options.enabledRules];
    const rulesSummary = appliedRules.length
        ? `\n\n[적용 규칙]\n- ${appliedRules.join('\n- ')}`
        : '\n\n[적용 규칙]\n- 없음';

    return {
        task: `${options.effectiveTaskInput}${rulesSummary}`,
        mode: options.effectiveModeState,
        manual_mode: false,
        companion_mode: options.companionMode,
        output_dir: options.continueInPlace ? options.outputDir : undefined,
        continue_in_place: options.continueInPlace,
        run_id: options.nextRunId,
        max_tokens: options.maxTokens,
        conversation: options.conversation,
    };
}

export function applyAdminRunOptions(options: {
    incomingOptions?: {
        task?: string;
        nextMode?: string;
        nextPreset?: any;
        nextCapabilityActionId?: string;
    };
    currentMode: string;
    getEffectiveTaskInput: () => string;
    setUnifiedPrompt: (value: string) => void;
    setSelectedPreset: (value: any) => void;
    setSelectedCapabilityActionId: (value: string) => void;
    setMode: (value: string) => void;
    setTask: (value: string) => void;
}) {
    const effectiveTaskInput = options.incomingOptions?.task?.trim() || options.getEffectiveTaskInput();
    if (!effectiveTaskInput) {
        return null;
    }
    const effectiveModeState = options.incomingOptions?.nextMode ?? options.currentMode;
    if (options.incomingOptions?.task) {
        options.setUnifiedPrompt(effectiveTaskInput);
    }
    if (options.incomingOptions?.nextPreset !== undefined) {
        options.setSelectedPreset(options.incomingOptions.nextPreset);
    }
    if (options.incomingOptions?.nextCapabilityActionId !== undefined) {
        options.setSelectedCapabilityActionId(options.incomingOptions.nextCapabilityActionId);
    }
    options.setMode(effectiveModeState);
    options.setTask(effectiveTaskInput);

    return {
        effectiveTaskInput,
        effectiveModeState,
    };
}

export function applyAdminRunSuccessState(options: {
    normalizedRunResult: ReturnType<typeof normalizeAdminRunResult>;
    liveRunIdRef: { current: string };
    setLiveRunId: (value: string) => void;
    setLiveOrchestrationSpec: (value: any) => void;
    setLiveOutputDir: (value: string) => void;
    setWorkOutputDir: (value: string) => void;
    setLiveApplyError: (value: string) => void;
    setLivePipeline: (value: string[]) => void;
    setLiveStateHistory: (value: string[]) => void;
    setLiveCurrentState: (value: string) => void;
    setLiveSemanticAudit: (value: RunLifecycleSemanticAuditLike | null) => void;
    setLiveStatus: (value: 'success' | 'failed') => void;
    setLiveApplyState: (value: 'applied' | 'failed' | 'response-only') => void;
    appendLiveLog: (event: string, message: string, stage?: string) => void;
    setConversation: (value: any[]) => void;
    setResult: (value: any) => void;
    setActiveResult: (value: number) => void;
}) {
    const { normalizedRunResult } = options;
    if (normalizedRunResult.nextRunId) {
        options.liveRunIdRef.current = normalizedRunResult.nextRunId;
        options.setLiveRunId(normalizedRunResult.nextRunId);
    }
    options.setLiveOrchestrationSpec(normalizedRunResult.orchestrationSpec);
    options.setLiveOutputDir(normalizedRunResult.outputDir);
    if (normalizedRunResult.nextWorkOutputDir) {
        options.setWorkOutputDir(normalizedRunResult.nextWorkOutputDir);
    }
    options.setLiveApplyError(normalizedRunResult.applyError);
    options.setLivePipeline(normalizedRunResult.pipeline);
    options.setLiveStateHistory(normalizedRunResult.stateHistory);
    options.setLiveCurrentState(normalizedRunResult.currentState);
    options.setLiveSemanticAudit(normalizedRunResult.semanticAudit);
    options.setLiveStatus(normalizedRunResult.liveStatus);
    options.setLiveApplyState(normalizedRunResult.liveApplyState);
    options.appendLiveLog('client', '최종 응답 수신 완료', normalizedRunResult.completionStage);
    if (normalizedRunResult.conversation.length > 0) {
        options.setConversation(normalizedRunResult.conversation);
    }
    options.setResult(normalizedRunResult.result);
    options.setActiveResult(normalizedRunResult.result.results.length - 1);
}

export function applyAdminRunFailureState(options: {
    errorMessage: string;
    fallbackState: string;
    setLiveStatus: (value: 'failed') => void;
    setLiveApplyState: (value: 'failed') => void;
    setLiveApplyError: (value: string) => void;
    appendLiveLog: (event: string, message: string, stage?: string) => void;
    setError: (value: string) => void;
}) {
    options.setLiveStatus('failed');
    options.setLiveApplyState('failed');
    options.setLiveApplyError(options.errorMessage);
    options.appendLiveLog('client-error', `실행 오류: ${options.errorMessage}`, options.fallbackState || 'FAILED');
    options.setError(`오류: ${options.errorMessage}`);
}

export function resetAdminRunLifecycleState(options: {
    nextRunId: string;
    effectiveTaskInput: string;
    effectiveModeState: string;
    continueInPlace: boolean;
    workOutputDir: string;
    liveOutputDir: string;
    setLiveRunId: (value: string) => void;
    setLiveTask: (value: string) => void;
    setLiveMode: (value: string) => void;
    setLivePipeline: (value: string[]) => void;
    setLiveStatus: (value: 'running') => void;
    setLiveCurrentState: (value: string) => void;
    setLiveStateHistory: (value: string[]) => void;
    setLiveLogs: (value: any[]) => void;
    setLiveUpdatedAt: (value: string) => void;
    setLiveSemanticAudit: (value: RunLifecycleSemanticAuditLike | null) => void;
    setLiveOrchestrationSpec: (value: any) => void;
    setLiveOutputDir: (value: string) => void;
    setLiveApplyState: (value: 'running') => void;
    setLiveApplyError: (value: string) => void;
    setLoading: (value: boolean) => void;
    setError: (value: string) => void;
    setResult: (value: any | null) => void;
}) {
    options.setLiveRunId(options.nextRunId);
    options.setLiveTask(options.effectiveTaskInput);
    options.setLiveMode(options.effectiveModeState);
    options.setLivePipeline([]);
    options.setLiveStatus('running');
    options.setLiveCurrentState('');
    options.setLiveStateHistory([]);
    options.setLiveLogs([]);
    options.setLiveUpdatedAt(new Date().toISOString());
    options.setLiveSemanticAudit(null);
    options.setLiveOrchestrationSpec(null);
    options.setLiveOutputDir(options.continueInPlace ? (options.workOutputDir || options.liveOutputDir) : '');
    options.setLiveApplyState('running');
    options.setLiveApplyError('');
    options.setLoading(true);
    options.setError('');
    options.setResult(null);
}

export function normalizeAdminRunResult<T extends Record<string, any>>(data: T) {
    return {
        nextRunId: typeof data.run_id === 'string' ? data.run_id : '',
        orchestrationSpec: data.orchestration_spec || null,
        outputDir: data.output_dir || data.failed_output_dir || '',
        nextWorkOutputDir: data.applied && data.output_dir ? data.output_dir : '',
        applyError: data.apply_error || '',
        pipeline: Array.isArray(data.pipeline) ? data.pipeline : [],
        stateHistory: Array.isArray(data.state_history) ? data.state_history : [],
        currentState: Array.isArray(data.state_history) && data.state_history.length > 0
            ? data.state_history[data.state_history.length - 1]
            : '',
        semanticAudit: typeof data.semantic_audit_ok === 'boolean' || Array.isArray(data.semantic_audit_checklist)
            ? {
                passed: data.semantic_audit_ok ?? undefined,
                error: data.semantic_audit_error || '',
                summary: data.semantic_audit_summary || '',
                score: typeof data.semantic_audit_score === 'number' ? data.semantic_audit_score : undefined,
                maxScore: typeof data.semantic_audit_max_score === 'number' ? data.semantic_audit_max_score : undefined,
                threshold: typeof data.semantic_audit_threshold === 'number' ? data.semantic_audit_threshold : undefined,
                checklist: Array.isArray(data.semantic_audit_checklist) ? data.semantic_audit_checklist : [],
            }
            : null,
        liveStatus: (data.apply_error ? 'failed' : 'success') as 'success' | 'failed',
        liveApplyState: (data.applied ? 'applied' : (data.apply_error ? 'failed' : 'response-only')) as 'applied' | 'failed' | 'response-only',
        completionStage: data.state_history?.[data.state_history.length - 1] || 'DONE',
        conversation: Array.isArray(data.conversation) ? data.conversation : [],
        result: data,
    };
}

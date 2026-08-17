import type { AdminDashboardSelfRunStatusLike } from '@/lib/admin-self-run-control';

export type SelfRunFailureInsightLike = {
    severity: 'warning' | 'critical';
    category: 'python_compile_fail' | 'import_error' | 'dependency' | 'timeout' | 'output_shortage' | 'unknown';
    title: string;
    reason: string;
    automatedActions: string[];
    priorityFixPaths: string[];
    guideHref: string;
};

export type AutoRecoveryHistoryItemLike = {
    id: string;
    triggeredAt: string;
    mode: 'auto' | 'manual';
    title: string;
    category: SelfRunFailureInsightLike['category'] | 'generic';
    summary: string;
    approvalId?: string;
    primaryPath?: string;
    retryQueued?: boolean;
    retryMessage?: string;
    retryStage?: 'diagnosis' | 'remediation';
    failedFiles?: string[];
    normalizationAction?: string;
    normalizationMessage?: string;
};

export type AutoRecoveryExecutionResult = {
    retryResult: any;
    normalizationResult: any;
    shouldOpenPanels: boolean;
    shouldOpenSystemSettingsPanel: boolean;
    shouldReloadDashboard: boolean;
    historyItem: AutoRecoveryHistoryItemLike;
};

export async function executeAdminAutomaticRecovery(options: {
    mode: 'auto' | 'manual';
    selfRunFailureInsight: SelfRunFailureInsightLike | null;
    dashboardSelfRunStatus: AdminDashboardSelfRunStatusLike | null;
    systemSettingsDisconnected: boolean;
    hasOrchestratorCapabilityError: boolean;
    hasOrchestratorCapabilityWarning: boolean;
    selfRunApiUnavailable: boolean;
    retryWorkspaceSelfRun: (targetStage: 'diagnosis' | 'remediation', sourcePath?: string | null) => Promise<any>;
    normalizeWorkspaceSelfRun: (cleanupOnly?: boolean) => Promise<any>;
}) {
    let retryResult: any = null;
    let normalizationResult: any = null;
    const focusedSourcePath = options.dashboardSelfRunStatus?.python_compile_failed_files?.[0]
        || options.selfRunFailureInsight?.priorityFixPaths?.[0]
        || options.dashboardSelfRunStatus?.source_path
        || null;

    if (options.selfRunFailureInsight) {
        if (!options.selfRunApiUnavailable) {
            retryResult = await options.retryWorkspaceSelfRun('remediation', focusedSourcePath);
        }
        if (!options.selfRunApiUnavailable && (!retryResult || retryResult?.queued !== true)) {
            normalizationResult = await options.normalizeWorkspaceSelfRun(Boolean(retryResult && retryResult?.queued === false));
        }
    }

    const executedAt = new Date().toLocaleString('ko-KR', { hour12: false });
    const historyItem: AutoRecoveryHistoryItemLike = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        triggeredAt: executedAt,
        mode: options.mode,
        title: options.selfRunFailureInsight?.title || '일반 자동 복구 실행',
        category: options.selfRunFailureInsight?.category ?? 'generic',
        summary: [
            options.selfRunFailureInsight?.reason,
            retryResult?.message,
            normalizationResult?.message,
            focusedSourcePath ? `집중 경로 ${focusedSourcePath}` : '',
            '경고/실패 상태에 따라 패널 개방과 재진단을 실행했습니다.',
        ].filter(Boolean).join(' · '),
        approvalId: options.dashboardSelfRunStatus?.approval_id,
        primaryPath: retryResult?.focused_path
            || retryResult?.target_source_path
            || retryResult?.latest?.python_compile_failed_files?.[0]
            || normalizationResult?.latest?.python_compile_failed_files?.[0]
            || focusedSourcePath
            || undefined,
        retryQueued: typeof retryResult?.queued === 'boolean' ? retryResult.queued : undefined,
        retryMessage: retryResult?.message || undefined,
        retryStage: options.selfRunFailureInsight ? 'remediation' : undefined,
        failedFiles: retryResult?.latest?.python_compile_failed_files
            || normalizationResult?.latest?.python_compile_failed_files
            || options.dashboardSelfRunStatus?.python_compile_failed_files
            || [],
        normalizationAction: normalizationResult?.action || undefined,
        normalizationMessage: normalizationResult?.message || undefined,
    };

    return {
        retryResult,
        normalizationResult,
        shouldOpenPanels: !!options.selfRunFailureInsight,
        shouldOpenSystemSettingsPanel: options.systemSettingsDisconnected,
        shouldReloadDashboard: !!(
            options.hasOrchestratorCapabilityError
            || options.hasOrchestratorCapabilityWarning
            || options.selfRunFailureInsight
        ),
        historyItem,
        executedAt,
    } satisfies AutoRecoveryExecutionResult & { executedAt: string };
}

export function shouldRunSelfRunAutoNormalization(options: {
    autoOpsEnabled: boolean;
    dashboardSelfRunStatus: AdminDashboardSelfRunStatusLike | null;
    selfRunApiUnavailable: boolean;
    selfRunRetrying: boolean;
    selfRunNormalizing: boolean;
    hasSecurityGuardProblem: boolean;
    normalizationSignature: string;
    currentSignature: string;
}) {
    if (!options.autoOpsEnabled || !options.dashboardSelfRunStatus || options.dashboardSelfRunStatus.status !== 'failed') {
        return false;
    }
    if (options.selfRunApiUnavailable) {
        return false;
    }
    if (options.selfRunRetrying || options.selfRunNormalizing) {
        return false;
    }
    if (options.hasSecurityGuardProblem) {
        return false;
    }
    if (options.normalizationSignature === options.currentSignature) {
        return false;
    }
    return true;
}

export function assertAdminAutoRecoveryContract() {
    const sample = shouldRunSelfRunAutoNormalization({
        autoOpsEnabled: true,
        dashboardSelfRunStatus: { approval_id: 'sample', status: 'failed' },
        selfRunApiUnavailable: false,
        selfRunRetrying: false,
        selfRunNormalizing: false,
        hasSecurityGuardProblem: false,
        normalizationSignature: '',
        currentSignature: 'sample:failed',
    });
    if (typeof sample !== 'boolean') {
        throw new Error('admin auto recovery contract 누락: shouldRunSelfRunAutoNormalization boolean 반환 필요');
    }
}

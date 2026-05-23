interface HardGateStageLike {
    id: string;
    ok: boolean;
    summary: string;
}

interface HardGateLike {
    ok?: boolean;
    summary?: string | null;
    failed_stages?: string[];
    stages?: HardGateStageLike[];
    archive_path?: string | null;
}

export function buildAdminResultSummarySectionData(options: {
    effectiveProductReadinessHardGate: HardGateLike | null;
    hasCompletionGateResult: boolean;
    effectiveCompletionGateOk: boolean;
    effectiveCompletionGateError: string;
    effectiveCompletionSummary: string;
    hasSemanticAuditResult: boolean;
    effectiveSemanticAuditOk: boolean;
    effectiveSemanticAuditError: string;
    effectiveSemanticAuditSummary: string;
    effectiveSemanticAuditScore?: number;
    effectiveSemanticAuditMaxScore?: number;
    effectiveSemanticAuditThreshold?: number;
    effectiveSemanticAuditChecklist: any[];
    effectiveSemanticAuditReportPath: string;
    effectiveApplyState: string;
    applyStateLabel: string;
    effectiveOutputDir: string;
    effectiveFailedOutputDir: string;
    effectiveApplyError: string;
}) {
    const hardGate = options.effectiveProductReadinessHardGate;
    return {
        hardGate: hardGate
            ? {
                ok: !!hardGate.ok,
                statusLabel: hardGate.ok ? 'pass' : 'fail',
                statusClassName: hardGate.ok
                    ? 'border border-[#238636] bg-[rgba(35,134,54,0.16)] text-[#9be9a8]'
                    : 'border border-[#da3633] bg-[rgba(218,54,51,0.18)] text-[#ffb3ad]',
                summary: hardGate.summary || '출고 hard gate 요약 없음',
                stages: hardGate.stages || [],
                archivePath: hardGate.archive_path || '-',
                failedStagesText: (hardGate.failed_stages || []).join(', ') || '없음',
            }
            : null,
        completionGate: options.hasCompletionGateResult
            ? {
                ok: options.effectiveCompletionGateOk,
                statusLabel: options.effectiveCompletionGateOk ? 'pass' : 'fail',
                statusClassName: options.effectiveCompletionGateOk
                    ? 'border border-[#238636] bg-[rgba(35,134,54,0.16)] text-[#9be9a8]'
                    : 'border border-[#da3633] bg-[rgba(218,54,51,0.18)] text-[#ffb3ad]',
                summary: options.effectiveCompletionSummary || '-',
                error: options.effectiveCompletionGateError || '-',
            }
            : null,
        semanticAudit: options.hasSemanticAuditResult
            ? {
                ok: options.effectiveSemanticAuditOk,
                statusLabel: options.effectiveSemanticAuditOk ? 'pass' : 'fail',
                statusClassName: options.effectiveSemanticAuditOk
                    ? 'border border-[#238636] bg-[rgba(35,134,54,0.16)] text-[#9be9a8]'
                    : 'border border-[#da3633] bg-[rgba(218,54,51,0.18)] text-[#ffb3ad]',
                summary: options.effectiveSemanticAuditSummary || '-',
                error: options.effectiveSemanticAuditError || '-',
                scoreLabel: options.effectiveSemanticAuditScore != null && options.effectiveSemanticAuditMaxScore != null
                    ? `${options.effectiveSemanticAuditScore}/${options.effectiveSemanticAuditMaxScore}`
                    : '-',
                thresholdLabel: options.effectiveSemanticAuditThreshold != null ? String(options.effectiveSemanticAuditThreshold) : '-',
                checklistCount: options.effectiveSemanticAuditChecklist.length,
                reportPath: options.effectiveSemanticAuditReportPath || '-',
            }
            : null,
        execution: {
            applyState: options.effectiveApplyState,
            applyStateLabel: options.applyStateLabel,
            outputDir: options.effectiveOutputDir || '-',
            failedOutputDir: options.effectiveFailedOutputDir || '-',
            applyError: options.effectiveApplyError || '-',
        },
    };
}

import type { SharedOrchestratorStageRun } from '@/shared/orchestrator-stage-card-panel';

export function buildAdminStageCardBindings(options: {
    selfRunResult: { stage_run?: SharedOrchestratorStageRun | null } | null;
    adminStageNoteDraft: string;
    setAdminStageNoteDraft: (value: string) => void;
    adminStageSubstepChecks: Record<string, boolean>;
    setAdminStageSubstepChecks: (value: Record<string, boolean>) => void;
    adminStageRevisionNote: string;
    setAdminStageRevisionNote: (value: string | ((prev: string) => string)) => void;
    selfRunBusy: boolean;
    updateAdminStageStatus: (status: 'passed' | 'manual_correction' | 'failed', options: {
        stageNote: string;
        manualCorrection: string;
        substepChecks: Record<string, boolean>;
        revisionNote: string;
        onSuccess?: () => void;
    }) => Promise<unknown>;
    runAdminOperationalVerification: () => Promise<unknown>;
    ideaPresets: string[];
    applyStageIdeaPresetValue: (previous: string, preset: string) => string;
}) {
    const sharedPayload = {
        stageNote: options.adminStageNoteDraft,
        manualCorrection: options.adminStageNoteDraft,
        substepChecks: options.adminStageSubstepChecks,
        revisionNote: options.adminStageRevisionNote,
        onSuccess: () => options.setAdminStageRevisionNote(''),
    };

    return {
        tone: 'admin' as const,
        title: '관리자 반자동 단계 카드 오케스트레이터',
        description: '현재 작업 폴더, 프로젝트 생성/불러오기 흐름과 함께 self-run 단계를 수동 승인 + 자동 다음 카드 연결 방식으로 운영합니다.',
        stageRun: (options.selfRunResult?.stage_run || null) as SharedOrchestratorStageRun | null,
        stageNoteDraft: options.adminStageNoteDraft,
        onStageNoteDraftChange: options.setAdminStageNoteDraft,
        substepChecks: options.adminStageSubstepChecks,
        onSubstepChecksChange: options.setAdminStageSubstepChecks,
        revisionNote: options.adminStageRevisionNote,
        onRevisionNoteChange: options.setAdminStageRevisionNote,
        stageUpdateLoading: options.selfRunBusy,
        onMarkPassed: () => void options.updateAdminStageStatus('passed', sharedPayload),
        onMarkManualCorrection: () => void options.updateAdminStageStatus('manual_correction', sharedPayload),
        onMarkFailed: () => void options.updateAdminStageStatus('failed', sharedPayload),
        onRefresh: () => void options.runAdminOperationalVerification(),
        ideaPresets: options.ideaPresets,
        onApplyIdeaPreset: (preset: string) => options.setAdminStageRevisionNote((prev) => options.applyStageIdeaPresetValue(prev, preset)),
        onRunOperationalVerification: () => void options.runAdminOperationalVerification(),
        operationalVerificationLabel: 'workspace-self-run-record 실검증',
        commandRules: [
            '모든 질문/명령은 지시 입력창에 적고 Enter로 수행합니다.',
            '`/run` 실행, `/pass` 통과, `/fix` 수동 보정, `/fail` 미통과, `/verify` 운영 API 실검증입니다.',
            '`/preset 번호`로 단계 아이디어 preset을 수정 메모에 즉시 반영합니다.',
        ],
    };
}

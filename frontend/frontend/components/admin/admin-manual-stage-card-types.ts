import type { SharedOrchestratorStageRun } from '@shared/orchestrator-stage-card-panel';

export interface AdminManualOrchestratorStageCardProps {
    stageRun: SharedOrchestratorStageRun | null;
    stageNoteDraft: string;
    onStageNoteDraftChange: (value: string) => void;
    stageSubstepChecks: Record<string, boolean>;
    onStageSubstepChecksChange: (value: Record<string, boolean>) => void;
    stageRevisionNote: string;
    onStageRevisionNoteChange: (value: string) => void;
    stageUpdateLoading: boolean;
    onUpdateStageStatus: (status: 'passed' | 'failed' | 'manual_correction') => void;
    onRefreshStageRun: () => void;
}

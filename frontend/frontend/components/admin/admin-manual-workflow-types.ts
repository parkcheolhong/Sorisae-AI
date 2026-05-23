import type { AdminAdVideoOrderItem } from '@/lib/admin-dashboard-types';
import type {
    AdminDurationDays,
    AdminManualMeta,
    AdminManualStepDefinition,
    AdminManualStepState,
    AdminRouterStage,
} from '@/lib/admin-manual-orchestrator';

export interface AdminMarketplaceTraceOverride {
    architectureId?: string;
    flowId?: string;
    stepId?: string;
    action?: string;
    bridgeNote?: string;
}

export interface AdminManualOrchestratorWorkflowProps {
    latestDedicatedOrder: AdminAdVideoOrderItem | null;
    selectedStep: AdminManualStepDefinition;
    selectedStepState: AdminManualStepState;
    selectedStepId: string;
    completedStepCount: number;
    previousStep: AdminManualStepDefinition | null;
    nextStep: AdminManualStepDefinition | null;
    manualMeta: AdminManualMeta;
    onSelectedStepIdChange: (value: string) => void;
    onMoveStep: (direction: 'prev' | 'next') => void;
    onUpdateRouteStage: (stepId: string, stage: AdminRouterStage) => void;
    onUpdateDuration: (stepId: string, duration: AdminDurationDays) => void;
    onManualMetaChange: (value: AdminManualMeta | ((prev: AdminManualMeta) => AdminManualMeta)) => void;
    onDownloadWorklog: (format: 'md' | 'json' | 'zip') => void;
    onOpenAdminLlmBridge: (step: AdminManualStepDefinition, state: AdminManualStepState) => void;
    onOpenMarketplaceBridge: (order: AdminAdVideoOrderItem, traceOverride?: AdminMarketplaceTraceOverride) => void;
    onToggleManualAction: (stepId: string, actionId: string) => void;
    onToggleStepCompleted: (stepId: string, checked: boolean) => void;
    onUpdateStepNote: (stepId: string, value: string) => void;
    onUpdateStepField: (stepId: string, field: 'attachmentDraft' | 'referenceUrl' | 'startedAt' | 'endedAt', value: string) => void;
    onAddAttachmentLink: (stepId: string) => void;
    onRemoveAttachmentLink: (stepId: string, link: string) => void;
}

export interface AdminManualStepHeaderSlice {
    selectedStep: Pick<AdminManualStepDefinition, 'id' | 'title' | 'detail' | 'flowId' | 'stepId' | 'action'>;
}

export interface AdminManualExternalStageStatusSlice {
    selectedStepId: string;
    selectedStepState: Pick<AdminManualStepState, 'externalStageRunId' | 'externalStageStatus' | 'externalStageLabel' | 'externalStageTitle' | 'externalStageSummary' | 'externalStageUpdatedAt'>;
}

export interface AdminManualStatusSlices {
    header: AdminManualStepHeaderSlice;
    externalStage: AdminManualExternalStageStatusSlice;
}

export interface AdminManualRouteStageBlockSlice {
    selectedStepId: string;
    selectedStepState: Pick<AdminManualStepState, 'routeStage' | 'durationDays'>;
    previousStep: AdminManualStepDefinition | null;
    nextStep: AdminManualStepDefinition | null;
    onMoveStep: (direction: 'prev' | 'next') => void;
    onUpdateRouteStage: (stepId: string, stage: AdminRouterStage) => void;
    onUpdateDuration: (stepId: string, duration: AdminDurationDays) => void;
}

export interface AdminManualMetaBlockSlice {
    manualMeta: AdminManualMeta;
    onManualMetaChange: (value: AdminManualMeta | ((prev: AdminManualMeta) => AdminManualMeta)) => void;
    onDownloadWorklog: (format: 'md' | 'json' | 'zip') => void;
}

export interface AdminManualActionsBlockSlice {
    latestDedicatedOrder: AdminAdVideoOrderItem | null;
    selectedStep: AdminManualStepDefinition;
    selectedStepState: AdminManualStepState;
    onOpenAdminLlmBridge: (step: AdminManualStepDefinition, state: AdminManualStepState) => void;
    onOpenMarketplaceBridge: (order: AdminAdVideoOrderItem, traceOverride?: AdminMarketplaceTraceOverride) => void;
    onToggleManualAction: (stepId: string, actionId: string) => void;
}

export interface AdminManualNotesBlockSlice {
    selectedStepId: string;
    selectedStepState: Pick<AdminManualStepState, 'completed' | 'note' | 'attachmentDraft' | 'attachmentLinks' | 'referenceUrl' | 'startedAt' | 'endedAt' | 'updatedAt'>;
    onToggleStepCompleted: (stepId: string, checked: boolean) => void;
    onUpdateStepNote: (stepId: string, value: string) => void;
    onUpdateStepField: (stepId: string, field: 'attachmentDraft' | 'referenceUrl' | 'startedAt' | 'endedAt', value: string) => void;
    onAddAttachmentLink: (stepId: string) => void;
    onRemoveAttachmentLink: (stepId: string, link: string) => void;
}

export interface AdminManualWorkflowSlices {
    routeStage: AdminManualRouteStageBlockSlice;
    meta: AdminManualMetaBlockSlice;
    actions: AdminManualActionsBlockSlice;
    notes: AdminManualNotesBlockSlice;
}

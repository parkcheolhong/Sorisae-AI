import type {
    AdminManualActionsBlockSlice,
    AdminManualExternalStageStatusSlice,
    AdminManualMetaBlockSlice,
    AdminManualNotesBlockSlice,
    AdminManualOrchestratorWorkflowProps,
    AdminManualRouteStageBlockSlice,
    AdminManualStatusSlices,
    AdminManualStepHeaderSlice,
    AdminManualWorkflowSlices,
} from '@/components/admin/admin-manual-workflow-types';

export function buildAdminManualStepDetailSlices(workflow: AdminManualOrchestratorWorkflowProps): {
    statusSlices: AdminManualStatusSlices;
    workflowSlices: AdminManualWorkflowSlices;
} {
    const header: AdminManualStepHeaderSlice = {
        selectedStep: {
            id: workflow.selectedStep.id,
            title: workflow.selectedStep.title,
            detail: workflow.selectedStep.detail,
            flowId: workflow.selectedStep.flowId,
            stepId: workflow.selectedStep.stepId,
            action: workflow.selectedStep.action,
        },
    };

    const externalStage: AdminManualExternalStageStatusSlice = {
        selectedStepId: workflow.selectedStep.id,
        selectedStepState: {
            externalStageRunId: workflow.selectedStepState.externalStageRunId,
            externalStageStatus: workflow.selectedStepState.externalStageStatus,
            externalStageLabel: workflow.selectedStepState.externalStageLabel,
            externalStageTitle: workflow.selectedStepState.externalStageTitle,
            externalStageSummary: workflow.selectedStepState.externalStageSummary,
            externalStageUpdatedAt: workflow.selectedStepState.externalStageUpdatedAt,
        },
    };

    const routeStage: AdminManualRouteStageBlockSlice = {
        selectedStepId: workflow.selectedStep.id,
        selectedStepState: {
            routeStage: workflow.selectedStepState.routeStage,
            durationDays: workflow.selectedStepState.durationDays,
        },
        previousStep: workflow.previousStep,
        nextStep: workflow.nextStep,
        onMoveStep: workflow.onMoveStep,
        onUpdateRouteStage: workflow.onUpdateRouteStage,
        onUpdateDuration: workflow.onUpdateDuration,
    };

    const meta: AdminManualMetaBlockSlice = {
        manualMeta: workflow.manualMeta,
        onManualMetaChange: workflow.onManualMetaChange,
        onDownloadWorklog: workflow.onDownloadWorklog,
    };

    const actions: AdminManualActionsBlockSlice = {
        latestDedicatedOrder: workflow.latestDedicatedOrder,
        selectedStep: workflow.selectedStep,
        selectedStepState: workflow.selectedStepState,
        onOpenAdminLlmBridge: workflow.onOpenAdminLlmBridge,
        onOpenMarketplaceBridge: workflow.onOpenMarketplaceBridge,
        onToggleManualAction: workflow.onToggleManualAction,
    };

    const notes: AdminManualNotesBlockSlice = {
        selectedStepId: workflow.selectedStep.id,
        selectedStepState: {
            completed: workflow.selectedStepState.completed,
            note: workflow.selectedStepState.note,
            attachmentDraft: workflow.selectedStepState.attachmentDraft,
            attachmentLinks: workflow.selectedStepState.attachmentLinks,
            referenceUrl: workflow.selectedStepState.referenceUrl,
            startedAt: workflow.selectedStepState.startedAt,
            endedAt: workflow.selectedStepState.endedAt,
            updatedAt: workflow.selectedStepState.updatedAt,
        },
        onToggleStepCompleted: workflow.onToggleStepCompleted,
        onUpdateStepNote: workflow.onUpdateStepNote,
        onUpdateStepField: workflow.onUpdateStepField,
        onAddAttachmentLink: workflow.onAddAttachmentLink,
        onRemoveAttachmentLink: workflow.onRemoveAttachmentLink,
    };

    return {
        statusSlices: {
            header,
            externalStage,
        },
        workflowSlices: {
            routeStage,
            meta,
            actions,
            notes,
        },
    };
}

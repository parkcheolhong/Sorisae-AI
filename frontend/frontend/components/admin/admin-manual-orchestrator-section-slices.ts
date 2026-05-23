import type { AdminManualOrchestratorProductionPanelProps } from '@/components/admin/admin-manual-production-panel-types';
import type { AdminManualOrchestratorWorkflowProps } from '@/components/admin/admin-manual-workflow-types';

export function buildAdminManualOrchestratorSectionSlices(
    workflow: AdminManualOrchestratorWorkflowProps,
    productionPanel: AdminManualOrchestratorProductionPanelProps,
) {
    return {
        stepStrip: {
            selectedStepId: workflow.selectedStepId,
            selectedStepCompleted: workflow.selectedStepState.completed,
            completedStepCount: workflow.completedStepCount,
            onSelectedStepIdChange: workflow.onSelectedStepIdChange,
        },
        sectionIdMap: {
            selectedStepId: workflow.selectedStep.id,
        },
        productionPanel: {
            latestDedicatedOrder: productionPanel.latestDedicatedOrder,
            latestDedicatedCurrentStage: productionPanel.latestDedicatedCurrentStage,
            latestDedicatedWorkReady: productionPanel.latestDedicatedWorkReady,
            latestDedicatedReadyCount: productionPanel.latestDedicatedReadyCount,
            selectedFlowId: workflow.selectedStep.flowId,
            selectedStepId: workflow.selectedStep.stepId,
            selectedAction: workflow.selectedStep.action,
            filteredAdminCompletionHistory: productionPanel.filteredAdminCompletionHistory,
            filteredAdminTraceHistory: productionPanel.filteredAdminTraceHistory,
            filteredAdminRetryQueueItems: productionPanel.filteredAdminRetryQueueItems,
            latestDedicatedProductionStages: productionPanel.latestDedicatedProductionStages,
            actionTemplateLabel: productionPanel.actionTemplateLabel,
            motionTempoLabel: productionPanel.motionTempoLabel,
            humanInteractionRules: [...productionPanel.humanInteractionRules],
            onOpenMarketplaceBridge: () => productionPanel.latestDedicatedOrder && productionPanel.onOpenMarketplaceBridge(productionPanel.latestDedicatedOrder),
            onReloadTrace: productionPanel.onReloadTrace,
            onReplayRetryQueue: productionPanel.onReplayRetryQueue,
            adminReplayQueueId: productionPanel.adminReplayQueueId,
            adminTraceFilter: productionPanel.adminTraceFilter,
            onAdminTraceFilterChange: productionPanel.onAdminTraceFilterChange,
            getSceneFrameHint: productionPanel.getSceneFrameHint,
        },
    };
}

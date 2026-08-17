import type { SharedOrchestratorStageRun } from '@shared/orchestrator-stage-card-panel';
import type { AdminAdOrdersSectionProps } from '@/components/admin/admin-ad-orders-section';
import type { AdminManualOrchestratorSectionProps } from '@/components/admin/admin-manual-orchestrator-section';
import type { AdminSampleProductsSectionProps } from '@/components/admin/admin-sample-products-section';
import type { AdminSystemSettingsPanelProps } from '@/components/admin/admin-system-settings-panel';
import type { AdminAdOrderMonitorSummary, AdminAdOrderSettlementDashboard, AdminAdVideoOrderItem } from '@/lib/admin-dashboard-types';
import type { AdminManualMeta, AdminManualStepDefinition, AdminManualStepState } from '@/lib/admin-manual-orchestrator';

type AdminManualEditableField = 'attachmentDraft' | 'referenceUrl' | 'startedAt' | 'endedAt';

export interface AdminPageManualOrchestratorAssemblyInput {
    adminStageRun: SharedOrchestratorStageRun | null;
    adminStageNoteDraft: string;
    setAdminStageNoteDraft: (value: string) => void;
    adminStageSubstepChecks: Record<string, boolean>;
    setAdminStageSubstepChecks: (value: Record<string, boolean>) => void;
    adminStageRevisionNote: string;
    setAdminStageRevisionNote: (value: string) => void;
    adminStageUpdateLoading: boolean;
    updateAdminStageStatus: (status: 'passed' | 'failed' | 'manual_correction') => Promise<void> | void;
    refreshAdminStageRun: (runId: string) => Promise<unknown> | void;
    latestDedicatedOrder: AdminAdVideoOrderItem | null;
    selectedAdminManualStep: AdminManualStepDefinition;
    selectedAdminManualStepState: AdminManualStepState;
    adminManualOrchestratorStepId: string;
    completedManualStepCount: number;
    previousAdminManualStep: AdminManualStepDefinition | null;
    nextAdminManualStep: AdminManualStepDefinition | null;
    adminManualMeta: AdminManualMeta;
    setAdminManualOrchestratorStepId: (value: string) => void;
    moveAdminManualStep: (direction: 'prev' | 'next') => void;
    updateAdminManualStepRouteStage: (stepId: string, stage: AdminManualStepState['routeStage']) => void;
    updateAdminManualStepDuration: (stepId: string, duration: AdminManualStepState['durationDays']) => void;
    setAdminManualMeta: (value: AdminManualMeta | ((prev: AdminManualMeta) => AdminManualMeta)) => void;
    downloadAdminManualWorklog: (format: 'md' | 'json' | 'zip') => void;
    openAdminLlmOrchestratorBridge: (step: AdminManualStepDefinition, state: AdminManualStepState) => void;
    openMarketplaceOrchestratorBridge: AdminManualOrchestratorSectionProps['workflow']['onOpenMarketplaceBridge'];
    toggleAdminManualAction: (stepId: string, actionId: string) => void;
    toggleAdminManualStepCompleted: (stepId: string, checked: boolean) => void;
    updateAdminManualStepNote: (stepId: string, value: string) => void;
    updateAdminManualStepField: (stepId: string, field: AdminManualEditableField, value: string) => void;
    addAdminManualAttachmentLink: (stepId: string) => void;
    removeAdminManualAttachmentLink: (stepId: string, link: string) => void;
    latestDedicatedProductionStages: AdminManualOrchestratorSectionProps['productionPanel']['latestDedicatedProductionStages'];
    latestDedicatedCurrentStage: string;
    latestDedicatedWorkReady: boolean;
    latestDedicatedReadyCount: number;
    actionTemplateLabel: string;
    motionTempoLabel: string;
    humanInteractionRules: AdminManualOrchestratorSectionProps['productionPanel']['humanInteractionRules'];
    filteredAdminCompletionHistory: AdminManualOrchestratorSectionProps['productionPanel']['filteredAdminCompletionHistory'];
    filteredAdminTraceHistory: AdminManualOrchestratorSectionProps['productionPanel']['filteredAdminTraceHistory'];
    filteredAdminRetryQueueItems: AdminManualOrchestratorSectionProps['productionPanel']['filteredAdminRetryQueueItems'];
    adminReplayQueueId: number | null;
    adminTraceFilter: string;
    loadAdminCompletionHistory: () => void;
    loadAdminTraceHistory: () => void;
    loadAdminRetryQueue: () => void;
    handleReplayRetryQueue: (id: number) => void;
    setAdminTraceFilter: (value: string) => void;
    getAdminSceneFrameHint: (durationSec?: number, motionSpeedPercent?: number) => number;
}

export function buildAdminPageManualOrchestratorAssembly(input: AdminPageManualOrchestratorAssemblyInput): AdminManualOrchestratorSectionProps {
    return {
        stageCard: {
            stageRun: input.adminStageRun,
            stageNoteDraft: input.adminStageNoteDraft,
            onStageNoteDraftChange: input.setAdminStageNoteDraft,
            stageSubstepChecks: input.adminStageSubstepChecks,
            onStageSubstepChecksChange: input.setAdminStageSubstepChecks,
            stageRevisionNote: input.adminStageRevisionNote,
            onStageRevisionNoteChange: input.setAdminStageRevisionNote,
            stageUpdateLoading: input.adminStageUpdateLoading,
            onUpdateStageStatus: (status) => void input.updateAdminStageStatus(status),
            onRefreshStageRun: () => void input.refreshAdminStageRun(input.adminStageRun?.run_id || ''),
        },
        workflow: {
            latestDedicatedOrder: input.latestDedicatedOrder || null,
            selectedStep: input.selectedAdminManualStep,
            selectedStepState: input.selectedAdminManualStepState,
            selectedStepId: input.adminManualOrchestratorStepId,
            completedStepCount: input.completedManualStepCount,
            previousStep: input.previousAdminManualStep,
            nextStep: input.nextAdminManualStep,
            manualMeta: input.adminManualMeta,
            onSelectedStepIdChange: input.setAdminManualOrchestratorStepId,
            onMoveStep: input.moveAdminManualStep,
            onUpdateRouteStage: input.updateAdminManualStepRouteStage,
            onUpdateDuration: input.updateAdminManualStepDuration,
            onManualMetaChange: input.setAdminManualMeta,
            onDownloadWorklog: input.downloadAdminManualWorklog,
            onOpenAdminLlmBridge: input.openAdminLlmOrchestratorBridge,
            onOpenMarketplaceBridge: input.openMarketplaceOrchestratorBridge,
            onToggleManualAction: input.toggleAdminManualAction,
            onToggleStepCompleted: input.toggleAdminManualStepCompleted,
            onUpdateStepNote: input.updateAdminManualStepNote,
            onUpdateStepField: input.updateAdminManualStepField,
            onAddAttachmentLink: input.addAdminManualAttachmentLink,
            onRemoveAttachmentLink: input.removeAdminManualAttachmentLink,
        },
        productionPanel: {
            latestDedicatedOrder: input.latestDedicatedOrder || null,
            latestDedicatedProductionStages: input.latestDedicatedProductionStages,
            latestDedicatedCurrentStage: input.latestDedicatedCurrentStage,
            latestDedicatedWorkReady: input.latestDedicatedWorkReady,
            latestDedicatedReadyCount: input.latestDedicatedReadyCount,
            actionTemplateLabel: input.actionTemplateLabel,
            motionTempoLabel: input.motionTempoLabel,
            humanInteractionRules: input.humanInteractionRules,
            filteredAdminCompletionHistory: input.filteredAdminCompletionHistory,
            filteredAdminTraceHistory: input.filteredAdminTraceHistory,
            filteredAdminRetryQueueItems: input.filteredAdminRetryQueueItems,
            adminReplayQueueId: input.adminReplayQueueId,
            adminTraceFilter: input.adminTraceFilter,
            onReloadTrace: () => {
                input.loadAdminCompletionHistory();
                input.loadAdminTraceHistory();
                input.loadAdminRetryQueue();
            },
            onReplayRetryQueue: input.handleReplayRetryQueue,
            onAdminTraceFilterChange: input.setAdminTraceFilter,
            onOpenMarketplaceBridge: input.openMarketplaceOrchestratorBridge,
            getSceneFrameHint: input.getAdminSceneFrameHint,
        },
    };
}

export interface AdminPageAdOrdersAssemblyInput {
    adOrdersOpen: boolean;
    setAdOrdersOpen: (value: boolean | ((prev: boolean) => boolean)) => void;
    adVideoTotal: number;
    adVideoOrders: AdminAdVideoOrderItem[];
    adOrderMonitorSummary: AdminAdOrderMonitorSummary | null;
    adSettlementDashboard: AdminAdOrderSettlementDashboard | null;
    adSettlementExporting: boolean;
    adMonitorApiUnavailable: boolean;
    adSettlementApiUnavailable: boolean;
    actionTemplateLabels: Record<string, string>;
    onRefresh: () => void;
    onExportSettlementCsv: () => void;
    buildSettlementConnectionId: (orderId: number) => string;
    review: AdminAdOrdersSectionProps['review'];
    actions: AdminAdOrdersSectionProps['actions'];
}

export function buildAdminPageAdOrdersAssembly(input: AdminPageAdOrdersAssemblyInput): AdminAdOrdersSectionProps {
    return {
        summary: {
            open: input.adOrdersOpen,
            onOpenChange: input.setAdOrdersOpen,
            total: input.adVideoTotal,
            orders: input.adVideoOrders,
            monitor: input.adOrderMonitorSummary,
            settlement: input.adSettlementDashboard,
            settlementExporting: input.adSettlementExporting,
            monitorApiUnavailable: input.adMonitorApiUnavailable,
            settlementApiUnavailable: input.adSettlementApiUnavailable,
            actionTemplateLabels: input.actionTemplateLabels,
            onRefresh: input.onRefresh,
            onExportSettlementCsv: input.onExportSettlementCsv,
            buildSettlementConnectionId: input.buildSettlementConnectionId,
        },
        review: input.review,
        actions: input.actions,
    };
}

export interface AdminPageSystemSettingsAssemblyInput extends AdminSystemSettingsPanelProps {}

export function buildAdminPageSystemSettingsAssembly(input: AdminPageSystemSettingsAssemblyInput): AdminSystemSettingsPanelProps {
    return {
        ...input,
    };
}

export interface AdminPageSampleProductsAssemblyInput extends AdminSampleProductsSectionProps {}

export function buildAdminPageSampleProductsAssembly(input: AdminPageSampleProductsAssemblyInput): AdminSampleProductsSectionProps {
    return {
        ...input,
    };
}

import type { AdminAdProductionStage } from '@/lib/admin-ad-production-analysis';
import type { AdminAdVideoOrderItem } from '@/lib/admin-dashboard-types';
import type { AdminCompletionHistoryItem, AdminRetryQueueItem, AdminTraceLogItem } from '@/lib/admin-auto-connect-service';
import type { AdminMarketplaceTraceOverride } from '@/components/admin/admin-manual-workflow-types';

export interface AdminManualOrchestratorProductionPanelProps {
    latestDedicatedOrder: AdminAdVideoOrderItem | null;
    latestDedicatedProductionStages: AdminAdProductionStage[];
    latestDedicatedCurrentStage: string;
    latestDedicatedWorkReady: boolean;
    latestDedicatedReadyCount: number;
    actionTemplateLabel: string;
    motionTempoLabel: string;
    humanInteractionRules: readonly string[] | string[];
    filteredAdminCompletionHistory: AdminCompletionHistoryItem[];
    filteredAdminTraceHistory: AdminTraceLogItem[];
    filteredAdminRetryQueueItems: AdminRetryQueueItem[];
    adminReplayQueueId: number | null;
    adminTraceFilter: string;
    onReloadTrace: () => void;
    onReplayRetryQueue: (id: number) => void;
    onAdminTraceFilterChange: (value: string) => void;
    onOpenMarketplaceBridge: (order: AdminAdVideoOrderItem, traceOverride?: AdminMarketplaceTraceOverride) => void;
    getSceneFrameHint: (durationSec?: number, motionSpeedPercent?: number) => number;
}

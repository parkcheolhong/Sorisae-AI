import type { AdminAdOrderActionsProps, AdminAdOrderReviewProps } from '@/components/admin/admin-ad-orders-table-types';
import type { AdminAdOrderMonitorSummary, AdminAdOrderSettlementDashboard, AdminAdVideoOrderItem } from '@/lib/admin-dashboard-types';

export interface AdminAdOrdersSummarySlice {
    open: boolean;
    onOpenChange: (value: boolean | ((prev: boolean) => boolean)) => void;
    total: number;
    orders: AdminAdVideoOrderItem[];
    monitor: AdminAdOrderMonitorSummary | null;
    settlement: AdminAdOrderSettlementDashboard | null;
    settlementExporting: boolean;
    monitorApiUnavailable: boolean;
    settlementApiUnavailable: boolean;
    actionTemplateLabels: Record<string, string>;
    onRefresh: () => void;
    onExportSettlementCsv: () => void;
    buildSettlementConnectionId: (orderId: number) => string;
}

export interface AdminAdOrdersSlices {
    summary: AdminAdOrdersSummarySlice;
    review: AdminAdOrderReviewProps;
    actions: AdminAdOrderActionsProps;
}

export function buildAdminAdOrdersSlices(slices: AdminAdOrdersSlices) {
    return {
        summaryBlock: slices.summary,
        tableBlock: {
            orders: slices.summary.orders,
            actionTemplateLabels: slices.summary.actionTemplateLabels,
            review: slices.review,
            actions: slices.actions,
        },
    };
}

'use client';

import { buildAdminAdOrdersSlices, type AdminAdOrdersSlices } from '@/components/admin/admin-ad-orders-slices';
import AdminAdOrdersSummaryBlock from '@/components/admin/admin-ad-orders-summary-block';
import AdminAdOrdersTableBlock from '@/components/admin/admin-ad-orders-table-block';
import type { AdminAdOrderActionsProps, AdminAdOrderReviewProps } from '@/components/admin/admin-ad-orders-table-types';
import type { AdminAdOrderMonitorSummary, AdminAdOrderSettlementDashboard, AdminAdVideoOrderItem } from '@/lib/admin-dashboard-types';

export interface AdminAdOrdersSectionProps {
    summary: {
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
    };
    review: AdminAdOrderReviewProps;
    actions: AdminAdOrderActionsProps;
}

export default function AdminAdOrdersSection({ summary, review, actions }: AdminAdOrdersSectionProps) {
    const orderSlices = buildAdminAdOrdersSlices({
        summary,
        review,
        actions,
    } satisfies AdminAdOrdersSlices);

    return (
        <>
            <AdminAdOrdersSummaryBlock {...orderSlices.summaryBlock} />
            {summary.open && (
                <AdminAdOrdersTableBlock {...orderSlices.tableBlock} />
            )}
        </>
    );
}

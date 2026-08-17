import type { AdminAutoConnectGraphPanelProps } from '@/components/admin/admin-auto-connect-graph-panel';
import type { AdminAutoConnectGraphSnapshot } from '@/lib/admin-dashboard-auto-connect';

export function buildAdminAutoConnectGraphAssembly(input: {
    autoConnectGraph: AdminAutoConnectGraphSnapshot;
    adminConnectionLookupId: string;
    onAdminConnectionLookupIdChange: (value: string) => void;
    onLoadLookup: () => void;
    adminConnectionLookupLoading: boolean;
    adminConnectionLookupResult: AdminAutoConnectGraphPanelProps['adminConnectionLookupResult'];
    adminReplayQueueId: number | null;
    onReplayRetryQueue: (id: number) => void;
    setAdminConnectionLookupId: (value: string) => void;
}): AdminAutoConnectGraphPanelProps {
    const activeEvent = input.autoConnectGraph.events.find((item) => item.connection_id === input.autoConnectGraph.active_connection_id) || null;
    const events = input.autoConnectGraph.events.slice(0, 8);

    return {
        activeEvent,
        events,
        adminConnectionLookupId: input.adminConnectionLookupId,
        onAdminConnectionLookupIdChange: input.onAdminConnectionLookupIdChange,
        onLoadActiveConnection: () => input.setAdminConnectionLookupId(activeEvent?.connection_id || ''),
        onLoadLookup: input.onLoadLookup,
        adminConnectionLookupLoading: input.adminConnectionLookupLoading,
        adminConnectionLookupResult: input.adminConnectionLookupResult,
        adminReplayQueueId: input.adminReplayQueueId,
        onReplayRetryQueue: input.onReplayRetryQueue,
    };
}

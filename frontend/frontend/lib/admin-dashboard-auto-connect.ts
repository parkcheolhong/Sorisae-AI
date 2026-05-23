import {
    attachActiveAdminConnectionMeta,
    buildAdminAutoConnectMeta,
    registerAdminAutoConnectGraphEvent,
    type AdminAutoConnectGraphSnapshot,
} from '@/lib/admin-auto-connect';

export function createDashboardAutoConnectTracker(options: {
    registerEvent: typeof registerAdminAutoConnectGraphEvent;
    attachMeta: typeof attachActiveAdminConnectionMeta;
    buildMeta: typeof buildAdminAutoConnectMeta;
}) {
    return (input: {
        capabilityId: string;
        title: string;
        detail: string;
        panelId: string;
        status: 'queued' | 'linked' | 'success' | 'warning' | 'error';
        execution?: 'chat' | 'prepare' | 'run' | 'observe' | 'sync';
    }) => {
        const activeMeta = options.attachMeta({
            fallbackCapabilityId: input.capabilityId,
            panelId: input.panelId,
            execution: input.execution || 'observe',
        });
        options.registerEvent({
            meta: activeMeta.connection_id
                ? {
                    ...activeMeta,
                    panel_id: input.panelId,
                    capability_id: input.capabilityId,
                }
                : options.buildMeta({
                    capabilityId: input.capabilityId,
                    panelId: input.panelId,
                    execution: input.execution || 'observe',
                }),
            source: input.capabilityId.includes('settlement')
                ? 'settlement'
                : input.capabilityId.includes('orchestrator')
                    ? 'orchestrator'
                    : 'admin-dashboard',
            title: input.title,
            detail: input.detail,
            status: input.status,
            activate: false,
        });
    };
}

export function buildCapabilityConnectionId(groupId: string) {
    return buildAdminAutoConnectMeta({
        capabilityId: `orchestrator-${groupId}`,
        execution: 'observe',
        panelId: 'PANEL-ADMIN-ORCHESTRATOR',
    }).connection_id;
}

export function buildSettlementOrderConnectionId(orderId: string | number) {
    return buildAdminAutoConnectMeta({
        capabilityId: `settlement-order-${orderId}`,
        execution: 'observe',
        panelId: 'PANEL-ADMIN-SETTLEMENT',
    }).connection_id;
}

export type { AdminAutoConnectGraphSnapshot };

export type AdminDashboardBootstrapPayload = {
    overviewData: any;
    revenueData: any;
    topData: any;
    healthData: any;
    llmData: any;
    adVideoData: any;
    adMonitorData: any;
    adSettlementData: any;
    capabilityData: any;
    selfRunData: any;
    securityGuardDetailData: any;
    adMonitorUnavailable: boolean;
    adSettlementUnavailable: boolean;
    buildFallbackAdOrderMonitorSummary: (orders: any[]) => any;
    buildFallbackAdSettlementDashboard: (orders: any[]) => any;
};

export type AdminDashboardStateAssembly = {
    adVideoTotal: number | null;
    adVideoOrders: any[] | null;
    adOrderMonitorSummary: any;
    adSettlementDashboard: any;
    orchestratorCapabilitySummary: any;
    securityGuardDetail: any;
    dashboardSelfRunStatus: any;
};

export function assembleAdminDashboardState(payload: AdminDashboardBootstrapPayload): AdminDashboardStateAssembly {
    const currentOrders = Array.isArray(payload.adVideoData?.orders) ? payload.adVideoData.orders : [];
    return {
        adVideoTotal: payload.adVideoData ? Number(payload.adVideoData.total || 0) : null,
        adVideoOrders: payload.adVideoData ? (Array.isArray(payload.adVideoData.orders) ? payload.adVideoData.orders : []) : null,
        adOrderMonitorSummary: payload.adMonitorData
            || (payload.adMonitorUnavailable ? payload.buildFallbackAdOrderMonitorSummary(currentOrders) : null),
        adSettlementDashboard: payload.adSettlementData
            || (payload.adSettlementUnavailable ? payload.buildFallbackAdSettlementDashboard(currentOrders) : null),
        orchestratorCapabilitySummary: payload.capabilityData || null,
        securityGuardDetail: payload.securityGuardDetailData || null,
        dashboardSelfRunStatus: payload.selfRunData || null,
    };
}

export function assertAdminDashboardStateAssemblerContract() {
    const sample = assembleAdminDashboardState({
        overviewData: null,
        revenueData: null,
        topData: null,
        healthData: null,
        llmData: null,
        adVideoData: { total: 0, orders: [] },
        adMonitorData: null,
        adSettlementData: null,
        capabilityData: null,
        selfRunData: null,
        securityGuardDetailData: null,
        adMonitorUnavailable: true,
        adSettlementUnavailable: true,
        buildFallbackAdOrderMonitorSummary: () => ({ fallback: true }),
        buildFallbackAdSettlementDashboard: () => ({ fallback: true }),
    });
    const requiredKeys = [
        'adVideoTotal',
        'adVideoOrders',
        'adOrderMonitorSummary',
        'adSettlementDashboard',
        'orchestratorCapabilitySummary',
        'securityGuardDetail',
        'dashboardSelfRunStatus',
    ];
    const missing = requiredKeys.filter((key) => !(key in sample));
    if (missing.length > 0) {
        throw new Error(`admin dashboard state assembler contract 누락: ${missing.join(', ')}`);
    }
}

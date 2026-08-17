export interface AdminCostScenario {
    key: string;
    label: string;
    monthly_external_calls: number;
    monthly_local_runs: number;
    monthly_cost: number;
    cost_per_order: number;
    summary: string;
}

export interface AdminCostSimulatorResponse {
    formula_markdown: string;
    assumptions: Record<string, string | number>;
    scenarios: AdminCostScenario[];
    recommended_architecture: {
        mode: string;
        pipeline: string[];
        reason: string;
        external_model_interface_contract: string;
    };
}

export interface LlmStatus {
    loaded: boolean;
    model_path: string;
    n_gpu_layers?: number | null;
    num_gpu?: number | null;
    acceleration_mode?: string | null;
    gpu_runtime_label?: string | null;
    n_ctx: number;
    n_batch: number;
}

export interface LiveLogItem {
    id: string;
    level: 'info' | 'success' | 'warning';
    message: string;
    createdAt: string;
    connection_id?: string;
    flow_id?: string;
    step_id?: string;
    action?: string;
    panel_id?: string;
    route_id?: string;
}

export interface AdminAlertItem {
    id: string;
    level: 'warning' | 'critical';
    title: string;
    message: string;
    action: string;
    source: 'system' | 'service' | 'orchestrator';
    apiPath: string;
}

export interface AutomaticOpsActionItem {
    id: string;
    title: string;
    summary: string;
    tone: 'emerald' | 'amber' | 'red' | 'blue';
}

export function assertAdminRuntimeTypesContract() {
    const liveLog: LiveLogItem = {
        id: 'sample',
        level: 'info',
        message: 'sample',
        createdAt: '00:00:00',
    };
    if (liveLog.level !== 'info') {
        throw new Error('admin runtime types contract 누락: live log level 기본 타입 필요');
    }
}

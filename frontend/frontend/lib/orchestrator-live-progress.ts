export const ORCHESTRATOR_LIVE_PROGRESS_KEY = 'orchestrator_live_progress_v1';
export const LEGACY_ADMIN_ORCHESTRATOR_LIVE_PROGRESS_KEY = 'admin_orchestrator_live_progress_v1';
export const ORCHESTRATOR_LIVE_PROGRESS_EVENT = 'admin-orchestrator-progress';

export type OrchestratorLiveLogEntry = {
    id: string;
    event: string;
    stage?: string;
    message: string;
    timestamp: string;
    severity?: 'info' | 'success' | 'warning' | 'error';
};

export type OrchestratorLiveProgressSubstep = {
    id: string;
    status: string;
    message?: string;
    at?: string;
};

export type OrchestratorLiveProgressSnapshot = {
    runId: string;
    sessionId?: string;
    task: string;
    mode: string;
    pipeline: string[];
    status: 'idle' | 'running' | 'success' | 'failed';
    currentState: string;
    executionState?: string;
    orchestratorCore?: string;
    autonomousIntent?: string;
    stageCommand?: string;
    stageNumber?: number | null;
    stagesCompleted?: number;
    stagesTotal?: number;
    currentStage?: string | null;
    agentResults?: Array<{ agent: string; status: string; elapsed_ms?: number }>;
    activeSubstep?: string | null;
    substeps?: OrchestratorLiveProgressSubstep[];
    progressSource?: 'autonomous_poll' | 'autonomous_sse' | 'autonomous_ws' | 'legacy_ws' | 'idle';
    stateHistory: string[];
    logs: OrchestratorLiveLogEntry[];
    wsConnected: boolean;
    updatedAt: string;
};

const emptySnapshot = (): OrchestratorLiveProgressSnapshot => ({
    runId: '',
    task: '',
    mode: '',
    pipeline: [],
    status: 'idle',
    currentState: '',
    stateHistory: [],
    logs: [],
    wsConnected: false,
    updatedAt: '',
});

function normalizeProgressStatus(raw: string): OrchestratorLiveProgressSnapshot['status'] {
    const backendStatus = String(raw || 'idle').toLowerCase();
    if (backendStatus === 'completed' || backendStatus === 'success') {
        return 'success';
    }
    if (backendStatus === 'failed') {
        return 'failed';
    }
    if (backendStatus === 'running' || backendStatus === 'accepted') {
        return 'running';
    }
    return 'idle';
}

function mapEventsToLogs(
    payload: Record<string, unknown>,
    events: unknown[],
): OrchestratorLiveLogEntry[] {
    return events.slice(-40).map((item, index) => {
        const row = item as Record<string, unknown>;
        const level = String(row.level || 'info').toLowerCase();
        const severity = level === 'error'
            ? 'error'
            : level === 'warning'
                ? 'warning'
                : level === 'success'
                    ? 'success'
                    : 'info';
        return {
            id: `${String(payload.run_id || payload.session_id || 'progress')}-${index}`,
            event: 'progress',
            stage: String(payload.current_stage || ''),
            message: String(row.message || ''),
            timestamp: String(row.at || payload.updated_at || new Date().toISOString()),
            severity,
        };
    });
}

export function mapProgressPayloadToSnapshot(payload: Record<string, unknown>): OrchestratorLiveProgressSnapshot {
    const events = Array.isArray(payload.events) ? payload.events : [];
    const logs = mapEventsToLogs(payload, events);
    const status = normalizeProgressStatus(String(payload.status || 'idle'));
    const agentResults = Array.isArray(payload.agent_results)
        ? payload.agent_results.map((item) => {
            const row = item as Record<string, unknown>;
            return {
                agent: String(row.agent || ''),
                status: String(row.status || ''),
                elapsed_ms: typeof row.elapsed_ms === 'number' ? row.elapsed_ms : undefined,
            };
        })
        : [];
    const substeps = Array.isArray(payload.substeps)
        ? payload.substeps.map((item) => {
            const row = item as Record<string, unknown>;
            return {
                id: String(row.id || ''),
                status: String(row.status || 'info'),
                message: row.message ? String(row.message) : undefined,
                at: row.at ? String(row.at) : undefined,
            };
        }).filter((item) => item.id)
        : [];
    const stageNumberRaw = payload.stage_number;
    const stageNumber = stageNumberRaw === null || stageNumberRaw === undefined
        ? null
        : Number(stageNumberRaw);

    const executionState = String(payload.execution_state || payload.current_state || '');
    const stateHistory = Array.isArray(payload.state_history)
        ? payload.state_history.map((item) => String(item))
        : [executionState].filter(Boolean);

    return {
        runId: String(payload.run_id || payload.session_id || ''),
        sessionId: String(payload.session_id || '') || undefined,
        task: String(payload.task || payload.project_name || ''),
        mode: String(payload.mode || ''),
        pipeline: Array.isArray(payload.pipeline) ? payload.pipeline.map((item) => String(item)) : [],
        status,
        currentState: executionState,
        executionState: executionState || undefined,
        orchestratorCore: String(payload.orchestrator_core || '') || undefined,
        autonomousIntent: String(payload.autonomous_intent || '') || undefined,
        stageCommand: String(payload.stage_command || '') || undefined,
        stageNumber: Number.isFinite(stageNumber) ? stageNumber : null,
        stagesCompleted: typeof payload.stages_completed === 'number' ? payload.stages_completed : undefined,
        stagesTotal: typeof payload.stages_total === 'number' ? payload.stages_total : undefined,
        currentStage: payload.current_stage ? String(payload.current_stage) : null,
        agentResults,
        activeSubstep: payload.active_substep ? String(payload.active_substep) : null,
        substeps,
        progressSource: payload.progress_source === 'autonomous_sse'
            ? 'autonomous_sse'
            : payload.progress_source === 'autonomous_ws'
                ? 'autonomous_ws'
                : payload.progress_source === 'autonomous_poll'
            ? 'autonomous_poll'
            : payload.progress_source === 'legacy_ws'
                ? 'legacy_ws'
                : undefined,
        stateHistory,
        logs,
        wsConnected: Boolean(payload.ws_connected),
        updatedAt: String(payload.updated_at || new Date().toISOString()),
    };
}

export function isAutonomousProgressSnapshot(snapshot: OrchestratorLiveProgressSnapshot | null | undefined): boolean {
    if (!snapshot) {
        return false;
    }
    if (snapshot.orchestratorCore === 'autonomous_turn_controller') {
        return true;
    }
    return snapshot.pipeline.includes('autonomous_turn_controller');
}

export function loadLiveProgressSnapshot(): OrchestratorLiveProgressSnapshot | null {
    if (typeof window === 'undefined') {
        return null;
    }
    try {
        const raw = window.localStorage.getItem(ORCHESTRATOR_LIVE_PROGRESS_KEY)
            || window.localStorage.getItem(LEGACY_ADMIN_ORCHESTRATOR_LIVE_PROGRESS_KEY);
        if (!raw) {
            return null;
        }
        const parsed = JSON.parse(raw) as OrchestratorLiveProgressSnapshot;
        if (!parsed || typeof parsed !== 'object') {
            return null;
        }
        return parsed;
    } catch {
        return null;
    }
}

export function dispatchLiveProgressUpdated(snapshot: OrchestratorLiveProgressSnapshot): void {
    if (typeof window === 'undefined') {
        return;
    }
    window.dispatchEvent(new CustomEvent(ORCHESTRATOR_LIVE_PROGRESS_EVENT, { detail: snapshot }));
}

export function saveLiveProgressSnapshot(snapshot: OrchestratorLiveProgressSnapshot): void {
    if (typeof window === 'undefined') {
        return;
    }
    try {
        const serialized = JSON.stringify(snapshot);
        window.localStorage.setItem(ORCHESTRATOR_LIVE_PROGRESS_KEY, serialized);
        window.localStorage.setItem(LEGACY_ADMIN_ORCHESTRATOR_LIVE_PROGRESS_KEY, serialized);
        dispatchLiveProgressUpdated(snapshot);
    } catch {
    }
}

export async function fetchOrchestratorProgress(
    progressUrl: string,
    authHeaders?: Record<string, string>,
): Promise<OrchestratorLiveProgressSnapshot | null> {
    const response = await fetch(progressUrl, {
        method: 'GET',
        headers: {
            Accept: 'application/json',
            ...(authHeaders || {}),
        },
        cache: 'no-store',
    });
    if (!response.ok) {
        return null;
    }
    const payload = await response.json().catch(() => null);
    if (!payload || typeof payload !== 'object') {
        return null;
    }
    return mapProgressPayloadToSnapshot(payload as Record<string, unknown>);
}

export function mergeProgressIntoDiagnostics(
    diagnostics: Record<string, unknown> | null | undefined,
    progress: OrchestratorLiveProgressSnapshot | null,
): Record<string, unknown> | null {
    if (!progress) {
        return diagnostics || null;
    }
    const base = { ...(diagnostics || {}) };
    if (progress.executionState) {
        base.execution_state = progress.executionState;
    }
    if (typeof progress.stagesCompleted === 'number') {
        base.stages_completed = progress.stagesCompleted;
    }
    if (typeof progress.stagesTotal === 'number') {
        base.stages_total = progress.stagesTotal;
    }
    if (progress.autonomousIntent) {
        base.autonomous_intent = progress.autonomousIntent;
    }
    if (progress.stageCommand) {
        base.stage_command = progress.stageCommand;
    }
    if (progress.stageNumber !== null && progress.stageNumber !== undefined) {
        base.stage_number = progress.stageNumber;
    }
    if (progress.agentResults && progress.agentResults.length > 0) {
        base.agent_results = progress.agentResults;
    }
    if (progress.currentStage) {
        base.current_stage = progress.currentStage;
    }
    if (progress.orchestratorCore) {
        base.orchestrator_core = progress.orchestratorCore;
    }
    base.progress_status = progress.status;
    base.progress_updated_at = progress.updatedAt;
    base.progress_polling = progress.status === 'running' && progress.progressSource === 'autonomous_poll';
    base.progress_streaming = progress.progressSource === 'autonomous_sse' || progress.progressSource === 'autonomous_ws';
    base.progress_logs = progress.logs;
    base.progress_substeps = progress.substeps || [];
    base.progress_active_substep = progress.activeSubstep || null;
    base.progress_source = progress.progressSource || 'autonomous_poll';
    return base;
}

export function createIdleProgressSnapshot(runId: string): OrchestratorLiveProgressSnapshot {
    return {
        ...emptySnapshot(),
        runId,
        updatedAt: new Date().toISOString(),
    };
}

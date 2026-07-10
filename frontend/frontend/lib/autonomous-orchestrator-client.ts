import { fetchWithAdminBootstrapRetry } from '@/lib/admin-bootstrap-fetch';
import {
    ORCHESTRATOR_DEBUG_AUTONOMOUS_CHAT_PATH,
    ORCHESTRATOR_DEBUG_AUTONOMOUS_SESSION_PATH,
    buildAdminOrchestratorChatUrl,
} from '@/lib/orchestrator-chat-endpoints';
import { postAdminOrchestratorChat } from '@/lib/orchestrator-chat-client';

const AUTONOMOUS_CHAT_TIMEOUT_MS = 300_000;

export type AutonomousExecutionMode = 'advisory' | 'semi_auto' | 'full_auto';

export interface AutonomousChatRequestBody {
    message: string;
    session_id?: string | null;
    mode?: AutonomousExecutionMode;
    project_name?: string | null;
    validation_profile?: string;
}

export interface AutonomousAgentResultSummary {
    agent: string;
    status: string;
    elapsed_ms?: number;
}

export interface AutonomousChatResponse {
    session_id: string;
    mode: string;
    intent: string;
    content: string;
    execution_state: string;
    approval_state: string;
    current_stage?: string | null;
    stages_completed?: number;
    stages_total?: number;
    agent_results?: AutonomousAgentResultSummary[];
    requires_approval?: boolean;
    llm_connected?: boolean;
    stages_remaining?: number;
    message_log?: Array<Record<string, unknown>>;
}

export interface AutonomousSessionStatusResponse {
    session_id: string;
    mode: string;
    execution_state: string;
    approval_state: string;
    stages: Array<{ stage_id: string; label: string; status: string }>;
    conversation_length: number;
    agent_result_count: number;
}

type OrchestratorSurfaceChatResponse = {
    session_id?: string | null;
    reply?: { content?: string };
    diagnostics?: Record<string, unknown>;
};

function mapOrchestratorSurfaceToAutonomous(
    response: OrchestratorSurfaceChatResponse,
    fallbackMode: AutonomousExecutionMode,
): AutonomousChatResponse {
    const diag = response.diagnostics || {};
    const stagesCompleted = Number(diag.stages_completed ?? 0) || 0;
    const stagesTotal = Number(diag.stages_total ?? 0) || 0;
    const agentResultsRaw = Array.isArray(diag.agent_results) ? diag.agent_results : [];
    return {
        session_id: String(response.session_id || diag.autonomous_session_id || ''),
        mode: String(diag.autonomous_mode || fallbackMode),
        intent: String(diag.autonomous_intent || 'unknown'),
        content: String(response.reply?.content || ''),
        execution_state: String(diag.execution_state || 'idle'),
        approval_state: String(diag.approval_state || 'none'),
        current_stage: typeof diag.current_stage === 'string' ? diag.current_stage : null,
        stages_completed: stagesCompleted,
        stages_total: stagesTotal,
        agent_results: agentResultsRaw
            .map((item) => {
                if (!item || typeof item !== 'object') {
                    return null;
                }
                const record = item as Record<string, unknown>;
                const agent = String(record.agent || '').trim();
                if (!agent) {
                    return null;
                }
                return {
                    agent,
                    status: String(record.status || 'unknown'),
                };
            })
            .filter((item): item is AutonomousAgentResultSummary => item !== null),
        requires_approval: Boolean(diag.requires_approval),
        llm_connected: typeof diag.llm_connected === 'boolean' ? diag.llm_connected : false,
        stages_remaining: Math.max(0, stagesTotal - stagesCompleted),
    };
}

async function authorizedFetch(
    url: string,
    accessToken: string,
    init: RequestInit,
): Promise<Response> {
    return fetchWithAdminBootstrapRetry(url, {
        ...init,
        headers: {
            ...(init.headers || {}),
            Authorization: `Bearer ${accessToken}`,
            ...(init.body ? { 'Content-Type': 'application/json' } : {}),
        },
    }, {
        timeoutMs: AUTONOMOUS_CHAT_TIMEOUT_MS,
        retries: 0,
        traceLabel: 'autonomous-orchestrator-debug',
    });
}

/**
 * Debug panel SSOT — routes through `/api/llm/orchestrate/chat` (① surface adapter).
 * Raw `/api/llm/autonomous/chat` is reserved for HTTP regression scripts only.
 */
export async function postAutonomousChat(
    apiBaseUrl: string,
    accessToken: string,
    body: AutonomousChatRequestBody,
): Promise<AutonomousChatResponse> {
    const mode = body.mode || 'semi_auto';
    const manualMode = mode !== 'advisory';
    const orchestratorMode = mode === 'full_auto' ? 'full_auto' : (mode === 'advisory' ? 'advisory' : 'manual_9step');
    const response = await postAdminOrchestratorChat<OrchestratorSurfaceChatResponse>(
        apiBaseUrl,
        accessToken,
        {
            message: body.message,
            session_id: body.session_id || undefined,
            task: body.project_name || body.message,
            mode: orchestratorMode,
            manual_mode: manualMode,
            companion_mode: 'project',
            multi_turn_enabled: true,
            context_tags: [
                'admin-orchestrator',
                'debug-autonomous-panel',
                `autonomous-mode-${mode}`,
            ],
        },
    );
    return mapOrchestratorSurfaceToAutonomous(response, mode);
}

/** Raw session probe — debug-only; no orchestrate/chat equivalent. */
export async function getAutonomousSessionStatus(
    apiBaseUrl: string,
    accessToken: string,
    sessionId: string,
): Promise<AutonomousSessionStatusResponse> {
    const base = apiBaseUrl.replace(/\/$/, '');
    const response = await authorizedFetch(
        `${base}${ORCHESTRATOR_DEBUG_AUTONOMOUS_SESSION_PATH}/${encodeURIComponent(sessionId)}`,
        accessToken,
        { method: 'GET' },
    );
    if (!response.ok) {
        const detail = await response.text();
        throw new Error(`HTTP ${response.status}: ${detail.slice(0, 240)}`);
    }
    return await response.json() as AutonomousSessionStatusResponse;
}

/** @internal Raw TurnController HTTP — scripts/tests only. */
export async function postDebugRawAutonomousChat(
    apiBaseUrl: string,
    accessToken: string,
    body: AutonomousChatRequestBody,
): Promise<AutonomousChatResponse> {
    const base = apiBaseUrl.replace(/\/$/, '');
    const response = await authorizedFetch(
        `${base}${ORCHESTRATOR_DEBUG_AUTONOMOUS_CHAT_PATH}`,
        accessToken,
        {
            method: 'POST',
            body: JSON.stringify(body),
        },
    );
    if (!response.ok) {
        const detail = await response.text();
        throw new Error(`HTTP ${response.status}: ${detail.slice(0, 240)}`);
    }
    return await response.json() as AutonomousChatResponse;
}

export { buildAdminOrchestratorChatUrl, ORCHESTRATOR_DEBUG_AUTONOMOUS_CHAT_PATH };

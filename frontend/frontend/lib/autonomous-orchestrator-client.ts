import { fetchWithAdminBootstrapRetry } from '@/lib/admin-bootstrap-fetch';

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
        traceLabel: 'autonomous-orchestrator',
    });
}

export async function postAutonomousChat(
    apiBaseUrl: string,
    accessToken: string,
    body: AutonomousChatRequestBody,
): Promise<AutonomousChatResponse> {
    const response = await authorizedFetch(
        `${apiBaseUrl}/api/llm/autonomous/chat`,
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

export async function getAutonomousSessionStatus(
    apiBaseUrl: string,
    accessToken: string,
    sessionId: string,
): Promise<AutonomousSessionStatusResponse> {
    const response = await authorizedFetch(
        `${apiBaseUrl}/api/llm/autonomous/session/${encodeURIComponent(sessionId)}`,
        accessToken,
        { method: 'GET' },
    );
    if (!response.ok) {
        const detail = await response.text();
        throw new Error(`HTTP ${response.status}: ${detail.slice(0, 240)}`);
    }
    return await response.json() as AutonomousSessionStatusResponse;
}

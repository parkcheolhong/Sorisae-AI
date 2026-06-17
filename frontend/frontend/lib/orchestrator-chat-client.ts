import { fetchWithAdminBootstrapRetry } from '@/lib/admin-bootstrap-fetch';
import {
    buildAdminOrchestratorChatUrl,
    buildMarketplaceOrchestratorChatUrl,
} from '@/lib/orchestrator-chat-endpoints';

const parseOrchestratorFetchTimeoutMs = (): number => {
    const raw = Number(process.env.NEXT_PUBLIC_ORCHESTRATOR_CHAT_FETCH_TIMEOUT_MS || 240_000);
    if (!Number.isFinite(raw)) {
        return 240_000;
    }
    return Math.min(300_000, Math.max(30_000, Math.trunc(raw)));
};

const ORCHESTRATOR_CHAT_FETCH_TIMEOUT_MS = parseOrchestratorFetchTimeoutMs();

export {
    ORCHESTRATOR_ADMIN_CHAT_PATH,
    ORCHESTRATOR_MARKETPLACE_CHAT_PATH,
    ORCHESTRATOR_DEBUG_AUTONOMOUS_CHAT_PATH,
    buildAdminOrchestratorChatUrl,
    buildMarketplaceOrchestratorChatUrl,
} from '@/lib/orchestrator-chat-endpoints';

/** @deprecated Prefer postAdminOrchestratorChat with SSOT path. */
export async function postOrchestratorChat<TResponse>(
    url: string,
    accessToken: string,
    body: Record<string, unknown>,
    signal?: AbortSignal,
): Promise<TResponse> {
    return postAdminOrchestratorChat<TResponse>(url, accessToken, body, signal);
}

export async function postAdminOrchestratorChat<TResponse>(
    urlOrApiBase: string,
    accessToken: string,
    body: Record<string, unknown>,
    signal?: AbortSignal,
): Promise<TResponse> {
    const url = urlOrApiBase.includes('/api/llm/orchestrate/chat')
        ? urlOrApiBase
        : buildAdminOrchestratorChatUrl(urlOrApiBase);
    const response = await fetchWithAdminBootstrapRetry(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify(body),
        signal,
    }, {
        timeoutMs: ORCHESTRATOR_CHAT_FETCH_TIMEOUT_MS,
        retries: 0,
        traceLabel: 'orchestrator-chat',
    });

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }

    return await response.json() as TResponse;
}

export async function postCustomerOrchestratorChat<TResponse>(
    apiBaseUrl: string,
    authHeaders: Record<string, string>,
    body: Record<string, unknown>,
    signal?: AbortSignal,
): Promise<TResponse> {
    const response = await fetch(buildMarketplaceOrchestratorChatUrl(apiBaseUrl), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...authHeaders,
        },
        body: JSON.stringify(body),
        signal,
    });
    const data = await response.json().catch(() => null);
    if (!response.ok || !data) {
        const detail = typeof data?.detail === 'string'
            ? data.detail
            : (Array.isArray(data?.detail) ? JSON.stringify(data.detail) : null);
        throw new Error(detail || '고객 협업 대화 호출에 실패했습니다.');
    }
    return data as TResponse;
}

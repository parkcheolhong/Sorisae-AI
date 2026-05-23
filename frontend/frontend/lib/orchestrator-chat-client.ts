import { fetchWithAdminBootstrapRetry } from '@/lib/admin-bootstrap-fetch';

const parseOrchestratorFetchTimeoutMs = (): number => {
    const raw = Number(process.env.NEXT_PUBLIC_ORCHESTRATOR_CHAT_FETCH_TIMEOUT_MS || 240_000);
    if (!Number.isFinite(raw)) {
        return 240_000;
    }
    return Math.min(300_000, Math.max(30_000, Math.trunc(raw)));
};

const ORCHESTRATOR_CHAT_FETCH_TIMEOUT_MS = parseOrchestratorFetchTimeoutMs();

export async function postOrchestratorChat<TResponse>(
    url: string,
    accessToken: string,
    body: Record<string, unknown>,
    signal?: AbortSignal,
): Promise<TResponse> {
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

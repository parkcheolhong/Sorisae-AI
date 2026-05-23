export const ADMIN_BOOTSTRAP_RETRYABLE_STATUSES = new Set([502, 503, 504]);

export async function fetchWithAdminBootstrapRetry(
    input: RequestInfo | URL,
    init?: RequestInit,
    options?: {
        retries?: number;
        retryDelayMs?: number;
        retryableStatuses?: Set<number>;
        timeoutMs?: number;
        traceLabel?: string;
        onMetric?: (metric: {
            traceLabel: string;
            input: string;
            attempt: number;
            retries: number;
            timeoutMs: number;
            status?: number;
            elapsedMs: number;
            outcome: 'response' | 'retryable-response' | 'error';
            error?: string;
        }) => void;
    },
) {
    const retries = Math.max(0, Number(options?.retries ?? 3));
    const retryDelayMs = Math.max(100, Number(options?.retryDelayMs ?? 1000));
    const retryableStatuses = options?.retryableStatuses || ADMIN_BOOTSTRAP_RETRYABLE_STATUSES;
    const timeoutMs = Math.max(1000, Number(options?.timeoutMs ?? 15_000));
    const traceLabel = String(options?.traceLabel || 'admin-bootstrap-fetch');
    const inputText = typeof input === 'string' ? input : String(input);
    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= retries; attempt += 1) {
        if (init?.signal?.aborted) {
            throw new DOMException('Aborted', 'AbortError');
        }
        const startedAt = globalThis.performance?.now?.() ?? Date.now();
        const controller = new AbortController();
        let timedOut = false;
        const timeoutId = globalThis.setTimeout(() => {
            timedOut = true;
            controller.abort();
        }, timeoutMs);
        const abortListener = () => controller.abort();
        init?.signal?.addEventListener('abort', abortListener, { once: true });

        try {
            const response = await fetch(input, {
                ...init,
                signal: controller.signal,
            });
            const elapsedMs = Math.round((globalThis.performance?.now?.() ?? Date.now()) - startedAt);
            const retryable = retryableStatuses.has(response.status) && attempt < retries;
            options?.onMetric?.({
                traceLabel,
                input: inputText,
                attempt: attempt + 1,
                retries,
                timeoutMs,
                status: response.status,
                elapsedMs,
                outcome: retryable ? 'retryable-response' : 'response',
            });
            if (!retryableStatuses.has(response.status) || attempt === retries) {
                return response;
            }
            const payload = await response.clone().json().catch(() => ({}));
            const detail = typeof (payload as any)?.detail === 'string'
                ? (payload as any).detail
                : `HTTP ${response.status}`;
            lastError = new Error(detail);
        } catch (error: any) {
            lastError = error instanceof Error ? error : new Error(String(error || '관리자 bootstrap 요청 실패'));
            if (lastError.name === 'AbortError' && timedOut) {
                const timeoutError = new Error(`요청 시간 초과 (${timeoutMs}ms)`);
                timeoutError.name = 'TimeoutError';
                lastError = timeoutError;
            }
            options?.onMetric?.({
                traceLabel,
                input: inputText,
                attempt: attempt + 1,
                retries,
                timeoutMs,
                elapsedMs: Math.round((globalThis.performance?.now?.() ?? Date.now()) - startedAt),
                outcome: 'error',
                error: lastError.message,
            });
            // 외부 signal 취소(탭 전환/언마운트)는 즉시 중단하고,
            // 내부 timeout 취소는 재시도 경로로 보낸다.
            if (lastError.name === 'AbortError') {
                throw lastError;
            }
            if (attempt === retries) {
                break;
            }
        } finally {
            globalThis.clearTimeout(timeoutId);
            init?.signal?.removeEventListener('abort', abortListener);
        }

        await new Promise((resolve) => window.setTimeout(resolve, retryDelayMs * (attempt + 1)));
    }

    throw lastError || new Error('관리자 bootstrap 요청 실패');
}

export function assertAdminBootstrapFetchContract() {
    if (!ADMIN_BOOTSTRAP_RETRYABLE_STATUSES.has(502) || !ADMIN_BOOTSTRAP_RETRYABLE_STATUSES.has(503) || !ADMIN_BOOTSTRAP_RETRYABLE_STATUSES.has(504)) {
        throw new Error('admin bootstrap fetch contract 누락: 502/503/504 재시도 필요');
    }
}

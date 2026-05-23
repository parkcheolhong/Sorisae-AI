export type AdminTraceLogItem = {
    id: number;
    trace_id: string;
    flow_id: string;
    step_id: string;
    action: string;
    entity_type: string;
    entity_id: string;
    status: string;
    message: string;
    payload_json?: string | null;
    created_at: string;
    connection_id?: string | null;
};

export type AdminRetryQueueItem = {
    id: number;
    trace_id: string;
    flow_id: string;
    step_id: string;
    action: string;
    entity_type: string;
    entity_id: string;
    queue_name: string;
    status: string;
    payload_json?: string | null;
    attempt_count: number;
    max_attempts: number;
    last_error?: string | null;
    updated_at?: string | null;
    created_at: string;
    connection_id?: string | null;
};

export type AdminCompletionHistoryItem = {
    id: number;
    trace_id?: string | null;
    flow_id?: string | null;
    step_id?: string | null;
    action?: string | null;
    project_name: string;
    mode: string;
    attempts: number;
    output_dir?: string | null;
    postcheck_ok?: boolean | null;
    gate_passed: boolean;
    override_used: boolean;
    created_at: string;
    connection_id?: string | null;
};

export type AdminAutoConnectLookupResponse = {
    connection_id: string;
    trace_key: string;
    capability_id?: string | null;
    completions: AdminCompletionHistoryItem[];
    logs: AdminTraceLogItem[];
    retry_queue: AdminRetryQueueItem[];
};

function isUnauthorized(status: number) {
    return status === 401 || status === 403;
}

export const buildAdminConnectionId = (flowId?: string | null, stepId?: string | null, action?: string | null, traceId?: string | null) => {
    const flow = String(flowId || '').trim();
    const step = String(stepId || '').trim();
    const actionValue = String(action || '').trim();
    if (flow && step && actionValue) {
        return `${flow}:${step}:${actionValue}`;
    }
    return String(traceId || '').trim();
};

export const parseAdminConnectionLookupKey = (connectionId: string) => {
    const normalized = connectionId.trim();
    const parts = normalized.split(':').map((part) => part.trim()).filter(Boolean);
    return {
        connection_id: normalized,
        trace_key: parts.length >= 3 ? parts.slice(0, 3).join(':') : normalized,
        capability_id: parts.length > 3 ? parts.slice(3).join(':') : null,
    };
};

export const matchesAdminConnectionLookup = (connectionId: string | null | undefined, traceId: string | null | undefined, lookupKey: string) => {
    const parsed = parseAdminConnectionLookupKey(lookupKey);
    const normalizedConnectionId = String(connectionId || '').trim();
    const normalizedTraceId = String(traceId || '').trim();
    if (normalizedConnectionId && normalizedConnectionId === parsed.connection_id) {
        return true;
    }
    if (!parsed.trace_key) {
        return false;
    }
    return normalizedTraceId === parsed.trace_key || normalizedTraceId.startsWith(`${parsed.trace_key}:`) || normalizedConnectionId === parsed.trace_key;
};

export const normalizeAdminCompletionItems = (items: AdminCompletionHistoryItem[]) => items.map((item) => ({
    ...item,
    connection_id: item.connection_id || buildAdminConnectionId(item.flow_id, item.step_id, item.action, item.trace_id),
}));

export const normalizeAdminTraceItems = (items: AdminTraceLogItem[]) => items.map((item) => ({
    ...item,
    connection_id: item.connection_id || buildAdminConnectionId(item.flow_id, item.step_id, item.action, item.trace_id),
}));

export const normalizeAdminRetryQueueItems = (items: AdminRetryQueueItem[]) => items.map((item) => ({
    ...item,
    connection_id: item.connection_id || buildAdminConnectionId(item.flow_id, item.step_id, item.action, item.trace_id),
}));

async function readArrayResponse<T>(response: Response) {
    const data = await response.json().catch(() => []);
    return Array.isArray(data) ? data as T[] : [];
}

export async function loadAdminAutoConnectCompletionHistory(options: {
    apiBaseUrl: string;
    token: string;
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const response = await fetcher(`${options.apiBaseUrl}/api/admin/auto-connect-graph/completions?limit=20`, {
        headers: { Authorization: `Bearer ${options.token}` },
    });
    if (response.status === 404) {
        return { unsupported: true, items: [] as AdminCompletionHistoryItem[] };
    }
    if (isUnauthorized(response.status)) {
        throw new Error('__ADMIN_AUTO_CONNECT_UNAUTHORIZED__');
    }
    const items = response.ok ? normalizeAdminCompletionItems(await readArrayResponse<AdminCompletionHistoryItem>(response)) : [];
    return { unsupported: false, items };
}

export async function loadAdminAutoConnectTraceHistory(options: {
    apiBaseUrl: string;
    token: string;
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const response = await fetcher(`${options.apiBaseUrl}/api/admin/auto-connect-graph/logs?limit=30`, {
        headers: { Authorization: `Bearer ${options.token}` },
    });
    if (response.status === 404) {
        return { unsupported: true, items: [] as AdminTraceLogItem[] };
    }
    if (isUnauthorized(response.status)) {
        throw new Error('__ADMIN_AUTO_CONNECT_UNAUTHORIZED__');
    }
    const items = response.ok ? normalizeAdminTraceItems(await readArrayResponse<AdminTraceLogItem>(response)) : [];
    return { unsupported: false, items };
}

export async function loadAdminAutoConnectRetryQueue(options: {
    apiBaseUrl: string;
    token: string;
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const response = await fetcher(`${options.apiBaseUrl}/api/admin/auto-connect-graph/retry-queue?limit=30`, {
        headers: { Authorization: `Bearer ${options.token}` },
    });
    if (response.status === 404) {
        return { unsupported: true, items: [] as AdminRetryQueueItem[] };
    }
    if (isUnauthorized(response.status)) {
        throw new Error('__ADMIN_AUTO_CONNECT_UNAUTHORIZED__');
    }
    const items = response.ok ? normalizeAdminRetryQueueItems(await readArrayResponse<AdminRetryQueueItem>(response)) : [];
    return { unsupported: false, items };
}

export async function loadAdminAutoConnectLookup(options: {
    apiBaseUrl: string;
    token: string;
    connectionId: string;
    fallbackCompletionHistory: AdminCompletionHistoryItem[];
    fallbackTraceHistory: AdminTraceLogItem[];
    fallbackRetryQueue: AdminRetryQueueItem[];
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const response = await fetcher(`${options.apiBaseUrl}/api/admin/auto-connect-graph/lookup?connection_id=${encodeURIComponent(options.connectionId)}&limit=20`, {
        headers: { Authorization: `Bearer ${options.token}` },
    });
    if (isUnauthorized(response.status)) {
        throw new Error('__ADMIN_AUTO_CONNECT_UNAUTHORIZED__');
    }
    if (response.status === 404) {
        const parsed = parseAdminConnectionLookupKey(options.connectionId);
        return {
            connection_id: parsed.connection_id,
            trace_key: parsed.trace_key,
            capability_id: parsed.capability_id,
            completions: normalizeAdminCompletionItems(options.fallbackCompletionHistory).filter((item) => matchesAdminConnectionLookup(item.connection_id, item.trace_id, options.connectionId)).slice(0, 20),
            logs: normalizeAdminTraceItems(options.fallbackTraceHistory).filter((item) => matchesAdminConnectionLookup(item.connection_id, item.trace_id, options.connectionId)).slice(0, 20),
            retry_queue: normalizeAdminRetryQueueItems(options.fallbackRetryQueue).filter((item) => matchesAdminConnectionLookup(item.connection_id, item.trace_id, options.connectionId)).slice(0, 20),
        } satisfies AdminAutoConnectLookupResponse;
    }
    const data = await response.json().catch(() => null);
    if (!response.ok) {
        throw new Error(data?.detail || 'connection_id 조회에 실패했습니다.');
    }
    return data as AdminAutoConnectLookupResponse;
}

export async function replayAdminAutoConnectRetryQueue(options: {
    apiBaseUrl: string;
    token: string;
    queueItemId: number;
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    let response = await fetcher(`${options.apiBaseUrl}/api/admin/auto-connect-graph/retry-queue/${options.queueItemId}/replay`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${options.token}` },
    });
    if (response.status === 404) {
        response = await fetcher(`${options.apiBaseUrl}/api/marketplace/customer-orchestrate/retry-queue/my/${options.queueItemId}/replay`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${options.token}` },
        });
    }
    if (isUnauthorized(response.status)) {
        throw new Error('__ADMIN_AUTO_CONNECT_UNAUTHORIZED__');
    }
    if (!response.ok) {
        const errorPayload = await response.json().catch(() => null);
        throw new Error(errorPayload?.detail || 'retry queue 재실행에 실패했습니다.');
    }
    return response.json().catch(() => null);
}

export function assertAdminAutoConnectServiceContract() {
    const connectionId = buildAdminConnectionId('FLOW-001', 'STEP-001', 'RUN', 'trace');
    if (!connectionId.includes('FLOW-001:STEP-001:RUN')) {
        throw new Error('admin auto-connect service contract 누락: connection id 조립 필요');
    }
}

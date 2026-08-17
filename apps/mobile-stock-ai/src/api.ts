export type OrchestrateRequest = {
    transcript: string;
    task: string;
    tts: boolean;
    auto_apply: boolean;
    agent_key: string;
    run_id: string | null;
    output_dir: string | null;
    conversation: Array<unknown>;
};

export type AuthConfig = {
    token: string;
    tokenHeaderName: string;
};

const REQUEST_TIMEOUT_MS = 30000;

function buildAuthHeaders(auth?: AuthConfig): Record<string, string> {
    if (!auth?.token?.trim()) {
        return {};
    }

    const token = auth.token.trim();
    const headerName = auth.tokenHeaderName?.trim() || 'Authorization';

    if (headerName.toLowerCase() === 'authorization') {
        return {
            Authorization: token.toLowerCase().startsWith('bearer ') ? token : `Bearer ${token}`,
        };
    }

    return {
        [headerName]: token,
    };
}

async function requestJson<T>(url: string, init?: RequestInit, auth?: AuthConfig): Promise<T> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    try {
        const response = await fetch(url, {
            ...init,
            signal: controller.signal,
            headers: {
                'Content-Type': 'application/json',
                ...buildAuthHeaders(auth),
                ...(init?.headers || {}),
            },
        });

        const text = await response.text();
        let parsed: unknown = null;

        try {
            parsed = text ? JSON.parse(text) : null;
        } catch {
            parsed = { raw: text };
        }

        if (!response.ok) {
            throw new Error(JSON.stringify(parsed));
        }

        return parsed as T;
    } finally {
        clearTimeout(timeout);
    }
}

export function getMarketplaceSummary(baseUrl: string, auth?: AuthConfig) {
    return requestJson<Record<string, unknown>>(`${baseUrl}/api/marketplace/metrics/summary`, {
        method: 'GET',
    }, auth);
}

export function getDetectorStatus(baseUrl: string, auth?: AuthConfig) {
    return requestJson<Record<string, unknown>>(`${baseUrl}/api/marketplace/ml-detectors/status`, {
        method: 'GET',
    }, auth);
}

export function postVoiceOrchestrate(baseUrl: string, payload: OrchestrateRequest, auth?: AuthConfig) {
    return requestJson<Record<string, unknown>>(`${baseUrl}/api/llm/voice/orchestrate`, {
        method: 'POST',
        body: JSON.stringify(payload),
    }, auth);
}

export function getDownloadProductUrl(baseUrl: string, product: string) {
    const normalizedBase = baseUrl.trim().replace(/\/$/, '');
    return `${normalizedBase}/api/marketplace/download-product?product=${encodeURIComponent(product)}`;
}

export function getLatestApkUrl(baseUrl: string) {
    const normalizedBase = baseUrl.trim().replace(/\/$/, '');
    return `${normalizedBase}/api/marketplace/latest.apk`;
}

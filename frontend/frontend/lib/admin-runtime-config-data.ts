type AdvisoryControlsLike = object;

interface OrchestratorRuntimeConfigLike {
    advisory_controls?: AdvisoryControlsLike;
}

export function normalizeRuntimeConfig<T extends OrchestratorRuntimeConfigLike>(
    data: T,
    defaultAdvisoryControls: AdvisoryControlsLike,
): T {
    return {
        ...data,
        advisory_controls: {
            ...defaultAdvisoryControls,
            ...(data.advisory_controls || {}),
        },
    } as T;
}

export async function fetchRuntimeConfigBundle<T extends OrchestratorRuntimeConfigLike>(options: {
    apiBaseUrl: string;
    adminFetch: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;
    defaultAdvisoryControls: AdvisoryControlsLike;
}) {
    const response = await options.adminFetch(`${options.apiBaseUrl}/api/llm/runtime-config`);
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    return normalizeRuntimeConfig(data as T, options.defaultAdvisoryControls);
}

export async function saveRuntimeConfigBundle<T extends OrchestratorRuntimeConfigLike>(options: {
    apiBaseUrl: string;
    adminFetch: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;
    runtimeDraft: T;
    defaultAdvisoryControls: AdvisoryControlsLike;
}) {
    const response = await options.adminFetch(`${options.apiBaseUrl}/api/llm/runtime-config`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(options.runtimeDraft),
    });
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    return normalizeRuntimeConfig(data as T, options.defaultAdvisoryControls);
}

export function restoreAdminPresetTask<TPreset extends { task?: string; mode?: string }>(options: {
    storageKey: string;
    task: string;
    setUnifiedPrompt: (value: string) => void;
    setMode: (value: string) => void;
    setSelectedPreset: (preset: TPreset) => void;
    setSelectedCapabilityActionId: (value: string) => void;
}) {
    try {
        const presetRaw = localStorage.getItem(options.storageKey);
        if (presetRaw && !options.task.trim()) {
            const parsed = JSON.parse(presetRaw) as TPreset;
            if (parsed?.task) {
                options.setUnifiedPrompt(parsed.task);
                options.setMode(parsed.mode || 'auto');
                options.setSelectedPreset(parsed);
                options.setSelectedCapabilityActionId('');
            }
            localStorage.removeItem(options.storageKey);
        }
    } catch {
    }
}

export async function runPostAuthBootstrap(options: {
    apiBaseUrl: string;
    adminFetch: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;
    fetchRuntimeConfig: () => Promise<void | { ok?: boolean; status?: number; error?: string }>;
    fetchWorkspaceListing: () => Promise<void | { ok?: boolean; status?: number; error?: string }>;
    fetchLatestQuantCompareSummary: () => Promise<void | { ok?: boolean; status?: number; error?: string }>;
    loadOrchestratorSystemSettings: () => Promise<void | { ok?: boolean; status?: number; error?: string }>;
    restoreLatestSelfRunRecord: () => Promise<unknown> | void;
    restorePresetTask: () => void;
    setLlmStatus: (value: any) => void;
    logBootstrapMetric?: (metric: {
        name: string;
        elapsedMs: number;
        status?: number;
        outcome: 'fulfilled' | 'rejected' | 'sync';
        error?: string;
    }) => void;
}) {
    const normalizeBootstrapResult = (value: any) => {
        const explicitStatus = typeof value?.status === 'number' ? value.status : undefined;
        const explicitOk = typeof value?.ok === 'boolean' ? value.ok : undefined;
        if (explicitOk === false) {
            return {
                status: explicitStatus,
                outcome: 'rejected' as const,
                error: typeof value?.error === 'string' && value.error.trim() ? value.error : 'bootstrap step failed',
            };
        }
        return {
            status: explicitStatus,
            outcome: 'fulfilled' as const,
            error: undefined,
        };
    };

    const measurePromise = <T>(name: string, factory: () => Promise<T>) => {
        const startedAt = performance.now();
        return factory()
            .then((value: any) => {
                const normalized = normalizeBootstrapResult(value);
                options.logBootstrapMetric?.({
                    name,
                    elapsedMs: Math.round(performance.now() - startedAt),
                    status: normalized.status,
                    outcome: normalized.outcome,
                    error: normalized.error,
                });
                return value;
            })
            .catch((error: any) => {
                options.logBootstrapMetric?.({
                    name,
                    elapsedMs: Math.round(performance.now() - startedAt),
                    outcome: 'rejected',
                    error: error?.message || String(error || 'unknown'),
                });
                throw error;
            });
    };

    measurePromise('bootstrap:llm-status', () => options.adminFetch(`${options.apiBaseUrl}/api/llm/status`))
        .then((response) => response.json())
        .then(options.setLlmStatus)
        .catch(() => { });
    void measurePromise('bootstrap:runtime-config', () => options.fetchRuntimeConfig()).catch(() => { });
    void measurePromise('bootstrap:workspace-listing', () => options.fetchWorkspaceListing()).catch(() => { });
    void measurePromise('bootstrap:quant-compare', () => options.fetchLatestQuantCompareSummary()).catch(() => { });
    void measurePromise('bootstrap:system-settings', () => options.loadOrchestratorSystemSettings()).catch(() => { });
    void measurePromise('bootstrap:workspace-self-run-record', async () => {
        // Delay fetch to let page navigation settle, reducing ERR_ABORTED on reload
        await new Promise<void>((resolve) => window.setTimeout(resolve, 400));
        const result = await options.restoreLatestSelfRunRecord();
        const hasRecord = result != null && typeof result === 'object' && !!(result as any).approval_id;
        return { ok: true, status: hasRecord ? 200 : 204 };
    }).catch(() => { });
    const presetStartedAt = performance.now();
    options.restorePresetTask();
    options.logBootstrapMetric?.({
        name: 'bootstrap:preset-restore',
        elapsedMs: Math.round(performance.now() - presetStartedAt),
        outcome: 'sync',
    });
}

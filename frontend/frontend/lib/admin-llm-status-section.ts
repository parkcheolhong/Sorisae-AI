export function buildAdminLlmStatusSectionData(options: {
    llmStatus: {
        loaded?: boolean;
        mode?: string;
        models?: unknown[];
        primary_model?: string;
        configured_models?: Record<string, string>;
    } | null;
    agentOptions: Array<{
        key: string;
        label: string;
        modelKey: string;
    }>;
}) {
    if (!options.llmStatus) {
        return null;
    }

    return {
        loaded: !!options.llmStatus.loaded,
        statusLabel: options.llmStatus.loaded ? '🟢 온라인' : '🔴 오프라인',
        statusClassName: options.llmStatus.loaded ? 'text-[#3fb950]' : 'text-[#f78166]',
        modeLabel: options.llmStatus.mode || 'ollama',
        modelCountLabel: `${options.llmStatus.models?.length || 0}개`,
        primaryModelLabel: options.llmStatus.primary_model || 'N/A',
        configuredModelRows: options.agentOptions.map((option) => ({
            key: option.key,
            label: option.label,
            value: options.llmStatus?.configured_models?.[option.modelKey] || 'N/A',
        })),
    };
}

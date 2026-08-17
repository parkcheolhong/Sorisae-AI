export function buildRuntimeConfigPanelData(options: {
    runtimeEditorOpen: boolean;
    runtimeDraft: any;
    runtimeLoading: boolean;
    runtimeSaving: boolean;
    orchestratorSystemSaving: boolean;
    runtimeMessage: string;
    runtimeConfig: any;
    quantCompareLoading: boolean;
    quantCompareMessage: string;
    quantCompareSummary: any;
    orchestratorSystemLoading: boolean;
    orchestratorSystemSettings: any;
    orchestratorSystemMessage: string;
    orchestratorSystemOpen: Record<string, boolean>;
}) {
    return {
        runtimeEditorOpen: options.runtimeEditorOpen,
        runtimeDraft: options.runtimeDraft,
        runtimeLoading: options.runtimeLoading,
        runtimeSaving: options.runtimeSaving,
        orchestratorSystemSaving: options.orchestratorSystemSaving,
        runtimeMessage: options.runtimeMessage,
        runtimeConfig: options.runtimeConfig,
        quantCompareLoading: options.quantCompareLoading,
        quantCompareMessage: options.quantCompareMessage,
        quantCompareSummary: options.quantCompareSummary,
        orchestratorSystemLoading: options.orchestratorSystemLoading,
        orchestratorSystemSettings: options.orchestratorSystemSettings,
        orchestratorSystemMessage: options.orchestratorSystemMessage,
        orchestratorSystemOpen: options.orchestratorSystemOpen,
    };
}

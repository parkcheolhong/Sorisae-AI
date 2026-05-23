export function buildCapabilityPanelBindings(options: {
    getPresetTitle: (presetId: string) => string;
    getCapabilityStateClassName: (state: any) => string;
    getCapabilityStateText: (capability: any) => string;
    selectCapabilityAction: (action: any) => Promise<void>;
    applyCapabilityAction: (action: any, execution: 'prepare' | 'run') => Promise<void>;
    toggleCapabilityVoiceAlert: () => void;
    speakCapabilityAlert: () => void;
    refreshCapabilitySummary: () => Promise<unknown>;
    activeCapabilityComparison: any;
    getCapabilityFindingRenderKey: (finding: any, index: number) => string;
    getCapabilityCodeExampleRenderKey: (example: any, index: number) => string;
    buildSelfRunStatusLabel: (status: any) => string;
}) {
    return {
        getLinkedPresetTitle: (presetId: string) => options.getPresetTitle(presetId),
        getCapabilityStateClassName: options.getCapabilityStateClassName,
        getCapabilityStateText: options.getCapabilityStateText,
        onSelectCapabilityAction: (action: any) => options.selectCapabilityAction(action),
        onApplyCapabilityAction: (action: any, execution: 'prepare' | 'run') => options.applyCapabilityAction(action, execution),
        onToggleCapabilityVoiceAlert: options.toggleCapabilityVoiceAlert,
        onSpeakCapabilityAlert: options.speakCapabilityAlert,
        onRefreshCapabilitySummary: options.refreshCapabilitySummary,
        activeCapabilityComparison: options.activeCapabilityComparison,
        getCapabilityFindingRenderKey: options.getCapabilityFindingRenderKey,
        getCapabilityCodeExampleRenderKey: options.getCapabilityCodeExampleRenderKey,
        buildSelfRunStatusLabel: (status: string) => options.buildSelfRunStatusLabel(status),
    };
}

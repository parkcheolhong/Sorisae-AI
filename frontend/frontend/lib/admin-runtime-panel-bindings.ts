type RuntimeConfigPanelActionBag = {
    toggleEditor: () => void;
    refresh: () => void;
    saveRuntime: () => void;
    saveSystem: () => void;
    applyModelTuningLevel: (level: number) => void;
    applyTokenTuningLevel: (level: number) => void;
    applyTimeoutTuningLevel: (level: number) => void;
    updateRuntimeField: (field: string, value: string) => void;
    updateRuntimeToggle: (field: string, value: boolean) => void;
    updateAdvisoryToggle: (field: string, value: boolean) => void;
    updateAdvisoryNumeric: (field: string, value: string) => void;
    applyRuntimeProfile: (profile: any) => void;
    applyFeaturedModelAction: (row: any, action: any) => void;
    applyFunctionalModelGrade: (row: any, grade: any) => void;
    fetchLatestQuantCompareSummary: () => void;
    updateRuntimeModelRoute: (...args: any[]) => void;
    updateGlobalExecutionPreference: (enabled: boolean) => void;
    updateGlobalExecutionNumeric: (...args: any[]) => void;
    updateRuntimeExecutionMode: (...args: any[]) => void;
    updateRuntimeExecutionNumeric: (...args: any[]) => void;
    loadOrchestratorSystemSettings: () => void;
    toggleOrchestratorSystemSection: (sectionId: string) => void;
    updateOrchestratorSystemSettingValue: (fieldKey: string, value: string) => void;
};

export function buildRuntimeConfigPanelBindings(options: {
    setRuntimeEditorOpen: (updater: (prev: boolean) => boolean) => void;
    fetchRuntimeConfig: () => void;
    saveRuntimeConfig: () => void;
    saveOrchestratorSystemSettings: () => void;
    applyModelTuningLevel: (level: number) => void;
    applyTokenTuningLevel: (level: number) => void;
    applyTimeoutTuningLevel: (level: number) => void;
    updateRuntimeField: (field: string, value: string) => void;
    updateGlobalExecutionPreference: (enabled: boolean) => void;
    updateRuntimeToggle: (field: string, value: boolean) => void;
    updateAdvisoryToggle: (field: string, value: boolean) => void;
    updateAdvisoryNumeric: (field: string, value: string) => void;
    applyRuntimeProfile: (profile: any) => void;
    applyFeaturedModelAction: (row: any, action: any) => void;
    applyFunctionalModelGrade: (row: any, grade: any) => void;
    fetchLatestQuantCompareSummary: () => void;
    updateRuntimeModelRoute: (...args: any[]) => void;
    updateGlobalExecutionNumeric: (...args: any[]) => void;
    updateRuntimeExecutionMode: (...args: any[]) => void;
    updateRuntimeExecutionNumeric: (...args: any[]) => void;
    loadOrchestratorSystemSettings: () => void;
    toggleOrchestratorSystemSection: (sectionId: string) => void;
    updateOrchestratorSystemSettingValue: (fieldKey: string, value: string) => void;
}): RuntimeConfigPanelActionBag {
    return {
        toggleEditor: () => options.setRuntimeEditorOpen((prev) => !prev),
        refresh: options.fetchRuntimeConfig,
        saveRuntime: options.saveRuntimeConfig,
        saveSystem: options.saveOrchestratorSystemSettings,
        applyModelTuningLevel: options.applyModelTuningLevel,
        applyTokenTuningLevel: options.applyTokenTuningLevel,
        applyTimeoutTuningLevel: options.applyTimeoutTuningLevel,
        updateRuntimeField: options.updateRuntimeField,
        updateRuntimeToggle: (field, value) => {
            if (field === 'gpu_only_preferred') {
                options.updateGlobalExecutionPreference(value);
                return;
            }
            options.updateRuntimeToggle(field as 'force_complete' | 'allow_synthetic_fallback', value);
        },
        updateAdvisoryToggle: options.updateAdvisoryToggle,
        updateAdvisoryNumeric: options.updateAdvisoryNumeric,
        applyRuntimeProfile: options.applyRuntimeProfile,
        applyFeaturedModelAction: options.applyFeaturedModelAction,
        applyFunctionalModelGrade: options.applyFunctionalModelGrade,
        fetchLatestQuantCompareSummary: options.fetchLatestQuantCompareSummary,
        updateRuntimeModelRoute: options.updateRuntimeModelRoute,
        updateGlobalExecutionPreference: options.updateGlobalExecutionPreference,
        updateGlobalExecutionNumeric: options.updateGlobalExecutionNumeric,
        updateRuntimeExecutionMode: options.updateRuntimeExecutionMode,
        updateRuntimeExecutionNumeric: options.updateRuntimeExecutionNumeric,
        loadOrchestratorSystemSettings: options.loadOrchestratorSystemSettings,
        toggleOrchestratorSystemSection: options.toggleOrchestratorSystemSection,
        updateOrchestratorSystemSettingValue: options.updateOrchestratorSystemSettingValue,
    };
}

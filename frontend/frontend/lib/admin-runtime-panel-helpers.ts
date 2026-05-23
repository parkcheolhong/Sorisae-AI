export function buildRuntimeConfigPanelHelpers(options: {
    runtimeTuningLevels: readonly number[];
    runtimeFields: Array<[string, string]>;
    defaultAdvisoryControls: any;
    modelGradeRows: any[];
    getMissingGradeModels: (availableModels: string[], targets: Record<string, string>) => string[];
    isGradeActive: (modelRoutes: Record<string, string>, targets: Record<string, string>) => boolean;
    codingQ4Tag: string;
    codingQ5Tag: string;
    codingQ6Tag: string;
    codingQ8Tag: string;
    formatMetricNumber: (value: number | null, digits?: number, suffix?: string) => string;
    modelRouteFields: Array<[string, string]>;
    runtimePolicyHints: Record<string, string>;
    executionModeLabels: Record<string, string>;
    resolveHybridExecutionNumGpu: (control?: any) => number | string;
}) {
    return {
        runtimeTuningLevels: options.runtimeTuningLevels,
        runtimeFields: options.runtimeFields,
        defaultAdvisoryControls: options.defaultAdvisoryControls,
        modelGradeRows: options.modelGradeRows,
        getMissingGradeModels: options.getMissingGradeModels,
        isGradeActive: options.isGradeActive,
        codingQ4Tag: options.codingQ4Tag,
        codingQ5Tag: options.codingQ5Tag,
        codingQ6Tag: options.codingQ6Tag,
        codingQ8Tag: options.codingQ8Tag,
        formatMetricNumber: options.formatMetricNumber,
        modelRouteFields: options.modelRouteFields,
        runtimePolicyHints: options.runtimePolicyHints,
        executionModeLabels: options.executionModeLabels,
        resolveHybridExecutionNumGpu: options.resolveHybridExecutionNumGpu,
    };
}

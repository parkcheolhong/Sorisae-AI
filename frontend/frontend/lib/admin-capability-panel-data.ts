export function buildAdminCapabilityPanelData<
    TSummary extends { id: string; state: string; detail?: string | null; summary?: string; metric?: string },
    TGroup extends { id: string },
    TFinding extends { severity: string; title: string },
    TDetail extends { capability: { id: string }; validation_findings: TFinding[] },
>(options: {
    capabilitySummary: { capabilities?: TSummary[]; groups?: TGroup[] } | null;
    capabilityExecutionComparison: {
        capabilityId: string;
        beforeDetail: TDetail | null;
        afterDetail: TDetail | null;
    } | null;
    capabilityDetail: TDetail | null;
    generatorDefinitions: Array<{ id: string; title: string; summary: string; finalStage: string }>;
    buildCapabilityComparisonTitles: (sourceFindings: TFinding[], targetFindings: TFinding[]) => string[];
    buildCapabilityAlertSpeech: (summary: any, detail: any) => string;
}) {
    const capabilitySummaryLookup = new Map(
        (options.capabilitySummary?.capabilities || []).map((capability) => [capability.id, capability]),
    );
    const capabilityGroupSummaryLookup = new Map(
        (options.capabilitySummary?.groups || []).map((group: any) => [group.id, group]),
    );
    const capabilityProblemCards = (options.capabilitySummary?.capabilities || [])
        .filter((capability) => (capability as any).attention_required || capability.state === 'error' || capability.state === 'warning')
        .slice(0, 4);
    const activeCapabilityComparison = options.capabilityExecutionComparison?.capabilityId === options.capabilityDetail?.capability.id
        ? options.capabilityExecutionComparison
        : null;
    const beforeComparisonErrors = activeCapabilityComparison?.beforeDetail?.validation_findings.filter((item) => item.severity === 'error').length || 0;
    const afterComparisonErrors = activeCapabilityComparison?.afterDetail?.validation_findings.filter((item) => item.severity === 'error').length || 0;
    const beforeComparisonWarnings = activeCapabilityComparison?.beforeDetail?.validation_findings.filter((item) => item.severity === 'warning').length || 0;
    const afterComparisonWarnings = activeCapabilityComparison?.afterDetail?.validation_findings.filter((item) => item.severity === 'warning').length || 0;
    const comparisonResolvedTitles = options.buildCapabilityComparisonTitles(
        activeCapabilityComparison?.beforeDetail?.validation_findings || [],
        activeCapabilityComparison?.afterDetail?.validation_findings || [],
    );
    const comparisonNewTitles = options.buildCapabilityComparisonTitles(
        activeCapabilityComparison?.afterDetail?.validation_findings || [],
        activeCapabilityComparison?.beforeDetail?.validation_findings || [],
    );
    const capabilityAlertSpeech = options.buildCapabilityAlertSpeech(
        options.capabilitySummary,
        options.capabilityDetail,
    );
    const generatorCapabilityStatusRows = options.generatorDefinitions.map((definition) => {
        const capability = capabilitySummaryLookup.get(definition.id) as any;
        return {
            ...definition,
            state: capability?.state || 'standby',
            metric: capability?.metric || '-',
            detail: capability?.detail || capability?.summary || definition.summary,
        };
    });

    return {
        capabilitySummaryLookup,
        capabilityGroupSummaryLookup,
        capabilityProblemCards,
        activeCapabilityComparison,
        beforeComparisonErrors,
        afterComparisonErrors,
        beforeComparisonWarnings,
        afterComparisonWarnings,
        comparisonResolvedTitles,
        comparisonNewTitles,
        capabilityAlertSpeech,
        generatorCapabilityStatusRows,
    };
}

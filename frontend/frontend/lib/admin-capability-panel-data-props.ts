export function buildCapabilityPanelDataProps(options: {
    capabilityLoading: boolean;
    capabilityMessage: string;
    capabilityDetail: any;
    detailCapabilityAction: any;
    beforeComparisonErrors: number;
    beforeComparisonWarnings: number;
    afterComparisonErrors: number;
    afterComparisonWarnings: number;
    comparisonResolvedTitles: string[];
    comparisonNewTitles: string[];
}) {
    return {
        capabilityLoading: options.capabilityLoading,
        capabilityMessage: options.capabilityMessage,
        capabilityDetail: options.capabilityDetail,
        detailCapabilityAction: options.detailCapabilityAction,
        beforeComparisonErrors: options.beforeComparisonErrors,
        beforeComparisonWarnings: options.beforeComparisonWarnings,
        afterComparisonErrors: options.afterComparisonErrors,
        afterComparisonWarnings: options.afterComparisonWarnings,
        comparisonResolvedTitles: options.comparisonResolvedTitles,
        comparisonNewTitles: options.comparisonNewTitles,
    };
}

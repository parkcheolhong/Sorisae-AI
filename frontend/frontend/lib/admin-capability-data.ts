export function createCapabilityDataHelpers<TSummary, TDetail>(options: {
    fetchCapabilitySummary: (request?: { silent?: boolean }) => Promise<TSummary | null>;
    fetchCapabilityDetail: (capabilityId: string, request?: { silent?: boolean }) => Promise<TDetail | null>;
}) {
    let summaryPromise: Promise<TSummary | null> | null = null;
    let detailPromises = new Map<string, Promise<TDetail | null>>();

    const fetchCapabilitySummaryDeduped = (request?: { silent?: boolean }) => {
        if (!summaryPromise) {
            summaryPromise = options.fetchCapabilitySummary(request)
                .finally(() => {
                    summaryPromise = null;
                });
        }
        return summaryPromise;
    };

    const fetchCapabilityDetailDeduped = (capabilityId: string, request?: { silent?: boolean }) => {
        const cacheKey = `${capabilityId}::${request?.silent === true ? 'silent' : 'default'}`;
        const existing = detailPromises.get(cacheKey);
        if (existing) {
            return existing;
        }
        const nextPromise = options.fetchCapabilityDetail(capabilityId, request)
            .finally(() => {
                detailPromises.delete(cacheKey);
            });
        detailPromises.set(cacheKey, nextPromise);
        return nextPromise;
    };

    const fetchCapabilityBundle = async (capabilityId: string, request?: { silent?: boolean }) => {
        const [summary, detail] = await Promise.all([
            fetchCapabilitySummaryDeduped(request),
            fetchCapabilityDetailDeduped(capabilityId, request),
        ]);
        return { summary, detail };
    };

    const refreshCapabilityDetail = async (capabilityId: string) => {
        const detail = await fetchCapabilityDetailDeduped(capabilityId);
        return detail;
    };

    const finalizeCapabilityExecutionComparison = async<TRunResult, TSelfRunResult>(request: {
        capabilityId: string;
        beforeDetail: TDetail | null;
        runResult: TRunResult | null;
        selfRunResult?: TSelfRunResult | null;
        capturedAt?: string;
    }) => {
        const { detail: afterDetail } = await fetchCapabilityBundle(request.capabilityId);
        return {
            capabilityId: request.capabilityId,
            capturedAt: request.capturedAt || new Date().toISOString(),
            beforeDetail: request.beforeDetail,
            afterDetail,
            runResult: request.runResult,
            selfRunResult: request.selfRunResult || null,
        };
    };

    const refreshCapabilityState = async<TCard extends { id: string }>(request: {
        selectedCapabilityActionId: string;
        pickPrimaryCapability: (cards: TCard[]) => TCard | null;
        getCards: (summary: TSummary | null) => TCard[];
        setSelectedCapabilityActionId: (capabilityId: string) => void;
        currentDetailCapabilityId?: string;
    }) => {
        const summary = await fetchCapabilitySummaryDeduped({ silent: true });
        const cards = request.getCards(summary);
        const nextTarget = request.pickPrimaryCapability(cards);
        const targetId = request.selectedCapabilityActionId && cards.some((card) => card.id === request.selectedCapabilityActionId)
            ? request.selectedCapabilityActionId
            : (nextTarget?.id || '');

        if (!targetId) {
            return { summary, detail: null, targetId: '' };
        }

        if (targetId !== request.selectedCapabilityActionId) {
            request.setSelectedCapabilityActionId(targetId);
        }

        if (request.currentDetailCapabilityId === targetId) {
            return { summary, detail: null, targetId };
        }

        const detail = await fetchCapabilityDetailDeduped(targetId, { silent: true });
        return { summary, detail, targetId };
    };

    return {
        fetchCapabilityBundle,
        refreshCapabilityDetail,
        finalizeCapabilityExecutionComparison,
        refreshCapabilityState,
    };
}

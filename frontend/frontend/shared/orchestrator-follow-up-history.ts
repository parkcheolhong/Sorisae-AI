export type SharedFollowUpHistoryEntry = {
    recordedAt: string;
    score: number;
};

export type SharedFollowUpHistoryStats = {
    averageScore: number;
    peakScore: number;
    latestScore: number;
    previousScore: number | null;
    momentum: number;
    cumulativeScore: number;
};

export type SharedFollowUpPriorityModelInput = {
    severity: number;
    recency: number;
    approvalRisk: number;
    hardGateImpact: number;
    operationalRisk: number;
    selfRunPriority: number;
};

const clampScore = (value: number) => Math.max(0, Math.min(100, Math.round(value)));

export const buildFollowUpPriorityScore = (input: SharedFollowUpPriorityModelInput) => {
    const normalized = {
        severity: clampScore(input.severity),
        recency: clampScore(input.recency),
        approvalRisk: clampScore(input.approvalRisk),
        hardGateImpact: clampScore(input.hardGateImpact),
        operationalRisk: clampScore(input.operationalRisk),
        selfRunPriority: clampScore(input.selfRunPriority),
    };
    const weighted = clampScore(
        (normalized.severity * 0.24)
        + (normalized.recency * 0.1)
        + (normalized.approvalRisk * 0.16)
        + (normalized.hardGateImpact * 0.2)
        + (normalized.operationalRisk * 0.15)
        + (normalized.selfRunPriority * 0.15),
    );
    return {
        axes: normalized,
        weighted,
    };
};

const parseHistoryPayload = (raw: string | null): Record<string, SharedFollowUpHistoryEntry[]> => {
    if (!raw) {
        return {};
    }
    try {
        const parsed = JSON.parse(raw) as Record<string, SharedFollowUpHistoryEntry[]>;
        if (!parsed || typeof parsed !== 'object') {
            return {};
        }
        return parsed;
    } catch {
        return {};
    }
};

export const readFollowUpHistory = (storageKey: string, historyId: string): SharedFollowUpHistoryEntry[] => {
    if (typeof window === 'undefined') {
        return [];
    }
    const payload = parseHistoryPayload(window.localStorage.getItem(storageKey));
    return Array.isArray(payload[historyId]) ? payload[historyId] : [];
};

export const appendFollowUpHistory = (
    storageKey: string,
    historyId: string,
    score: number,
    maxPoints = 8,
): SharedFollowUpHistoryEntry[] => {
    if (typeof window === 'undefined') {
        return [];
    }
    const payload = parseHistoryPayload(window.localStorage.getItem(storageKey));
    const currentEntries = Array.isArray(payload[historyId]) ? payload[historyId] : [];
    const normalizedScore = clampScore(score);
    const lastEntry = currentEntries[currentEntries.length - 1];
    const nextEntries = lastEntry && lastEntry.score === normalizedScore
        ? currentEntries
        : [...currentEntries, { recordedAt: new Date().toISOString(), score: normalizedScore }].slice(-maxPoints);
    payload[historyId] = nextEntries;
    window.localStorage.setItem(storageKey, JSON.stringify(payload));
    return nextEntries;
};

export const buildFollowUpTrendPoints = (entries: SharedFollowUpHistoryEntry[]) => entries.map((entry, index) => ({
    label: `${index + 1}`,
    value: clampScore(entry.score),
}));

export const computeFollowUpHistoryStats = (
    currentScore: number,
    entries: SharedFollowUpHistoryEntry[],
): SharedFollowUpHistoryStats => {
    const normalizedCurrent = clampScore(currentScore);
    const scores = entries.length > 0 ? entries.map((entry) => clampScore(entry.score)) : [normalizedCurrent];
    const total = scores.reduce((sum, value) => sum + value, 0);
    const averageScore = Math.round(total / scores.length);
    const peakScore = Math.max(...scores);
    const latestScore = scores[scores.length - 1] ?? normalizedCurrent;
    const previousScore = scores.length > 1 ? scores[scores.length - 2] : null;
    const momentum = previousScore === null ? 0 : latestScore - previousScore;
    const cumulativeScore = clampScore(
        (normalizedCurrent * 0.45)
        + (averageScore * 0.3)
        + (peakScore * 0.15)
        + (Math.max(0, momentum) * 0.1),
    );
    return {
        averageScore,
        peakScore,
        latestScore,
        previousScore,
        momentum,
        cumulativeScore,
    };
};

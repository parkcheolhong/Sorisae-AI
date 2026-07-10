const GPS_PERSISTED_MAX_AGE_MS = 2_000_000;

export type PersistedGpsSnapshot = {
    latitude: number;
    longitude: number;
    accuracy: number | null;
    overrideCountryCode?: string;
    overrideRegionHint?: string;
    recordedAt: number;
};

export function serializePersistedGpsSnapshot(snapshot: PersistedGpsSnapshot): string {
    return JSON.stringify({
        latitude: snapshot.latitude,
        longitude: snapshot.longitude,
        accuracy: snapshot.accuracy,
        overrideCountryCode: snapshot.overrideCountryCode ?? null,
        overrideRegionHint: snapshot.overrideRegionHint ?? null,
        recordedAt: snapshot.recordedAt,
    });
}

export function parsePersistedGpsSnapshot(
    rawSnapshot: string | null | undefined,
    nowMs: number = Date.now(),
): PersistedGpsSnapshot | null {
    if (!rawSnapshot) {
        return null;
    }

    try {
        const parsed = JSON.parse(rawSnapshot) as Partial<PersistedGpsSnapshot>;
        const latitude = Number(parsed.latitude);
        const longitude = Number(parsed.longitude);
        const recordedAt = Number(parsed.recordedAt);
        if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || !Number.isFinite(recordedAt)) {
            return null;
        }
        if (nowMs - recordedAt > GPS_PERSISTED_MAX_AGE_MS) {
            return null;
        }

        const accuracyValue = parsed.accuracy;
        const accuracy = accuracyValue == null || Number.isNaN(Number(accuracyValue))
            ? null
            : Number(accuracyValue);

        const overrideCountryCode = typeof parsed.overrideCountryCode === 'string'
            ? parsed.overrideCountryCode.trim().toUpperCase() || undefined
            : undefined;
        const overrideRegionHint = typeof parsed.overrideRegionHint === 'string'
            ? parsed.overrideRegionHint.trim().toLowerCase() || undefined
            : undefined;

        return {
            latitude,
            longitude,
            accuracy,
            overrideCountryCode,
            overrideRegionHint,
            recordedAt,
        };
    } catch {
        return null;
    }
}

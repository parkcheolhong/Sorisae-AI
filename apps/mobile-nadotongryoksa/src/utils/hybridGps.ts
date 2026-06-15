export type HybridGpsMode = 'satellite' | 'hybrid' | 'wifi_fallback';

export function detectHybridGpsMode(accuracy: number | null | undefined): HybridGpsMode {
    if (accuracy == null || Number.isNaN(accuracy)) {
        return 'wifi_fallback';
    }
    if (accuracy <= 25) {
        return 'satellite';
    }
    if (accuracy <= 90) {
        return 'hybrid';
    }
    return 'wifi_fallback';
}

export function scoreLocationQuality(accuracy: number | null | undefined): number {
    if (accuracy == null || Number.isNaN(accuracy)) {
        return 35;
    }
    if (accuracy <= 10) {
        return 96;
    }
    if (accuracy <= 20) {
        return 88;
    }
    if (accuracy <= 45) {
        return 74;
    }
    if (accuracy <= 100) {
        return 58;
    }
    return 40;
}

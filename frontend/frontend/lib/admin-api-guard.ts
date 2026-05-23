export const ADMIN_API_BACKOFF_UNTIL_STORAGE_KEY = 'admin_api_backoff_until_v1';
export const ADMIN_API_BACKOFF_MS = 60_000;

export function buildApiErrorMessage(apiPath: string, status: number, detail?: string | null, fallback = '요청에 실패했습니다.') {
    const trimmedDetail = String(detail || '').trim();
    if (trimmedDetail && trimmedDetail !== 'Not Found') {
        return `${apiPath} · ${trimmedDetail}`;
    }
    if (status === 404) {
        return `${apiPath} · 404 Not Found`;
    }
    return `${apiPath} · ${fallback} (${status})`;
}

export function readAdminApiBackoffMap(): Record<string, number> {
    if (typeof window === 'undefined') {
        return {};
    }
    try {
        const raw = window.localStorage.getItem(ADMIN_API_BACKOFF_UNTIL_STORAGE_KEY);
        if (!raw) {
            return {};
        }
        const parsed = JSON.parse(raw) as Record<string, number>;
        return parsed && typeof parsed === 'object' ? parsed : {};
    } catch {
        return {};
    }
}

export function writeAdminApiBackoffMap(value: Record<string, number>) {
    if (typeof window === 'undefined') {
        return;
    }
    window.localStorage.setItem(ADMIN_API_BACKOFF_UNTIL_STORAGE_KEY, JSON.stringify(value));
}

export function getAdminApiBackoffUntil(apiKey: string): number {
    const map = readAdminApiBackoffMap();
    const value = Number(map[apiKey] || 0);
    if (!Number.isFinite(value) || value <= Date.now()) {
        if (value > 0) {
            delete map[apiKey];
            writeAdminApiBackoffMap(map);
        }
        return 0;
    }
    return value;
}

export function isAdminApiBackoffActive(apiKey: string): boolean {
    return getAdminApiBackoffUntil(apiKey) > Date.now();
}

export function setAdminApiBackoff(apiKey: string, durationMs = ADMIN_API_BACKOFF_MS) {
    const map = readAdminApiBackoffMap();
    map[apiKey] = Date.now() + durationMs;
    writeAdminApiBackoffMap(map);
}

export function clearAdminApiBackoff(apiKey: string) {
    const map = readAdminApiBackoffMap();
    if (!(apiKey in map)) {
        return;
    }
    delete map[apiKey];
    writeAdminApiBackoffMap(map);
}

export function assertAdminApiGuardContract() {
    const sample = buildApiErrorMessage('/api/test', 500, '', 'fallback');
    if (!sample.includes('/api/test')) {
        throw new Error('admin api guard contract 누락: buildApiErrorMessage path 포함 필요');
    }
}

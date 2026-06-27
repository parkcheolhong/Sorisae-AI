export const ADMIN_PROXY_TIMEOUT_MS = 20_000;
export const ADMIN_SESSION_WARNING_WINDOW_MS = 5 * 60 * 1000;
export const ADMIN_SESSION_CHECK_INTERVAL_MS = 30 * 1000;

type TokenResponse = {
    access_token: string;
    token_type: string;
};

function decodeBase64Url(value: string): string {
    const normalized = value.replace(/-/g, '+').replace(/_/g, '/');
    const padded = normalized.padEnd(
        normalized.length + ((4 - (normalized.length % 4)) % 4),
        '=',
    );

    if (typeof window !== 'undefined' && typeof window.atob === 'function') {
        return window.atob(padded);
    }

    return Buffer.from(padded, 'base64').toString('utf-8');
}

function canUseBrowserStorage(): boolean {
    return typeof window !== 'undefined' && typeof localStorage !== 'undefined';
}

export function getAdminToken(): string {
    if (!canUseBrowserStorage()) {
        return '';
    }

    try {
        return localStorage.getItem('admin_token') || '';
    } catch {
        return '';
    }
}

export function resolveAdminAccessToken(): string {
    const adminToken = getAdminToken();
    if (adminToken) {
        return adminToken;
    }
    if (!canUseBrowserStorage()) {
        return '';
    }
    try {
        return localStorage.getItem('token') || '';
    } catch {
        return '';
    }
}

export function setAdminToken(token: string): void {
    if (!canUseBrowserStorage()) {
        return;
    }

    try {
        localStorage.setItem('admin_token', token);
    } catch {
    }
}

export function clearAdminToken(): void {
    if (!canUseBrowserStorage()) {
        return;
    }

    try {
        localStorage.removeItem('admin_token');
    } catch {
    }
}

export function getAdminTokenExpiryMs(token: string): number | null {
    if (!token) {
        return null;
    }

    const segments = token.split('.');
    if (segments.length < 2) {
        return null;
    }

    try {
        const payload = JSON.parse(decodeBase64Url(segments[1]));
        const exp = payload?.exp;
        if (typeof exp !== 'number' || !Number.isFinite(exp)) {
            return null;
        }
        return exp * 1000;
    } catch {
        return null;
    }
}

export function getRemainingSessionMinutes(expiryMs: number): number {
    return Math.max(1, Math.ceil((expiryMs - Date.now()) / 60000));
}

export async function extendAdminSessionToken(
    currentToken: string = getAdminToken(),
): Promise<TokenResponse> {
    if (!currentToken) {
        throw new Error('관리자 인증 정보가 없습니다.');
    }

    const response = await fetch('/api/proxy', {
        method: 'PUT',
        headers: {
            Authorization: `Bearer ${currentToken}`,
        },
    });

    const raw = await response.text();
    let payload: any = null;
    try {
        payload = raw ? JSON.parse(raw) : null;
    } catch {
        payload = raw;
    }

    if (!response.ok) {
        if (payload && typeof payload.detail === 'string' && payload.detail.trim()) {
            throw new Error(payload.detail);
        }
        if (payload && typeof payload.error === 'string' && payload.error.trim()) {
            throw new Error(payload.error);
        }
        if (typeof payload === 'string' && payload.trim()) {
            throw new Error(payload);
        }
        throw new Error(`세션 연장 실패 (HTTP ${response.status})`);
    }

    if (!payload || typeof payload.access_token !== 'string' || !payload.access_token.trim()) {
        throw new Error('세션 연장 응답에 access_token이 없습니다.');
    }

    setAdminToken(payload.access_token);
    return payload as TokenResponse;
}
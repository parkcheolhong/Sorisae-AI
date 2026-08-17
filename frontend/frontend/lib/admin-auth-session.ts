export async function readJsonSafely(response: Response) {
    try {
        return await response.json();
    } catch {
        return null;
    }
}

export const extractApiErrorMessage = (payload: any, status: number) => {
    if (typeof payload === 'string' && payload.trim()) {
        return payload;
    }
    if (payload && typeof payload.detail === 'string' && payload.detail.trim()) {
        return payload.detail;
    }
    if (payload && typeof payload.error === 'string' && payload.error.trim()) {
        return payload.error;
    }
    return `HTTP ${status}`;
};

export async function verifyAdminBootstrap(options: {
    accessToken: string;
    setAdminToken: (token: string) => void;
}) {
    const response = await fetch('/api/proxy', {
        headers: { Authorization: `Bearer ${options.accessToken}` },
    });
    const payload = await readJsonSafely(response);
    if (!response.ok) {
        throw new Error(extractApiErrorMessage(payload, response.status));
    }
    if (!payload || (!(payload as any).is_admin && !(payload as any).is_superuser)) {
        throw new Error('관리자 권한이 확인되지 않았습니다.');
    }
    try {
        if (!localStorage.getItem('admin_token')) {
            options.setAdminToken(options.accessToken);
        }
    } catch {
    }
    return payload;
}

export function createAdminSessionExpiryChecker(options: {
    token: () => string;
    getAdminTokenExpiryMs: (token: string) => number | null;
    warningWindowMs: number;
    getRemainingSessionMinutes: (expiryMs: number) => number;
    sessionWarningExpRef: { current: number | null };
    onUnauthorized: (message: string) => void;
    onAppendLiveLog: (event: string, message: string, stage?: string, timestamp?: string, severity?: 'info' | 'success' | 'warning' | 'error') => void;
    onRuntimeMessage: (message: string) => void;
    onPushAssistantNotice: (title: string, content: string) => void;
    extendAdminSessionToken: (token: string) => Promise<unknown>;
}) {
    return async function checkSessionExpiry() {
        const currentToken = options.token();
        const expiryMs = options.getAdminTokenExpiryMs(currentToken);

        if (!currentToken || !expiryMs) {
            return;
        }

        // 관리자 세션은 만료 경고/자동 로그아웃 없이 유지한다.
        // explicit logout 이외의 세션 해제는 정책상 사용하지 않는다.
        options.sessionWarningExpRef.current = null;
    };
}

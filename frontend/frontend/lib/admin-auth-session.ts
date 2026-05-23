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

        const remainingMs = expiryMs - Date.now();
        if (remainingMs <= 0) {
            options.onUnauthorized('관리자 세션 시간이 만료되었습니다. 다시 로그인해 주세요.');
            return;
        }

        if (remainingMs > options.warningWindowMs) {
            options.sessionWarningExpRef.current = null;
            return;
        }

        if (options.sessionWarningExpRef.current === expiryMs) {
            return;
        }

        options.sessionWarningExpRef.current = expiryMs;
        const shouldExtend = window.confirm(
            `관리자 세션이 약 ${options.getRemainingSessionMinutes(expiryMs)}분 후 만료됩니다. 로그인 시간을 연장할까요?`,
        );

        if (!shouldExtend) {
            options.onAppendLiveLog('client', '관리자 세션 연장 안내를 보류했습니다.', 'AUTH', undefined, 'warning');
            return;
        }

        try {
            await options.extendAdminSessionToken(currentToken);
            options.sessionWarningExpRef.current = null;
            options.onRuntimeMessage('관리자 세션 시간을 연장했습니다.');
            options.onAppendLiveLog('client', '관리자 세션 시간을 연장했습니다.', 'AUTH', undefined, 'success');
            options.onPushAssistantNotice('세션 연장', '관리자 세션 시간이 만료 전에 연장되었습니다.');
        } catch (error: any) {
            options.onUnauthorized(error?.message || '관리자 세션 연장에 실패했습니다. 다시 로그인해 주세요.');
        }
    };
}

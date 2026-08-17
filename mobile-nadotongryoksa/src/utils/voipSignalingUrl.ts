const trimTrailingSlash = (value: string): string => value.replace(/\/+$/, '');

function hostIsPrivateOrLoopback(hostname: string): boolean {
    const host = String(hostname || '').trim().toLowerCase();
    if (!host || host === 'localhost') {
        return true;
    }
    if (/^127\./.test(host) || /^10\./.test(host) || /^192\.168\./.test(host)) {
        return true;
    }
    return /^172\.(1[6-9]|2\d|3[01])\./.test(host);
}

function rewritePrivateSignalingToApiBase(
    signalingUrl: string,
    participantRole: 'caller' | 'callee',
    apiBaseUrl: string,
): string {
    const apiBase = trimTrailingSlash(String(apiBaseUrl || '').trim());
    if (!apiBase || !/^https:\/\//i.test(apiBase)) {
        return signalingUrl;
    }
    try {
        const parsed = new URL(signalingUrl);
        if (!hostIsPrivateOrLoopback(parsed.hostname)) {
            return signalingUrl;
        }
        const apiParsed = new URL(apiBase);
        const path = `${parsed.pathname}${parsed.search}`;
        const withRole = path.includes('role=')
            ? path
            : `${path}${path.includes('?') ? '&' : '?'}role=${participantRole}`;
        return `wss://${apiParsed.host}${withRole}`;
    } catch {
        return signalingUrl;
    }
}

export function resolveVoipSignalingServerUrl(
    signalingServer: string | undefined,
    participantRole: 'caller' | 'callee',
    apiBaseUrl: string,
): string {
    const raw = String(signalingServer || '').trim();
    if (!raw) {
        throw new Error('VoIP signaling server URL is missing');
    }

    if (/^wss?:\/\//i.test(raw)) {
        return rewritePrivateSignalingToApiBase(raw, participantRole, apiBaseUrl);
    }

    const base = trimTrailingSlash(String(apiBaseUrl || '').trim());
    if (!base) {
        throw new Error('API base URL is missing for VoIP signaling resolution');
    }

    const path = raw.startsWith('/') ? raw : `/${raw}`;
    const httpBase = base.replace(/^wss:/i, 'https:').replace(/^ws:/i, 'http:');
    const absoluteHttp = `${httpBase}${path}`;
    const withRole = absoluteHttp.includes('role=')
        ? absoluteHttp
        : `${absoluteHttp}${absoluteHttp.includes('?') ? '&' : '?'}role=${participantRole}`;

    return withRole.replace(/^http:/i, 'ws:').replace(/^https:/i, 'wss:');
}

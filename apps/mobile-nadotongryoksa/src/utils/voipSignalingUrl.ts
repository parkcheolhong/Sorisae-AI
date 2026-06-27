const trimTrailingSlash = (value: string): string => value.replace(/\/+$/, '');

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
        return raw;
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

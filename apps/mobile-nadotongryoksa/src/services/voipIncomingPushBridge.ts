import type { CallInitResponse } from './voipCallClient';

const DEFAULT_STUN_SERVERS = [
    { urls: ['stun:stun.l.google.com:19302'] },
    { urls: ['stun:stun1.l.google.com:19302'] },
    { urls: ['stun:stun.cloudflare.com:3478'] },
];

function parseJsonField<T>(value: unknown, fallback: T): T {
    if (value == null || value === '') {
        return fallback;
    }
    if (typeof value === 'object') {
        return value as T;
    }
    try {
        return JSON.parse(String(value)) as T;
    } catch {
        return fallback;
    }
}

function parseBooleanField(value: unknown): boolean | undefined {
    if (value === true || value === 'true' || value === '1') {
        return true;
    }
    if (value === false || value === 'false' || value === '0') {
        return false;
    }
    return undefined;
}

/** FCM data payload → partial CallInitResponse for callee incoming UI. */
export function parseIncomingCallFcmData(
    data: Record<string, unknown> | undefined | null,
): (CallInitResponse & { caller_label?: string; caller_voice_id?: string }) | null {
    if (!data) {
        return null;
    }
    const type = String(data.type ?? '');
    if (type !== 'incoming_call') {
        return null;
    }
    const callId = String(data.call_id ?? '').trim();
    const signalingServer = String(data.signaling_server ?? '').trim();
    if (!callId || !signalingServer) {
        if (!callId) {
            return null;
        }
        return {
            call_id: callId,
            signaling_server: '',
            turn_servers: DEFAULT_STUN_SERVERS,
            call_route: 'app_webrtc',
            participant_role: 'callee',
            status: 'ringing',
            caller_label: String(data.caller_label ?? data.display_label ?? ''),
        };
    }

    return {
        call_id: callId,
        signaling_server: signalingServer,
        turn_servers: parseJsonField(data.turn_servers, DEFAULT_STUN_SERVERS),
        call_route: String(data.call_route ?? 'app_webrtc'),
        callee_app_online: parseBooleanField(data.callee_app_online),
        caller_voice_id: data.caller_voice_id ? String(data.caller_voice_id) : undefined,
        callee_voice_id: data.callee_voice_id ? String(data.callee_voice_id) : undefined,
        participant_role: 'callee',
        display_label: data.display_label ? String(data.display_label) : undefined,
        display_language: data.display_language ? String(data.display_language) : undefined,
        display_country_code: data.display_country_code ? String(data.display_country_code) : undefined,
        status: data.status ? String(data.status) : 'ringing',
        requested_mode: data.requested_mode ? String(data.requested_mode) : undefined,
        resolved_mode: data.resolved_mode ? String(data.resolved_mode) : undefined,
        caller_label: String(data.caller_label ?? data.display_label ?? ''),
    };
}

export function shouldPersistIncomingFcmData(data: Record<string, unknown> | undefined | null): boolean {
    return String(data?.type ?? '') === 'incoming_call' && Boolean(String(data?.call_id ?? '').trim());
}

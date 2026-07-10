export const INCOMING_RING_VOIP_STATUSES = new Set(['ringing', 'initiated']);

export const RESUMABLE_INCOMING_VOIP_STATUSES = new Set([
    'initiated',
    'ringing',
    'callee_offline',
    'connecting',
    'active',
]);

export function isIncomingRingVoipStatus(status?: string | null): boolean {
    return Boolean(status && INCOMING_RING_VOIP_STATUSES.has(status));
}

export function isResumableIncomingVoipStatus(status?: string | null): boolean {
    return Boolean(status && RESUMABLE_INCOMING_VOIP_STATUSES.has(status));
}

export function shouldDeferCalleeResumeToIncomingAccept(
    status?: string | null,
    isStoredAcceptedSession = false,
): boolean {
    if (isStoredAcceptedSession) {
        return false;
    }
    return isIncomingRingVoipStatus(status) || status === 'callee_offline';
}

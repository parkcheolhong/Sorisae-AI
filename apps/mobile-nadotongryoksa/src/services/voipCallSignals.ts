type VoipCallEndedListener = (callId: string) => void;

const voipCallEndedListeners = new Set<VoipCallEndedListener>();

export function emitVoipCallEnded(callId: string): void {
    const normalizedCallId = String(callId || '').trim();
    if (!normalizedCallId) {
        return;
    }
    for (const listener of voipCallEndedListeners) {
        try {
            listener(normalizedCallId);
        } catch {
            // no-op
        }
    }
}

export function subscribeVoipCallEnded(listener: VoipCallEndedListener): () => void {
    voipCallEndedListeners.add(listener);
    return () => {
        voipCallEndedListeners.delete(listener);
    };
}
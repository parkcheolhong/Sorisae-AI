export type VoiceRelayParticipantRole = 'caller' | 'callee';

export type VoiceRelayTurnSnapshot = {
    lastRemoteRelayAtMs: number;
    lastLocalRelayAtMs: number;
    remoteListenUntilMs: number;
    remotePlaybackUntilMs: number;
};

export const VOICE_RELAY_TURN_DEFAULTS = {
    /** Minimum post-playback guard before local mic capture resumes (echo avoidance). */
    remoteListenHoldMs: 2_500,
    /** Extra tail after estimated TTS playback before reopening the mic. */
    postPlaybackGuardMs: 700,
    playbackCharMs: 45,
    playbackMinMs: 2_800,
    playbackMaxMs: 5_500,
    speechMeterMinDb: -52,
} as const;

export function createInitialVoiceRelayTurnSnapshot(nowMs: number = Date.now()): VoiceRelayTurnSnapshot {
    return {
        lastRemoteRelayAtMs: 0,
        lastLocalRelayAtMs: 0,
        remoteListenUntilMs: 0,
        remotePlaybackUntilMs: 0,
    };
}

export function normalizeLangCode(value: string): string {
    return String(value || '').trim().toLowerCase().split('-')[0];
}

/** Map STT-detected speech to the correct outbound relay language pair. */
export function resolveVoiceRelayLanguagePair(
    localSourceLang: string,
    localTargetLang: string,
    detectedLang: string,
): { sourceLang: string; targetLang: string } {
    const source = normalizeLangCode(localSourceLang);
    const target = normalizeLangCode(localTargetLang);
    const detected = normalizeLangCode(detectedLang) || source;

    if (detected === source) {
        return { sourceLang: source, targetLang: target };
    }
    if (detected === target) {
        return { sourceLang: target, targetLang: source };
    }
    return { sourceLang: detected, targetLang: target };
}

export function estimateVoiceRelayPlaybackMs(translatedText: string, speakerOn: boolean): number {
    const cappedLen = Math.min(translatedText.trim().length, 96);
    const estimated = Math.max(
        VOICE_RELAY_TURN_DEFAULTS.playbackMinMs,
        cappedLen * VOICE_RELAY_TURN_DEFAULTS.playbackCharMs,
    );
    const speakerBoost = speakerOn ? 900 : 0;
    return Math.min(VOICE_RELAY_TURN_DEFAULTS.playbackMaxMs + speakerBoost, estimated + speakerBoost);
}

export function applyRemoteRelayTurn(params: {
    turn: VoiceRelayTurnSnapshot;
    nowMs: number;
    translatedText: string;
    speakerOn: boolean;
}): VoiceRelayTurnSnapshot {
    const playbackMs = estimateVoiceRelayPlaybackMs(params.translatedText, params.speakerOn);
    const listenUntilMs = params.nowMs + Math.max(
        VOICE_RELAY_TURN_DEFAULTS.remoteListenHoldMs,
        playbackMs + VOICE_RELAY_TURN_DEFAULTS.postPlaybackGuardMs,
    );
    return {
        ...params.turn,
        lastRemoteRelayAtMs: params.nowMs,
        remoteListenUntilMs: listenUntilMs,
        remotePlaybackUntilMs: params.nowMs + playbackMs,
    };
}

/** After local relay send: hold mic until peer finishes listening/TTS window. */
export function applyLocalRelayTurn(params: {
    turn: VoiceRelayTurnSnapshot;
    nowMs: number;
    translatedText: string;
}): VoiceRelayTurnSnapshot {
    const waitMs = Math.max(
        VOICE_RELAY_TURN_DEFAULTS.remoteListenHoldMs,
        estimateVoiceRelayPlaybackMs(params.translatedText, false)
            + VOICE_RELAY_TURN_DEFAULTS.postPlaybackGuardMs,
    );
    return {
        ...params.turn,
        lastLocalRelayAtMs: params.nowMs,
        remoteListenUntilMs: params.nowMs + waitMs,
        remotePlaybackUntilMs: params.nowMs,
    };
}

export function markRemotePlaybackFinished(
    turn: VoiceRelayTurnSnapshot,
    nowMs: number = Date.now(),
): VoiceRelayTurnSnapshot {
    return {
        ...turn,
        remotePlaybackUntilMs: Math.min(turn.remotePlaybackUntilMs, nowMs),
    };
}

export function isVoiceRelayListenActive(turn: VoiceRelayTurnSnapshot, nowMs: number = Date.now()): boolean {
    return nowMs < turn.remoteListenUntilMs || nowMs < turn.remotePlaybackUntilMs;
}

export function shouldStartVoiceRelayCapture(params: {
    participantRole: VoiceRelayParticipantRole;
    turn: VoiceRelayTurnSnapshot;
    nowMs?: number;
}): { allowed: boolean; reason?: string } {
    const nowMs = params.nowMs ?? Date.now();
    if (isVoiceRelayListenActive(params.turn, nowMs)) {
        return { allowed: false, reason: 'remote_listen_active' };
    }
    return { allowed: true };
}

export function shouldDeferVoiceRelayFlush(params: {
    participantRole: VoiceRelayParticipantRole;
    turn: VoiceRelayTurnSnapshot;
    reason: string;
    meterUnavailable: boolean;
    flushHadSpeech: boolean;
    hasRemoteAudio: boolean;
    remoteAudioSuppressed?: boolean;
    nowMs?: number;
}): { defer: boolean; skipReason?: string } {
    if (params.reason !== 'fixed_interval') {
        return { defer: false };
    }

    const nowMs = params.nowMs ?? Date.now();
    if (isVoiceRelayListenActive(params.turn, nowMs)) {
        return { defer: true, skipReason: 'remote_listen_active' };
    }

    if (!params.meterUnavailable || params.flushHadSpeech) {
        return { defer: false };
    }

    // Callee: defer timer flush while listening to remote TTS (Android metering dead).
    if (params.participantRole === 'callee') {
        if (isVoiceRelayListenActive(params.turn, nowMs)) {
            return { defer: true, skipReason: 'callee_remote_listen_active' };
        }
        return { defer: false };
    }

    const remoteQuietMs = params.turn.lastRemoteRelayAtMs > 0
        ? nowMs - params.turn.lastRemoteRelayAtMs
        : Number.POSITIVE_INFINITY;

    // Caller first turn: defer only while live WebRTC is still routed to the speaker.
    // During relay capture we mute remote WebRTC, so timer flush can proceed safely.
    if (
        params.turn.lastRemoteRelayAtMs === 0
        && params.hasRemoteAudio
        && !params.remoteAudioSuppressed
    ) {
        return { defer: true, skipReason: 'caller_hearing_remote_webrtc' };
    }

    // Caller reply turn: only after callee relay finished and listen hold elapsed.
    if (
        params.turn.lastRemoteRelayAtMs > 0
        && remoteQuietMs < VOICE_RELAY_TURN_DEFAULTS.remoteListenHoldMs
    ) {
        return { defer: true, skipReason: 'caller_waiting_callee_turn' };
    }

    return { defer: false };
}

export function shouldSendVoiceRelaySegment(params: {
    participantRole: VoiceRelayParticipantRole;
    turn: VoiceRelayTurnSnapshot;
    meterUnavailable: boolean;
    flushHadSpeech: boolean;
    flushReason: string | null;
    peakMeterDb: number;
    hasRemoteAudio: boolean;
    remoteAudioSuppressed?: boolean;
    nowMs?: number;
}): { allowed: boolean; reason?: string } {
    const nowMs = params.nowMs ?? Date.now();
    if (isVoiceRelayListenActive(params.turn, nowMs)) {
        return { allowed: false, reason: 'remote_listen_active' };
    }

    // Captured segment is ready for STT — do not re-apply pre-flush defer gates
    // (caller_hearing_remote_webrtc fires after WebRTC mic restore in stopVoiceRelaySegment).
    const timedFlush = params.flushReason === 'fixed_interval' || params.flushReason === 'max_duration';
    const bypassSpeechMeterGate = params.meterUnavailable
        && params.flushHadSpeech
        && (
            timedFlush
            || params.peakMeterDb <= -159
        );

    if (!bypassSpeechMeterGate && !timedFlush && params.peakMeterDb < VOICE_RELAY_TURN_DEFAULTS.speechMeterMinDb) {
        return { allowed: false, reason: 'low_speech_meter' };
    }

    return { allowed: true };
}

/** Receiver plays TTS when the relay target matches either side of their local language pair. */
export function shouldPlayRemoteVoiceRelay(params: {
    participantRole: VoiceRelayParticipantRole;
    fromRole: VoiceRelayParticipantRole;
    relaySourceLang: string;
    relayTargetLang: string;
    localSourceLang: string;
    localTargetLang: string;
}): { allowed: boolean; reason?: string } {
    const relayTarget = normalizeLangCode(params.relayTargetLang);
    const localSource = normalizeLangCode(params.localSourceLang);
    const localTarget = normalizeLangCode(params.localTargetLang);
    const matchesReceiverLang = relayTarget === localSource || relayTarget === localTarget;
    if (!matchesReceiverLang) {
        return { allowed: false, reason: 'target_lang_mismatch' };
    }

    if (
        params.participantRole === 'callee'
        && params.fromRole === 'caller'
        && normalizeLangCode(params.relaySourceLang) === localSource
        && relayTarget === localSource
    ) {
        return { allowed: false, reason: 'caller_echo_in_callee_language' };
    }

    return { allowed: true };
}

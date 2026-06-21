export type VoiceRelayParticipantRole = 'caller' | 'callee';

export type VoiceRelayTurnSnapshot = {
    lastRemoteRelayAtMs: number;
    lastLocalRelayAtMs: number;
    remoteListenUntilMs: number;
    remotePlaybackUntilMs: number;
};

export const VOICE_RELAY_TURN_DEFAULTS = {
    /** Minimum post-playback guard before local mic capture resumes (echo avoidance).
     *  (G1 정합) SSOT(worldlinco_tuning_config.json voip.remote_listen_hold_ms=2600)와 동일. */
    remoteListenHoldMs: 2_600,
    /** Extra tail after estimated TTS playback before reopening the mic. */
    postPlaybackGuardMs: 550,
    playbackCharMs: 38,
    playbackMinMs: 1_800,
    playbackMaxMs: 4_800,
    speechMeterMinDb: -52,
    /** 굶김 방지(공정성 캡): 로컬이 이 시간 이상 연속으로 턴을 못 잡으면(상대 연속 발화가
     *  listen-hold 를 계속 갱신) 캡처를 강제 허용한다. 단, **활성 재생 중에는 절대 적용 안 함**
     *  (자기 TTS 재캡처 방지) — 재생 종료 후의 courtesy listen-hold 만 푼다. 0 이면 비활성. */
    fairnessBargeInMs: 7_000,
} as const;

export function createInitialVoiceRelayTurnSnapshot(nowMs: number = Date.now()): VoiceRelayTurnSnapshot {
    return {
        lastRemoteRelayAtMs: 0,
        // 굶김 시계 기준점 = 통화 시작. (0 이면 즉시 무한 굶김으로 오인되어 첫 listen-hold 를
        //  공정성 캡이 잘못 풀 수 있으므로 nowMs 로 초기화.)
        lastLocalRelayAtMs: nowMs,
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

/** Short re-arm guard after a local send so the recorder can reset cleanly. */
export const VOICE_RELAY_LOCAL_SEND_REARM_MS = 300;

/**
 * After a local relay send, do NOT lock the mic for the peer's estimated TTS
 * playback. A single speaker often continues with the next phrase immediately;
 * the old long hold (playback estimate, ~2.3s) dropped those follow-on phrases
 * entirely ("only the first phrase is delivered, later phrases can't sync").
 * The real turn switch happens when a remote relay actually arrives
 * (applyRemoteRelayTurn). Here we keep only a brief re-arm guard so the local
 * speaker can keep talking with minimal gap.
 */
export function applyLocalRelayTurn(params: {
    turn: VoiceRelayTurnSnapshot;
    nowMs: number;
    translatedText: string;
}): VoiceRelayTurnSnapshot {
    return {
        ...params.turn,
        lastLocalRelayAtMs: params.nowMs,
        remoteListenUntilMs: params.nowMs + VOICE_RELAY_LOCAL_SEND_REARM_MS,
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

/**
 * Remote TTS queue fully drained (no more pending relay playback): release the
 * extended listen hold down to a short echo guard so the local mic can reclaim
 * its turn promptly. Prevents the "one side talks, the other only listens"
 * deadlock where each received relay keeps renewing remoteListenUntilMs.
 * The independent echo-suppression window (voiceRelaySuppressUntilRef) still
 * guards against TTS tail bleeding back into the mic.
 */
export function markRemotePlaybackDrained(
    turn: VoiceRelayTurnSnapshot,
    nowMs: number = Date.now(),
    guardMs: number = VOICE_RELAY_TURN_DEFAULTS.postPlaybackGuardMs,
): VoiceRelayTurnSnapshot {
    const releasedUntil = nowMs + Math.max(0, guardMs);
    return {
        ...turn,
        remotePlaybackUntilMs: Math.min(turn.remotePlaybackUntilMs, nowMs),
        remoteListenUntilMs: Math.min(turn.remoteListenUntilMs, releasedUntil),
    };
}

export function isVoiceRelayListenActive(turn: VoiceRelayTurnSnapshot, nowMs: number = Date.now()): boolean {
    return nowMs < turn.remoteListenUntilMs || nowMs < turn.remotePlaybackUntilMs;
}

export function shouldStartVoiceRelayCapture(params: {
    participantRole: VoiceRelayParticipantRole;
    turn: VoiceRelayTurnSnapshot;
    fairnessBargeInMs?: number;
    nowMs?: number;
}): { allowed: boolean; reason?: string; bargeIn?: boolean; starvedMs?: number } {
    const nowMs = params.nowMs ?? Date.now();
    if (isVoiceRelayListenActive(params.turn, nowMs)) {
        // 공정성 캡(굶김 방지): 상대가 쉼 없이 발화해 listen-hold 가 계속 갱신되면 로컬이
        // 영원히 턴을 못 잡는다. 일정 시간 굶주리면 캡처를 강제 허용한다.
        // 단, ① 활성 재생 중(remotePlaybackUntilMs)에는 절대 적용하지 않는다(자기 TTS 재캡처/에코 방지).
        //     ② 에코 억제창·remote_tts_active 게이트는 상위(VoIPCallScreen)에서 별도로 막으므로
        //        여기서 푸는 건 '재생 종료 후의 courtesy listen-hold' 뿐이다.
        const cap = params.fairnessBargeInMs ?? VOICE_RELAY_TURN_DEFAULTS.fairnessBargeInMs;
        const playbackActive = nowMs < params.turn.remotePlaybackUntilMs;
        const starvedMs = nowMs - params.turn.lastLocalRelayAtMs;
        if (cap > 0 && !playbackActive && starvedMs >= cap) {
            return { allowed: true, bargeIn: true, starvedMs };
        }
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
    // A device plays ONLY relays translated into its own user's language
    // (localSourceLang = my preferred language). Relays translated into the
    // peer's language (localTargetLang) are meant for the peer, not for me —
    // playing them caused cross-play/echo, especially in bilingual mode where
    // both devices share the same language pair (e.g. same-room ko/ja pickup).
    if (relayTarget !== localSource) {
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

/** Generous window for dropping retransmits of the SAME utterance id. */
export const VOICE_RELAY_REMOTE_UTTERANCE_DEDUPE_MS = 15_000;
/** Window for dropping text-identical relays when no stable utterance id exists. */
export const VOICE_RELAY_REMOTE_TEXT_DEDUPE_MS = 8_000;

export type RemoteRelayDedupeRecord = {
    utteranceKey: string;
    textKey: string;
    atMs: number;
};

export function buildRemoteRelayDedupeKeys(params: {
    utteranceId?: string | null;
    chunkIndex?: number | null;
    normalizedTranscript: string;
    normalizedTranslated: string;
    targetLang: string;
}): { utteranceKey: string; textKey: string } {
    const utteranceId = String(params.utteranceId || '').trim();
    const utteranceKey = utteranceId
        ? `${utteranceId}#${Number.isFinite(params.chunkIndex as number) ? params.chunkIndex : 0}`
        : '';
    const textKey = `${params.normalizedTranscript}::${params.normalizedTranslated}::${normalizeLangCode(params.targetLang)}`;
    return { utteranceKey, textKey };
}

/**
 * Robust duplicate suppression for inbound relay playback. A single spoken
 * utterance must be delivered exactly once even when the sender retransmits,
 * the socket replays on reconnect, or STT text varies slightly between copies.
 * - Stable utterance id match -> drop within a generous window.
 * - Otherwise text-identical relay -> drop within a window that covers the
 *   full TTS playback span (so a late duplicate after playback is still caught).
 */
export function shouldDedupeRemoteVoiceRelay(params: {
    keys: { utteranceKey: string; textKey: string };
    previous: RemoteRelayDedupeRecord | null;
    nowMs: number;
    utteranceWindowMs?: number;
    textWindowMs?: number;
}): { dedupe: boolean; reason?: string } {
    const prev = params.previous;
    if (!prev) {
        return { dedupe: false };
    }
    const utteranceWindow = params.utteranceWindowMs ?? VOICE_RELAY_REMOTE_UTTERANCE_DEDUPE_MS;
    const textWindow = params.textWindowMs ?? VOICE_RELAY_REMOTE_TEXT_DEDUPE_MS;
    if (
        params.keys.utteranceKey
        && prev.utteranceKey === params.keys.utteranceKey
        && params.nowMs - prev.atMs < utteranceWindow
    ) {
        return { dedupe: true, reason: 'remote_relay_dedupe_utterance' };
    }
    if (
        params.keys.textKey
        && prev.textKey === params.keys.textKey
        && params.nowMs - prev.atMs < textWindow
    ) {
        return { dedupe: true, reason: 'remote_relay_dedupe_text' };
    }
    return { dedupe: false };
}

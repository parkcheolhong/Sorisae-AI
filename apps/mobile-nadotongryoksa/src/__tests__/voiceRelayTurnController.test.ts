import {
    applyLocalRelayTurn,
    applyRemoteRelayTurn,
    buildRemoteRelayDedupeKeys,
    createInitialVoiceRelayTurnSnapshot,
    markRemotePlaybackDrained,
    resolveVoiceRelayLanguagePair,
    shouldDedupeRemoteVoiceRelay,
    shouldDeferVoiceRelayFlush,
    shouldPlayRemoteVoiceRelay,
    shouldSendVoiceRelaySegment,
    shouldStartVoiceRelayCapture,
    VOICE_RELAY_LOCAL_SEND_REARM_MS,
    VOICE_RELAY_TURN_DEFAULTS,
    type RemoteRelayDedupeRecord,
} from '../features/voip-voice-relay/voiceRelayTurnController';

describe('voiceRelayTurnController', () => {
    it('resolves relay pair when speaker uses the remote language', () => {
        expect(resolveVoiceRelayLanguagePair('en', 'ko', 'ko')).toEqual({
            sourceLang: 'ko',
            targetLang: 'en',
        });
    });

    it('keeps relay pair when speaker uses their own language', () => {
        expect(resolveVoiceRelayLanguagePair('en', 'ko', 'en')).toEqual({
            sourceLang: 'en',
            targetLang: 'ko',
        });
    });

    it('keeps ja to ko relay when callee speaks Japanese', () => {
        expect(resolveVoiceRelayLanguagePair('ja', 'ko', 'ja')).toEqual({
            sourceLang: 'ja',
            targetLang: 'ko',
        });
    });

    it('blocks caller timer flush while hearing remote WebRTC before any callee relay', () => {
        const turn = createInitialVoiceRelayTurnSnapshot();
        const result = shouldDeferVoiceRelayFlush({
            participantRole: 'caller',
            turn,
            reason: 'fixed_interval',
            meterUnavailable: true,
            flushHadSpeech: false,
            hasRemoteAudio: true,
            nowMs: 10_000,
        });
        expect(result.defer).toBe(true);
        expect(result.skipReason).toBe('caller_hearing_remote_webrtc');
    });

    it('allows caller timer flush when remote WebRTC is suppressed for relay capture', () => {
        const turn = createInitialVoiceRelayTurnSnapshot();
        const result = shouldDeferVoiceRelayFlush({
            participantRole: 'caller',
            turn,
            reason: 'fixed_interval',
            meterUnavailable: true,
            flushHadSpeech: false,
            hasRemoteAudio: true,
            remoteAudioSuppressed: true,
            nowMs: 10_000,
        });
        expect(result.defer).toBe(false);
    });

    it('allows callee timer flush when Android metering is unavailable', () => {
        const turn = createInitialVoiceRelayTurnSnapshot();
        const result = shouldDeferVoiceRelayFlush({
            participantRole: 'callee',
            turn,
            reason: 'fixed_interval',
            meterUnavailable: true,
            flushHadSpeech: false,
            hasRemoteAudio: true,
            nowMs: 10_000,
        });
        expect(result.defer).toBe(false);
    });

    it('defers callee timer flush right after remote relay playback', () => {
        const turn = applyRemoteRelayTurn({
            turn: createInitialVoiceRelayTurnSnapshot(),
            nowMs: 10_000,
            translatedText: 'Hello there',
            speakerOn: false,
        });
        const result = shouldDeferVoiceRelayFlush({
            participantRole: 'callee',
            turn,
            reason: 'fixed_interval',
            meterUnavailable: true,
            flushHadSpeech: false,
            hasRemoteAudio: true,
            nowMs: 11_000,
        });
        expect(result.defer).toBe(true);
    });

    it('lets the same speaker resume quickly after a local send (no long mic lock)', () => {
        const turn = applyLocalRelayTurn({
            turn: applyRemoteRelayTurn({
                turn: createInitialVoiceRelayTurnSnapshot(),
                nowMs: 5_000,
                translatedText: 'Earlier remote',
                speakerOn: false,
            }),
            nowMs: 10_000,
            translatedText: 'Hello, testing.',
        });
        expect(turn.lastRemoteRelayAtMs).toBe(5_000);
        expect(turn.lastLocalRelayAtMs).toBe(10_000);
        // Only a brief re-arm guard — the next phrase of the same speaker is not dropped.
        expect(shouldStartVoiceRelayCapture({
            participantRole: 'caller',
            turn,
            nowMs: 10_000 + VOICE_RELAY_LOCAL_SEND_REARM_MS - 100,
        }).allowed).toBe(false);
        expect(shouldStartVoiceRelayCapture({
            participantRole: 'caller',
            turn,
            nowMs: 10_000 + VOICE_RELAY_LOCAL_SEND_REARM_MS + 100,
        }).allowed).toBe(true);
    });

    it('allows timed send when Android metering is unavailable even without speech flags', () => {
        const turn = createInitialVoiceRelayTurnSnapshot();
        const result = shouldSendVoiceRelaySegment({
            participantRole: 'callee',
            turn,
            meterUnavailable: true,
            flushHadSpeech: false,
            flushReason: 'fixed_interval',
            peakMeterDb: -160,
            hasRemoteAudio: true,
            nowMs: 10_000,
        });
        expect(result.allowed).toBe(true);
    });

    it('blocks capture and send during remote listen window', () => {
        const turn = applyRemoteRelayTurn({
            turn: createInitialVoiceRelayTurnSnapshot(),
            nowMs: 10_000,
            translatedText: 'Hello there',
            speakerOn: true,
        });
        expect(shouldStartVoiceRelayCapture({ participantRole: 'callee', turn, nowMs: 11_000 }).allowed).toBe(false);
        expect(shouldDeferVoiceRelayFlush({
            participantRole: 'callee',
            turn,
            reason: 'fixed_interval',
            meterUnavailable: true,
            flushHadSpeech: false,
            hasRemoteAudio: true,
            nowMs: 11_000,
        }).defer).toBe(true);
        expect(shouldSendVoiceRelaySegment({
            participantRole: 'callee',
            turn,
            meterUnavailable: true,
            flushHadSpeech: false,
            flushReason: 'fixed_interval',
            peakMeterDb: -160,
            hasRemoteAudio: true,
            nowMs: 11_000,
        }).allowed).toBe(false);
    });

    it('allows send after capture even when caller hears remote WebRTC (post-restore)', () => {
        const turn = createInitialVoiceRelayTurnSnapshot();
        const result = shouldSendVoiceRelaySegment({
            participantRole: 'caller',
            turn,
            meterUnavailable: true,
            flushHadSpeech: false,
            flushReason: 'fixed_interval',
            peakMeterDb: -160,
            hasRemoteAudio: true,
            remoteAudioSuppressed: false,
            nowMs: 10_000,
        });
        expect(result.allowed).toBe(true);
    });

    it('allows caller send after callee turn and listen hold', () => {
        const turn = applyRemoteRelayTurn({
            turn: createInitialVoiceRelayTurnSnapshot(),
            nowMs: 10_000,
            translatedText: 'Hello',
            speakerOn: false,
        });
        const result = shouldSendVoiceRelaySegment({
            participantRole: 'caller',
            turn,
            meterUnavailable: true,
            flushHadSpeech: true,
            flushReason: 'fixed_interval',
            peakMeterDb: -160,
            hasRemoteAudio: true,
            nowMs: 20_000,
        });
        expect(result.allowed).toBe(true);
    });

    it('blocks callee playback of caller-echoed Korean identity relay only', () => {
        const playback = shouldPlayRemoteVoiceRelay({
            participantRole: 'callee',
            fromRole: 'caller',
            relaySourceLang: 'ko',
            relayTargetLang: 'ko',
            localSourceLang: 'ko',
            localTargetLang: 'en',
        });
        expect(playback.allowed).toBe(false);
        expect(playback.reason).toBe('caller_echo_in_callee_language');
    });

    it('blocks playback of a relay translated into the peer language (not my own)', () => {
        // A Korean user (localSourceLang=ko) must only hear Korean. A ko→en relay
        // is meant for the English-side peer, so this device must NOT play it.
        // (Prevents cross-play/echo when both devices share the same language pair.)
        const playback = shouldPlayRemoteVoiceRelay({
            participantRole: 'callee',
            fromRole: 'caller',
            relaySourceLang: 'ko',
            relayTargetLang: 'en',
            localSourceLang: 'ko',
            localTargetLang: 'en',
        });
        expect(playback.allowed).toBe(false);
        expect(playback.reason).toBe('target_lang_mismatch');
    });

    it('blocks the receiver from playing a relay into the peer language for a ko/ja pair', () => {
        // Live regression: S10 (my lang ko, peer ja) must not play a ko→ja relay.
        const playback = shouldPlayRemoteVoiceRelay({
            participantRole: 'callee',
            fromRole: 'caller',
            relaySourceLang: 'ko',
            relayTargetLang: 'ja',
            localSourceLang: 'ko',
            localTargetLang: 'ja',
        });
        expect(playback.allowed).toBe(false);
        expect(playback.reason).toBe('target_lang_mismatch');
    });

    it('allows tab playback of callee Korean to English relay', () => {
        const playback = shouldPlayRemoteVoiceRelay({
            participantRole: 'caller',
            fromRole: 'callee',
            relaySourceLang: 'ko',
            relayTargetLang: 'en',
            localSourceLang: 'en',
            localTargetLang: 'ko',
        });
        expect(playback.allowed).toBe(true);
    });

    it('blocks playback when relay target matches neither local language', () => {
        const playback = shouldPlayRemoteVoiceRelay({
            participantRole: 'caller',
            fromRole: 'callee',
            relaySourceLang: 'ko',
            relayTargetLang: 'ja',
            localSourceLang: 'ko',
            localTargetLang: 'en',
        });
        expect(playback.allowed).toBe(false);
        expect(playback.reason).toBe('target_lang_mismatch');
    });

    it('releases the listen hold when the playback queue drains so the mic can reclaim its turn', () => {
        const turn = applyRemoteRelayTurn({
            turn: createInitialVoiceRelayTurnSnapshot(),
            nowMs: 10_000,
            translatedText: 'A fairly long sentence that holds the floor for a while.',
            speakerOn: true,
        });
        // Without draining, the listen window extends well past playback end.
        expect(turn.remoteListenUntilMs).toBeGreaterThan(13_000);
        const drained = markRemotePlaybackDrained(turn, 12_500);
        expect(drained.remoteListenUntilMs).toBe(12_500 + VOICE_RELAY_TURN_DEFAULTS.postPlaybackGuardMs);
        expect(shouldStartVoiceRelayCapture({
            participantRole: 'callee',
            turn: drained,
            nowMs: 12_500 + VOICE_RELAY_TURN_DEFAULTS.postPlaybackGuardMs + 1,
        }).allowed).toBe(true);
    });

    it('never extends the listen window when draining', () => {
        const turn = applyRemoteRelayTurn({
            turn: createInitialVoiceRelayTurnSnapshot(),
            nowMs: 10_000,
            translatedText: 'Hi',
            speakerOn: false,
        });
        // Draining far in the future must not push the (earlier) listen window out.
        const drained = markRemotePlaybackDrained(turn, 50_000);
        expect(drained.remoteListenUntilMs).toBe(turn.remoteListenUntilMs);
    });

    it('fairness cap: barges in after starvation but never during active playback', () => {
        // Continuous remote speech keeps renewing the listen hold; local last sent at t=0.
        const starvedTurn = {
            lastRemoteRelayAtMs: 8_000,
            lastLocalRelayAtMs: 0,
            remoteListenUntilMs: 12_000, // courtesy hold still active
            remotePlaybackUntilMs: 8_500, // active playback ends at 8_500
        };
        // During ACTIVE playback (now < remotePlaybackUntilMs): must NOT barge in (echo guard).
        const duringPlayback = shouldStartVoiceRelayCapture({
            participantRole: 'callee',
            turn: starvedTurn,
            fairnessBargeInMs: 7_000,
            nowMs: 8_400,
        });
        expect(duringPlayback.allowed).toBe(false);
        expect(duringPlayback.bargeIn).toBeFalsy();

        // After playback ends, hold still active, starved >= cap: barge in to reclaim turn.
        const afterStarve = shouldStartVoiceRelayCapture({
            participantRole: 'callee',
            turn: starvedTurn,
            fairnessBargeInMs: 7_000,
            nowMs: 9_000,
        });
        expect(afterStarve.allowed).toBe(true);
        expect(afterStarve.bargeIn).toBe(true);

        // Not yet starved past the (larger) cap: keep waiting.
        const notStarvedYet = shouldStartVoiceRelayCapture({
            participantRole: 'callee',
            turn: starvedTurn,
            fairnessBargeInMs: 20_000,
            nowMs: 9_000,
        });
        expect(notStarvedYet.allowed).toBe(false);

        // Disabled (cap = 0): never barges in.
        const disabled = shouldStartVoiceRelayCapture({
            participantRole: 'callee',
            turn: starvedTurn,
            fairnessBargeInMs: 0,
            nowMs: 9_000,
        });
        expect(disabled.allowed).toBe(false);
    });
});

describe('shouldDedupeRemoteVoiceRelay', () => {
    const keysFor = (utteranceId: string | null, transcript: string, translated: string) =>
        buildRemoteRelayDedupeKeys({
            utteranceId,
            chunkIndex: 0,
            normalizedTranscript: transcript,
            normalizedTranslated: translated,
            targetLang: 'ko',
        });

    const recordFor = (
        utteranceId: string | null,
        transcript: string,
        translated: string,
        atMs: number,
    ): RemoteRelayDedupeRecord => {
        const keys = keysFor(utteranceId, transcript, translated);
        return { utteranceKey: keys.utteranceKey, textKey: keys.textKey, atMs };
    };

    it('does not dedupe the first relay', () => {
        expect(shouldDedupeRemoteVoiceRelay({
            keys: keysFor('utt-1', 'hello', '안녕'),
            previous: null,
            nowMs: 1_000,
        }).dedupe).toBe(false);
    });

    it('drops a retransmit of the same utterance id even if STT text differs', () => {
        const previous = recordFor('utt-1', 'hello there', '안녕하세요', 1_000);
        const decision = shouldDedupeRemoteVoiceRelay({
            keys: keysFor('utt-1', 'hello their', '안녕 하세요'),
            previous,
            nowMs: 9_000,
        });
        expect(decision.dedupe).toBe(true);
        expect(decision.reason).toBe('remote_relay_dedupe_utterance');
    });

    it('drops text-identical relays without utterance id within the playback window', () => {
        const previous = recordFor(null, 'hello', '안녕', 1_000);
        const decision = shouldDedupeRemoteVoiceRelay({
            keys: keysFor(null, 'hello', '안녕'),
            previous,
            nowMs: 6_000,
        });
        expect(decision.dedupe).toBe(true);
        expect(decision.reason).toBe('remote_relay_dedupe_text');
    });

    it('allows a distinct next utterance', () => {
        const previous = recordFor('utt-1', 'hello', '안녕', 1_000);
        expect(shouldDedupeRemoteVoiceRelay({
            keys: keysFor('utt-2', 'goodbye', '잘 가'),
            previous,
            nowMs: 2_000,
        }).dedupe).toBe(false);
    });

    it('allows the same text again after the dedupe window elapses', () => {
        const previous = recordFor(null, 'hello', '안녕', 1_000);
        expect(shouldDedupeRemoteVoiceRelay({
            keys: keysFor(null, 'hello', '안녕'),
            previous,
            nowMs: 1_000 + 9_000,
        }).dedupe).toBe(false);
    });
});

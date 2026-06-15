import {
    applyLocalRelayTurn,
    applyRemoteRelayTurn,
    createInitialVoiceRelayTurnSnapshot,
    resolveVoiceRelayLanguagePair,
    shouldDeferVoiceRelayFlush,
    shouldPlayRemoteVoiceRelay,
    shouldSendVoiceRelaySegment,
    shouldStartVoiceRelayCapture,
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

    it('applies local relay turn hold without touching remote relay timestamp', () => {
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
        expect(shouldStartVoiceRelayCapture({ participantRole: 'caller', turn, nowMs: 11_000 }).allowed).toBe(false);
        expect(shouldStartVoiceRelayCapture({ participantRole: 'caller', turn, nowMs: 20_000 }).allowed).toBe(true);
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

    it('allows callee playback of caller Korean to English relay', () => {
        const playback = shouldPlayRemoteVoiceRelay({
            participantRole: 'callee',
            fromRole: 'caller',
            relaySourceLang: 'ko',
            relayTargetLang: 'en',
            localSourceLang: 'ko',
            localTargetLang: 'en',
        });
        expect(playback.allowed).toBe(true);
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
});

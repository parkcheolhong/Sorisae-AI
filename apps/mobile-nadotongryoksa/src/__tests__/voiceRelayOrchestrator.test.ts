import { describe, expect, it } from '@jest/globals';

import {
    collapseRepeatedRelayPhrases,
    createInitialVoiceRelaySegmentState,
    evaluateVoiceRelaySegmentDecision,
    isLikelyGibberishRelayTranscript,
    isLikelyRepetitionHallucination,
    isLikelyVoiceRelayEcho,
    isLikelySilenceHallucination,
    isVoiceRelaySilenceCapture,
    nextVoiceRelaySegmentStateAfterFlush,
    shouldRejectRemoteVoiceRelayPlayback,
    updateVoiceRelaySegmentSpeechState,
    updateVoiceRelaySegmentSpeechStateFromFileRms,
    VOICE_RELAY_VAD_DEFAULTS,
    resolveVoiceRelayFixedFlushDelayMs,
} from '../features/voip-voice-relay/voiceRelayOrchestrator';
import { VoiceRelayPlaybackQueue } from '../features/voip-voice-relay/voiceRelayPlaybackQueue';

describe('voiceRelayOrchestrator', () => {
    it('waits for minimum duration before silence flush', () => {
        const startedAt = 1_000;
        let state = createInitialVoiceRelaySegmentState(startedAt);
        state = updateVoiceRelaySegmentSpeechState(state, -30, startedAt + 400);

        const decision = evaluateVoiceRelaySegmentDecision(
            state,
            startedAt + VOICE_RELAY_VAD_DEFAULTS.minSegmentMs - 1,
            -80,
        );

        expect(decision.action).toBe('continue');
    });

    it('flushes short utterances after silence threshold', () => {
        const startedAt = 2_000;
        let state = createInitialVoiceRelaySegmentState(startedAt);
        state = updateVoiceRelaySegmentSpeechState(state, -30, startedAt + 500);

        const decision = evaluateVoiceRelaySegmentDecision(
            state,
            startedAt + 500 + VOICE_RELAY_VAD_DEFAULTS.silenceFlushMs + VOICE_RELAY_VAD_DEFAULTS.minSegmentMs,
            -80,
        );

        expect(decision).toEqual({
            action: 'flush',
            reason: 'silence',
            isFinal: true,
        });
    });

    it('flushes long utterances in chunks before final silence', () => {
        const startedAt = 3_000;
        let state = createInitialVoiceRelaySegmentState(startedAt);
        state = updateVoiceRelaySegmentSpeechState(state, -30, startedAt + 500);

        const decision = evaluateVoiceRelaySegmentDecision(
            state,
            startedAt + VOICE_RELAY_VAD_DEFAULTS.maxSegmentMs,
            -30,
        );

        expect(decision).toEqual({
            action: 'flush',
            reason: 'max_duration',
            isFinal: false,
        });
    });

    it('ignores max duration flush when no speech was captured', () => {
        const startedAt = 3_000;
        const state = createInitialVoiceRelaySegmentState(startedAt);

        const decision = evaluateVoiceRelaySegmentDecision(
            state,
            startedAt + VOICE_RELAY_VAD_DEFAULTS.maxSegmentMs,
            -160,
        );

        expect(decision.action).toBe('continue');
    });

    it('collapses repeated relay phrases', () => {
        expect(collapseRepeatedRelayPhrases('hello everyone. hello everyone. hello everyone.')).toBe('hello everyone');
        expect(collapseRepeatedRelayPhrases('안녕하세요, 여러분. 안녕하세요, 여러분. 안녕하세요, 여러분.')).toBe('안녕하세요, 여러분');
        expect(collapseRepeatedRelayPhrases(
            Array.from({ length: 6 }, () => '안녕하세요 여러분').join(' '),
        )).toBe('안녕하세요 여러분');
        expect(collapseRepeatedRelayPhrases(
            Array.from({ length: 5 }, () => 'Hello everyone').join(' '),
        )).toBe('Hello everyone');
    });

    it('detects repetition hallucinations from looped playback pickup', () => {
        const repeatedKo = Array.from({ length: 20 }, () => '안녕하세요 여러분').join(' ');
        const repeatedEn = Array.from({ length: 20 }, () => 'Hello everyone').join(' ');
        expect(isLikelyRepetitionHallucination(repeatedKo)).toBe(true);
        expect(isLikelyRepetitionHallucination(repeatedEn)).toBe(true);
        expect(isLikelyRepetitionHallucination('고맙습니다. 땡큐.')).toBe(false);
    });

    it('rejects remote playback when repetition hallucination is detected', () => {
        const repeatedEn = Array.from({ length: 12 }, () => 'Hello everyone').join(' ');
        expect(shouldRejectRemoteVoiceRelayPlayback({
            captureTrust: 'high',
            transcript: repeatedEn,
            translatedText: repeatedEn,
            sourceLang: 'ko',
            targetLang: 'en',
            langScope: ['ko', 'en'],
        }).reason).toBe('repetition_hallucination');
    });

    it('detects common silence hallucinations', () => {
        expect(isLikelySilenceHallucination('You', 'en')).toBe(true);
        expect(isLikelySilenceHallucination('Hello', 'en')).toBe(true);
        expect(isLikelySilenceHallucination('안녕하세요', 'ko')).toBe(true);
        expect(isLikelySilenceHallucination('Hello there', 'en')).toBe(false);
        expect(isVoiceRelaySilenceCapture(true, -160, false)).toBe(true);
    });

    it('rejects Georgian and repeated-symbol Whisper gibberish', () => {
        const georgianSpam = 'ლლლლლლლლლლლლლლლლლლლლლლ: ლლლლლლლლლლლლლლლლლლლლლლ:';
        expect(isLikelyGibberishRelayTranscript(georgianSpam, ['ko', 'en'])).toBe(true);
        expect(isLikelyGibberishRelayTranscript('aaaaBBBB', ['ko', 'en'])).toBe(true);
        expect(isLikelyGibberishRelayTranscript('고맙습니다', ['ko', 'en'])).toBe(false);
        expect(isLikelyGibberishRelayTranscript('Thank you.', ['ko', 'en'])).toBe(false);
    });

    it('detects playback pickup echo for callee send', () => {
        const echo = isLikelyVoiceRelayEcho({
            transcript: 'Now do the test.',
            translatedText: 'Now do the test.',
            nowMs: 10_000,
            recentRemotePlaybackTranslated: 'Now do the test.',
            recentRemotePlaybackAtMs: 9_000,
        });
        expect(echo.echo).toBe(true);
        expect(echo.reason).toBe('playback_pickup_echo');
    });

    it('rejects low-trust remote playback but keeps trusted thanks', () => {
        expect(shouldRejectRemoteVoiceRelayPlayback({
            captureTrust: 'low',
            transcript: '고맙습니다',
            translatedText: 'Thank you.',
            sourceLang: 'ko',
            targetLang: 'en',
            langScope: ['ko', 'en'],
        }).reject).toBe(true);

        expect(shouldRejectRemoteVoiceRelayPlayback({
            captureTrust: 'high',
            transcript: '고맙습니다',
            translatedText: 'Thank you.',
            sourceLang: 'ko',
            targetLang: 'en',
            langScope: ['ko', 'en'],
        }).reject).toBe(false);
    });

    it('marks speech from file RMS when Android metering is dead', () => {
        const startedAt = 2_000;
        const next = updateVoiceRelaySegmentSpeechStateFromFileRms(
            createInitialVoiceRelaySegmentState(startedAt),
            -45,
            startedAt + 900,
        );
        expect(next.hasSpeech).toBe(true);
        expect(next.lastSpeechAtMs).toBe(startedAt + 900);
    });

    it('uses longer auto flush when Android metering is unavailable', () => {
        expect(resolveVoiceRelayFixedFlushDelayMs(true)).toBe(
            VOICE_RELAY_VAD_DEFAULTS.meterUnavailableFixedFlushMs,
        );
        expect(resolveVoiceRelayFixedFlushDelayMs(false)).toBe(
            VOICE_RELAY_VAD_DEFAULTS.maxSegmentMs,
        );
    });

    it('increments chunk index for non-final flushes', () => {
        const nextState = nextVoiceRelaySegmentStateAfterFlush(
            createInitialVoiceRelaySegmentState(4_000, 1),
            false,
            16_500,
        );

        expect(nextState.chunkIndex).toBe(2);
        expect(nextState.hasSpeech).toBe(false);
    });
});

describe('voiceRelayPlaybackQueue', () => {
    it('plays queued items in seq_id order', async () => {
        const played: number[] = [];
        const queue = new VoiceRelayPlaybackQueue(async (item) => {
            played.push(item.seqId);
        });

        queue.enqueue({
            seqId: 1,
            utteranceId: 'u1',
            chunkIndex: 0,
            isFinal: true,
            translatedText: 'one',
            targetLang: 'en',
        });
        queue.enqueue({
            seqId: 2,
            utteranceId: 'u1',
            chunkIndex: 0,
            isFinal: true,
            translatedText: 'two',
            targetLang: 'en',
        });

        await new Promise((resolve) => setTimeout(resolve, 50));
        expect(played).toEqual([1, 2]);
    });
});

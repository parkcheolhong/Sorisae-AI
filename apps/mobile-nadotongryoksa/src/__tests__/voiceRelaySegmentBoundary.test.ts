import { describe, expect, it } from '@jest/globals';

import {
    resolveSileroSafetyCapDelayMs,
    shouldFlushOnSileroSpeechEnd,
    shouldFlushSileroSafetyCap,
    VOICE_RELAY_SILERO_BOUNDARY_DEFAULTS,
} from '../features/voip-voice-relay/voiceRelaySegmentBoundary';

describe('voiceRelaySegmentBoundary', () => {
    it('defers flush when segment or speech span is too short', () => {
        expect(shouldFlushOnSileroSpeechEnd({
            segmentDurationMs: VOICE_RELAY_SILERO_BOUNDARY_DEFAULTS.minSegmentMs - 1,
            speechSpanMs: VOICE_RELAY_SILERO_BOUNDARY_DEFAULTS.minSegmentMs - 1,
            lastSileroFlushAtMs: null,
            nowMs: 10_000,
        })).toEqual({ flush: false, deferReason: 'segment_too_short' });

        expect(shouldFlushOnSileroSpeechEnd({
            segmentDurationMs: VOICE_RELAY_SILERO_BOUNDARY_DEFAULTS.minSegmentMs + 1_600,
            speechSpanMs: VOICE_RELAY_SILERO_BOUNDARY_DEFAULTS.minSpeechSpanMs - 1,
            lastSileroFlushAtMs: null,
            nowMs: 10_000,
        })).toEqual({ flush: false, deferReason: 'speech_span_too_short' });
    });

    it('allows flush for natural phrase boundaries', () => {
        expect(shouldFlushOnSileroSpeechEnd({
            segmentDurationMs: 7_988,
            speechSpanMs: 6_500,
            lastSileroFlushAtMs: null,
            nowMs: 20_000,
        })).toEqual({ flush: true });
    });

    it('defers flush during post-flush cooldown', () => {
        expect(shouldFlushOnSileroSpeechEnd({
            segmentDurationMs: 8_000,
            speechSpanMs: 6_000,
            lastSileroFlushAtMs: 19_500,
            nowMs: 20_000,
        })).toEqual({ flush: false, deferReason: 'post_flush_cooldown' });
    });

    it('computes remaining safety cap delay', () => {
        const nowMs = 5_000;
        const startedAt = nowMs - 4_000;
        expect(resolveSileroSafetyCapDelayMs(startedAt, nowMs)).toBe(
            VOICE_RELAY_SILERO_BOUNDARY_DEFAULTS.safetyCapMs - 4_000,
        );
    });

    it('flushes safety cap only at the cap with speech', () => {
        const cap = VOICE_RELAY_SILERO_BOUNDARY_DEFAULTS.safetyCapMs;
        expect(shouldFlushSileroSafetyCap({
            segmentDurationMs: cap - 1,
            hasSpeech: true,
        })).toBe(false);
        expect(shouldFlushSileroSafetyCap({
            segmentDurationMs: cap,
            hasSpeech: true,
        })).toBe(true);
        expect(shouldFlushSileroSafetyCap({
            segmentDurationMs: cap + 1_000,
            hasSpeech: false,
        })).toBe(false);
    });
});

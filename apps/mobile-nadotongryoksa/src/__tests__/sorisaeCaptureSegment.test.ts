import { describe, expect, it } from '@jest/globals';

import { echoOverlapRatio, normalizeEchoText } from '../features/sorisae/sorisaeEcho';
import {
    shouldFlushOnSileroSpeechEnd,
    shouldFlushSileroSafetyCap,
    VOICE_RELAY_SILERO_BOUNDARY_DEFAULTS,
} from '../features/voip-voice-relay/voiceRelaySegmentBoundary';

describe('sorisaeCaptureSegment gate', () => {
    it('keeps short or low-speech segments from flushing', () => {
        expect(shouldFlushOnSileroSpeechEnd({
            segmentDurationMs: VOICE_RELAY_SILERO_BOUNDARY_DEFAULTS.minSegmentMs - 1,
            speechSpanMs: VOICE_RELAY_SILERO_BOUNDARY_DEFAULTS.minSpeechSpanMs,
            lastSileroFlushAtMs: null,
            nowMs: 10_000,
        })).toEqual({ flush: false, deferReason: 'segment_too_short' });

        expect(shouldFlushOnSileroSpeechEnd({
            segmentDurationMs: VOICE_RELAY_SILERO_BOUNDARY_DEFAULTS.minSegmentMs,
            speechSpanMs: VOICE_RELAY_SILERO_BOUNDARY_DEFAULTS.minSpeechSpanMs - 1,
            lastSileroFlushAtMs: null,
            nowMs: 10_000,
        })).toEqual({ flush: false, deferReason: 'speech_span_too_short' });
    });

    it('allows natural speech boundaries and safety-cap flushes', () => {
        expect(shouldFlushOnSileroSpeechEnd({
            segmentDurationMs: VOICE_RELAY_SILERO_BOUNDARY_DEFAULTS.minSegmentMs,
            speechSpanMs: VOICE_RELAY_SILERO_BOUNDARY_DEFAULTS.minSpeechSpanMs,
            lastSileroFlushAtMs: null,
            nowMs: 20_000,
        })).toEqual({ flush: true });

        expect(shouldFlushSileroSafetyCap({
            segmentDurationMs: VOICE_RELAY_SILERO_BOUNDARY_DEFAULTS.safetyCapMs,
            hasSpeech: true,
        })).toBe(true);
    });

    it('detects likely self-echo before recapturing companion speech', () => {
        const full = normalizeEchoText('오늘 여행 준비를 같이 도와줄게요');
        const partial = normalizeEchoText('여행 준비를 같이');

        expect(echoOverlapRatio(full, partial)).toBe(1);
    });
});

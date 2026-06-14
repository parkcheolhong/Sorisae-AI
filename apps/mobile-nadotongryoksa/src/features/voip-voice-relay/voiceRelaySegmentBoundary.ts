/**
 * Silero-driven phrase boundary gates — reduce mid-utterance cuts and fragment STT turns.
 */
export const VOICE_RELAY_SILERO_BOUNDARY_DEFAULTS = {
    /** Native Silero trailing silence before speech_end. */
    silenceMs: 1_100,
    /** Native Silero minimum voiced frames before speech_start. */
    speechMs: 120,
    /** Minimum captured segment length before endpoint flush. */
    minSegmentMs: 3_200,
    /** Minimum voiced span (first speech_start → speech_end) in the segment. */
    minSpeechSpanMs: 2_000,
    /** Safety cap while Silero owns boundaries (no fixed_interval mid-phrase). */
    safetyCapMs: 14_000,
    /** Ignore rapid endpoint events right after a flush. */
    postFlushCooldownMs: 1_200,
} as const;

export function shouldFlushOnSileroSpeechEnd(params: {
    segmentDurationMs: number;
    speechSpanMs: number | null;
    lastSileroFlushAtMs: number | null;
    nowMs: number;
    config?: typeof VOICE_RELAY_SILERO_BOUNDARY_DEFAULTS;
}): { flush: boolean; deferReason?: string } {
    const cfg = params.config ?? VOICE_RELAY_SILERO_BOUNDARY_DEFAULTS;

    if (params.lastSileroFlushAtMs != null && params.nowMs - params.lastSileroFlushAtMs < cfg.postFlushCooldownMs) {
        return { flush: false, deferReason: 'post_flush_cooldown' };
    }

    if (params.segmentDurationMs < cfg.minSegmentMs) {
        return { flush: false, deferReason: 'segment_too_short' };
    }

    const speechSpanMs = params.speechSpanMs ?? 0;
    if (speechSpanMs < cfg.minSpeechSpanMs) {
        return { flush: false, deferReason: 'speech_span_too_short' };
    }

    return { flush: true };
}

export function shouldFlushSileroSafetyCap(params: {
    segmentDurationMs: number;
    hasSpeech: boolean;
    config?: typeof VOICE_RELAY_SILERO_BOUNDARY_DEFAULTS;
}): boolean {
    const cfg = params.config ?? VOICE_RELAY_SILERO_BOUNDARY_DEFAULTS;
    return params.hasSpeech && params.segmentDurationMs >= cfg.safetyCapMs;
}

export function resolveSileroSafetyCapDelayMs(
    segmentStartedAtMs: number,
    nowMs: number = Date.now(),
    config: typeof VOICE_RELAY_SILERO_BOUNDARY_DEFAULTS = VOICE_RELAY_SILERO_BOUNDARY_DEFAULTS,
): number {
    const elapsedMs = Math.max(0, nowMs - segmentStartedAtMs);
    return Math.max(config.safetyCapMs - elapsedMs, config.minSegmentMs);
}

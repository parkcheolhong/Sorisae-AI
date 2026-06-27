/**
 * Silero-driven phrase boundary gates — reduce mid-utterance cuts and fragment STT turns.
 */
// NOTE: 런타임에는 resolveSileroBoundaryFromTuning()(backend SSOT)이 이 값을 덮어쓴다.
// (G1 정합) fallback 값은 SSOT(worldlinco_tuning_config.json voip)와 동일하게 둔다:
// silenceMs=1400(silero_silence_ms)·safetyCapMs=12000(silero_safety_cap_ms).
// 콜드스타트/원격 fetch 실패 구간에서도 정상값(자연 장문 수용·호흡 통과)과 일치하도록 정합.
export const VOICE_RELAY_SILERO_BOUNDARY_DEFAULTS = {
    /** Native Silero trailing silence before speech_end. */
    silenceMs: 1_400,
    /** Native Silero minimum voiced frames before speech_start. */
    speechMs: 120,
    /** Minimum captured segment length before endpoint flush. */
    minSegmentMs: 2_400,
    /** Minimum voiced span (first speech_start → speech_end) in the segment. */
    minSpeechSpanMs: 1_700,
    /** Safety cap while Silero owns boundaries (no fixed_interval mid-phrase). */
    safetyCapMs: 12_000,
    /** Ignore rapid endpoint events right after a flush. */
    postFlushCooldownMs: 1_000,
} as const;

// 런타임 SSOT(resolveSileroBoundaryFromTuning)는 number 값을 주입하므로, config 파라미터는
// as const 리터럴이 아니라 number 기반 타입으로 받는다(리터럴 기본값도 이 타입에 할당 가능).
export type VoiceRelaySileroBoundaryConfig = {
    silenceMs: number;
    speechMs: number;
    minSegmentMs: number;
    minSpeechSpanMs: number;
    safetyCapMs: number;
    postFlushCooldownMs: number;
};

export function shouldFlushOnSileroSpeechEnd(params: {
    segmentDurationMs: number;
    speechSpanMs: number | null;
    lastSileroFlushAtMs: number | null;
    nowMs: number;
    config?: VoiceRelaySileroBoundaryConfig;
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
    config?: VoiceRelaySileroBoundaryConfig;
}): boolean {
    const cfg = params.config ?? VOICE_RELAY_SILERO_BOUNDARY_DEFAULTS;
    return params.hasSpeech && params.segmentDurationMs >= cfg.safetyCapMs;
}

export function resolveSileroSafetyCapDelayMs(
    segmentStartedAtMs: number,
    nowMs: number = Date.now(),
    config: VoiceRelaySileroBoundaryConfig = VOICE_RELAY_SILERO_BOUNDARY_DEFAULTS,
): number {
    const elapsedMs = Math.max(0, nowMs - segmentStartedAtMs);
    return Math.max(config.safetyCapMs - elapsedMs, config.minSegmentMs);
}

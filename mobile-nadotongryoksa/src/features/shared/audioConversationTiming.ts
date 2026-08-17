/**
 * Shared audio timing kernel: safe to import from Sorisae and face interpreter.
 * Keep policy-only constants here so engines stay decoupled at module level.
 */

/** TTS end -> next capture restart delay. */
export const FACE_CONVERSATION_RESTART_MS = 180;

/** Capture watchdog cap for long playback/reply turns. */
export const FACE_CONVERSATION_PLAYBACK_CAP_MS = 50_000;

/** Microphone permission retry interval. */
export const FACE_CONVERSATION_PERMISSION_RETRY_MS = 800;

/** Window to suppress immediate self-echo after speaking. */
export const FACE_CONVERSATION_ECHO_GUARD_MS = 25_000;

/** Number of spoken entries retained for overlap matching. */
export const FACE_CONVERSATION_SPOKEN_HISTORY = 5;

/** Drain delay after playback completion before reopening capture. */
export const FACE_CONVERSATION_PLAYBACK_DRAIN_MS = 2_500;

/** Shorter guard for output-language echo comparison. */
export const FACE_OUTPUT_ECHO_GUARD_MS = 5_000;

/**
 * Dynamic safety cap for long TTS content.
 * 250 chars should allow approximately 45s+ playback while staying below hard 90s cap.
 */
export function computeFaceTtsSafetyCapMs(textLength: number): number {
    const normalized = Math.max(0, Math.floor(textLength));
    const perCharMs = 170;
    const baseMs = 7_000;
    const computed = baseMs + (normalized * perCharMs);
    return Math.max(20_000, Math.min(90_000, computed));
}

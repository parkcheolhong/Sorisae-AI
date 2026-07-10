export type AudioEngineId = 'face' | 'sorisae' | 'inter_call' | 'song' | 'voip';

type TransitionHooks = {
    stopPrevious?: (previous: AudioEngineId) => void;
    startNext?: (next: AudioEngineId) => void;
};

let activeEngine: AudioEngineId | null = null;
let transitionInProgress = false;

export function getActiveAudioEngine(): AudioEngineId | null {
    return activeEngine;
}

/**
 * Thin audio kernel: guarantees stop-previous then start-next ordering for a single active engine.
 */
export function transitionToAudioEngine(
    next: AudioEngineId,
    reason: string,
    hooks: TransitionHooks = {},
): void {
    const previous = activeEngine;
    if (previous === next) {
        return;
    }

    if (transitionInProgress) {
        // eslint-disable-next-line no-console
        console.log('[AUDIO_ENGINE_KERNEL]', JSON.stringify({
            event: 'transition_reentered',
            previous,
            next,
            reason,
        }));
    }

    transitionInProgress = true;
    activeEngine = null;

    try {
        if (previous && hooks.stopPrevious) {
            try {
                hooks.stopPrevious(previous);
            } catch (error) {
                // Self-heal: never leave kernel locked on stop errors.
                // eslint-disable-next-line no-console
                console.log('[AUDIO_ENGINE_KERNEL]', JSON.stringify({
                    event: 'stop_previous_failed',
                    previous,
                    next,
                    reason,
                    error: error instanceof Error ? error.message : String(error),
                }));
            }
        }

        hooks.startNext?.(next);
        activeEngine = next;
        // eslint-disable-next-line no-console
        console.log('[AUDIO_ENGINE_KERNEL]', JSON.stringify({
            event: 'transition',
            previous,
            next,
            reason,
        }));
    } catch (error) {
        activeEngine = previous;
        // eslint-disable-next-line no-console
        console.log('[AUDIO_ENGINE_KERNEL]', JSON.stringify({
            event: 'start_next_failed',
            previous,
            next,
            reason,
            error: error instanceof Error ? error.message : String(error),
        }));
        throw error;
    } finally {
        transitionInProgress = false;
    }
}

export function clearActiveAudioEngine(engine: AudioEngineId, reason: string): void {
    if (activeEngine !== engine) {
        return;
    }
    activeEngine = null;
    // eslint-disable-next-line no-console
    console.log('[AUDIO_ENGINE_KERNEL]', JSON.stringify({
        event: 'clear',
        engine,
        reason,
    }));
}

export function forceResetAudioEngineKernelForTest(): void {
    activeEngine = null;
    transitionInProgress = false;
}

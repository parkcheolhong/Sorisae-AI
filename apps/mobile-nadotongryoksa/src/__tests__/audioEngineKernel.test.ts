import { describe, expect, it, beforeEach } from '@jest/globals';

import {
    clearActiveAudioEngine,
    forceResetAudioEngineKernelForTest,
    getActiveAudioEngine,
    transitionToAudioEngine,
} from '../services/audioEngineKernel';

describe('audioEngineKernel', () => {
    beforeEach(() => {
        forceResetAudioEngineKernelForTest();
    });

    it('keeps single active engine and transitions with stop-before-start ordering', () => {
        const events: string[] = [];

        transitionToAudioEngine('sorisae', 'boot', {
            startNext: () => events.push('start:sorisae'),
        });

        transitionToAudioEngine('face', 'mode_switch', {
            stopPrevious: () => events.push('stop:sorisae'),
            startNext: () => events.push('start:face'),
        });

        expect(events).toEqual(['start:sorisae', 'stop:sorisae', 'start:face']);
        expect(getActiveAudioEngine()).toBe('face');
    });

    it('self-heals when stopPrevious throws and still activates next engine', () => {
        transitionToAudioEngine('sorisae', 'boot');

        transitionToAudioEngine('voip', 'incoming_call', {
            stopPrevious: () => {
                throw new Error('simulated stop failure');
            },
        });

        expect(getActiveAudioEngine()).toBe('voip');
    });

    it('clears active engine only when requested engine owns the slot', () => {
        transitionToAudioEngine('face', 'boot');

        clearActiveAudioEngine('sorisae', 'noop');
        expect(getActiveAudioEngine()).toBe('face');

        clearActiveAudioEngine('face', 'shutdown');
        expect(getActiveAudioEngine()).toBeNull();
    });
});

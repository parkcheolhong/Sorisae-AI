import { describe, expect, it, jest } from '@jest/globals';

import { handleSorisaeDormantTimeout } from '../features/sorisae/sorisaeDormantWatchdog';

describe('sorisaeDormantWatchdog', () => {
    it('sleeps the session, closes the window, and restarts listening when still armed', async () => {
        const companionVoiceCallRef = { current: { phase: 'awake', lastWakeAtMs: 1, lastActivityAtMs: 1 } as any };
        const companionVoiceCallArmedRef = { current: true };
        const faceAiModeRef = { current: 'gpt' as const };
        const voiceInputTargetRef = { current: 'inter_call' as const };
        const setFaceAiMode = jest.fn();
        const setAutoVoiceModeEnabled = jest.fn();
        const setGpsStatus = jest.fn();
        const startVoiceInput = jest.fn();
        const closeSorisaeWindow = jest.fn(async () => undefined);
        const sleep = jest.fn((state: any) => ({ ...state, phase: 'dormant' }));
        const shouldSleep = jest.fn(() => true);

        await handleSorisaeDormantTimeout({
            companionVoiceCallRef,
            companionVoiceCallArmed: true,
            companionVoiceCallArmedRef,
            faceAiModeRef,
            setFaceAiMode,
            voiceInputTargetRef,
            setAutoVoiceModeEnabled,
            recordingRef: { current: false },
            startVoiceInput,
            closeSorisaeWindow,
            shouldSleep,
            sleep,
            setGpsStatus,
            dormantStatusText: 'dormant',
        });

        expect(sleep).toHaveBeenCalled();
        expect(setGpsStatus).toHaveBeenCalledWith('dormant');
        expect(closeSorisaeWindow).toHaveBeenCalled();
        expect(faceAiModeRef.current).toBe('translate');
        expect(voiceInputTargetRef.current).toBe('main');
        expect(setAutoVoiceModeEnabled).toHaveBeenCalledWith(true);
        expect(startVoiceInput).toHaveBeenCalledWith({ autoMode: true });
        expect(companionVoiceCallRef.current.phase).toBe('dormant');
        expect(shouldSleep).not.toHaveBeenCalledWith(expect.anything(), expect.any(Number));
    });
});
import { describe, expect, it, jest } from '@jest/globals';

import { syncWakeCompanionVoiceCallNowRef, wakeSorisaeVoiceCallNow } from '../features/sorisae/sorisaeWakeController';

describe('sorisaeWakeController', () => {
    it('opens sorisae wake state and updates the visible mode', () => {
        const companionVoiceCallRef = { current: { phase: 'dormant', lastWakeAtMs: null, lastActivityAtMs: null } as any };
        const faceAiModeRef = { current: 'translate' as const };
        const sorisaeWindowOpenRef = { current: false };
        const setFaceAiMode = jest.fn();
        const setSorisaeWindowOpen = jest.fn();
        const setGpsStatus = jest.fn();
        const wakeCompanionVoiceCall = jest.fn((state: any) => ({ ...state, phase: 'awake', lastWakeAtMs: 123456, lastActivityAtMs: 123456 }));

        wakeSorisaeVoiceCallNow({
            companionVoiceCallRef,
            wakeCompanionVoiceCall,
            faceAiModeRef,
            setFaceAiMode,
            sorisaeWindowOpenRef,
            setSorisaeWindowOpen,
            setGpsStatus,
            aiDisplayName: '소리새 AI',
            wakeSuccessText: 'awake',
        }, 123456);

        expect(wakeCompanionVoiceCall).toHaveBeenCalledWith(expect.objectContaining({ phase: 'dormant' }), 123456);
        expect(faceAiModeRef.current).toBe('gpt');
        expect(sorisaeWindowOpenRef.current).toBe(true);
        expect(setFaceAiMode).toHaveBeenCalledWith('gpt');
        expect(setSorisaeWindowOpen).toHaveBeenCalledWith(true);
        expect(setGpsStatus).toHaveBeenCalledWith('awake');
        expect(companionVoiceCallRef.current.phase).toBe('awake');
    });

    it('syncs the wake callback ref without changing the callback', () => {
        const wakeCompanionVoiceCallNow = jest.fn();
        const ref = { current: jest.fn() };

        syncWakeCompanionVoiceCallNowRef(ref, wakeCompanionVoiceCallNow);

        expect(ref.current).toBe(wakeCompanionVoiceCallNow);
    });
});
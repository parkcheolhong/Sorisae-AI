import { describe, expect, it, jest } from '@jest/globals';

import { closeSorisaeWindowNow, syncSorisaeWindowOpenStateNow } from '../features/sorisae/sorisaeWindowController';

describe('sorisaeWindowController', () => {
    it('stops active playback and resets the visible sorisae window state', async () => {
        const recordingRef = { current: true };
        const voiceInputTargetRef = { current: 'main' as const };
        const stopVoiceInput = jest.fn(async () => undefined);
        const stopFaceVoicePlayback = jest.fn(async () => undefined);
        const faceVoicePlaybackSoundRef = { current: null };
        const sorisaeVoicePlaybackSoundRef = { current: null };
        const sorisaeSpeakingRef = { current: true };
        const sorisaeWindowOpenRef = { current: true };
        const faceAiModeRef = { current: 'gpt' as const };
        const setFaceAiMode = jest.fn();
        const setAutoVoiceModeEnabled = jest.fn();
        const setSorisaeWindowOpen = jest.fn();

        await closeSorisaeWindowNow({
            autoVoiceModeEnabled: true,
            recordingRef,
            voiceInputTargetRef,
            stopVoiceInput,
            stopFaceVoicePlayback,
            faceVoicePlaybackSoundRef,
            sorisaeVoicePlaybackSoundRef,
            sorisaeSpeakingRef,
            sorisaeWindowOpenRef,
            faceAiModeRef,
            setFaceAiMode,
            setAutoVoiceModeEnabled,
            setSorisaeWindowOpen,
        });

        expect(stopVoiceInput).toHaveBeenCalledWith({ suppressAutoRestart: true });
        expect(stopFaceVoicePlayback).toHaveBeenCalledWith(sorisaeVoicePlaybackSoundRef);
        expect(stopFaceVoicePlayback).toHaveBeenCalledWith(faceVoicePlaybackSoundRef);
        expect(setAutoVoiceModeEnabled).toHaveBeenCalledWith(false);
        expect(setFaceAiMode).toHaveBeenCalledWith('translate');
        expect(setSorisaeWindowOpen).toHaveBeenCalledWith(false);
        expect(sorisaeSpeakingRef.current).toBe(false);
        expect(sorisaeWindowOpenRef.current).toBe(false);
        expect(faceAiModeRef.current).toBe('translate');
    });

    it('syncs an opened window by preserving awake companion listening state', async () => {
        const events: string[] = [];
        const sorisaeWindowOpenRef = { current: false };
        const companionVoiceCallRef = { current: { phase: 'awake', lastActivityMs: 0 } };
        const autoVoiceModeEnabledRef = { current: false };

        await syncSorisaeWindowOpenStateNow({
            autoVoiceModeEnabled: false,
            recordingRef: { current: false },
            voiceInputTargetRef: { current: 'inter_call' },
            autoVoiceModeEnabledRef,
            stopVoiceInput: async () => {
                events.push('stopVoiceInput');
            },
            stopFaceVoicePlayback: async () => {
                events.push('stopFaceVoicePlayback');
            },
            faceVoicePlaybackSoundRef: { current: null },
            sorisaeVoicePlaybackSoundRef: { current: null },
            sorisaeSpeakingRef: { current: true },
            sorisaeWindowOpenRef,
            companionVoiceCallRef,
            faceAiModeRef: { current: 'translate' as 'translate' | 'gpt' },
            setFaceAiMode: (mode) => {
                events.push(`setFaceAiMode:${mode}`);
            },
            setAutoVoiceModeEnabled: (enabled) => {
                events.push(`setAutoVoiceModeEnabled:${String(enabled)}`);
            },
            setSorisaeWindowOpen: () => undefined,
            startVoiceInput: (opts) => {
                events.push(`startVoiceInput:${String(opts.autoMode)}`);
            },
        }, true);

        expect(sorisaeWindowOpenRef.current).toBe(true);
        expect(autoVoiceModeEnabledRef.current).toBe(true);
        expect(events).toEqual([
            'setFaceAiMode:gpt',
            'setAutoVoiceModeEnabled:true',
            'startVoiceInput:true',
            'stopFaceVoicePlayback',
        ]);
    });
});
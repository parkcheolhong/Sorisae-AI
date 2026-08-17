import { describe, expect, it, jest } from '@jest/globals';

import {
    resolveSorisaeConversationWebGuard,
    toggleSorisaeConversation,
} from '../features/sorisae/sorisaeConversationController';

describe('sorisaeConversationController', () => {
    it('returns a web-only guard when the platform is web', () => {
        expect(resolveSorisaeConversationWebGuard({
            platform: 'web',
            title: 'web title',
            body: 'web body',
        })).toEqual({ title: 'web title', message: 'web body' });
    });

    it('starts sorisae chat when inactive and stops it when already active', async () => {
        const setAutoVoiceModeEnabled = jest.fn();
        const stopVoiceInput = jest.fn(async () => undefined);
        const stopFaceVoicePlayback = jest.fn(async () => undefined);
        const setFaceAiMode = jest.fn();
        const setGpsStatus = jest.fn();
        const startVoiceInput = jest.fn();
        const sorisaeSpeakingRef = { current: true };
        const faceAiModeRef = { current: 'translate' as const };
        const voiceInputTargetRef = { current: 'inter_call' as const };

        await toggleSorisaeConversation({
            autoVoiceModeEnabled: false,
            setAutoVoiceModeEnabled,
            recordingRef: { current: false },
            stopVoiceInput,
            stopFaceVoicePlayback,
            sorisaeVoicePlaybackSoundRef: { current: null },
            sorisaeSpeakingRef,
            faceAiModeRef,
            setFaceAiMode,
            voiceInputTargetRef,
            startVoiceInput,
            setGpsStatus,
            aiDisplayName: '소리새 AI',
            faceModeTexts: {
                webOnlyTitle: 'web title',
                webOnlyBody: 'web body',
                convStarted: 'started',
                convEnded: 'ended',
            },
        }, {
            platform: 'android',
        });

        expect(setFaceAiMode).toHaveBeenCalledWith('gpt');
        expect(setAutoVoiceModeEnabled).toHaveBeenCalledWith(true);
        expect(setGpsStatus).toHaveBeenCalledWith('started');
        expect(voiceInputTargetRef.current).toBe('main');
        expect(startVoiceInput).toHaveBeenCalledWith({ autoMode: true });
        expect(stopVoiceInput).not.toHaveBeenCalled();

        setAutoVoiceModeEnabled.mockClear();
        setGpsStatus.mockClear();
        startVoiceInput.mockClear();

        await toggleSorisaeConversation({
            autoVoiceModeEnabled: true,
            setAutoVoiceModeEnabled,
            recordingRef: { current: true },
            stopVoiceInput,
            stopFaceVoicePlayback,
            sorisaeVoicePlaybackSoundRef: { current: null },
            sorisaeSpeakingRef,
            faceAiModeRef,
            setFaceAiMode,
            voiceInputTargetRef,
            startVoiceInput,
            setGpsStatus,
            aiDisplayName: '소리새 AI',
            faceModeTexts: {
                webOnlyTitle: 'web title',
                webOnlyBody: 'web body',
                convStarted: 'started',
                convEnded: 'ended',
            },
        }, {
            platform: 'android',
        });

        expect(stopVoiceInput).toHaveBeenCalledWith({ suppressAutoRestart: true });
        expect(stopFaceVoicePlayback).toHaveBeenCalledTimes(1);
        expect(sorisaeSpeakingRef.current).toBe(false);
        expect(setAutoVoiceModeEnabled).toHaveBeenCalledWith(false);
        expect(setGpsStatus).toHaveBeenCalledWith('ended');
        expect(startVoiceInput).not.toHaveBeenCalled();
    });

    it('uses the injected alert callback for web-only gating', async () => {
        const alert = jest.fn();

        await toggleSorisaeConversation({
            autoVoiceModeEnabled: false,
            setAutoVoiceModeEnabled: jest.fn(),
            recordingRef: { current: false },
            stopVoiceInput: jest.fn(async () => undefined),
            stopFaceVoicePlayback: jest.fn(async () => undefined),
            sorisaeVoicePlaybackSoundRef: { current: null },
            sorisaeSpeakingRef: { current: false },
            faceAiModeRef: { current: 'translate' },
            setFaceAiMode: jest.fn(),
            voiceInputTargetRef: { current: 'main' },
            startVoiceInput: jest.fn(),
            setGpsStatus: jest.fn(),
            aiDisplayName: '소리새 AI',
            faceModeTexts: {
                webOnlyTitle: 'web title',
                webOnlyBody: 'web body',
                convStarted: 'started',
                convEnded: 'ended',
            },
        }, {
            platform: 'web',
            alert,
        });

        expect(alert).toHaveBeenCalledWith('web title', 'web body');
    });
});
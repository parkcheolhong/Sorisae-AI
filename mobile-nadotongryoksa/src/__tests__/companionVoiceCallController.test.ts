import { describe, expect, it } from '@jest/globals';

import {
    buildCompanionVoiceCallControllerDeps,
    buildCompanionVoiceCallTexts,
    toggleCompanionVoiceCall,
} from '../features/sorisae/companionVoiceCallController';

describe('companionVoiceCallController', () => {
    it('builds companion voice-call texts from feature text and display name', () => {
        expect(buildCompanionVoiceCallTexts((key, params) => `${key}:${params?.name ?? ''}`, '소리새 AI')).toEqual({
            webWakeOnly: 'sorisae.webWakeOnly:소리새 AI',
            wakeEnded: 'sorisae.wakeEnded:소리새 AI',
            wakeArmedStatus: 'sorisae.wakeArmedStatus:소리새 AI',
        });
    });

    it('builds controller deps with derived texts', () => {
        const deps = buildCompanionVoiceCallControllerDeps({
            autoVoiceModeEnabled: false,
            setAutoVoiceModeEnabled: () => undefined,
            recordingRef: { current: false },
            stopVoiceInput: async () => undefined,
            faceConversationSessionRef: { current: true },
            companionVoiceCallArmedRef: { current: false },
            companionVoiceCallRef: { current: { phase: 'off', lastActivityMs: 0 } },
            setCompanionVoiceCallArmed: () => undefined,
            sorisaeWindowOpenRef: { current: false },
            faceAiModeRef: { current: 'gpt' as 'translate' | 'gpt' },
            setFaceAiMode: () => undefined,
            voiceInputTargetRef: { current: 'inter_call' as 'main' | 'inter_call' },
            startVoiceInput: () => undefined,
            setGpsStatus: () => undefined,
            aiDisplayName: '소리새 AI',
            getFeatureUiText: (key, params) => `${key}:${params?.name ?? ''}`,
        });

        expect(deps.companionVoiceCallTexts).toEqual({
            webWakeOnly: 'sorisae.webWakeOnly:소리새 AI',
            wakeEnded: 'sorisae.wakeEnded:소리새 AI',
            wakeArmedStatus: 'sorisae.wakeArmedStatus:소리새 AI',
        });
    });

    it('disarms, stops, and updates status when already armed', async () => {
        const events: string[] = [];
        const companionVoiceCallArmedRef = { current: true };
        const companionVoiceCallRef = { current: { phase: 'awake', lastActivityMs: 0 } };

        await toggleCompanionVoiceCall({
            autoVoiceModeEnabled: true,
            setAutoVoiceModeEnabled: (enabled) => {
                events.push(`setAutoVoiceModeEnabled:${String(enabled)}`);
            },
            recordingRef: { current: true },
            stopVoiceInput: async () => {
                events.push('stopVoiceInput');
            },
            faceConversationSessionRef: { current: true },
            companionVoiceCallArmedRef,
            companionVoiceCallRef,
            setCompanionVoiceCallArmed: (armed) => {
                events.push(`setCompanionVoiceCallArmed:${String(armed)}`);
            },
            sorisaeWindowOpenRef: { current: false },
            faceAiModeRef: { current: 'gpt' as 'translate' | 'gpt' },
            setFaceAiMode: (mode) => {
                events.push(`setFaceAiMode:${mode}`);
            },
            voiceInputTargetRef: { current: 'main' as 'main' | 'inter_call' },
            startVoiceInput: () => undefined,
            setGpsStatus: (value) => {
                events.push(`setGpsStatus:${value}`);
            },
            aiDisplayName: '소리새 AI',
            getFeatureUiText: (key, params) => `${key}:${params?.name ?? ''}`,
            companionVoiceCallTexts: {
                webWakeOnly: 'web only',
                wakeEnded: 'ended',
                wakeArmedStatus: 'armed',
            },
        });

        expect(companionVoiceCallArmedRef.current).toBe(false);
        expect(companionVoiceCallRef.current.phase).toBe('off');
        expect(events).toEqual([
            'setCompanionVoiceCallArmed:false',
            'stopVoiceInput',
            'setAutoVoiceModeEnabled:false',
            'setGpsStatus:ended',
        ]);
    });

    it('arms and starts voice input when inactive', async () => {
        const events: string[] = [];
        const companionVoiceCallArmedRef = { current: false };
        const companionVoiceCallRef = { current: { phase: 'off', lastActivityMs: 0 } };

        await toggleCompanionVoiceCall({
            autoVoiceModeEnabled: false,
            setAutoVoiceModeEnabled: (enabled) => {
                events.push(`setAutoVoiceModeEnabled:${String(enabled)}`);
            },
            recordingRef: { current: false },
            stopVoiceInput: async () => {
                events.push('stopVoiceInput');
            },
            faceConversationSessionRef: { current: true },
            companionVoiceCallArmedRef,
            companionVoiceCallRef,
            setCompanionVoiceCallArmed: (armed) => {
                events.push(`setCompanionVoiceCallArmed:${String(armed)}`);
            },
            sorisaeWindowOpenRef: { current: false },
            faceAiModeRef: { current: 'gpt' as 'translate' | 'gpt' },
            setFaceAiMode: (mode) => {
                events.push(`setFaceAiMode:${mode}`);
            },
            voiceInputTargetRef: { current: 'inter_call' as 'main' | 'inter_call' },
            startVoiceInput: (opts) => {
                events.push(`startVoiceInput:${String(opts.autoMode)}`);
            },
            setGpsStatus: (value) => {
                events.push(`setGpsStatus:${value}`);
            },
            aiDisplayName: '소리새 AI',
            getFeatureUiText: (key, params) => `${key}:${params?.name ?? ''}`,
            companionVoiceCallTexts: {
                webWakeOnly: 'web only',
                wakeEnded: 'ended',
                wakeArmedStatus: 'armed',
            },
        });

        expect(companionVoiceCallArmedRef.current).toBe(true);
        expect(companionVoiceCallRef.current.phase).toBe('dormant');
        expect(events).toEqual([
            'setCompanionVoiceCallArmed:true',
            'setFaceAiMode:translate',
            'setAutoVoiceModeEnabled:true',
            'startVoiceInput:true',
            'setGpsStatus:armed',
        ]);
    });
});
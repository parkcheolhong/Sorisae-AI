import { describe, expect, it } from '@jest/globals';

import {
    buildFaceConversationTexts,
    buildFaceConversationControllerDeps,
    disarmCompanionVoiceCallForFaceConversation,
    resolveFaceConversationProfileLang,
    resolveFaceConversationStartGuard,
    stopFaceConversationAutoVoiceMode,
    startFaceConversationSession,
} from '../features/face-interpretation/faceConversationController';

describe('faceConversationController guards', () => {
    it('keeps a supported preferred language and falls back to fromLang otherwise', () => {
        expect(resolveFaceConversationProfileLang('ko', 'en')).toBe('en');
        expect(resolveFaceConversationProfileLang('ko', 'zz')).toBe('ko');
        expect(resolveFaceConversationProfileLang('ja', '   ')).toBe('ja');
    });

    it('blocks web start and same-language start with explicit guard text', () => {
        const webGuard = resolveFaceConversationStartGuard({
            platform: 'web',
            toLang: 'en',
            profileLang: 'ko',
            webOnlyTitle: 'web title',
            webOnlyBody: 'web body',
            peerLangTitle: 'peer title',
            peerLangBody: 'peer body',
        });
        const sameLangGuard = resolveFaceConversationStartGuard({
            platform: 'android',
            toLang: 'ko',
            profileLang: 'ko',
            webOnlyTitle: 'web title',
            webOnlyBody: 'web body',
            peerLangTitle: 'peer title',
            peerLangBody: 'peer body',
        });

        expect(webGuard).toEqual({ title: 'web title', message: 'web body' });
        expect(sameLangGuard).toEqual({ title: 'peer title', message: 'peer body' });
    });

    it('builds face conversation texts with display fallbacks', () => {
        expect(buildFaceConversationTexts((key) => `feature:${key}`, {
            faceConversationPeerRequired: 'display peer',
            autoVoiceModeStopped: 'display stopped',
            autoVoiceModeStarted: 'display started',
        })).toEqual({
            webOnlyTitle: 'feature:face.webOnlyTitle',
            webOnlyBody: 'feature:face.webOnlyBody',
            peerLangTitle: 'feature:face.peerLangTitle',
            peerLangBody: 'display peer',
            autoVoiceModeStopped: 'display stopped',
            autoVoiceModeStarted: 'display started',
        });

        expect(buildFaceConversationTexts((key) => `feature:${key}`, {})).toEqual({
            webOnlyTitle: 'feature:face.webOnlyTitle',
            webOnlyBody: 'feature:face.webOnlyBody',
            peerLangTitle: 'feature:face.peerLangTitle',
            peerLangBody: 'feature:face.peerLangTitle',
            autoVoiceModeStopped: '🎙️ 대화 통역을 종료했습니다.',
            autoVoiceModeStarted: '🎙️ 대화 통역 시작 · 말 끝날 때까지 듣습니다',
        });
    });

    it('builds face conversation controller deps by composing the text helper', () => {
        const faceConversationSessionRef = { current: false };
        const controllerDeps = buildFaceConversationControllerDeps({
            autoVoiceModeEnabled: false,
            setAutoVoiceModeEnabled: () => undefined,
            fromLang: 'ko',
            toLang: 'en',
            userPreferredLanguage: 'ja',
            recordingRef: { current: false },
            stopVoiceInput: async () => undefined,
            stopFaceVoicePlayback: async () => undefined,
            faceVoicePlaybackSoundRef: { current: null },
            faceConversationSessionRef,
            faceAiModeRef: { current: 'gpt' as 'translate' | 'gpt' },
            setFaceAiMode: () => undefined,
            companionVoiceCallArmedRef: { current: false },
            companionVoiceCallRef: { current: null },
            disarmCompanionVoiceCall: (state) => state,
            setCompanionVoiceCallArmed: () => undefined,
            voiceInputTargetRef: { current: 'inter_call' as 'main' | 'inter_call' },
            startVoiceInput: () => undefined,
            setGpsStatus: () => undefined,
            aiDisplayName: 'AI',
            getFeatureUiText: (key) => `feature:${key}`,
            displayUiText: {
                faceConversationPeerRequired: 'display peer',
                autoVoiceModeStopped: 'display stopped',
                autoVoiceModeStarted: 'display started',
            },
        });

        expect(controllerDeps.faceConversationTexts).toEqual({
            webOnlyTitle: 'feature:face.webOnlyTitle',
            webOnlyBody: 'feature:face.webOnlyBody',
            peerLangTitle: 'feature:face.peerLangTitle',
            peerLangBody: 'display peer',
            autoVoiceModeStopped: 'display stopped',
            autoVoiceModeStarted: 'display started',
        });
        expect(controllerDeps.faceConversationSessionRef).toBe(faceConversationSessionRef);
        expect(controllerDeps.aiDisplayName).toBe('AI');
    });

    it('allows face conversation start when platform and languages are valid', () => {
        expect(resolveFaceConversationStartGuard({
            platform: 'android',
            toLang: 'en',
            profileLang: 'ko',
            webOnlyTitle: 'web title',
            webOnlyBody: 'web body',
            peerLangTitle: 'peer title',
            peerLangBody: 'peer body',
        })).toBeNull();
    });

    it('stops auto voice mode in the expected order and resets state', async () => {
        const events: string[] = [];
        const recordingRef = { current: true };
        const faceConversationSessionRef = { current: true };
        await stopFaceConversationAutoVoiceMode({
            recordingRef,
            stopVoiceInput: async () => {
                events.push('stopVoiceInput');
            },
            stopFaceVoicePlayback: async () => {
                events.push('stopFaceVoicePlayback');
            },
            faceVoicePlaybackSoundRef: { current: null },
            faceConversationSessionRef,
            setAutoVoiceModeEnabled: (enabled) => {
                events.push(`setAutoVoiceModeEnabled:${String(enabled)}`);
            },
            setGpsStatus: (value) => {
                events.push(`setGpsStatus:${value}`);
            },
            faceConversationTexts: {
                webOnlyTitle: 'web title',
                webOnlyBody: 'web body',
                peerLangTitle: 'peer title',
                peerLangBody: 'peer body',
                autoVoiceModeStopped: 'stopped',
                autoVoiceModeStarted: 'started',
            },
        });

        expect(events).toEqual([
            'stopVoiceInput',
            'stopFaceVoicePlayback',
            'setAutoVoiceModeEnabled:false',
            'setGpsStatus:stopped',
        ]);
        expect(recordingRef.current).toBe(true);
        expect(faceConversationSessionRef.current).toBe(false);
    });

    it('disarms companion voice call only when armed', () => {
        const events: string[] = [];
        const armedRef = { current: true };
        const companionVoiceCallRef = { current: { id: 'call-1' } };

        disarmCompanionVoiceCallForFaceConversation({
            companionVoiceCallArmedRef: armedRef,
            companionVoiceCallRef,
            disarmCompanionVoiceCall: (state) => {
                events.push(`disarm:${state?.id ?? 'null'}`);
                return null;
            },
            setCompanionVoiceCallArmed: (armed) => {
                events.push(`setCompanionVoiceCallArmed:${String(armed)}`);
            },
        });

        expect(events).toEqual(['disarm:call-1', 'setCompanionVoiceCallArmed:false']);
        expect(armedRef.current).toBe(false);
        expect(companionVoiceCallRef.current).toBeNull();

        events.length = 0;
        disarmCompanionVoiceCallForFaceConversation({
            companionVoiceCallArmedRef: armedRef,
            companionVoiceCallRef,
            disarmCompanionVoiceCall: (state) => {
                events.push(`disarm:${state?.id ?? 'null'}`);
                return null;
            },
            setCompanionVoiceCallArmed: (armed) => {
                events.push(`setCompanionVoiceCallArmed:${String(armed)}`);
            },
        });

        expect(events).toEqual([]);
    });

    it('starts face conversation by forcing translate mode and arming voice input', () => {
        const events: string[] = [];
        const faceAiModeRef = { current: 'gpt' as 'translate' | 'gpt' };
        const companionVoiceCallArmedRef = { current: true };
        const companionVoiceCallRef = { current: { id: 'call-2' } };
        const faceConversationSessionRef = { current: false };
        const voiceInputTargetRef = { current: 'inter_call' as 'main' | 'inter_call' };

        startFaceConversationSession({
            faceAiModeRef,
            setFaceAiMode: (mode) => {
                events.push(`setFaceAiMode:${mode}`);
            },
            companionVoiceCallArmedRef,
            companionVoiceCallRef,
            disarmCompanionVoiceCall: (state) => {
                events.push(`disarm:${state?.id ?? 'null'}`);
                return null;
            },
            setCompanionVoiceCallArmed: (armed) => {
                events.push(`setCompanionVoiceCallArmed:${String(armed)}`);
            },
            faceConversationSessionRef,
            setAutoVoiceModeEnabled: (enabled) => {
                events.push(`setAutoVoiceModeEnabled:${String(enabled)}`);
            },
            setGpsStatus: (value) => {
                events.push(`setGpsStatus:${value}`);
            },
            faceConversationTexts: {
                webOnlyTitle: 'web title',
                webOnlyBody: 'web body',
                peerLangTitle: 'peer title',
                peerLangBody: 'peer body',
                autoVoiceModeStopped: 'stopped',
                autoVoiceModeStarted: 'started',
            },
            voiceInputTargetRef,
            startVoiceInput: (opts) => {
                events.push(`startVoiceInput:${String(opts.autoMode)}`);
            },
        });

        expect(faceAiModeRef.current).toBe('translate');
        expect(faceConversationSessionRef.current).toBe(true);
        expect(voiceInputTargetRef.current).toBe('main');
        expect(companionVoiceCallArmedRef.current).toBe(false);
        expect(companionVoiceCallRef.current).toBeNull();
        expect(events).toEqual([
            'setFaceAiMode:translate',
            'disarm:call-2',
            'setCompanionVoiceCallArmed:false',
            'setAutoVoiceModeEnabled:true',
            'setGpsStatus:started',
            'startVoiceInput:true',
        ]);
    });
});
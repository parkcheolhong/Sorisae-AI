import { useCallback, useEffect } from 'react';
import { Alert, Platform } from 'react-native';

import { isSupportedLangCode, type LangCode } from '../language/languageCatalog';
import type { CompanionVoiceCallState } from '../sorisae/companionVoiceCall';

type FaceConversationToggleGuard = {
    title: string;
    message: string;
};

type FaceConversationTextSource = {
    faceConversationPeerRequired?: string;
    autoVoiceModeStopped?: string;
    autoVoiceModeStarted?: string;
};

type FaceConversationControllerSetup = {
    autoVoiceModeEnabled: boolean;
    setAutoVoiceModeEnabled: (enabled: boolean) => void;
    fromLang: LangCode;
    toLang: LangCode;
    userPreferredLanguage?: string | null;
    recordingRef: { current: boolean };
    stopVoiceInput: (opts: { suppressAutoRestart: boolean }) => Promise<void>;
    stopFaceVoicePlayback: (soundRef: { current: unknown }) => Promise<void>;
    faceVoicePlaybackSoundRef: { current: unknown };
    faceConversationSessionRef: { current: boolean };
    faceAiModeRef: { current: 'translate' | 'gpt' };
    setFaceAiMode: (mode: 'translate' | 'gpt') => void;
    companionVoiceCallArmedRef: { current: boolean };
    companionVoiceCallRef: { current: CompanionVoiceCallState | null };
    disarmCompanionVoiceCall: (state: CompanionVoiceCallState | null) => CompanionVoiceCallState | null;
    setCompanionVoiceCallArmed: (armed: boolean) => void;
    voiceInputTargetRef: { current: 'main' | 'inter_call' };
    startVoiceInput: (opts: { autoMode: boolean }) => void;
    setGpsStatus: (value: string) => void;
    aiDisplayName: string;
    getFeatureUiText: (key: string) => string;
    displayUiText: FaceConversationTextSource;
};

type FaceConversationControllerDeps = {
    autoVoiceModeEnabled: boolean;
    setAutoVoiceModeEnabled: (enabled: boolean) => void;
    fromLang: LangCode;
    toLang: LangCode;
    userPreferredLanguage?: string | null;
    recordingRef: { current: boolean };
    stopVoiceInput: (opts: { suppressAutoRestart: boolean }) => Promise<void>;
    stopFaceVoicePlayback: (soundRef: { current: unknown }) => Promise<void>;
    faceVoicePlaybackSoundRef: { current: unknown };
    faceConversationSessionRef: { current: boolean };
    faceAiModeRef: { current: 'translate' | 'gpt' };
    setFaceAiMode: (mode: 'translate' | 'gpt') => void;
    companionVoiceCallArmedRef: { current: boolean };
    companionVoiceCallRef: { current: CompanionVoiceCallState | null };
    disarmCompanionVoiceCall: (state: CompanionVoiceCallState | null) => CompanionVoiceCallState | null;
    setCompanionVoiceCallArmed: (armed: boolean) => void;
    voiceInputTargetRef: { current: 'main' | 'inter_call' };
    startVoiceInput: (opts: { autoMode: boolean }) => void;
    setGpsStatus: (value: string) => void;
    aiDisplayName: string;
    faceConversationTexts: {
        webOnlyTitle: string;
        webOnlyBody: string;
        peerLangTitle: string;
        peerLangBody: string;
        autoVoiceModeStopped: string;
        autoVoiceModeStarted: string;
    };
};

export function resolveFaceConversationProfileLang(fromLang: LangCode, preferredLanguage?: string | null): LangCode {
    const profileLangRaw = String(preferredLanguage || fromLang).trim().toLowerCase();
    return isSupportedLangCode(profileLangRaw) ? profileLangRaw as LangCode : fromLang;
}

export function resolveFaceConversationStartGuard(params: {
    platform: string;
    toLang: LangCode;
    profileLang: LangCode;
    webOnlyTitle: string;
    webOnlyBody: string;
    peerLangTitle: string;
    peerLangBody: string;
}): FaceConversationToggleGuard | null {
    if (params.platform === 'web') {
        return {
            title: params.webOnlyTitle,
            message: params.webOnlyBody,
        };
    }

    if (params.toLang === params.profileLang) {
        return {
            title: params.peerLangTitle,
            message: params.peerLangBody,
        };
    }

    return null;
}

export function buildFaceConversationTexts(getFeatureUiText: (key: string) => string, displayUiText: FaceConversationTextSource): FaceConversationControllerDeps['faceConversationTexts'] {
    return {
        webOnlyTitle: getFeatureUiText('face.webOnlyTitle'),
        webOnlyBody: getFeatureUiText('face.webOnlyBody'),
        peerLangTitle: getFeatureUiText('face.peerLangTitle'),
        peerLangBody: displayUiText.faceConversationPeerRequired ?? getFeatureUiText('face.peerLangTitle'),
        autoVoiceModeStopped: displayUiText.autoVoiceModeStopped ?? '🎙️ 대화 통역을 종료했습니다.',
        autoVoiceModeStarted: displayUiText.autoVoiceModeStarted ?? '🎙️ 대화 통역 시작 · 말 끝날 때까지 듣습니다',
    };
}

export function buildFaceConversationControllerDeps(params: FaceConversationControllerSetup): FaceConversationControllerDeps {
    return {
        autoVoiceModeEnabled: params.autoVoiceModeEnabled,
        setAutoVoiceModeEnabled: params.setAutoVoiceModeEnabled,
        fromLang: params.fromLang,
        toLang: params.toLang,
        userPreferredLanguage: params.userPreferredLanguage,
        recordingRef: params.recordingRef,
        stopVoiceInput: params.stopVoiceInput,
        stopFaceVoicePlayback: params.stopFaceVoicePlayback,
        faceVoicePlaybackSoundRef: params.faceVoicePlaybackSoundRef,
        faceConversationSessionRef: params.faceConversationSessionRef,
        faceAiModeRef: params.faceAiModeRef,
        setFaceAiMode: params.setFaceAiMode,
        companionVoiceCallArmedRef: params.companionVoiceCallArmedRef,
        companionVoiceCallRef: params.companionVoiceCallRef,
        disarmCompanionVoiceCall: params.disarmCompanionVoiceCall,
        setCompanionVoiceCallArmed: params.setCompanionVoiceCallArmed,
        voiceInputTargetRef: params.voiceInputTargetRef,
        startVoiceInput: params.startVoiceInput,
        setGpsStatus: params.setGpsStatus,
        aiDisplayName: params.aiDisplayName,
        faceConversationTexts: buildFaceConversationTexts(params.getFeatureUiText, params.displayUiText),
    };
}

export async function stopFaceConversationAutoVoiceMode(deps: Pick<FaceConversationControllerDeps, 'recordingRef' | 'stopVoiceInput' | 'stopFaceVoicePlayback' | 'faceVoicePlaybackSoundRef' | 'faceConversationSessionRef' | 'setAutoVoiceModeEnabled' | 'setGpsStatus' | 'faceConversationTexts'>): Promise<void> {
    console.log('[FACE_CONVERSATION]', JSON.stringify({ event: 'face_auto_voice_stop_begin' }));
    deps.faceConversationSessionRef.current = false;
    if (deps.recordingRef.current) {
        await deps.stopVoiceInput({ suppressAutoRestart: true });
    }
    await deps.stopFaceVoicePlayback(deps.faceVoicePlaybackSoundRef);
    deps.setAutoVoiceModeEnabled(false);
    deps.setGpsStatus(deps.faceConversationTexts.autoVoiceModeStopped);
    console.log('[FACE_CONVERSATION]', JSON.stringify({ event: 'face_auto_voice_stop_end' }));
}

export function disarmCompanionVoiceCallForFaceConversation(deps: Pick<FaceConversationControllerDeps, 'companionVoiceCallArmedRef' | 'companionVoiceCallRef' | 'disarmCompanionVoiceCall' | 'setCompanionVoiceCallArmed'>): void {
    if (!deps.companionVoiceCallArmedRef.current) {
        return;
    }

    deps.companionVoiceCallRef.current = deps.disarmCompanionVoiceCall(deps.companionVoiceCallRef.current);
    deps.companionVoiceCallArmedRef.current = false;
    deps.setCompanionVoiceCallArmed(false);
}

export function startFaceConversationSession(deps: Pick<FaceConversationControllerDeps, 'faceAiModeRef' | 'setFaceAiMode' | 'companionVoiceCallArmedRef' | 'companionVoiceCallRef' | 'disarmCompanionVoiceCall' | 'setCompanionVoiceCallArmed' | 'faceConversationSessionRef' | 'setAutoVoiceModeEnabled' | 'setGpsStatus' | 'faceConversationTexts' | 'voiceInputTargetRef' | 'startVoiceInput'>): void {
    console.log('[FACE_CONVERSATION]', JSON.stringify({ event: 'face_auto_voice_start_begin' }));
    deps.faceAiModeRef.current = 'translate';
    deps.setFaceAiMode('translate');
    disarmCompanionVoiceCallForFaceConversation(deps);
    deps.faceConversationSessionRef.current = true;
    deps.setAutoVoiceModeEnabled(true);
    deps.setGpsStatus(deps.faceConversationTexts.autoVoiceModeStarted);
    deps.voiceInputTargetRef.current = 'main';
    void deps.startVoiceInput({ autoMode: true });
    console.log('[FACE_CONVERSATION]', JSON.stringify({ event: 'face_auto_voice_start_end' }));
}

export function useFaceConversationController(deps: FaceConversationControllerDeps): {
    handleToggleFaceConversation: () => Promise<void>;
} {
    const handleToggleFaceConversation = useCallback(async () => {
        const profileLang = resolveFaceConversationProfileLang(deps.fromLang, deps.userPreferredLanguage);
        const guard = resolveFaceConversationStartGuard({
            platform: Platform.OS,
            toLang: deps.toLang,
            profileLang,
            webOnlyTitle: deps.faceConversationTexts.webOnlyTitle,
            webOnlyBody: deps.faceConversationTexts.webOnlyBody,
            peerLangTitle: deps.faceConversationTexts.peerLangTitle,
            peerLangBody: deps.faceConversationTexts.peerLangBody,
        });

        if (deps.autoVoiceModeEnabled) {
            await stopFaceConversationAutoVoiceMode(deps);
            return;
        }

        if (guard) {
            Alert.alert(guard.title, guard.message);
            return;
        }

        // 대면 통역 화면은 '통역' 단일 모드 — 소리새(gpt) 모드가 메인 캡처 루프로 새지 않게 강제.
        startFaceConversationSession(deps);
    }, [deps]);

    return {
        handleToggleFaceConversation,
    };
}

type FaceConversationAutoVoiceGuardDeps = {
    autoVoiceModeEnabled: boolean;
    toLang: LangCode;
    fromLang: LangCode;
    faceScreenOpen: boolean;
    isTranslateWorkspaceVisible: boolean;
    recordingRef: { current: boolean };
    stopVoiceInput: (opts: { suppressAutoRestart: boolean }) => Promise<void>;
    startVoiceInput: (opts: { autoMode: boolean }) => void;
    setAutoVoiceModeEnabled: (enabled: boolean) => void;
    setGpsStatus: (value: string) => void;
    getPeerRequiredText: () => string;
    platformOs: string;
};

export function useFaceConversationAutoVoiceGuards(deps: FaceConversationAutoVoiceGuardDeps): void {
    const {
        autoVoiceModeEnabled,
        toLang,
        fromLang,
        faceScreenOpen,
        isTranslateWorkspaceVisible,
        recordingRef,
        stopVoiceInput,
        startVoiceInput,
        setAutoVoiceModeEnabled,
        setGpsStatus,
        getPeerRequiredText,
        platformOs,
    } = deps;

    useEffect(() => {
        if (!autoVoiceModeEnabled || toLang !== fromLang) {
            return;
        }
        void stopVoiceInput({ suppressAutoRestart: true });
        setAutoVoiceModeEnabled(false);
        setGpsStatus(getPeerRequiredText());
    }, [autoVoiceModeEnabled, fromLang, getPeerRequiredText, setAutoVoiceModeEnabled, setGpsStatus, stopVoiceInput, toLang]);

    useEffect(() => {
        if ((!isTranslateWorkspaceVisible && !faceScreenOpen) && autoVoiceModeEnabled) {
            void stopVoiceInput({ suppressAutoRestart: true });
            setAutoVoiceModeEnabled(false);
        }
    }, [autoVoiceModeEnabled, faceScreenOpen, isTranslateWorkspaceVisible, setAutoVoiceModeEnabled, stopVoiceInput]);

    useEffect(() => {
        if (!isTranslateWorkspaceVisible && !faceScreenOpen) {
            return;
        }
        if (!autoVoiceModeEnabled || platformOs === 'web' || recordingRef.current) {
            return;
        }
        void startVoiceInput({ autoMode: true });
    }, [autoVoiceModeEnabled, faceScreenOpen, isTranslateWorkspaceVisible, platformOs, recordingRef, startVoiceInput]);
}
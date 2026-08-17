import { useCallback } from 'react';
import { Alert, Platform } from 'react-native';

import type { CompanionVoiceCallState } from './companionVoiceCall';

type CompanionVoiceCallTextSource = {
    webWakeOnly?: string;
    wakeEnded?: string;
    wakeArmedStatus?: string;
};

type CompanionVoiceCallControllerSetup = {
    autoVoiceModeEnabled: boolean;
    setAutoVoiceModeEnabled: (enabled: boolean) => void;
    recordingRef: { current: boolean };
    stopVoiceInput: (opts: { suppressAutoRestart: boolean }) => Promise<void>;
    faceConversationSessionRef: { current: boolean };
    companionVoiceCallArmedRef: { current: boolean };
    companionVoiceCallRef: { current: CompanionVoiceCallState | null };
    setCompanionVoiceCallArmed: (armed: boolean) => void;
    sorisaeWindowOpenRef: { current: boolean };
    faceAiModeRef: { current: 'translate' | 'gpt' };
    setFaceAiMode: (mode: 'translate' | 'gpt') => void;
    voiceInputTargetRef: { current: 'main' | 'inter_call' };
    startVoiceInput: (opts: { autoMode: boolean }) => void;
    setGpsStatus: (value: string) => void;
    aiDisplayName: string;
    getFeatureUiText: (key: string, params?: { name?: string }) => string;
};

export function buildCompanionVoiceCallTexts(getFeatureUiText: (key: string, params?: { name?: string }) => string, aiDisplayName: string): CompanionVoiceCallControllerDeps['companionVoiceCallTexts'] {
    return {
        webWakeOnly: getFeatureUiText('sorisae.webWakeOnly', { name: aiDisplayName }),
        wakeEnded: getFeatureUiText('sorisae.wakeEnded', { name: aiDisplayName }),
        wakeArmedStatus: getFeatureUiText('sorisae.wakeArmedStatus', { name: aiDisplayName }),
    };
}

type CompanionVoiceCallControllerDeps = CompanionVoiceCallControllerSetup & {
    companionVoiceCallTexts: ReturnType<typeof buildCompanionVoiceCallTexts>;
};

function armCompanionVoiceCallNow(_state: CompanionVoiceCallState): CompanionVoiceCallState {
    return { phase: 'dormant', lastActivityMs: 0 };
}

function disarmCompanionVoiceCallNow(_state: CompanionVoiceCallState): CompanionVoiceCallState {
    return { phase: 'off', lastActivityMs: 0 };
}

export function buildCompanionVoiceCallControllerDeps(params: CompanionVoiceCallControllerSetup): CompanionVoiceCallControllerDeps {
    return {
        ...params,
        companionVoiceCallTexts: buildCompanionVoiceCallTexts(params.getFeatureUiText, params.aiDisplayName),
    };
}

export async function toggleCompanionVoiceCall(
    deps: CompanionVoiceCallControllerDeps,
    runtime: { platform?: string; alert?: (title: string, message: string) => void } = {},
): Promise<void> {
    if ((runtime.platform ?? Platform.OS) === 'web') {
        (runtime.alert ?? Alert.alert)(deps.aiDisplayName, deps.companionVoiceCallTexts.webWakeOnly);
        return;
    }

    if (deps.companionVoiceCallArmedRef.current) {
        deps.companionVoiceCallRef.current = disarmCompanionVoiceCallNow(deps.companionVoiceCallRef.current);
        deps.companionVoiceCallArmedRef.current = false;
        deps.setCompanionVoiceCallArmed(false);
        if (deps.recordingRef.current && deps.voiceInputTargetRef.current === 'main' && !deps.sorisaeWindowOpenRef.current) {
            await deps.stopVoiceInput({ suppressAutoRestart: true });
            deps.setAutoVoiceModeEnabled(false);
        }
        deps.setGpsStatus(deps.companionVoiceCallTexts.wakeEnded);
        return;
    }

    deps.faceConversationSessionRef.current = false;
    deps.companionVoiceCallRef.current = armCompanionVoiceCallNow(deps.companionVoiceCallRef.current);
    deps.companionVoiceCallArmedRef.current = true;
    deps.setCompanionVoiceCallArmed(true);
    deps.faceAiModeRef.current = 'translate';
    deps.setFaceAiMode('translate');
    deps.voiceInputTargetRef.current = 'main';
    deps.setAutoVoiceModeEnabled(true);
    if (!deps.recordingRef.current) {
        void deps.startVoiceInput({ autoMode: true });
    }
    deps.setGpsStatus(deps.companionVoiceCallTexts.wakeArmedStatus);
}

export function useCompanionVoiceCallController(deps: CompanionVoiceCallControllerDeps): {
    handleToggleCompanionVoiceCall: () => Promise<void>;
} {
    const handleToggleCompanionVoiceCall = useCallback(async () => {
        await toggleCompanionVoiceCall(deps);
    }, [deps]);

    return {
        handleToggleCompanionVoiceCall,
    };
}
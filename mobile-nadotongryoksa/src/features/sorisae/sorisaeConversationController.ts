import { useCallback } from 'react';
import { Alert, Platform } from 'react-native';

type SorisaeConversationControllerDeps = {
    autoVoiceModeEnabled: boolean;
    setAutoVoiceModeEnabled: (enabled: boolean) => void;
    recordingRef: { current: boolean };
    stopVoiceInput: (opts: { suppressAutoRestart: boolean }) => Promise<void>;
    stopFaceVoicePlayback: (soundRef: { current: unknown }) => Promise<void>;
    sorisaeVoicePlaybackSoundRef: { current: unknown };
    sorisaeSpeakingRef: { current: boolean };
    faceAiModeRef: { current: 'translate' | 'gpt' };
    setFaceAiMode: (mode: 'translate' | 'gpt') => void;
    voiceInputTargetRef: { current: 'main' | 'inter_call' };
    startVoiceInput: (opts: { autoMode: boolean }) => void;
    setGpsStatus: (value: string) => void;
    aiDisplayName: string;
    faceModeTexts: {
        webOnlyTitle: string;
        webOnlyBody: string;
        convStarted: string;
        convEnded: string;
    };
};

export function resolveSorisaeConversationWebGuard(params: {
    platform: string;
    title: string;
    body: string;
}): { title: string; message: string } | null {
    if (params.platform !== 'web') {
        return null;
    }

    return { title: params.title, message: params.body };
}

export async function toggleSorisaeConversation(
    deps: SorisaeConversationControllerDeps,
    runtime: { platform?: string; alert?: (title: string, message: string) => void } = {},
): Promise<void> {
    const guard = resolveSorisaeConversationWebGuard({
        platform: runtime.platform ?? Platform.OS,
        title: deps.faceModeTexts.webOnlyTitle,
        body: deps.faceModeTexts.webOnlyBody,
    });

    if (guard) {
        (runtime.alert ?? Alert.alert)(guard.title, guard.message);
        return;
    }

    // 소리새 모드 강제(통역 경로로 새지 않게).
    deps.faceAiModeRef.current = 'gpt';
    deps.setFaceAiMode('gpt');

    if (deps.autoVoiceModeEnabled) {
        if (deps.recordingRef.current) {
            await deps.stopVoiceInput({ suppressAutoRestart: true });
        }
        await deps.stopFaceVoicePlayback(deps.sorisaeVoicePlaybackSoundRef);
        deps.sorisaeSpeakingRef.current = false;
        deps.setAutoVoiceModeEnabled(false);
        deps.setGpsStatus(deps.faceModeTexts.convEnded);
        return;
    }

    deps.setAutoVoiceModeEnabled(true);
    deps.setGpsStatus(deps.faceModeTexts.convStarted);
    deps.voiceInputTargetRef.current = 'main';
    void deps.startVoiceInput({ autoMode: true });
}

export function useSorisaeConversationController(deps: SorisaeConversationControllerDeps): {
    handleToggleSorisaeConversation: () => Promise<void>;
} {
    const handleToggleSorisaeConversation = useCallback(async () => {
        await toggleSorisaeConversation(deps);
    }, [deps]);

    return {
        handleToggleSorisaeConversation,
    };
}
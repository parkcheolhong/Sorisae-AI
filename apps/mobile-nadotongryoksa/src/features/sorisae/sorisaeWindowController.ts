import { useCallback } from 'react';

type SorisaeWindowControllerDeps = {
    autoVoiceModeEnabled: boolean;
    recordingRef: { current: boolean };
    voiceInputTargetRef: { current: 'main' | 'inter_call' };
    autoVoiceModeEnabledRef: { current: boolean };
    stopVoiceInput: (opts: { suppressAutoRestart: boolean }) => Promise<void>;
    stopFaceVoicePlayback: (soundRef: { current: unknown }) => Promise<void>;
    faceVoicePlaybackSoundRef: { current: unknown };
    sorisaeVoicePlaybackSoundRef: { current: unknown };
    sorisaeSpeakingRef: { current: boolean };
    sorisaeWindowOpenRef: { current: boolean };
    faceAiModeRef: { current: 'translate' | 'gpt' };
    setFaceAiMode: (mode: 'translate' | 'gpt') => void;
    setAutoVoiceModeEnabled: (enabled: boolean) => void;
    setSorisaeWindowOpen: (open: boolean) => void;
};

export function syncSorisaeWindowOpenStateNow(deps: SorisaeWindowControllerDeps, sorisaeWindowOpen: boolean): Promise<void> {
    return (async () => {
        deps.sorisaeWindowOpenRef.current = sorisaeWindowOpen;
        if (!sorisaeWindowOpen) {
            return;
        }

        if (deps.companionVoiceCallRef.current.phase === 'awake') {
            deps.faceAiModeRef.current = 'gpt';
            deps.setFaceAiMode('gpt');
            deps.voiceInputTargetRef.current = 'main';
            if (!deps.autoVoiceModeEnabledRef.current) {
                deps.autoVoiceModeEnabledRef.current = true;
                deps.setAutoVoiceModeEnabled(true);
            }
            if (!deps.recordingRef.current) {
                void deps.startVoiceInput({ autoMode: true });
            }
            void deps.stopFaceVoicePlayback(deps.faceVoicePlaybackSoundRef);
            return;
        }

        if (deps.recordingRef.current) {
            void deps.stopVoiceInput({ suppressAutoRestart: true });
        }
        if (deps.autoVoiceModeEnabledRef.current) {
            deps.autoVoiceModeEnabledRef.current = false;
            deps.setAutoVoiceModeEnabled(false);
        }
        void deps.stopFaceVoicePlayback(deps.faceVoicePlaybackSoundRef);
    })();
}

export function closeSorisaeWindowNow(deps: SorisaeWindowControllerDeps): Promise<void> {
    return (async () => {
        if (deps.recordingRef.current && deps.voiceInputTargetRef.current === 'main') {
            await deps.stopVoiceInput({ suppressAutoRestart: true });
        }
        await deps.stopFaceVoicePlayback(deps.sorisaeVoicePlaybackSoundRef);
        deps.sorisaeSpeakingRef.current = false;
        if (deps.autoVoiceModeEnabled) {
            await deps.stopFaceVoicePlayback(deps.faceVoicePlaybackSoundRef);
            deps.setAutoVoiceModeEnabled(false);
        }
        deps.sorisaeWindowOpenRef.current = false;
        deps.faceAiModeRef.current = 'translate';
        deps.setFaceAiMode('translate');
        deps.setSorisaeWindowOpen(false);
    })();
}

export function useSorisaeWindowController(deps: SorisaeWindowControllerDeps): {
    closeSorisaeWindow: () => Promise<void>;
} {
    const closeSorisaeWindow = useCallback(async () => {
        await closeSorisaeWindowNow(deps);
    }, [deps]);

    return {
        closeSorisaeWindow,
    };
}

export function useSorisaeWindowOpenStateController(deps: SorisaeWindowControllerDeps): {
    syncSorisaeWindowOpenState: (open: boolean) => Promise<void>;
} {
    const syncSorisaeWindowOpenState = useCallback(async (open: boolean) => {
        await syncSorisaeWindowOpenStateNow(deps, open);
    }, [deps]);

    return {
        syncSorisaeWindowOpenState,
    };
}
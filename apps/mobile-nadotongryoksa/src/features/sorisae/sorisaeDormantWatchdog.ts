import { useEffect } from 'react';

import type { CompanionVoiceCallState } from './companionVoiceCall';

type SorisaeDormantWatchdogDeps = {
    companionVoiceCallRef: { current: CompanionVoiceCallState };
    companionVoiceCallArmed: boolean;
    companionVoiceCallArmedRef: { current: boolean };
    faceAiModeRef: { current: 'translate' | 'gpt' };
    setFaceAiMode: (mode: 'translate' | 'gpt') => void;
    voiceInputTargetRef: { current: 'main' | 'inter_call' };
    setAutoVoiceModeEnabled: (enabled: boolean) => void;
    recordingRef: { current: boolean };
    startVoiceInput: (opts: { autoMode: boolean }) => void;
    closeSorisaeWindow: () => Promise<void>;
    shouldSleep: (state: CompanionVoiceCallState, now: number) => boolean;
    sleep: (state: CompanionVoiceCallState) => CompanionVoiceCallState;
    setGpsStatus: (value: string) => void;
    dormantStatusText: string;
};

export async function handleSorisaeDormantTimeout(deps: SorisaeDormantWatchdogDeps): Promise<void> {
    deps.companionVoiceCallRef.current = deps.sleep(deps.companionVoiceCallRef.current);
    deps.setGpsStatus(deps.dormantStatusText);
    await deps.closeSorisaeWindow();
    if (!deps.companionVoiceCallArmedRef.current) {
        return;
    }
    deps.faceAiModeRef.current = 'translate';
    deps.setFaceAiMode('translate');
    deps.voiceInputTargetRef.current = 'main';
    deps.setAutoVoiceModeEnabled(true);
    if (!deps.recordingRef.current) {
        void deps.startVoiceInput({ autoMode: true });
    }
}

export function useSorisaeDormantWatchdog(deps: SorisaeDormantWatchdogDeps): void {
    useEffect(() => {
        if (!deps.companionVoiceCallArmed) return undefined;
        const timer = setInterval(() => {
            if (!deps.shouldSleep(deps.companionVoiceCallRef.current, Date.now())) return;
            void handleSorisaeDormantTimeout(deps);
        }, 15_000);
        return () => clearInterval(timer);
    }, [deps]);
}
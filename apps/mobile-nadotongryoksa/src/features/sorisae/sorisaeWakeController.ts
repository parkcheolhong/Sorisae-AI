import { useCallback } from 'react';

import type { CompanionVoiceCallState } from './companionVoiceCall';

type SorisaeWakeControllerDeps = {
    companionVoiceCallRef: { current: CompanionVoiceCallState };
    wakeCompanionVoiceCall: (state: CompanionVoiceCallState, now: number) => CompanionVoiceCallState;
    faceAiModeRef: { current: 'translate' | 'gpt' };
    setFaceAiMode: (mode: 'translate' | 'gpt') => void;
    sorisaeWindowOpenRef: { current: boolean };
    setSorisaeWindowOpen: (open: boolean) => void;
    setGpsStatus: (value: string) => void;
    aiDisplayName: string;
    wakeSuccessText: string;
};

export function wakeSorisaeVoiceCallNow(deps: SorisaeWakeControllerDeps, now: number = Date.now()): void {
    deps.companionVoiceCallRef.current = deps.wakeCompanionVoiceCall(deps.companionVoiceCallRef.current, now);
    deps.faceAiModeRef.current = 'gpt';
    deps.sorisaeWindowOpenRef.current = true;
    deps.setFaceAiMode('gpt');
    deps.setSorisaeWindowOpen(true);
    deps.setGpsStatus(deps.wakeSuccessText);
}

export function syncWakeCompanionVoiceCallNowRef(ref: { current: () => void }, wakeCompanionVoiceCallNow: () => void): void {
    ref.current = wakeCompanionVoiceCallNow;
}

export function useSorisaeWakeController(deps: SorisaeWakeControllerDeps): {
    wakeSorisaeVoiceCall: () => void;
} {
    const wakeSorisaeVoiceCall = useCallback(() => {
        wakeSorisaeVoiceCallNow(deps);
    }, [deps]);

    return {
        wakeSorisaeVoiceCall,
    };
}
/**
 * VoIP 세션(발신·수신·통화 중) 동안 소리새/대면통역 등 비-VoIP 음성 경로를 차단한다.
 * WebRTC 마이크는 voiceCaptureLease 밖이라, App 레벨에서 명시적으로 quiesce 해야 한다.
 */
import { clearActiveAudioEngine, transitionToAudioEngine } from './audioEngineKernel';

export type VoipSessionProbe = () => boolean;

let sessionProbe: VoipSessionProbe = () => false;

export function registerVoipSessionProbe(probe: VoipSessionProbe): void {
    sessionProbe = probe;
}

export function isVoipSessionActive(): boolean {
    try {
        return sessionProbe();
    } catch {
        return false;
    }
}

export type QuiesceNonVoipAudioOptions = {
    stopVoiceInput: (options?: { suppressAutoRestart?: boolean }) => Promise<void>;
    stopCompanionKws: () => Promise<void>;
    stopSorisaePlayback: () => Promise<void>;
    stopFacePlayback: () => Promise<void>;
    disarmCompanion: () => Promise<void>;
    clearSpeakingFlags: () => void;
    stopDeviceTts: () => void;
    reason: string;
};

async function runLocalAudioQuiesce(options: QuiesceNonVoipAudioOptions): Promise<void> {
    options.clearSpeakingFlags();
    options.stopDeviceTts();
    try {
        await options.stopSorisaePlayback();
    } catch {
        /* no-op */
    }
    try {
        await options.stopFacePlayback();
    } catch {
        /* no-op */
    }
    try {
        await options.stopCompanionKws();
    } catch {
        /* no-op */
    }
    try {
        await options.stopVoiceInput({ suppressAutoRestart: true });
    } catch {
        /* no-op */
    }
    try {
        await options.disarmCompanion();
    } catch {
        /* no-op */
    }
}

/** VoIP 세션 진입 시 소리새·대면통역·단말 TTS를 즉시 정지한다. */
export async function quiesceNonVoipAudioForVoipSession(
    options: QuiesceNonVoipAudioOptions,
): Promise<void> {
    await runLocalAudioQuiesce(options);
    transitionToAudioEngine('voip', options.reason);
    // eslint-disable-next-line no-console
    console.log('[VOIP_SESSION_GUARD]', JSON.stringify({ event: 'quiesce_voip', reason: options.reason }));
}

/** PSTN(일반전화 통역) 발신 전 비-PSTN 음성 경로를 정지한다. */
export async function quiesceBeforePstnDial(
    options: QuiesceNonVoipAudioOptions,
): Promise<void> {
    await runLocalAudioQuiesce(options);
    transitionToAudioEngine('inter_call', options.reason);
    // eslint-disable-next-line no-console
    console.log('[VOIP_SESSION_GUARD]', JSON.stringify({ event: 'quiesce_pstn', reason: options.reason }));
}

export function clearVoipAudioSession(reason: string = 'voip_session_end'): void {
    clearActiveAudioEngine('voip', reason);
}

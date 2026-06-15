import { NativeEventEmitter, NativeModules, Platform } from 'react-native';

import { VOICE_RELAY_SILERO_BOUNDARY_DEFAULTS } from '../features/voip-voice-relay/voiceRelaySegmentBoundary';

export type VoiceRelaySileroVadEventName = 'speech_start' | 'speech_end';

export type VoiceRelaySileroVadEvent = {
    event: VoiceRelaySileroVadEventName;
    timestampMs: number;
    isSpeech: boolean;
    silenceDurationMs: number;
    speechDurationMs: number;
};

type VoiceRelaySileroVadNativeModule = {
    isSupported: () => Promise<boolean>;
    startMonitor: (silenceMs: number, speechMs: number) => Promise<boolean>;
    stopMonitor: () => Promise<boolean>;
    addListener: (eventName: string) => void;
    removeListeners: (count: number) => void;
};

const nativeModule = NativeModules.VoiceRelaySileroVad as VoiceRelaySileroVadNativeModule | undefined;

export const VOICE_RELAY_SILERO_DEFAULTS = {
    silenceMs: VOICE_RELAY_SILERO_BOUNDARY_DEFAULTS.silenceMs,
    speechMs: VOICE_RELAY_SILERO_BOUNDARY_DEFAULTS.speechMs,
} as const;

export function isVoiceRelaySileroVadNativeAvailable(): boolean {
    return Platform.OS === 'android' && Boolean(nativeModule?.startMonitor);
}

export async function probeVoiceRelaySileroVadSupport(): Promise<boolean> {
    if (!isVoiceRelaySileroVadNativeAvailable()) {
        return false;
    }
    try {
        return await nativeModule!.isSupported();
    } catch {
        return false;
    }
}

export async function startVoiceRelaySileroVadMonitor(
    silenceMs: number = VOICE_RELAY_SILERO_DEFAULTS.silenceMs,
    speechMs: number = VOICE_RELAY_SILERO_DEFAULTS.speechMs,
): Promise<boolean> {
    if (!isVoiceRelaySileroVadNativeAvailable()) {
        return false;
    }
    return nativeModule!.startMonitor(silenceMs, speechMs);
}

export async function stopVoiceRelaySileroVadMonitor(): Promise<void> {
    if (!isVoiceRelaySileroVadNativeAvailable()) {
        return;
    }
    try {
        await nativeModule!.stopMonitor();
    } catch {
        // ignore stop races during segment teardown
    }
}

export function subscribeVoiceRelaySileroVadEvents(
    listener: (event: VoiceRelaySileroVadEvent) => void,
): () => void {
    if (!isVoiceRelaySileroVadNativeAvailable()) {
        return () => {};
    }
    const emitter = new NativeEventEmitter(nativeModule as unknown as {
        addListener: (eventName: string) => void;
        removeListeners: (count: number) => void;
    });
    const subscription = emitter.addListener('VoiceRelaySileroVadEvent', (payload: VoiceRelaySileroVadEvent) => {
        if (!payload?.event) {
            return;
        }
        listener(payload);
    });
    return () => {
        subscription.remove();
    };
}

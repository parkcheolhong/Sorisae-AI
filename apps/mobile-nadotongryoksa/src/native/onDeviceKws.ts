import { NativeEventEmitter, NativeModules, Platform } from 'react-native';

export type OnDeviceKwsProvider = 'vosk' | 'porcupine';

export type OnDeviceKwsStartOptions = {
    provider: OnDeviceKwsProvider;
    modelPath?: string;
    accessKey?: string;
    keywordPaths?: string[];
    sensitivities?: number[];
    keywords: string[];
    sampleRate?: number;
};

export type OnDeviceKwsEvent = {
    event: 'wake' | 'state' | 'error';
    provider: OnDeviceKwsProvider | string;
    transcript?: string;
    keyword?: string;
    message?: string;
    timestampMs: number;
};

type OnDeviceKwsNativeModule = {
    isSupported: () => Promise<boolean>;
    startKws: (configJson: string) => Promise<boolean>;
    stopKws: () => Promise<boolean>;
    addListener: (eventName: string) => void;
    removeListeners: (count: number) => void;
};

const nativeModule = NativeModules.OnDeviceKws as OnDeviceKwsNativeModule | undefined;

export function isOnDeviceKwsNativeAvailable(): boolean {
    return Platform.OS === 'android' && Boolean(nativeModule?.startKws);
}

export async function probeOnDeviceKwsSupport(): Promise<boolean> {
    if (!isOnDeviceKwsNativeAvailable()) {
        return false;
    }
    try {
        return await nativeModule!.isSupported();
    } catch {
        return false;
    }
}

export async function startOnDeviceKws(options: OnDeviceKwsStartOptions): Promise<boolean> {
    if (!isOnDeviceKwsNativeAvailable()) {
        return false;
    }
    try {
        return await nativeModule!.startKws(JSON.stringify(options));
    } catch {
        return false;
    }
}

export async function stopOnDeviceKws(): Promise<void> {
    if (!isOnDeviceKwsNativeAvailable()) {
        return;
    }
    try {
        await nativeModule!.stopKws();
    } catch {
        // ignore stop races
    }
}

export function subscribeOnDeviceKwsEvents(
    listener: (event: OnDeviceKwsEvent) => void,
): () => void {
    if (!isOnDeviceKwsNativeAvailable()) {
        return () => { };
    }
    const emitter = new NativeEventEmitter(nativeModule as unknown as {
        addListener: (eventName: string) => void;
        removeListeners: (count: number) => void;
    });
    const subscription = emitter.addListener('OnDeviceKwsEvent', (payload: OnDeviceKwsEvent) => {
        if (!payload?.event) {
            return;
        }
        listener(payload);
    });
    return () => {
        subscription.remove();
    };
}

import * as Speech from 'expo-speech';

import { Audio } from '../compat/expoAvAudio';

export type InstantDeviceSpeechOptions = {
    text: string;
    language: string;
    rate?: number;
    allowsRecordingIOS?: boolean;
    playThroughEarpieceAndroid?: boolean;
};

/** Start device TTS immediately — no await on audio teardown or mode switches. */
export function speakDeviceTextInstant(options: InstantDeviceSpeechOptions): Promise<void> {
    const normalized = options.text.trim();
    if (!normalized) {
        return Promise.resolve();
    }

    Speech.stop();

    void Audio.setAudioModeAsync({
        allowsRecordingIOS: options.allowsRecordingIOS ?? false,
        playsInSilentModeIOS: true,
        shouldDuckAndroid: true,
        playThroughEarpieceAndroid: options.playThroughEarpieceAndroid ?? false,
        staysActiveInBackground: false,
    }).catch(() => {
        // playback should still proceed via expo-speech
    });

    const rate = options.rate ?? 1.12;
    const estimatedMs = Math.min(12_000, Math.max(800, normalized.length * 68));

    return Promise.race([
        new Promise<void>((resolve) => {
            Speech.speak(normalized, {
                language: options.language,
                rate,
                volume: 1.0,
                onDone: () => resolve(),
                onStopped: () => resolve(),
                onError: () => resolve(),
            });
        }),
        new Promise<void>((resolve) => setTimeout(resolve, estimatedMs)),
    ]);
}

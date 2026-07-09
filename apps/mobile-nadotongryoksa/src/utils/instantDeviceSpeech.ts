import * as Speech from 'expo-speech';

import { Audio } from '../compat/expoAvAudio';

export type InstantDeviceSpeechOptions = {
    text: string;
    language: string;
    rate?: number;
    allowsRecordingIOS?: boolean;
    playThroughEarpieceAndroid?: boolean;
    shouldDuckAndroid?: boolean;
    onError?: (message: string) => void;
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
        shouldDuckAndroid: options.shouldDuckAndroid ?? true,
        playThroughEarpieceAndroid: options.playThroughEarpieceAndroid ?? false,
        staysActiveInBackground: false,
    }).catch(() => {
        // playback should still proceed via expo-speech
    });

    const rate = options.rate ?? 1.12;
    const estimatedMs = Math.min(45_000, Math.max(4_000, normalized.length * 170 + 4_000));

    return Promise.race([
        new Promise<void>((resolve) => {
            Speech.speak(normalized, {
                language: options.language,
                rate,
                volume: 1.0,
                onDone: () => resolve(),
                onStopped: () => resolve(),
                onError: (error) => {
                    const message = typeof error === 'string'
                        ? error
                        : (error && typeof error === 'object' && 'message' in error
                            ? String((error as { message?: unknown }).message ?? 'speech_error')
                            : 'speech_error');
                    options.onError?.(message);
                    resolve();
                },
            });
        }),
        new Promise<void>((resolve) => setTimeout(resolve, estimatedMs)),
    ]).then(async () => {
        try {
            for (let i = 0; i < 30; i += 1) {
                const stillSpeaking = await Speech.isSpeakingAsync();
                if (!stillSpeaking) {
                    break;
                }
                await new Promise<void>((resolve) => setTimeout(resolve, 150));
            }
        } catch {
            // no-op
        }
    });
}

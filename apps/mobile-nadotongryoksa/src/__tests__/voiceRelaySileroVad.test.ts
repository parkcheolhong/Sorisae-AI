import { describe, expect, it, jest } from '@jest/globals';

jest.mock('react-native', () => ({
    Platform: { OS: 'android' },
    NativeModules: {
        VoiceRelaySileroVad: {
            isSupported: jest.fn(async () => true),
            startMonitor: jest.fn(async () => true),
            stopMonitor: jest.fn(async () => true),
            addListener: jest.fn(),
            removeListeners: jest.fn(),
        },
    },
    NativeEventEmitter: jest.fn().mockImplementation(() => ({
        addListener: jest.fn(() => ({ remove: jest.fn() })),
    })),
}));

import {
    isVoiceRelaySileroVadNativeAvailable,
    probeVoiceRelaySileroVadSupport,
    startVoiceRelaySileroVadMonitor,
    stopVoiceRelaySileroVadMonitor,
} from '../native/voiceRelaySileroVad';

describe('voiceRelaySileroVad', () => {
    it('detects native module availability on Android', () => {
        expect(isVoiceRelaySileroVadNativeAvailable()).toBe(true);
    });

    it('probes native support', async () => {
        await expect(probeVoiceRelaySileroVadSupport()).resolves.toBe(true);
    });

    it('starts and stops monitor', async () => {
        await expect(startVoiceRelaySileroVadMonitor(1100, 120)).resolves.toBe(true);
        await expect(stopVoiceRelaySileroVadMonitor()).resolves.toBeUndefined();
    });
});

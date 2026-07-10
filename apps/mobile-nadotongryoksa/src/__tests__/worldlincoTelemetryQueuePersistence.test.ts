import { beforeEach, describe, expect, it, jest } from '@jest/globals';

const mockMemoryStore = new Map<string, string>();

jest.mock('@react-native-async-storage/async-storage', () => ({
    __esModule: true,
    default: {
        getItem: jest.fn(async (key: string) => mockMemoryStore.get(key) ?? null),
        setItem: jest.fn(async (key: string, value: string) => {
            mockMemoryStore.set(key, value);
        }),
    },
}));

describe('worldlinco telemetry queue persistence', () => {
    beforeEach(() => {
        mockMemoryStore.clear();
        jest.resetModules();
        jest.clearAllMocks();
    });

    it('restores unsent telemetry after module reload and flushes it', async () => {
        const fetchMock = jest.fn(async () => ({ ok: true }));
        // @ts-expect-error jest test runtime fetch mock
        global.fetch = fetchMock;

        // eslint-disable-next-line @typescript-eslint/no-var-requires
        const first = require('../services/worldlincoTuningConfig');
        first.configureWorldlincoTelemetryUploader(null);
        first.reportFaceVoiceAutoTuningMetric({
            roundtripMs: 980,
            playbackMs: 640,
            overlapDetected: false,
        });

        const persistedRaw = mockMemoryStore.get('@worldlinco/telemetry-queue/v1');
        expect(typeof persistedRaw).toBe('string');
        expect(persistedRaw || '').toContain('roundtrip_ms');

        jest.resetModules();

        // eslint-disable-next-line @typescript-eslint/no-var-requires
        const second = require('../services/worldlincoTuningConfig');
        second.configureWorldlincoTelemetryUploader({
            apiBaseUrl: 'http://127.0.0.1:8000',
            getAuthToken: () => 'token-1',
            getUserId: () => 'u-1',
            getDeviceId: () => 'device-1',
        });
        await second.flushWorldlincoTelemetryQueue('test-restart-restore');

        expect(fetchMock).toHaveBeenCalled();
        const [, requestInit] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
        const body = JSON.parse(String(requestInit.body || '{}')) as { items?: Array<{ metric?: string }> };
        expect(Array.isArray(body.items)).toBe(true);
        expect(body.items?.some((item) => item.metric === 'roundtrip_ms')).toBe(true);

        const afterFlushRaw = mockMemoryStore.get('@worldlinco/telemetry-queue/v1');
        expect(afterFlushRaw).toBeDefined();
        expect(JSON.parse(String(afterFlushRaw))).toEqual([]);
    });
});

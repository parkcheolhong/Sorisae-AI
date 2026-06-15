import { beforeEach, describe, expect, it, jest } from '@jest/globals';

jest.mock('expo-constants', () => ({
    expoConfig: {
        extra: {
            apiBaseUrl: 'http://127.0.0.1:8000',
        },
    },
}));

import { translateImage, translateText, voiceTranslate } from '../api/translate';
import { parsePersistedGpsSnapshot, serializePersistedGpsSnapshot } from '../utils/hybridGpsCache';
import { detectHybridGpsMode, scoreLocationQuality } from '../utils/hybridGps';
import { resolveNadotongryoksaProjectId, resetNadotongryoksaProjectIdCache } from '../utils/nadotongryoksaProject';
import { resolveWorldLincoProjectId, resetWorldLincoProjectIdCache } from '../utils/worldlincoProject';

describe('Local mobile validation guards', () => {
    let fetchMock: jest.MockedFunction<typeof fetch>;

    beforeEach(() => {
        jest.clearAllMocks();
        resetNadotongryoksaProjectIdCache();
        resetWorldLincoProjectIdCache();
        fetchMock = jest.fn<typeof fetch>();
        global.fetch = fetchMock;
    });

    it('classifies hybrid GPS modes at the documented thresholds', () => {
        expect(detectHybridGpsMode(null)).toBe('wifi_fallback');
        expect(detectHybridGpsMode(15)).toBe('satellite');
        expect(detectHybridGpsMode(25)).toBe('satellite');
        expect(detectHybridGpsMode(26)).toBe('hybrid');
        expect(detectHybridGpsMode(90)).toBe('hybrid');
        expect(detectHybridGpsMode(91)).toBe('wifi_fallback');
    });

    it('scores location quality consistently for fallback and GPS ranges', () => {
        expect(scoreLocationQuality(null)).toBe(35);
        expect(scoreLocationQuality(10)).toBe(96);
        expect(scoreLocationQuality(20)).toBe(88);
        expect(scoreLocationQuality(45)).toBe(74);
        expect(scoreLocationQuality(100)).toBe(58);
        expect(scoreLocationQuality(150)).toBe(40);
    });

    it('keeps a recent persisted GPS snapshot for service-off fallback', () => {
        const rawSnapshot = serializePersistedGpsSnapshot({
            latitude: 37.9083941,
            longitude: 127.9327704,
            accuracy: 9.28,
            overrideCountryCode: 'kr',
            overrideRegionHint: 'JeJu',
            recordedAt: 1_000_000,
        });

        expect(parsePersistedGpsSnapshot(rawSnapshot, 1_100_000)).toEqual({
            latitude: 37.9083941,
            longitude: 127.9327704,
            accuracy: 9.28,
            overrideCountryCode: 'KR',
            overrideRegionHint: 'jeju',
            recordedAt: 1_000_000,
        });
    });

    it('rejects stale persisted GPS snapshots', () => {
        const rawSnapshot = serializePersistedGpsSnapshot({
            latitude: 37.9083941,
            longitude: 127.9327704,
            accuracy: 9.28,
            recordedAt: 1_000_000,
        });

        expect(parsePersistedGpsSnapshot(rawSnapshot, 3_000_001)).toBeNull();
    });

    it('sends region_hint with chat translation requests', async () => {
        fetchMock.mockResolvedValueOnce({
            ok: true,
            json: async () => ({ translated: '안녕하세요', engine: 'nado' }),
        } as Response);

        await translateText('Hello', 'en', 'ko', 8000, { regionHint: 'jeju' });

        expect(global.fetch).toHaveBeenCalledWith(
            'http://127.0.0.1:8000/api/llm/translate',
            expect.objectContaining({
                method: 'POST',
                body: JSON.stringify({
                    text: 'Hello',
                    from_lang: 'en',
                    to_lang: 'ko',
                    region_hint: 'jeju',
                }),
            }),
        );
    });

    it('sends region_hint with voice translation requests', async () => {
        fetchMock.mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                original_text: 'hello',
                translated: '안녕하세요',
                engine: 'nado-voice',
                audio_url: '/audio/test.mp3',
            }),
        } as Response);

        await voiceTranslate('base64-audio', 'en', 'ko', 'kansai');

        expect(global.fetch).toHaveBeenCalledWith(
            'http://127.0.0.1:8000/api/llm/voice-translate',
            expect.objectContaining({
                method: 'POST',
                body: JSON.stringify({
                    audio_base64: 'base64-audio',
                    from_lang: 'en',
                    to_lang: 'ko',
                    region_hint: 'kansai',
                }),
            }),
        );
    });

    it('uses effective OCR source and target languages returned by the server', async () => {
        fetchMock.mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                original_text: 'Welcome to Seoul Station',
                translated: '서울역에 오신 것을 환영합니다',
                source_language: 'en',
                target_language: 'ko',
                engine: 'rapidocr+nado',
                offline: false,
                file_name: 'station.png',
                content_type: 'image/png',
                line_count: 1,
            }),
        } as Response);

        const result = await translateImage(
            { uri: 'file:///station.png', name: 'station.png', mimeType: 'image/png' },
            'ko',
            'ko',
            'jeju',
        );

        expect(result.from).toBe('en');
        expect(result.to).toBe('ko');
        expect(result.translated).toBe('서울역에 오신 것을 환영합니다');
    });

    it('resolves the live WorldLinco marketplace project id from legacy metadata', async () => {
        fetchMock.mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                projects: [
                    {
                        id: 38,
                        title: '소리새 통번역 스위트 – AI 실시간 13개 언어 완제품',
                        description: '나도통역사(실시간 13개 언어 통역) + AI 자연어 음성 처리',
                    },
                ],
            }),
        } as Response);

        await expect(resolveNadotongryoksaProjectId('http://127.0.0.1:8000', fetchMock)).resolves.toBe(38);
        expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/marketplace/projects?skip=0&limit=200');
    });

    it('resolves the live WorldLinco marketplace project id from WorldLinco title', async () => {
        fetchMock.mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                projects: [
                    {
                        id: 41,
                        title: 'WorldLinco · 월드링코 실시간 통역',
                        description: '모바일 APK build35',
                    },
                ],
            }),
        } as Response);

        await expect(resolveWorldLincoProjectId('http://127.0.0.1:8000', fetchMock)).resolves.toBe(41);
    });
});

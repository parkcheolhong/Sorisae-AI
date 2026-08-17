import { describe, expect, it, jest } from '@jest/globals';

import { applySongFileTimelineReadyNow, beginSongFileSelection, exportSongFileTimelineNow, loadSongFileSoundNow, replaceSongFileSegment, resetSongFileWorkspaceNow, toggleSongFilePlaybackNow, updateSongFileSegmentText } from '../features/song/songFilePlaybackController';

describe('songFilePlaybackController', () => {
    it('resets playback state and stores the created sound', async () => {
        const unloadAsync = jest.fn(async () => undefined);
        const setProgressUpdateIntervalAsync = jest.fn(async () => undefined);
        const sound = { unloadAsync, setProgressUpdateIntervalAsync } as any;
        const songFileSoundRef = { current: sound };
        const setSongFilePlaybackMs = jest.fn();
        const setSongFilePlaying = jest.fn();
        const createSoundAsync = jest.fn(async (_uri, onStatus) => {
            onStatus({ isLoaded: true, positionMillis: 123, isPlaying: false });
            return sound;
        });

        await loadSongFileSoundNow({
            songFileSoundRef,
            setSongFilePlaybackMs,
            setSongFilePlaying,
        }, 'file:///song.mp3', {
            createSoundAsync,
        });

        expect(unloadAsync).toHaveBeenCalled();
        expect(setSongFilePlaybackMs).toHaveBeenNthCalledWith(1, 0);
        expect(setSongFilePlaying).toHaveBeenNthCalledWith(1, false);
        expect(setSongFilePlaybackMs).toHaveBeenLastCalledWith(123);
        expect(setSongFilePlaying).toHaveBeenLastCalledWith(false);
        expect(setProgressUpdateIntervalAsync).toHaveBeenCalledWith(500);
        expect(songFileSoundRef.current).toBe(sound);
    });

    it('alerts when playback is requested before a file is loaded', async () => {
        const alert = jest.fn();

        await toggleSongFilePlaybackNow({ current: null }, alert);

        expect(alert).toHaveBeenCalledWith('재생 준비 필요', '먼저 노래 파일을 선택하세요.');
    });

    it('updates and replaces song file segments immutably', () => {
        const segments = [
            { id: 'a', translated: 'old' },
            { id: 'b', translated: 'keep' },
        ] as any;

        expect(updateSongFileSegmentText(segments, 'a', 'new')).toEqual([
            { id: 'a', translated: 'new' },
            { id: 'b', translated: 'keep' },
        ]);
        expect(replaceSongFileSegment(segments, { id: 'b', translated: 'updated' } as any)).toEqual([
            { id: 'a', translated: 'old' },
            { id: 'b', translated: 'updated' },
        ]);
    });

    it('initializes song file selection state', () => {
        const events: string[] = [];

        beginSongFileSelection({
            setSongModeEnabled: (enabled) => events.push(`setSongModeEnabled:${String(enabled)}`),
            setSongFileLoading: (loading) => events.push(`setSongFileLoading:${String(loading)}`),
            setSongFileName: (name) => events.push(`setSongFileName:${name}`),
            setSongFileJob: (job) => events.push(`setSongFileJob:${String(job)}`),
            setSongFileSegments: (segments) => events.push(`setSongFileSegments:${segments.length}`),
            setSongFileExportPreview: (preview) => events.push(`setSongFileExportPreview:${preview}`),
            setSongModeStatus: (status) => events.push(`setSongModeStatus:${status}`),
        }, 'song.mp3');

        expect(events).toEqual([
            'setSongModeEnabled:true',
            'setSongFileLoading:true',
            'setSongFileName:song.mp3',
            'setSongFileJob:null',
            'setSongFileSegments:0',
            'setSongFileExportPreview:',
            'setSongModeStatus:🎵 노래 파일을 업로드하고 백엔드 자막 작업을 시작합니다.',
        ]);
    });

    it('exports a song timeline preview', async () => {
        const events: string[] = [];

        await exportSongFileTimelineNow({
            setSongFileExportPreview: (preview) => events.push(`preview:${preview}`),
            setSongModeStatus: (status) => events.push(`status:${status}`),
        }, 'job-1', 'srt', async (_jobId, _format) => '1\n00:00:00,000 --> 00:00:01,000\nhello world');

        expect(events).toEqual([
            'preview:1\n00:00:00,000 --> 00:00:01,000\nhello world',
            'status:🎵 SRT 자막 내보내기 미리보기를 생성했습니다.',
        ]);
    });

    it('resets the song file workspace', () => {
        const events: string[] = [];

        resetSongFileWorkspaceNow({
            setSongSubtitles: (value) => events.push(`subtitles:${value.length}`),
            setSongFileSegments: (value) => events.push(`segments:${value.length}`),
            setSongFileJob: (value) => events.push(`job:${String(value)}`),
            setSongFileExportPreview: (value) => events.push(`preview:${value}`),
        });

        expect(events).toEqual(['subtitles:0', 'segments:0', 'job:null', 'preview:']);
    });
    it('applies ready song timeline state', () => {
        const events: string[] = [];

        applySongFileTimelineReadyNow({
            setSongModeEnabled: () => undefined,
            setSongFileLoading: () => undefined,
            setSongFileName: () => undefined,
            setSongFileJob: () => undefined,
            setSongFileSegments: (value) => events.push(`segments:${value.length}`),
            setSongFileExportPreview: () => undefined,
            setSongModeStatus: (value) => events.push(`status:${value}`),
        }, [{ id: 'seg-1' } as any], 'ko', 'ja', 1, 0.85);

        expect(events).toEqual(['segments:1', 'status:🎵 파일 자막 준비: ko → ja · 1개 구간 · 품질 85%']);
    });
});
import type { AudioSound } from '../../compat/expoAvAudio';
import type { SongFileJobStatus, SongFileTimelineSegment } from '../../app/appTypes';

type SongFilePlaybackDeps = {
    songFileSoundRef: { current: AudioSound | null };
    setSongFilePlaybackMs: (value: number) => void;
    setSongFilePlaying: (value: boolean) => void;
};

type SongFileSelectionDeps = {
    setSongModeEnabled: (value: boolean) => void;
    setSongFileLoading: (value: boolean) => void;
    setSongFileName: (value: string) => void;
    setSongFileJob: (value: SongFileJobStatus | null) => void;
    setSongFileSegments: (value: SongFileTimelineSegment[]) => void;
    setSongFileExportPreview: (value: string) => void;
    setSongModeStatus: (value: string) => void;
};

type SongFileResetDeps = {
    setSongSubtitles: (value: SongFileTimelineSegment[]) => void;
    setSongFileSegments: (value: SongFileTimelineSegment[]) => void;
    setSongFileJob: (value: SongFileJobStatus | null) => void;
    setSongFileExportPreview: (value: string) => void;
};

type SongFileAudioApi = {
    createSoundAsync: (uri: string, onStatus: (status: { isLoaded: boolean; positionMillis?: number; isPlaying?: boolean }) => void) => Promise<AudioSound>;
};

type SongFilePlaybackAlert = (title: string, message: string) => void;

type SongFileExportDeps = {
    setSongFileExportPreview: (value: string) => void;
    setSongModeStatus: (value: string) => void;
};

type SongFileTimelineExportApi = (jobId: string, format: 'srt' | 'vtt' | 'lrc' | 'json') => Promise<string>;

export function beginSongFileSelection(deps: SongFileSelectionDeps, fileName: string): void {
    deps.setSongModeEnabled(true);
    deps.setSongFileLoading(true);
    deps.setSongFileName(fileName);
    deps.setSongFileJob(null);
    deps.setSongFileSegments([]);
    deps.setSongFileExportPreview('');
    deps.setSongModeStatus('🎵 노래 파일을 업로드하고 백엔드 자막 작업을 시작합니다.');
}

export async function loadSongFileSoundNow(deps: SongFilePlaybackDeps, assetUri: string, audioApi: SongFileAudioApi): Promise<void> {
    await deps.songFileSoundRef.current?.unloadAsync().catch(() => { /* no-op */ });
    deps.songFileSoundRef.current = null;
    deps.setSongFilePlaybackMs(0);
    deps.setSongFilePlaying(false);
    const sound = await audioApi.createSoundAsync(assetUri, (status) => {
        if (!status.isLoaded) return;
        deps.setSongFilePlaybackMs(status.positionMillis ?? 0);
        deps.setSongFilePlaying(Boolean(status.isPlaying));
    });
    await sound.setProgressUpdateIntervalAsync(500);
    deps.songFileSoundRef.current = sound;
}

export async function toggleSongFilePlaybackNow(soundRef: { current: AudioSound | null }, alert: SongFilePlaybackAlert = (title, message) => void 0): Promise<void> {
    const sound = soundRef.current;
    if (!sound) {
        alert('재생 준비 필요', '먼저 노래 파일을 선택하세요.');
        return;
    }
    const status = await sound.getStatusAsync();
    if (!status.isLoaded) return;
    if (status.isPlaying) {
        await sound.pauseAsync();
    } else {
        await sound.playAsync();
    }
}

export function updateSongFileSegmentText(segments: SongFileTimelineSegment[], segmentId: string, translated: string): SongFileTimelineSegment[] {
    return segments.map((segment) => (segment.id === segmentId ? { ...segment, translated } : segment));
}

export function replaceSongFileSegment(segments: SongFileTimelineSegment[], nextSegment: SongFileTimelineSegment): SongFileTimelineSegment[] {
    return segments.map((segment) => (segment.id === nextSegment.id ? nextSegment : segment));
}
export async function exportSongFileTimelineNow(deps: SongFileExportDeps, jobId: string, format: 'srt' | 'vtt' | 'lrc' | 'json', exportApi: SongFileTimelineExportApi): Promise<void> {
    const exported = await exportApi(jobId, format);
    deps.setSongFileExportPreview(exported.slice(0, 900));
    deps.setSongModeStatus(`🎵 ${format.toUpperCase()} 자막 내보내기 미리보기를 생성했습니다.`);
}
export function applySongFileTimelineReadyNow(deps: SongFileSelectionDeps, segments: SongFileTimelineSegment[], sourceLabel: string, targetLabel: string, segmentCount: number, qualityScore: number): void {
    deps.setSongFileSegments(segments);
    deps.setSongModeStatus(`🎵 파일 자막 준비: ${sourceLabel} → ${targetLabel} · ${segmentCount}개 구간 · 품질 ${(qualityScore * 100).toFixed(0)}%`);
}
export function resetSongFileWorkspaceNow(deps: SongFileResetDeps): void {
    deps.setSongSubtitles([]);
    deps.setSongFileSegments([]);
    deps.setSongFileJob(null);
    deps.setSongFileExportPreview('');
}
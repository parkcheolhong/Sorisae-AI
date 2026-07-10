import type { AudioRecording } from '../../compat/expoAvAudio';

export type FaceConversationVadSnapshot = {
    hasSpeech: boolean;
    meterUnavailable: boolean;
    peakMeterDb: number;
};

export type FaceConversationVadController = {
    start: (params: {
        recording: AudioRecording;
        config?: {
            minSegmentMs: number;
            maxSegmentMs: number;
            silenceFlushMs: number;
            speechMeterMinDb: number;
            meterPollMs: number;
            meterUnavailableFixedFlushMs: number;
            meterUnavailableFilePollEvery?: number;
            shortSpeechThresholdMs?: number;
        };
        onFlush: (reason: string) => void;
        isStillActive: () => boolean;
    }) => Promise<void>;
    stop: () => Promise<void>;
    getSnapshot: () => FaceConversationVadSnapshot;
};

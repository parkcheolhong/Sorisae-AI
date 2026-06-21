import type { Audio } from '../../compat/expoAvAudio';
import * as FileSystem from 'expo-file-system/legacy';

import {
    estimateRecordingRmsDb,
    mapFileRmsToPseudoMeterDb,
} from '../voip-voice-relay/voiceRelayAudioMetrics';
import {
    createInitialVoiceRelaySegmentState,
    evaluateVoiceRelaySegmentDecision,
    resolveVoiceRelayFixedFlushDelayMs,
    updateVoiceRelaySegmentSpeechState,
    updateVoiceRelaySegmentSpeechStateFromFileRms,
    type VoiceRelaySegmentState,
} from '../voip-voice-relay/voiceRelayOrchestrator';
import {
    getWorldlincoTuning,
    resolveFaceFileSpeechRmsDb,
    resolveFaceVadDefaultsFromTuning,
} from '../../services/worldlincoTuningConfig';

const METER_UNAVAILABLE_POLLS = 5;

function getFaceVadConfig() {
    return resolveFaceVadDefaultsFromTuning(getWorldlincoTuning());
}

function getFaceFileSpeechRmsDb() {
    return resolveFaceFileSpeechRmsDb(getWorldlincoTuning());
}

export type FaceConversationVadSnapshot = {
    hasSpeech: boolean;
    meterUnavailable: boolean;
    peakMeterDb: number;
};

export type FaceConversationVadController = {
    start: (params: {
        recording: Audio.Recording;
        onFlush: (reason: string) => void;
        isStillActive: () => boolean;
    }) => Promise<void>;
    stop: () => Promise<void>;
    getSnapshot: () => FaceConversationVadSnapshot;
};

export function createFaceConversationVadController(): FaceConversationVadController {
    let recording: Audio.Recording | null = null;
    let onFlush: ((reason: string) => void) | null = null;
    let isStillActive: (() => boolean) | null = null;
    let segmentState: VoiceRelaySegmentState = createInitialVoiceRelaySegmentState(Date.now());
    let meterPollRef: ReturnType<typeof setInterval> | null = null;
    let fixedFlushTimerRef: ReturnType<typeof setTimeout> | null = null;
    let flushInProgress = false;
    let meterPollMisses = 0;
    let meterUnavailable = false;
    let fileRmsPollTick = 0;
    let peakMeterDb = -160;
    // 파일 증가율(bytes/sec) 기반 발화 활동 판정 상태 — 메트릭이 죽은 기기에서 무음(말 끝)을 추정한다.
    let prevFileSize = 0;
    let prevFilePollMs = 0;
    let peakGrowthBps = 0;
    let growthSpeechActive = false;

    const clearTimers = () => {
        if (meterPollRef) {
            clearInterval(meterPollRef);
            meterPollRef = null;
        }
        if (fixedFlushTimerRef) {
            clearTimeout(fixedFlushTimerRef);
            fixedFlushTimerRef = null;
        }
    };

    const getSnapshot = (): FaceConversationVadSnapshot => ({
        hasSpeech: segmentState.hasSpeech,
        meterUnavailable,
        peakMeterDb,
    });

    const requestFlush = (reason: string) => {
        if (flushInProgress || !onFlush || !isStillActive?.()) {
            return;
        }
        flushInProgress = true;
        console.log('[FACE_CONVERSATION]', JSON.stringify({ event: 'vad_flush', reason }));
        onFlush(reason);
    };

    const scheduleFixedFlush = () => {
        if (fixedFlushTimerRef) {
            clearTimeout(fixedFlushTimerRef);
            fixedFlushTimerRef = null;
        }
        if (!recording || !isStillActive?.()) {
            return;
        }
        const faceVadConfig = getFaceVadConfig();
        const segmentStartedAtMs = segmentState.segmentStartedAtMs;
        const elapsedMs = Date.now() - segmentStartedAtMs;
        let waitMs: number;
        if (meterUnavailable) {
            // 증가율(bytes/sec) VAD가 자연스러운 무음 컷을 담당하므로,
            // 이 블라인드 타이머는 최대 길이(maxSegmentMs) 안전 백스톱으로만 동작한다.
            waitMs = Math.max(faceVadConfig.meterPollMs, faceVadConfig.maxSegmentMs - elapsedMs);
        } else {
            const flushDelayMs = resolveVoiceRelayFixedFlushDelayMs(meterUnavailable, faceVadConfig);
            waitMs = elapsedMs < faceVadConfig.minSegmentMs
                ? Math.max(faceVadConfig.minSegmentMs - elapsedMs, faceVadConfig.meterPollMs)
                : flushDelayMs;
        }

        fixedFlushTimerRef = setTimeout(() => {
            fixedFlushTimerRef = null;
            if (!recording || flushInProgress || !isStillActive?.()) {
                return;
            }
            const elapsed = Date.now() - segmentState.segmentStartedAtMs;
            const minReadyMs = faceVadConfig.minSegmentMs + 250;
            if (elapsed < minReadyMs) {
                scheduleFixedFlush();
                return;
            }
            if (meterUnavailable) {
                // 백스톱: 최대 길이 도달 시에만 강제 종료. 그 전에는 증가율 VAD에 맡기고 재대기.
                if (segmentState.hasSpeech && elapsed >= faceVadConfig.maxSegmentMs) {
                    requestFlush('max_duration');
                } else {
                    scheduleFixedFlush();
                }
                return;
            }
            if (segmentState.hasSpeech) {
                requestFlush('max_duration');
                return;
            }
            scheduleFixedFlush();
        }, waitMs);
    };

    const startMeterPoll = () => {
        if (meterPollRef || !recording) {
            return;
        }
        meterPollRef = setInterval(() => {
            void (async () => {
                const activeRecording = recording;
                const faceVadConfig = getFaceVadConfig();
                if (!activeRecording || flushInProgress || !isStillActive?.()) {
                    return;
                }
                try {
                    const status = await activeRecording.getStatusAsync();
                    if (!status.isRecording) {
                        return;
                    }
                    const meteringUnavailableSample = typeof status.metering !== 'number'
                        || status.metering <= -159;
                    if (meteringUnavailableSample) {
                        meterPollMisses += 1;
                        if (meterPollMisses >= METER_UNAVAILABLE_POLLS && !meterUnavailable) {
                            meterUnavailable = true;
                            console.log('[FACE_CONVERSATION]', JSON.stringify({
                                event: 'meter_unavailable',
                                file_rms_vad: true,
                            }));
                            scheduleFixedFlush();
                        }
                        if (meterUnavailable) {
                            fileRmsPollTick += 1;
                            if (fileRmsPollTick >= faceVadConfig.meterUnavailableFilePollEvery) {
                                fileRmsPollTick = 0;
                                const recordingUri = activeRecording.getURI();
                                if (recordingUri) {
                                    try {
                                        // 메트릭이 죽은 기기: AAC 바이트 RMS는 음량과 무관해 쓸 수 없으므로
                                        // 녹음 파일의 증가율(bytes/sec)로 발화/무음을 추정한다.
                                        const info = await FileSystem.getInfoAsync(recordingUri, { size: true });
                                        const size = info.exists && typeof info.size === 'number' ? info.size : 0;
                                        const nowMs = Date.now();
                                        if (prevFilePollMs > 0 && size > 0) {
                                            const dtSec = Math.max(0.001, (nowMs - prevFilePollMs) / 1000);
                                            const growthBps = Math.max(0, (size - prevFileSize) / dtSec);
                                            // 발화 중 최고 증가율을 추적(완만한 감쇠)해 상대 임계값을 만든다.
                                            peakGrowthBps = Math.max(peakGrowthBps * 0.9, growthBps);
                                            // 32kbps AAC 기준 발화 바닥값 + 발화 정점 대비 상대 임계값.
                                            const SPEECH_FLOOR_BPS = 1800;
                                            const relThreshold = peakGrowthBps * 0.5;
                                            const speechNow = peakGrowthBps >= SPEECH_FLOOR_BPS
                                                && growthBps >= Math.max(SPEECH_FLOOR_BPS * 0.6, relThreshold);
                                            const priorHasSpeech = segmentState.hasSpeech;
                                            const pseudoMeterDb = speechNow ? -40 : -160;
                                            if (pseudoMeterDb > peakMeterDb) {
                                                peakMeterDb = pseudoMeterDb;
                                            }
                                            segmentState = updateVoiceRelaySegmentSpeechState(
                                                segmentState,
                                                pseudoMeterDb,
                                                nowMs,
                                                faceVadConfig.speechMeterMinDb,
                                            );
                                            if (speechNow !== growthSpeechActive) {
                                                growthSpeechActive = speechNow;
                                                console.log('[FACE_CONVERSATION]', JSON.stringify({
                                                    event: speechNow ? 'file_growth_speech' : 'file_growth_silence',
                                                    growth_bps: Math.round(growthBps),
                                                    peak_bps: Math.round(peakGrowthBps),
                                                }));
                                            }
                                            if (!priorHasSpeech && segmentState.hasSpeech) {
                                                console.log('[FACE_CONVERSATION]', JSON.stringify({
                                                    event: 'file_rms_speech',
                                                    growth_bps: Math.round(growthBps),
                                                }));
                                            }
                                            const fileDecision = evaluateVoiceRelaySegmentDecision(
                                                segmentState,
                                                nowMs,
                                                pseudoMeterDb,
                                                faceVadConfig,
                                            );
                                            if (fileDecision.action === 'flush') {
                                                prevFileSize = size;
                                                prevFilePollMs = nowMs;
                                                requestFlush(fileDecision.reason);
                                                return;
                                            }
                                        }
                                        prevFileSize = size;
                                        prevFilePollMs = nowMs;
                                    } catch {
                                        // partial m4a reads can fail while recording
                                    }
                                }
                            }
                        }
                        return;
                    }

                    meterPollMisses = 0;
                    if (typeof status.metering === 'number' && status.metering > peakMeterDb) {
                        peakMeterDb = status.metering;
                    }
                    const now = Date.now();
                    segmentState = updateVoiceRelaySegmentSpeechState(
                        segmentState,
                        status.metering,
                        now,
                        faceVadConfig.speechMeterMinDb,
                    );
                    const decision = evaluateVoiceRelaySegmentDecision(
                        segmentState,
                        now,
                        status.metering,
                        faceVadConfig,
                    );
                    if (decision.action === 'flush') {
                        requestFlush(decision.reason);
                    }
                } catch {
                    flushInProgress = false;
                }
            })();
        }, getFaceVadConfig().meterPollMs);
    };

    return {
        getSnapshot,

        async start(params) {
            await this.stop();
            recording = params.recording;
            onFlush = params.onFlush;
            isStillActive = params.isStillActive;
            flushInProgress = false;
            meterPollMisses = 0;
            meterUnavailable = false;
            fileRmsPollTick = 0;
            peakMeterDb = -160;
            prevFileSize = 0;
            prevFilePollMs = 0;
            peakGrowthBps = 0;
            growthSpeechActive = false;
            segmentState = createInitialVoiceRelaySegmentState(Date.now());
            startMeterPoll();
            scheduleFixedFlush();
        },

        async stop() {
            clearTimers();
            recording = null;
            onFlush = null;
            isStillActive = null;
            flushInProgress = false;
        },
    };
}

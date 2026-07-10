import { describe, expect, it } from '@jest/globals';

import {
    TTS_RATE_DEFAULT,
    TTS_RATE_MAX,
    TTS_RATE_MIN,
    TTS_VOLUME_DEFAULT,
    TTS_VOLUME_MAX,
    TTS_VOLUME_MIN,
    applyVoiceRuntimeObservation,
    createInitialVoiceRuntimeTuningState,
    deserializeVoiceRuntimeTuningState,
    ingestVoiceRuntimeObservation,
    resolveVoiceRuntimeTuning,
    serializeVoiceRuntimeTuningState,
    type VoiceRuntimeObservation,
} from '../features/voip-voice-relay/voiceRuntimeAutoTuning';

function obs(partial: Partial<VoiceRuntimeObservation> = {}): VoiceRuntimeObservation {
    return {
        segmentDurationMs: 2000,
        transcriptCharCount: 11, // 5.5 cps (기준)
        peakMeterDb: -28,
        meterAvailable: true,
        ...partial,
    };
}

describe('voiceRuntimeAutoTuning', () => {
    it('초기 상태는 미학습 + 기본 산출값', () => {
        const state = createInitialVoiceRuntimeTuningState();
        expect(state).toEqual({ speechRateCps: null, loudnessDb: null, sampleCount: 0 });
        const out = resolveVoiceRuntimeTuning(state);
        expect(out.ttsRate).toBe(TTS_RATE_DEFAULT);
        expect(out.ttsVolume).toBe(TTS_VOLUME_DEFAULT);
    });

    it('워밍업 전(1표본)에는 기본값 유지', () => {
        const s1 = applyVoiceRuntimeObservation(createInitialVoiceRuntimeTuningState(), obs());
        expect(s1.sampleCount).toBe(1);
        const out = resolveVoiceRuntimeTuning(s1);
        expect(out.ttsRate).toBe(TTS_RATE_DEFAULT);
    });

    it('너무 짧거나 글자수 부족한 표본은 무시', () => {
        const base = createInitialVoiceRuntimeTuningState();
        expect(applyVoiceRuntimeObservation(base, obs({ segmentDurationMs: 300 })).sampleCount).toBe(0);
        expect(applyVoiceRuntimeObservation(base, obs({ transcriptCharCount: 1 })).sampleCount).toBe(0);
    });

    it('비현실적 cps(환각)는 학습 제외', () => {
        const base = createInitialVoiceRuntimeTuningState();
        // 1000자 / 1초 = 1000 cps → 컷
        expect(applyVoiceRuntimeObservation(base, obs({ transcriptCharCount: 1000, segmentDurationMs: 1000 })).sampleCount).toBe(0);
    });

    it('빠르게 말하는 사용자 → TTS rate 상승(기본보다 빠름)', () => {
        let state = createInitialVoiceRuntimeTuningState();
        // 10 cps (20자 / 2s) — 기준 5.5 보다 빠름
        for (let i = 0; i < 4; i += 1) {
            state = applyVoiceRuntimeObservation(state, obs({ transcriptCharCount: 20, segmentDurationMs: 2000 }));
        }
        const out = resolveVoiceRuntimeTuning(state);
        expect(out.ttsRate).toBeGreaterThan(TTS_RATE_DEFAULT);
        expect(out.ttsRate).toBeLessThanOrEqual(TTS_RATE_MAX);
    });

    it('느리게 말하는 사용자 → TTS rate 하락(기본보다 느림)', () => {
        let state = createInitialVoiceRuntimeTuningState();
        // 2 cps (6자 / 3s) — 기준보다 느림
        for (let i = 0; i < 4; i += 1) {
            state = applyVoiceRuntimeObservation(state, obs({ transcriptCharCount: 6, segmentDurationMs: 3000 }));
        }
        const out = resolveVoiceRuntimeTuning(state);
        expect(out.ttsRate).toBeLessThan(TTS_RATE_DEFAULT);
        expect(out.ttsRate).toBeGreaterThanOrEqual(TTS_RATE_MIN);
    });

    it('크게 말하는 사용자(높은 peak dB) → 볼륨 상승', () => {
        let state = createInitialVoiceRuntimeTuningState();
        for (let i = 0; i < 4; i += 1) {
            state = applyVoiceRuntimeObservation(state, obs({ peakMeterDb: -12 }));
        }
        const out = resolveVoiceRuntimeTuning(state);
        expect(out.ttsVolume).toBeGreaterThan(TTS_VOLUME_DEFAULT - 0.001);
        expect(out.ttsVolume).toBeLessThanOrEqual(TTS_VOLUME_MAX);
    });

    it('작게 말하는 사용자(낮은 peak dB) → 볼륨 하락(하한 준수)', () => {
        let state = createInitialVoiceRuntimeTuningState();
        for (let i = 0; i < 4; i += 1) {
            state = applyVoiceRuntimeObservation(state, obs({ peakMeterDb: -55 }));
        }
        const out = resolveVoiceRuntimeTuning(state);
        expect(out.ttsVolume).toBeLessThan(TTS_VOLUME_DEFAULT);
        expect(out.ttsVolume).toBeGreaterThanOrEqual(TTS_VOLUME_MIN);
    });

    it('meterAvailable=false 면 볼륨 학습 제외(loudness null 유지)', () => {
        let state = createInitialVoiceRuntimeTuningState();
        for (let i = 0; i < 4; i += 1) {
            state = applyVoiceRuntimeObservation(state, obs({ peakMeterDb: -10, meterAvailable: false }));
        }
        expect(state.loudnessDb).toBeNull();
        const out = resolveVoiceRuntimeTuning(state);
        expect(out.ttsVolume).toBe(TTS_VOLUME_DEFAULT);
    });

    it('repeatRequested 면 속도↓·볼륨↑ (일회성, 상태 불변)', () => {
        let state = createInitialVoiceRuntimeTuningState();
        for (let i = 0; i < 3; i += 1) {
            state = applyVoiceRuntimeObservation(state, obs());
        }
        const normal = resolveVoiceRuntimeTuning(state);
        const repeat = resolveVoiceRuntimeTuning(state, { repeatRequested: true });
        expect(repeat.ttsRate).toBeLessThan(normal.ttsRate + 0.0001);
        expect(repeat.ttsVolume).toBeGreaterThanOrEqual(normal.ttsVolume);
    });

    it('산출값은 항상 안전 범위 내로 클램프', () => {
        let state = createInitialVoiceRuntimeTuningState();
        // 극단적으로 빠르고 큰 발화 반복
        for (let i = 0; i < 10; i += 1) {
            state = applyVoiceRuntimeObservation(state, obs({ transcriptCharCount: 38, segmentDurationMs: 2000, peakMeterDb: -3 }));
        }
        const out = resolveVoiceRuntimeTuning(state, { repeatRequested: false });
        expect(out.ttsRate).toBeGreaterThanOrEqual(TTS_RATE_MIN);
        expect(out.ttsRate).toBeLessThanOrEqual(TTS_RATE_MAX);
        expect(out.ttsVolume).toBeGreaterThanOrEqual(TTS_VOLUME_MIN);
        expect(out.ttsVolume).toBeLessThanOrEqual(TTS_VOLUME_MAX);
    });

    it('ingest 편의 함수는 상태+산출을 함께 반환', () => {
        const { state, output } = ingestVoiceRuntimeObservation(createInitialVoiceRuntimeTuningState(), obs());
        expect(state.sampleCount).toBe(1);
        expect(output.ttsRate).toBeGreaterThanOrEqual(TTS_RATE_MIN);
    });

    it('직렬화 ↔ 역직렬화 왕복 보존', () => {
        let state = createInitialVoiceRuntimeTuningState();
        state = applyVoiceRuntimeObservation(state, obs({ transcriptCharCount: 16, segmentDurationMs: 2000 }));
        state = applyVoiceRuntimeObservation(state, obs({ transcriptCharCount: 16, segmentDurationMs: 2000 }));
        const restored = deserializeVoiceRuntimeTuningState(serializeVoiceRuntimeTuningState(state));
        expect(restored).toEqual(state);
    });

    it('손상된 직렬화 입력은 초기 상태로 복구', () => {
        expect(deserializeVoiceRuntimeTuningState('not-json')).toEqual(createInitialVoiceRuntimeTuningState());
        expect(deserializeVoiceRuntimeTuningState(null)).toEqual(createInitialVoiceRuntimeTuningState());
        expect(deserializeVoiceRuntimeTuningState('{"sampleCount":"x"}')).toEqual(createInitialVoiceRuntimeTuningState());
    });
});

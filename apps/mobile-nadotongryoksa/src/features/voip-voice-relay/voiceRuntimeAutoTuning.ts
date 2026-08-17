/**
 * [기능 분리 Phase6.2] VoIP 통화 음성 속도·볼륨 런타임 자동 튜닝 — 순수 상태기계(SSOT, App/RN 비의존).
 *
 * 사장님 요청: "음성 전화 통화 음성 속도·볼륨 런타임 튜닝을 사용자 패턴에 맞게 자동감지 조절".
 *
 * 통화 중 매 STT 턴마다 관찰값(발화 길이/인식 글자수/피크 음량 dB)을 받아
 * 사용자의 평소 말하기 속도(글자/초)와 발성 음량을 EMA로 학습하고,
 * 이를 통역 TTS 재생의 rate(속도)·volume(볼륨)으로 환산한다.
 *
 *  - 빨리 말하는 사용자  → 빠른 통역 재생에 익숙 → ttsRate ↑
 *  - 천천히 말하는 사용자 → 느린 통역 재생 선호  → ttsRate ↓
 *  - 크게 말하는 사용자(시끄러운 환경 보정)        → ttsVolume ↑
 *  - 작게 말하는 사용자(조용한 환경)              → ttsVolume 기본 유지
 *  - 사용자가 다시 듣기를 요청(repeat)            → 그 턴은 ttsRate ↓ · ttsVolume ↑ (접근성)
 *
 * RN/타이머/오디오/스토리지에 의존하지 않는 순수 함수만 노출 → 단위 테스트로 회귀를 막는다.
 * 실제 영속화(AsyncStorage)·Speech.speak/Sound 적용은 VoIPCallScreen 이 이 모듈의 산출값으로 수행한다.
 */

/** TTS 재생 속도 한계(expo-speech rate). 너무 느리거나 빠르면 알아듣기 어려우므로 안전 범위로 고정. */
export const TTS_RATE_MIN = 0.85;
export const TTS_RATE_MAX = 1.25;
export const TTS_RATE_DEFAULT = 1.05;

/** TTS 재생 볼륨 한계(0~1). 통화 음량이라 하한을 0.7 로 둬 너무 작아지지 않게 한다. */
export const TTS_VOLUME_MIN = 0.7;
export const TTS_VOLUME_MAX = 1.0;
export const TTS_VOLUME_DEFAULT = 1.0;

/**
 * 기준 말하기 속도(글자/초). 한국어/일본어 보통 대화 속도 ≈ 5~7 cps.
 * 사용자 cps 가 이 값보다 빠르면 rate↑, 느리면 rate↓ 로 비례 조정한다.
 */
const REFERENCE_SPEECH_CPS = 5.5;

/** cps 편차가 TTS rate 에 반영되는 민감도(±). 1.0=기준 대비 100% 편차 시 ±SENSITIVITY 만큼 이동. */
const RATE_SENSITIVITY = 0.28;

/** 음량 환산 기준 피크 dB. 이 값보다 크게(가깝게) 말하면 volume↑, 작으면 기본 유지. */
const REFERENCE_PEAK_DB = -28;

/** dB 1 단위당 볼륨 증가량. (-18dB 처럼 크게 말하면 +0.1 → 시끄러운 환경 보정) */
const VOLUME_DB_GAIN = 0.012;

/** EMA 가중치(최근 표본에 더 큰 비중). */
const EMA_ALPHA = 0.3;

/** 학습이 안정되기 전(워밍업) 최소 표본 수. 이 전에는 기본값으로 보수적 반환. */
const WARMUP_SAMPLES = 2;

/** 한 턴이 학습 표본으로 인정되는 최소 발화 길이/글자수(잡음·환각 컷). */
const MIN_VALID_DURATION_MS = 600;
const MIN_VALID_CHARS = 2;

export interface VoiceRuntimeObservation {
    /** VAD 가 측정한 발화 구간 길이(ms). */
    segmentDurationMs: number;
    /** STT 가 인식한 전사 글자수(공백 제거 권장). */
    transcriptCharCount: number;
    /** 사용자 발화의 피크 음량(dB, -160~0). meterAvailable=false 면 볼륨 학습에서 제외. */
    peakMeterDb: number;
    /** 단말 미터가 신뢰 가능한지(메트릭 죽은 기기는 false). */
    meterAvailable: boolean;
}

export interface VoiceRuntimeTuningState {
    /** 사용자 말하기 속도 EMA(글자/초). 미학습이면 null. */
    speechRateCps: number | null;
    /** 사용자 발성 피크 음량 EMA(dB). 미학습이면 null. */
    loudnessDb: number | null;
    /** 학습에 사용된 유효 표본 수. */
    sampleCount: number;
}

export interface VoiceRuntimeTuningOutput {
    /** 통역 TTS 재생 속도(expo-speech rate). */
    ttsRate: number;
    /** 통역 TTS 재생 볼륨(0~1). */
    ttsVolume: number;
}

/** 옵션: 이번 산출에 한해 적용할 일회성 조정(영속 상태는 바꾸지 않음). */
export interface VoiceRuntimeResolveOptions {
    /** 사용자가 '다시 듣기'를 요청한 턴 → 속도↓·볼륨↑ 로 접근성 강화. */
    repeatRequested?: boolean;
}

function clamp(value: number, min: number, max: number): number {
    if (!Number.isFinite(value)) return min;
    return Math.min(max, Math.max(min, value));
}

function round2(value: number): number {
    return Math.round(value * 100) / 100;
}

export function createInitialVoiceRuntimeTuningState(): VoiceRuntimeTuningState {
    return { speechRateCps: null, loudnessDb: null, sampleCount: 0 };
}

function ema(prev: number | null, next: number, alpha: number = EMA_ALPHA): number {
    if (prev == null || !Number.isFinite(prev)) return next;
    return prev + alpha * (next - prev);
}

/**
 * 관찰값 1건을 학습에 반영한다(순수). 유효하지 않은 표본(너무 짧음/글자수 부족)은 무시한다.
 * 음량은 meterAvailable=true 인 표본만 EMA 에 반영한다(메트릭 죽은 기기 보호).
 */
export function applyVoiceRuntimeObservation(
    state: VoiceRuntimeTuningState,
    obs: VoiceRuntimeObservation,
): VoiceRuntimeTuningState {
    const durationMs = Number(obs.segmentDurationMs);
    const chars = Number(obs.transcriptCharCount);
    if (!Number.isFinite(durationMs) || durationMs < MIN_VALID_DURATION_MS) return state;
    if (!Number.isFinite(chars) || chars < MIN_VALID_CHARS) return state;

    const cps = chars / (durationMs / 1000);
    // 비현실적 cps(환각/초단발) 컷: 0.5~20 cps 범위만 학습.
    if (cps < 0.5 || cps > 20) return state;

    const nextRate = ema(state.speechRateCps, cps);

    let nextLoudness = state.loudnessDb;
    if (obs.meterAvailable && Number.isFinite(obs.peakMeterDb) && obs.peakMeterDb > -159) {
        nextLoudness = ema(state.loudnessDb, obs.peakMeterDb);
    }

    return {
        speechRateCps: round2(nextRate),
        loudnessDb: nextLoudness == null ? null : round2(nextLoudness),
        sampleCount: state.sampleCount + 1,
    };
}

/**
 * 현재 학습 상태로 TTS rate/volume 을 환산한다(순수). 워밍업 전에는 기본값을 반환한다.
 * repeatRequested 면 이번 산출에 한해 속도↓(-0.12)·볼륨↑(+0.1) 보정한다.
 */
export function resolveVoiceRuntimeTuning(
    state: VoiceRuntimeTuningState,
    options: VoiceRuntimeResolveOptions = {},
): VoiceRuntimeTuningOutput {
    let rate = TTS_RATE_DEFAULT;
    let volume = TTS_VOLUME_DEFAULT;

    const warmedUp = state.sampleCount >= WARMUP_SAMPLES;

    if (warmedUp && state.speechRateCps != null) {
        const deviation = (state.speechRateCps - REFERENCE_SPEECH_CPS) / REFERENCE_SPEECH_CPS;
        rate = TTS_RATE_DEFAULT + deviation * RATE_SENSITIVITY;
    }

    if (warmedUp && state.loudnessDb != null) {
        // 기준보다 크게 말하면(피크 dB 가 높으면) 시끄러운 환경 보정으로 볼륨↑.
        volume = TTS_VOLUME_DEFAULT - Math.max(0, REFERENCE_PEAK_DB - state.loudnessDb) * VOLUME_DB_GAIN
            + Math.max(0, state.loudnessDb - REFERENCE_PEAK_DB) * VOLUME_DB_GAIN;
    }

    if (options.repeatRequested) {
        rate -= 0.12;
        volume += 0.1;
    }

    return {
        ttsRate: round2(clamp(rate, TTS_RATE_MIN, TTS_RATE_MAX)),
        ttsVolume: round2(clamp(volume, TTS_VOLUME_MIN, TTS_VOLUME_MAX)),
    };
}

/** 관찰 반영 + 산출을 한 번에(편의 함수). 반환 state 를 영속화하면 통화 간 학습이 누적된다. */
export function ingestVoiceRuntimeObservation(
    state: VoiceRuntimeTuningState,
    obs: VoiceRuntimeObservation,
    options: VoiceRuntimeResolveOptions = {},
): { state: VoiceRuntimeTuningState; output: VoiceRuntimeTuningOutput } {
    const nextState = applyVoiceRuntimeObservation(state, obs);
    return { state: nextState, output: resolveVoiceRuntimeTuning(nextState, options) };
}

/** 영속 직렬화(저장) — 숫자 3필드만. 손상 입력은 초기 상태로 복구. */
export function serializeVoiceRuntimeTuningState(state: VoiceRuntimeTuningState): string {
    return JSON.stringify({
        speechRateCps: state.speechRateCps,
        loudnessDb: state.loudnessDb,
        sampleCount: state.sampleCount,
    });
}

/** 영속 역직렬화(복원) — 형식이 어긋나면 초기 상태로 안전 복구. */
export function deserializeVoiceRuntimeTuningState(raw: string | null | undefined): VoiceRuntimeTuningState {
    if (!raw) return createInitialVoiceRuntimeTuningState();
    try {
        const parsed = JSON.parse(raw) as Partial<VoiceRuntimeTuningState>;
        const speechRateCps = typeof parsed.speechRateCps === 'number' && Number.isFinite(parsed.speechRateCps)
            ? parsed.speechRateCps
            : null;
        const loudnessDb = typeof parsed.loudnessDb === 'number' && Number.isFinite(parsed.loudnessDb)
            ? parsed.loudnessDb
            : null;
        const sampleCount = typeof parsed.sampleCount === 'number' && Number.isFinite(parsed.sampleCount)
            ? Math.max(0, Math.floor(parsed.sampleCount))
            : 0;
        return { speechRateCps, loudnessDb, sampleCount };
    } catch {
        return createInitialVoiceRuntimeTuningState();
    }
}

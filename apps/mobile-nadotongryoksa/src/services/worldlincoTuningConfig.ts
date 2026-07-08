import AsyncStorage from '@react-native-async-storage/async-storage';

export type WorldlincoVoipTuning = {
    silero_silence_ms: number;
    silero_speech_ms: number;
    silero_min_segment_ms: number;
    silero_min_speech_span_ms: number;
    silero_safety_cap_ms: number;
    silero_post_flush_cooldown_ms: number;
    remote_echo_guard_ms: number;
    speaker_echo_guard_ms: number;
    remote_listen_hold_ms: number;
    post_playback_guard_ms: number;
    fairness_barge_in_ms: number;
    vad_silence_flush_ms: number;
    vad_min_segment_ms: number;
    vad_max_segment_ms: number;
    speech_meter_min_db: number;
    file_speech_rms_db: number;
    meter_unavailable_fixed_flush_ms: number;
};

export type WorldlincoFaceTuning = {
    silence_flush_ms: number;
    min_segment_ms: number;
    max_segment_ms: number;
    file_speech_rms_db: number;
    meter_poll_every: number;
    restart_ms: number;
    playback_cap_ms: number;
};

export type WorldlincoTuningSnapshot = {
    version: number;
    updated_at: string | null;
    voip: WorldlincoVoipTuning;
    face_conversation: WorldlincoFaceTuning;
};

export const WORLDLINGCO_TUNING_DEFAULTS: WorldlincoTuningSnapshot = {
    version: 1,
    updated_at: null,
    // NOTE: 런타임 SSOT(backend /api/marketplace/worldlinco/tuning)와 정합 유지.
    // 원격 fetch 실패 시에도 14s/12s 과배칭으로 회귀하지 않도록 calibrated 값과 동일하게 둔다.
    voip: {
        silero_silence_ms: 1400,
        silero_speech_ms: 120,
        silero_min_segment_ms: 2400,
        silero_min_speech_span_ms: 1700,
        silero_safety_cap_ms: 12000,
        silero_post_flush_cooldown_ms: 1000,
        remote_echo_guard_ms: 3000,
        speaker_echo_guard_ms: 4000,
        remote_listen_hold_ms: 2600,
        post_playback_guard_ms: 550,
        fairness_barge_in_ms: 7000,
        vad_silence_flush_ms: 1500,
        vad_min_segment_ms: 2200,
        vad_max_segment_ms: 12000,
        speech_meter_min_db: -52,
        file_speech_rms_db: -52,
        meter_unavailable_fixed_flush_ms: 4000,
    },
    face_conversation: {
        silence_flush_ms: 1600,
        min_segment_ms: 2200,
        max_segment_ms: 12000,
        file_speech_rms_db: -50,
        meter_poll_every: 2,
        restart_ms: 250,
        playback_cap_ms: 10000,
    },
};

const STORAGE_KEY = '@worldlinco/tuning/v1';

let cachedSnapshot: WorldlincoTuningSnapshot = { ...WORLDLINGCO_TUNING_DEFAULTS };
let refreshPromise: Promise<WorldlincoTuningSnapshot> | null = null;

function mergeSection<T extends Record<string, number>>(
    defaults: T,
    remote?: Partial<T> | null,
): T {
    if (!remote) {
        return { ...defaults };
    }
    const merged = { ...defaults };
    for (const key of Object.keys(defaults) as (keyof T)[]) {
        const value = remote[key];
        if (typeof value === 'number' && Number.isFinite(value)) {
            merged[key] = value;
        }
    }
    return merged;
}

function mergeTuningPayload(payload: Partial<WorldlincoTuningSnapshot> | null | undefined): WorldlincoTuningSnapshot {
    return {
        version: typeof payload?.version === 'number' ? payload.version : WORLDLINGCO_TUNING_DEFAULTS.version,
        updated_at: typeof payload?.updated_at === 'string' ? payload.updated_at : null,
        voip: mergeSection(WORLDLINGCO_TUNING_DEFAULTS.voip, payload?.voip),
        face_conversation: mergeSection(WORLDLINGCO_TUNING_DEFAULTS.face_conversation, payload?.face_conversation),
    };
}

export function getWorldlincoTuning(): WorldlincoTuningSnapshot {
    return cachedSnapshot;
}

export async function hydrateWorldlincoTuningFromStorage(): Promise<WorldlincoTuningSnapshot> {
    try {
        const raw = await AsyncStorage.getItem(STORAGE_KEY);
        if (!raw) {
            return cachedSnapshot;
        }
        cachedSnapshot = mergeTuningPayload(JSON.parse(raw));
    } catch {
        // keep in-memory defaults
    }
    return cachedSnapshot;
}

export async function refreshWorldlincoTuning(apiBaseUrl: string): Promise<WorldlincoTuningSnapshot> {
    if (refreshPromise) {
        return refreshPromise;
    }
    refreshPromise = (async () => {
        try {
            const response = await fetch(`${apiBaseUrl.replace(/\/$/, '')}/api/marketplace/worldlinco/tuning`, {
                method: 'GET',
                headers: { Accept: 'application/json' },
            });
            if (response.ok) {
                const payload = await response.json();
                cachedSnapshot = mergeTuningPayload(payload);
                await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(cachedSnapshot));
                console.log('[WORLDLINGCO_TUNING]', JSON.stringify({
                    event: 'remote_loaded',
                    updated_at: cachedSnapshot.updated_at,
                    version: cachedSnapshot.version,
                }));
            }
        } catch (error) {
            console.log('[WORLDLINGCO_TUNING]', JSON.stringify({
                event: 'remote_load_failed',
                message: error instanceof Error ? error.message : 'unknown',
            }));
            await hydrateWorldlincoTuningFromStorage();
        } finally {
            refreshPromise = null;
        }
        return cachedSnapshot;
    })();
    return refreshPromise;
}

export function resolveSileroBoundaryFromTuning(tuning: WorldlincoTuningSnapshot = cachedSnapshot) {
    return {
        silenceMs: tuning.voip.silero_silence_ms,
        speechMs: tuning.voip.silero_speech_ms,
        minSegmentMs: tuning.voip.silero_min_segment_ms,
        minSpeechSpanMs: tuning.voip.silero_min_speech_span_ms,
        safetyCapMs: tuning.voip.silero_safety_cap_ms,
        postFlushCooldownMs: tuning.voip.silero_post_flush_cooldown_ms,
    };
}

export function resolveFaceVadDefaultsFromTuning(tuning: WorldlincoTuningSnapshot = cachedSnapshot) {
    return {
        maxSegmentMs: tuning.face_conversation.max_segment_ms,
        silenceFlushMs: tuning.face_conversation.silence_flush_ms,
        minSegmentMs: tuning.face_conversation.min_segment_ms,
        meterUnavailableFilePollEvery: tuning.face_conversation.meter_poll_every,
        speechMeterMinDb: tuning.voip.speech_meter_min_db,
        meterUnavailableFixedFlushMs: tuning.voip.meter_unavailable_fixed_flush_ms,
        meterPollMs: 180,
    };
}

export function resolveFaceFileSpeechRmsDb(tuning: WorldlincoTuningSnapshot = cachedSnapshot): number {
    return tuning.face_conversation.file_speech_rms_db;
}

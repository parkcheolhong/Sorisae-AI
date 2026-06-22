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
    // 실시간 라이브 듀플렉스(1=ON): 원격 원음을 끊지 않고(라이브 통화) 통역을 자막/TTS 오버레이로.
    // 턴 잠금(listen-hold) 캡처 차단을 해제해 무전기 느낌 제거. 0 이면 기존 반이중(무전기) 동작.
    // 백엔드 SSOT(/api/marketplace/worldlinco/tuning)에서 0 으로 내리면 빌드 없이 즉시 회귀 가능.
    live_duplex_mode: number;
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
        // 0=휴면(기존 동작 유지). 서버측 STT(P-server) 가 들어와 클라가 마이크를 점유하지 않게 된 뒤
        // 1 로 올린다. 클라 단독으로 1 로 두면 마이크 점유 충돌로 라이브 음성이 흐르지 못한다(R7).
        live_duplex_mode: 0,
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
            merged[key] = value as T[keyof T];
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

// ── 서버 미디어 브리지(MCU) 런타임 플래그 (체크리스트 §13 / MB-5) ──────────────
// 서버가 통화 미디어를 종단·중계하고 STT/번역/TTS 를 처리하는 모드.
// 통화 중 서버 answer(from_role='server_bridge') 수신 시 켜진다(통화 단위 런타임).
// 켜지면: (1) 라이브 듀플렉스 동작(원음 연속, 무전기 제거)이 강제 활성,
//        (2) 클라 로컬 STT 캡처/마이크 잠금/voice_translation 송신을 전면 중단(서버가 대신 수행).
let serverBridgeActive = false;

export function setVoipServerBridgeActive(active: boolean): void {
    serverBridgeActive = active;
}

export function isVoipServerBridgeActive(): boolean {
    return serverBridgeActive;
}

// 라이브 연속 음성(무전기 제거) 활성 여부:
//  - 서버 브리지 모드면 무조건 활성(서버가 STT 하므로 마이크 점유 충돌 없음 → R7 해소),
//  - 아니면 기존 P1 플래그(live_duplex_mode===1).
export function isLiveDuplexActive(): boolean {
    return serverBridgeActive || cachedSnapshot.voip.live_duplex_mode === 1;
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

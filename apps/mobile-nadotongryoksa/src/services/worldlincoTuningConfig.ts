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
    playback_drain_ms: number;
    tts_rate: number;
};

export type WorldlincoTuningSnapshot = {
    version: number;
    updated_at: string | null;
    voip: WorldlincoVoipTuning;
    face_conversation: WorldlincoFaceTuning;
};

export type ResolvedFaceVadConfig = {
    maxSegmentMs: number;
    silenceFlushMs: number;
    minSegmentMs: number;
    meterUnavailableFilePollEvery: number;
    speechMeterMinDb: number;
    meterUnavailableFixedFlushMs: number;
    meterPollMs: number;
};

export type WorldlincoRuntimeAutoProfile = 'default' | 'face' | 'sorisae' | 'voip';

export const WORLDLINGCO_TUNING_DEFAULTS: WorldlincoTuningSnapshot = {
    version: 6,
    updated_at: '2026-07-05T06:55:00Z',
    // NOTE: 런타임 SSOT(backend /api/marketplace/worldlinco/tuning)와 정합 유지.
    // 원격 fetch 실패 시에도 과거 14s/12s 과배칭으로 회귀하지 않도록 calibrated 값과 동일하게 둔다.
    voip: {
        silero_silence_ms: 1000,
        silero_speech_ms: 120,
        silero_min_segment_ms: 3000,
        silero_min_speech_span_ms: 1700,
        silero_safety_cap_ms: 7000,
        silero_post_flush_cooldown_ms: 1000,
        remote_echo_guard_ms: 4800,
        speaker_echo_guard_ms: 5800,
        remote_listen_hold_ms: 2600,
        post_playback_guard_ms: 550,
        fairness_barge_in_ms: 7000,
        vad_silence_flush_ms: 1000,
        vad_min_segment_ms: 3000,
        vad_max_segment_ms: 7000,
        speech_meter_min_db: -52,
        file_speech_rms_db: -52,
        meter_unavailable_fixed_flush_ms: 4000,
        // 0=휴면(기존 동작 유지). 서버측 STT(P-server) 가 들어와 클라가 마이크를 점유하지 않게 된 뒤
        // 1 로 올린다. 클라 단독으로 1 로 두면 마이크 점유 충돌로 라이브 음성이 흐르지 못한다(R7).
        live_duplex_mode: 0,
    },
    face_conversation: {
        silence_flush_ms: 1000,
        min_segment_ms: 1800,
        max_segment_ms: 18000,
        file_speech_rms_db: -50,
        meter_poll_every: 2,
        restart_ms: 290,
        playback_cap_ms: 45_000,
        playback_drain_ms: 1300,
        tts_rate: 0.95,
    },
};

const STORAGE_KEY = '@worldlinco/tuning/v1';

let cachedSnapshot: WorldlincoTuningSnapshot = { ...WORLDLINGCO_TUNING_DEFAULTS };
let refreshPromise: Promise<WorldlincoTuningSnapshot> | null = null;
let runtimeAutoProfile: WorldlincoRuntimeAutoProfile = 'default';

type WorldlincoTelemetryUploadContext = {
    apiBaseUrl: string;
    getAuthToken: () => string;
    getUserId?: () => string;
    getRunId?: () => string;
    getDeviceId?: () => string;
};

type WorldlincoTelemetryItem = {
    source: string;
    feature: string;
    metric: string;
    value: number;
    unit?: string;
    timestamp?: string;
    device_id?: string;
    run_id?: string;
    tags?: Record<string, string>;
};

const WORLDLINCO_TELEMETRY_FLUSH_INTERVAL_MS = 45_000;
const WORLDLINCO_TELEMETRY_FLUSH_THRESHOLD = 6;
const WORLDLINCO_TELEMETRY_BATCH_SIZE = 24;
const WORLDLINCO_TELEMETRY_MAX_QUEUE = 240;
const WORLDLINCO_TELEMETRY_QUEUE_STORAGE_KEY = '@worldlinco/telemetry-queue/v1';

let telemetryUploadContext: WorldlincoTelemetryUploadContext | null = null;
let telemetryQueue: WorldlincoTelemetryItem[] = [];
let telemetryFlushTimer: ReturnType<typeof setTimeout> | null = null;
let telemetryFlushInFlight: Promise<void> | null = null;
let telemetryQueueHydrationPromise: Promise<void> | null = null;
let telemetryQueueHydrated = false;

type VoiceAutoTuningRuntime = {
    faceTurns: number;
    faceOverlapEvents: number;
    faceRoundtripEmaMs: number;
    facePlaybackEmaMs: number;
    voipTurns: number;
    voipEchoBlocks: number;
    voipFairnessBargeIns: number;
};

const AUTO_TUNING_ALPHA = 0.18;
const autoRuntime: VoiceAutoTuningRuntime = {
    faceTurns: 0,
    faceOverlapEvents: 0,
    faceRoundtripEmaMs: 0,
    facePlaybackEmaMs: 0,
    voipTurns: 0,
    voipEchoBlocks: 0,
    voipFairnessBargeIns: 0,
};

function clearTelemetryFlushTimer(): void {
    if (telemetryFlushTimer) {
        clearTimeout(telemetryFlushTimer);
        telemetryFlushTimer = null;
    }
}

function normalizeTelemetryQueueItem(raw: unknown): WorldlincoTelemetryItem | null {
    if (!raw || typeof raw !== 'object') {
        return null;
    }
    const item = raw as Record<string, unknown>;
    const source = String(item.source || '').trim();
    const feature = String(item.feature || '').trim();
    const metric = String(item.metric || '').trim();
    const value = Number(item.value);
    if (!source || !feature || !metric || !Number.isFinite(value)) {
        return null;
    }
    const tagsRaw = item.tags;
    const tags = tagsRaw && typeof tagsRaw === 'object'
        ? Object.fromEntries(Object.entries(tagsRaw as Record<string, unknown>).map(([k, v]) => [String(k), String(v)]))
        : undefined;
    return {
        source,
        feature,
        metric,
        value,
        unit: item.unit != null ? String(item.unit) : undefined,
        timestamp: item.timestamp != null ? String(item.timestamp) : undefined,
        device_id: item.device_id != null ? String(item.device_id) : undefined,
        run_id: item.run_id != null ? String(item.run_id) : undefined,
        tags,
    };
}

function persistTelemetryQueue(): void {
    void AsyncStorage.setItem(
        WORLDLINCO_TELEMETRY_QUEUE_STORAGE_KEY,
        JSON.stringify(telemetryQueue.slice(-WORLDLINCO_TELEMETRY_MAX_QUEUE)),
    ).catch((error) => {
        console.log('[WORLDLINGCO_TELEMETRY]', JSON.stringify({
            event: 'queue_persist_failed',
            message: error instanceof Error ? error.message : 'unknown',
        }));
    });
}

function hydrateTelemetryQueue(): Promise<void> {
    if (telemetryQueueHydrated) {
        return Promise.resolve();
    }
    if (telemetryQueueHydrationPromise) {
        return telemetryQueueHydrationPromise;
    }
    telemetryQueueHydrationPromise = (async () => {
        try {
            const raw = await AsyncStorage.getItem(WORLDLINCO_TELEMETRY_QUEUE_STORAGE_KEY);
            if (!raw) {
                telemetryQueueHydrated = true;
                return;
            }
            const parsed = JSON.parse(raw);
            if (!Array.isArray(parsed)) {
                telemetryQueueHydrated = true;
                return;
            }
            const restored = parsed
                .map((item) => normalizeTelemetryQueueItem(item))
                .filter((item): item is WorldlincoTelemetryItem => Boolean(item));
            telemetryQueue = [...restored, ...telemetryQueue].slice(-WORLDLINCO_TELEMETRY_MAX_QUEUE);
            telemetryQueueHydrated = true;
        } catch (error) {
            console.log('[WORLDLINGCO_TELEMETRY]', JSON.stringify({
                event: 'queue_hydrate_failed',
                message: error instanceof Error ? error.message : 'unknown',
            }));
            telemetryQueueHydrated = true;
        } finally {
            telemetryQueueHydrationPromise = null;
        }
    })();
    return telemetryQueueHydrationPromise;
}

function scheduleTelemetryFlush(delayMs: number = WORLDLINCO_TELEMETRY_FLUSH_INTERVAL_MS): void {
    clearTelemetryFlushTimer();
    telemetryFlushTimer = setTimeout(() => {
        void flushWorldlincoTelemetryQueue('interval');
    }, Math.max(1_000, delayMs));
}

function enqueueWorldlincoTelemetryMetric(item: WorldlincoTelemetryItem): void {
    if (!telemetryQueueHydrated) {
        void hydrateTelemetryQueue();
    }
    telemetryQueue.push(item);
    if (telemetryQueue.length > WORLDLINCO_TELEMETRY_MAX_QUEUE) {
        telemetryQueue = telemetryQueue.slice(-WORLDLINCO_TELEMETRY_MAX_QUEUE);
    }
    persistTelemetryQueue();
    if (telemetryQueue.length >= WORLDLINCO_TELEMETRY_FLUSH_THRESHOLD) {
        void flushWorldlincoTelemetryQueue('threshold');
        return;
    }
    scheduleTelemetryFlush();
}

export function configureWorldlincoTelemetryUploader(context: WorldlincoTelemetryUploadContext | null): void {
    telemetryUploadContext = context && context.apiBaseUrl
        ? {
            ...context,
            apiBaseUrl: context.apiBaseUrl.replace(/\/$/, ''),
        }
        : null;
    void hydrateTelemetryQueue().then(() => {
        if (telemetryUploadContext && telemetryQueue.length > 0) {
            void flushWorldlincoTelemetryQueue('context-update');
        }
    });
}

void hydrateTelemetryQueue().catch(() => {
    // no-op
});

export function flushWorldlincoTelemetryQueue(reason: string = 'manual'): Promise<void> {
    if (telemetryFlushInFlight) {
        return telemetryFlushInFlight;
    }

    telemetryFlushInFlight = (async () => {
        await hydrateTelemetryQueue();
        const context = telemetryUploadContext;
        if (!context || telemetryQueue.length === 0) {
            return;
        }

        const token = String(context.getAuthToken() || '').trim();
        if (!token) {
            scheduleTelemetryFlush();
            return;
        }

        const batch = telemetryQueue.slice(0, WORLDLINCO_TELEMETRY_BATCH_SIZE);
        if (!batch.length) {
            return;
        }

        const userId = context.getUserId ? String(context.getUserId() || '').trim() : '';
        const deviceId = context.getDeviceId ? String(context.getDeviceId() || '').trim() : '';
        const runId = context.getRunId ? String(context.getRunId() || '').trim() : '';
        const stampedBatch = batch.map((item) => ({
            ...item,
            timestamp: item.timestamp || new Date().toISOString(),
            device_id: item.device_id || deviceId || undefined,
            run_id: item.run_id || runId || undefined,
            tags: {
                ...(item.tags || {}),
                upload_reason: reason,
                ...(userId ? { user_id: userId } : {}),
            },
        }));

        try {
            const response = await fetch(`${context.apiBaseUrl}/api/marketplace/worldlinco/telemetry/upload`, {
                method: 'POST',
                headers: {
                    Accept: 'application/json',
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({
                    note: 'mobile-auto-upload',
                    items: stampedBatch,
                }),
            });
            if (response.ok) {
                telemetryQueue = telemetryQueue.slice(stampedBatch.length);
                persistTelemetryQueue();
            } else {
                console.log('[WORLDLINGCO_TELEMETRY]', JSON.stringify({
                    event: 'flush_failed',
                    status: response.status,
                    queued: telemetryQueue.length,
                }));
            }
        } catch (error) {
            console.log('[WORLDLINGCO_TELEMETRY]', JSON.stringify({
                event: 'flush_error',
                message: error instanceof Error ? error.message : 'unknown',
                queued: telemetryQueue.length,
            }));
        } finally {
            if (telemetryQueue.length > 0) {
                scheduleTelemetryFlush(telemetryQueue.length >= WORLDLINCO_TELEMETRY_FLUSH_THRESHOLD ? 2_500 : WORLDLINCO_TELEMETRY_FLUSH_INTERVAL_MS);
            } else {
                clearTelemetryFlushTimer();
            }
        }
    })().finally(() => {
        telemetryFlushInFlight = null;
    });

    return telemetryFlushInFlight;
}

function clamp(value: number, min: number, max: number): number {
    return Math.max(min, Math.min(max, value));
}

function updateEma(prev: number, next: number): number {
    if (!Number.isFinite(next) || next <= 0) {
        return prev;
    }
    if (prev <= 0) {
        return next;
    }
    return (prev * (1 - AUTO_TUNING_ALPHA)) + (next * AUTO_TUNING_ALPHA);
}

function buildAutoTunedSnapshot(base: WorldlincoTuningSnapshot): WorldlincoTuningSnapshot {
    const faceOverlapRate = autoRuntime.faceTurns > 0
        ? autoRuntime.faceOverlapEvents / autoRuntime.faceTurns
        : 0;
    const voipEchoRate = autoRuntime.voipTurns > 0
        ? autoRuntime.voipEchoBlocks / autoRuntime.voipTurns
        : 0;
    const voipFairnessRate = autoRuntime.voipTurns > 0
        ? autoRuntime.voipFairnessBargeIns / autoRuntime.voipTurns
        : 0;

    const roundtripPenalty = autoRuntime.faceRoundtripEmaMs > 0
        ? clamp((autoRuntime.faceRoundtripEmaMs - 3200) * 0.05, -120, 260)
        : 0;
    const overlapPenalty = clamp(faceOverlapRate * 260, 0, 260);
    const playbackDrivenCap = autoRuntime.facePlaybackEmaMs > 0
        ? clamp((autoRuntime.facePlaybackEmaMs * 1.35) + 900, 6_000, 20_000)
        : base.face_conversation.playback_cap_ms;

    const adaptiveFaceRestartMs = Math.round(clamp(
        base.face_conversation.restart_ms + roundtripPenalty + overlapPenalty,
        120,
        1_200,
    ));
    const adaptiveFacePlaybackCapMs = Math.round(clamp(
        Math.max(base.face_conversation.playback_cap_ms, playbackDrivenCap),
        6_000,
        20_000,
    ));

    const adaptiveRemoteListenHoldMs = Math.round(clamp(
        base.voip.remote_listen_hold_ms + (voipEchoRate * 800) - (voipFairnessRate * 500),
        1_200,
        4_500,
    ));
    const adaptivePostPlaybackGuardMs = Math.round(clamp(
        base.voip.post_playback_guard_ms + (voipEchoRate * 220),
        250,
        1_400,
    ));
    const adaptiveFairnessBargeInMs = Math.round(clamp(
        base.voip.fairness_barge_in_ms - (voipFairnessRate * 1400),
        2_500,
        9_000,
    ));

    return {
        ...base,
        voip: {
            ...base.voip,
            remote_listen_hold_ms: adaptiveRemoteListenHoldMs,
            post_playback_guard_ms: adaptivePostPlaybackGuardMs,
            fairness_barge_in_ms: adaptiveFairnessBargeInMs,
        },
        face_conversation: {
            ...base.face_conversation,
            restart_ms: adaptiveFaceRestartMs,
            playback_cap_ms: adaptiveFacePlaybackCapMs,
        },
    };
}

function applyRuntimeAutoProfile(
    base: WorldlincoTuningSnapshot,
    profile: WorldlincoRuntimeAutoProfile,
): WorldlincoTuningSnapshot {
    if (profile === 'sorisae') {
        return {
            ...base,
            face_conversation: {
                ...base.face_conversation,
                silence_flush_ms: 1000,
                min_segment_ms: 1700,
                max_segment_ms: 6500,
                restart_ms: 240,
                playback_cap_ms: 50000,
            },
        };
    }
    if (profile === 'face') {
        return {
            ...base,
            face_conversation: {
                ...base.face_conversation,
                silence_flush_ms: 1000,
                min_segment_ms: 1800,
                max_segment_ms: 18000,
                restart_ms: 240,
                playback_cap_ms: 50000,
            },
        };
    }
    if (profile === 'voip') {
        return {
            ...base,
            voip: {
                ...base.voip,
                silero_silence_ms: 1000,
                silero_speech_ms: 120,
                silero_min_segment_ms: 3000,
                silero_min_speech_span_ms: 1700,
                silero_safety_cap_ms: 7000,
                silero_post_flush_cooldown_ms: 1000,
                remote_echo_guard_ms: 4800,
                speaker_echo_guard_ms: 5800,
                remote_listen_hold_ms: 2600,
                post_playback_guard_ms: 550,
                fairness_barge_in_ms: 7000,
                vad_silence_flush_ms: 1000,
                vad_min_segment_ms: 3000,
                vad_max_segment_ms: 7000,
                speech_meter_min_db: -52,
                file_speech_rms_db: -52,
                meter_unavailable_fixed_flush_ms: 4000,
            },
        };
    }
    return {
        ...base,
        face_conversation: {
            ...base.face_conversation,
            silence_flush_ms: 1000,
            min_segment_ms: 1800,
            max_segment_ms: 18000,
            restart_ms: 240,
            playback_cap_ms: 50000,
        },
        voip: {
            ...base.voip,
            silero_silence_ms: 1000,
            silero_speech_ms: 120,
            silero_min_segment_ms: 3000,
            silero_min_speech_span_ms: 1700,
            silero_safety_cap_ms: 7000,
            silero_post_flush_cooldown_ms: 1000,
            remote_echo_guard_ms: 4800,
            speaker_echo_guard_ms: 5800,
            remote_listen_hold_ms: 2600,
            post_playback_guard_ms: 550,
            fairness_barge_in_ms: 7000,
            vad_silence_flush_ms: 1000,
            vad_min_segment_ms: 3000,
            vad_max_segment_ms: 7000,
            speech_meter_min_db: -52,
            file_speech_rms_db: -52,
            meter_unavailable_fixed_flush_ms: 4000,
        },
    };
}

export function setWorldlincoRuntimeAutoProfile(profile: WorldlincoRuntimeAutoProfile): void {
    if (runtimeAutoProfile === profile) {
        return;
    }
    runtimeAutoProfile = profile;
    console.log('[WORLDLINGCO_TUNING]', JSON.stringify({
        event: 'runtime_auto_profile_changed',
        profile,
    }));
}

export function getWorldlincoRuntimeAutoProfile(): WorldlincoRuntimeAutoProfile {
    return runtimeAutoProfile;
}

export function reportFaceVoiceAutoTuningMetric(sample: {
    roundtripMs?: number;
    playbackMs?: number;
    overlapDetected?: boolean;
}): void {
    autoRuntime.faceTurns += 1;
    if (sample.overlapDetected) {
        autoRuntime.faceOverlapEvents += 1;
    }
    if (typeof sample.roundtripMs === 'number') {
        autoRuntime.faceRoundtripEmaMs = updateEma(autoRuntime.faceRoundtripEmaMs, sample.roundtripMs);
    }
    if (typeof sample.playbackMs === 'number') {
        autoRuntime.facePlaybackEmaMs = updateEma(autoRuntime.facePlaybackEmaMs, sample.playbackMs);
    }

    if (typeof sample.roundtripMs === 'number' && Number.isFinite(sample.roundtripMs) && sample.roundtripMs > 0) {
        enqueueWorldlincoTelemetryMetric({
            source: 'mobile',
            feature: 'face_conversation',
            metric: 'roundtrip_ms',
            value: sample.roundtripMs,
            unit: 'ms',
        });
    }
    if (typeof sample.playbackMs === 'number' && Number.isFinite(sample.playbackMs) && sample.playbackMs > 0) {
        enqueueWorldlincoTelemetryMetric({
            source: 'mobile',
            feature: 'face_conversation',
            metric: 'playback_ms',
            value: sample.playbackMs,
            unit: 'ms',
        });
    }
    if (sample.overlapDetected) {
        enqueueWorldlincoTelemetryMetric({
            source: 'mobile',
            feature: 'face_conversation',
            metric: 'overlap_detected',
            value: 1,
            unit: 'count',
        });
    }
}

export function reportVoipVoiceAutoTuningMetric(sample: {
    echoBlocked?: boolean;
    fairnessBargeIn?: boolean;
}): void {
    autoRuntime.voipTurns += 1;
    if (sample.echoBlocked) {
        autoRuntime.voipEchoBlocks += 1;
    }
    if (sample.fairnessBargeIn) {
        autoRuntime.voipFairnessBargeIns += 1;
    }

    if (sample.echoBlocked) {
        enqueueWorldlincoTelemetryMetric({
            source: 'mobile',
            feature: 'voip',
            metric: 'echo_blocked',
            value: 1,
            unit: 'count',
        });
    }
    if (sample.fairnessBargeIn) {
        enqueueWorldlincoTelemetryMetric({
            source: 'mobile',
            feature: 'voip',
            metric: 'fairness_barge_in',
            value: 1,
            unit: 'count',
        });
    }
}

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
    const merged: WorldlincoTuningSnapshot = {
        version: typeof payload?.version === 'number' ? payload.version : WORLDLINGCO_TUNING_DEFAULTS.version,
        updated_at: typeof payload?.updated_at === 'string' ? payload.updated_at : null,
        voip: mergeSection(WORLDLINGCO_TUNING_DEFAULTS.voip, payload?.voip),
        face_conversation: mergeSection(WORLDLINGCO_TUNING_DEFAULTS.face_conversation, payload?.face_conversation),
    };

    // 원격 튜닝이 오래된 스냅샷(예: v3의 공격적 900/1600)으로 내려와도
    // 실기기 대면/소리새 캡처가 다시 짧게 끊기지 않도록 최소 안정 바닥을 강제한다.
    merged.face_conversation.silence_flush_ms = Math.max(
        merged.face_conversation.silence_flush_ms,
        WORLDLINGCO_TUNING_DEFAULTS.face_conversation.silence_flush_ms,
    );
    merged.face_conversation.min_segment_ms = Math.max(
        merged.face_conversation.min_segment_ms,
        WORLDLINGCO_TUNING_DEFAULTS.face_conversation.min_segment_ms,
    );
    merged.face_conversation.restart_ms = Math.max(
        merged.face_conversation.restart_ms,
        WORLDLINGCO_TUNING_DEFAULTS.face_conversation.restart_ms,
    );

    return merged;
}

export function getWorldlincoTuning(): WorldlincoTuningSnapshot {
    // 자동 튜닝 드리프트 대신, 모드별 고정 프로필을 우선 적용해
    // 대면/소리새/VoIP/일반 통역 전환 시 예측 가능한 런타임을 유지한다.
    const autoTuned = buildAutoTunedSnapshot(cachedSnapshot);
    return applyRuntimeAutoProfile(autoTuned, runtimeAutoProfile);
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

export function resolveFaceVadDefaultsFromTuning(
    tuning: WorldlincoTuningSnapshot = cachedSnapshot,
): ResolvedFaceVadConfig {
    return {
        maxSegmentMs: Math.min(tuning.face_conversation.max_segment_ms, 18_000),
        silenceFlushMs: tuning.face_conversation.silence_flush_ms,
        minSegmentMs: tuning.face_conversation.min_segment_ms,
        meterUnavailableFilePollEvery: tuning.face_conversation.meter_poll_every,
        speechMeterMinDb: tuning.voip.speech_meter_min_db,
        meterUnavailableFixedFlushMs: Math.min(tuning.voip.meter_unavailable_fixed_flush_ms, 2_200),
        meterPollMs: 180,
    };
}

export function resolveSorisaeCompanionVadDefaultsFromTuning(
    tuning: WorldlincoTuningSnapshot = cachedSnapshot,
): ResolvedFaceVadConfig {
    const base = resolveFaceVadDefaultsFromTuning(tuning);
    return {
        ...base,
        // 소리새 우선 안정 모드: 홈 Q&A는 통역보다 약간 넉넉하되,
        // 짧은 질문이 전송 전 단계에서 버려지지 않도록 고정 안정 경계를 유지한다.
        silenceFlushMs: 1000,
        minSegmentMs: 1700,
        // Android metering dead(-160dB 고정) 단말에서는 file-growth silence 검출이 흔들릴 수 있어
        // 마지막 발화 감지 뒤 짧은 fallback flush 로 질문 후 체감 지연을 제한한다.
        meterUnavailableFixedFlushMs: 450,
        maxSegmentMs: 6500,
    };
}

export function resolveFaceFileSpeechRmsDb(tuning: WorldlincoTuningSnapshot = cachedSnapshot): number {
    return tuning.face_conversation.file_speech_rms_db;
}

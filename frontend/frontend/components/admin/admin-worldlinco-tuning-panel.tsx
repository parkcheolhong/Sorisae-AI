'use client';

import * as React from 'react';
import {
    applyWorldlincoRecommendationField,
    loadAdminThresholdAnalysis,
    type AdminThresholdAnalysisResponse,
} from '@/lib/admin-threshold-analysis-service';
import {
    loadAdminWorldlincoCalibrationArtifacts,
    type AdminWorldlincoCalibrationArtifactsPayload,
    loadAdminWorldlincoTelemetry,
    uploadAdminWorldlincoTelemetry,
    type AdminWorldlincoTelemetryItem,
    type AdminWorldlincoTelemetryPayload,
} from '@/lib/admin-worldlinco-telemetry-service';

export type WorldlincoTuningGroup = 'voip' | 'face_conversation' | 'voip_bridge' | 'sorisae_ai' | 'pstn_assist' | 'chat';

export type WorldlincoTuningFieldSpec = {
    key: string;
    label: string;
    hint: string;
    min: number;
    max: number;
    step: number;
    unit: string;
    group: WorldlincoTuningGroup;
};

function formatTuningValue(value: number, spec: WorldlincoTuningFieldSpec) {
    if (!Number.isFinite(value)) {
        return '—';
    }
    const decimalPlaces = spec.step < 1
        ? Math.min(4, String(spec.step).split('.')[1]?.length || 0)
        : 0;
    return Number(value).toFixed(decimalPlaces);
}

function formatDeltaValue(value: number, spec: WorldlincoTuningFieldSpec) {
    const formatted = formatTuningValue(Math.abs(value), spec);
    if (value === 0) {
        return `Δ 0${spec.unit}`;
    }
    return `Δ ${value > 0 ? '+' : '-'}${formatted}${spec.unit}`;
}

function getMicroTuneSpan(spec: WorldlincoTuningFieldSpec) {
    return Math.max(spec.step * 10, spec.step);
}

function getDeltaBounds(spec: WorldlincoTuningFieldSpec, baselineValue: number, absoluteValue: number) {
    const microSpan = getMicroTuneSpan(spec);
    const lower = Math.max(spec.min - baselineValue, -microSpan);
    const upper = Math.min(spec.max - baselineValue, microSpan);
    const snappedAbsolute = Math.min(spec.max, Math.max(spec.min, absoluteValue));
    return {
        min: lower,
        max: upper,
        absolute: snappedAbsolute,
    };
}

function makeTickValues(min: number, max: number) {
    if (min === max) {
        return [min];
    }
    if (min < 0 && max > 0) {
        return [min, min / 2, 0, max / 2, max];
    }
    const mid = min + ((max - min) / 2);
    return [min, min + ((mid - min) / 2), mid, mid + ((max - mid) / 2), max];
}

export const WORLDLINGCO_TUNING_FIELD_SPECS: WorldlincoTuningFieldSpec[] = [
    { key: 'silero_silence_ms', label: 'Silero 침묵 판정', hint: '말 끝 후 이 시간만큼 조용하면 구간 종료', min: 500, max: 2500, step: 50, unit: 'ms', group: 'voip' },
    { key: 'silero_min_speech_span_ms', label: '최소 발화 길이', hint: '이보다 짧으면 번역하지 않음', min: 800, max: 5000, step: 100, unit: 'ms', group: 'voip' },
    { key: 'silero_min_segment_ms', label: '최소 녹음 구간', hint: 'STT 전송 전 최소 캡처 길이', min: 1500, max: 6000, step: 100, unit: 'ms', group: 'voip' },
    { key: 'silero_safety_cap_ms', label: 'Silero 안전 상한선', hint: '음성 분석 최대 허용 시간', min: 3000, max: 20000, step: 500, unit: 'ms', group: 'voip' },
    { key: 'silero_speech_ms', label: 'Silero 초음성 감지', hint: '초음성(120ms) 활성화 플래그', min: 0, max: 500, step: 10, unit: 'ms', group: 'voip' },
    { key: 'silero_post_flush_cooldown_ms', label: 'Silero 후 쿨다운', hint: 'VAD 후 마이크 쿨다운 시간', min: 500, max: 3000, step: 100, unit: 'ms', group: 'voip' },
    { key: 'vad_min_segment_ms', label: 'VAD 최소 구간', hint: '세그먼트 최소값', min: 1000, max: 5000, step: 100, unit: 'ms', group: 'voip' },
    { key: 'vad_max_segment_ms', label: 'VAD 최대 구간', hint: '세그먼트 최대값', min: 3000, max: 12000, step: 100, unit: 'ms', group: 'voip' },
    { key: 'post_playback_guard_ms', label: '재생 후 가드', hint: '스피커 재생 후 마이크 가드', min: 200, max: 2000, step: 100, unit: 'ms', group: 'voip' },
    { key: 'meter_unavailable_fixed_flush_ms', label: '메터 미지원 flush', hint: 'meter dead 기기 폴백 시간', min: 1000, max: 8000, step: 100, unit: 'ms', group: 'voip' },
    { key: 'fairness_barge_in_ms', label: '공정 끼어들기', hint: '상호 끼어들기 공정성 시간', min: 2000, max: 15000, step: 100, unit: 'ms', group: 'voip' },
    { key: 'remote_echo_guard_ms', label: '에코 가드 (수화기)', hint: 'TTS 후 마이크 재개 대기', min: 1500, max: 10000, step: 100, unit: 'ms', group: 'voip' },
    { key: 'speaker_echo_guard_ms', label: '에코 가드 (스피커)', hint: '스피커폰 TTS 후 마이크 재개 대기', min: 2000, max: 12000, step: 100, unit: 'ms', group: 'voip' },
    { key: 'remote_listen_hold_ms', label: '상대 통역 수신 hold', hint: '상대 TTS 들을 때 마이크 hold', min: 1000, max: 8000, step: 100, unit: 'ms', group: 'voip' },
    { key: 'vad_silence_flush_ms', label: 'VAD 침묵 flush', hint: 'meter/RMS 기반 침묵 판정', min: 600, max: 3500, step: 50, unit: 'ms', group: 'voip' },
    { key: 'speech_meter_min_db', label: '음성 meter 임계', hint: 'dBFS — 높을수록 민감', min: -70, max: -35, step: 1, unit: 'dB', group: 'voip' },
    { key: 'file_speech_rms_db', label: 'VoIP file-RMS 임계', hint: 'meter dead 기기 fallback', min: -70, max: -35, step: 1, unit: 'dB', group: 'voip' },
    { key: 'silence_flush_ms', label: '대면 침묵 flush', hint: '대면 통역 말 끝 판정', min: 600, max: 3500, step: 50, unit: 'ms', group: 'face_conversation' },
    { key: 'min_segment_ms', label: '대면 최소 구간', hint: '너무 짧은 클립 STT 방지', min: 1200, max: 5000, step: 100, unit: 'ms', group: 'face_conversation' },
    { key: 'max_segment_ms', label: '대면 최대 구간', hint: '세그먼트 상한, 길수록 단문장 허용', min: 5000, max: 60000, step: 500, unit: 'ms', group: 'face_conversation' },
    { key: 'file_speech_rms_db', label: '대면 file-RMS 임계', hint: 'Tab 등 meter dead 기기', min: -70, max: -35, step: 1, unit: 'dB', group: 'face_conversation' },
    { key: 'restart_ms', label: '대면 재시작 지연', hint: '구간 후 마이크 재개', min: 100, max: 1500, step: 50, unit: 'ms', group: 'face_conversation' },
    { key: 'meter_poll_every', label: '메터 폴링 간격', hint: '음성 레벨 감지 주기', min: 1, max: 10, step: 1, unit: 'frames', group: 'face_conversation' },
    { key: 'playback_cap_ms', label: 'TTS 재생 상한', hint: '최대 재생 길이', min: 20000, max: 60000, step: 1000, unit: 'ms', group: 'face_conversation' },
    { key: 'playback_drain_ms', label: 'TTS 드레인 시간', hint: '재생 후 출력 대기 시간', min: 500, max: 3000, step: 100, unit: 'ms', group: 'face_conversation' },
    { key: 'tts_rate', label: 'TTS 재생 속도', hint: '재생 속도 (1.0=정상)', min: 0.5, max: 2.0, step: 0.1, unit: '배수', group: 'face_conversation' },
    // 서버 미디어 브리지(MCU) — 서버측 통역 음량/템포/환각필터. 통화 중 ~2초 내 실시간 반영.
    { key: 'tts_target_rms', label: '번역 음량 (핵심)', hint: '클수록 크게 들림 — 차량/원거리 0.40~0.55 권장', min: 0.08, max: 0.70, step: 0.01, unit: '', group: 'voip_bridge' },
    { key: 'tts_max_gain', label: '음량 게인 상한', hint: '작은 발화를 끌어올리는 최대 배수', min: 1, max: 48, step: 1, unit: '×', group: 'voip_bridge' },
    { key: 'tts_target_peak', label: '피크 리미터', hint: '왜곡 방지 상한(0~1)', min: 0.5, max: 1.0, step: 0.01, unit: '', group: 'voip_bridge' },
    { key: 'silence_gap_ms', label: '발화 종료 침묵', hint: '↓ 낮출수록 턴이 빨라짐(대화 템포)', min: 300, max: 1500, step: 50, unit: 'ms', group: 'voip_bridge' },
    { key: 'max_speech_ms', label: '발화 최대 길이', hint: '↓ 낮출수록 전달 지연 상한 단축', min: 2000, max: 15000, step: 250, unit: 'ms', group: 'voip_bridge' },
    { key: 'min_speech_ms', label: '발화 최소 길이', hint: '이보다 짧으면 노이즈로 보고 컷', min: 200, max: 1500, step: 50, unit: 'ms', group: 'voip_bridge' },
    { key: 'rms_gate', label: '발화 감지 게이트', hint: '↑ 높일수록 노이즈에 강건', min: 100, max: 900, step: 10, unit: '', group: 'voip_bridge' },
    { key: 'min_segment_rms_for_stt', label: '최소 구간 RMS (STT)', hint: 'STT 전송 전 최소 RMS 값', min: 100, max: 1000, step: 50, unit: '', group: 'voip_bridge' },
    { key: 'asr_norm_floor_rms', label: 'ASR 정규화 하한', hint: '음성 정규화 최소값', min: 100, max: 1000, step: 50, unit: '', group: 'voip_bridge' },
    { key: 'tts_guard_tail_ms', label: '에코 가드 꼬리', hint: 'TTS 재생 후 마이크 탭 억제', min: 100, max: 2000, step: 50, unit: 'ms', group: 'voip_bridge' },
    { key: 'live_echo_guard_ms', label: 'Live 에코 가드', hint: '실시간 에코 검출 타임윈도우', min: 200, max: 2000, step: 100, unit: 'ms', group: 'voip_bridge' },
    { key: 'live_echo_forward_barge_in_rms', label: 'Live 에코 Forward RMS', hint: '전방향 에코 감지 RMS', min: 500, max: 5000, step: 100, unit: '', group: 'voip_bridge' },
    { key: 'live_echo_return_window_ms', label: 'Live 에코 Return Window', hint: '역방향 에코 감지 윈도우', min: 500, max: 5000, step: 100, unit: 'ms', group: 'voip_bridge' },
    { key: 'live_echo_return_barge_in_rms', label: 'Live 에코 Return RMS', hint: '역방향 에코 감지 RMS', min: 1000, max: 8000, step: 100, unit: '', group: 'voip_bridge' },
    { key: 'drop_no_speech_prob', label: '드롭 임계 (no-speech)', hint: '침묵 확률 드롭 threshold', min: 0.4, max: 0.99, step: 0.01, unit: '', group: 'voip_bridge' },
    { key: 'max_no_speech_prob', label: '환각 컷 (no-speech)', hint: '이 초과 + logprob 미만 동시 시 폐기', min: 0.4, max: 0.99, step: 0.01, unit: '', group: 'voip_bridge' },
    { key: 'min_avg_logprob', label: '환각 컷 (logprob)', hint: '이 미만 + no-speech 초과 동시 시 폐기', min: -3.0, max: -0.2, step: 0.1, unit: '', group: 'voip_bridge' },
    { key: 'downlink_queue_max_frames', label: 'MCU 큐 최대 프레임', hint: '서버 MCU 다운링크 버퍼 크기', min: 10, max: 500, step: 10, unit: 'frames', group: 'voip_bridge' },
    // 소리새 AI 친구 모드(여행 컨시어지 대화) — 횡설수설/지역 오답 정밀 튜닝.
    { key: 'friend_min_lang_prob', label: '언어 감지 신뢰 임계', hint: '이 미만이면 감지 언어 무시 → 프로필 언어로 답(외국어 오답 방지)', min: 0.0, max: 1.0, step: 0.05, unit: '', group: 'sorisae_ai' },
    { key: 'geo_accuracy_max_m', label: '위치 신뢰 상한', hint: 'GPS 정확도가 이보다 거칠면 근처 추천에 좌표 미사용', min: 200, max: 50000, step: 100, unit: 'm', group: 'sorisae_ai' },
    { key: 'geo_accuracy_nearby_max_m', label: '근처 POI 정확도', hint: '근처 추천 GPS 신뢰 거리', min: 200, max: 10000, step: 100, unit: 'm', group: 'sorisae_ai' },
    { key: 'geo_accuracy_overview_max_m', label: '둘러보기 정확도', hint: '개요 추천 GPS 신뢰 거리', min: 500, max: 50000, step: 500, unit: 'm', group: 'sorisae_ai' },
    { key: 'friend_timeout_sec', label: 'AI 응답 시간 제한', hint: '초 단위, 높을수록 길게 기다림', min: 5, max: 60, step: 1, unit: 's', group: 'sorisae_ai' },
    { key: 'friend_reply_max_tokens', label: '답변 길이 상한', hint: '토큰 수, 낮을수록 짧은 답변', min: 100, max: 1000, step: 10, unit: 'tok', group: 'sorisae_ai' },
    { key: 'friend_realtime_max_tokens', label: '실시간 번역 토큰', hint: '음성 번역 품질 상한', min: 50, max: 500, step: 10, unit: 'tok', group: 'sorisae_ai' },
    { key: 'tourism_guide_tier', label: '관광 정보 수준', hint: '높을수록 상세함', min: 1, max: 5, step: 1, unit: '단계', group: 'sorisae_ai' },
    { key: 'tts_rate', label: 'AI TTS 재생 속도', hint: '재생 속도 (1.0=정상)', min: 0.5, max: 2.0, step: 0.1, unit: '배수', group: 'sorisae_ai' },
    { key: 'call_connect_timeout_ms', label: '통화 연결 제한', hint: '일반통역 전화 연결 대기 상한', min: 3000, max: 30000, step: 500, unit: 'ms', group: 'pstn_assist' },
    { key: 'turn_pause_ms', label: '턴 전환 pause', hint: '일반통역 전화 턴 사이 pause', min: 300, max: 5000, step: 50, unit: 'ms', group: 'pstn_assist' },
    { key: 'subtitle_commit_delay_ms', label: '자막 commit 지연', hint: '자막 확정까지 대기 시간', min: 50, max: 3000, step: 50, unit: 'ms', group: 'pstn_assist' },
    { key: 'stt_confidence_floor', label: 'STT 신뢰 하한', hint: '이 미만이면 일반통역 전화 STT 문장 보류', min: 0.0, max: 1.0, step: 0.05, unit: '', group: 'pstn_assist' },
    { key: 'max_caption_chars', label: '자막 최대 글자수', hint: '일반통역 전화 자막 길이 상한', min: 20, max: 240, step: 2, unit: '자', group: 'pstn_assist' },
    { key: 'message_latency_budget_ms', label: '채팅 응답 예산', hint: '채팅 응답 체감 속도 상한', min: 200, max: 10000, step: 50, unit: 'ms', group: 'chat' },
    { key: 'stream_chunk_budget_ms', label: '채팅 chunk 예산', hint: '스트림 청크 생성 목표', min: 50, max: 3000, step: 25, unit: 'ms', group: 'chat' },
    { key: 'translation_cache_ttl_sec', label: '번역 캐시 TTL', hint: '채팅 번역 캐시 보존 시간', min: 0, max: 86400, step: 30, unit: 's', group: 'chat' },
    { key: 'typing_indicator_delay_ms', label: '타이핑 표시 지연', hint: '타이핑 indicator 표시 지연', min: 0, max: 3000, step: 20, unit: 'ms', group: 'chat' },
    { key: 'auto_summary_turn_threshold', label: '자동 요약 턴 기준', hint: '채팅 요약 자동 발동 턴 수', min: 0, max: 200, step: 1, unit: '턴', group: 'chat' },
];

const WORLDLINCO_GROUP_LABELS: Record<WorldlincoTuningGroup, string> = {
    voip: 'VoIP 음성 통역',
    voip_bridge: '서버 브리지(MCU)',
    face_conversation: '대면 통역',
    sorisae_ai: '소리새 AI 친구',
    pstn_assist: '일반 통역 전화',
    chat: '채팅',
};

export type WorldlincoTuningPayload = {
    version?: number;
    updated_at?: string | null;
    updated_by?: string | null;
    calibration_notes?: string;
    voip?: Record<string, number>;
    face_conversation?: Record<string, number>;
    voip_bridge?: Record<string, number>;
    sorisae_ai?: Record<string, number>;
    pstn_assist?: Record<string, number>;
    chat?: Record<string, number>;
    fixed_baseline?: Partial<Record<WorldlincoTuningGroup, Record<string, number>>>;
};

function buildBaselinePayload(data: WorldlincoTuningPayload): WorldlincoTuningPayload {
    return {
        ...data,
        sorisae_ai: {
            ...(data.sorisae_ai || {}),
            ...(data.fixed_baseline?.sorisae_ai || {}),
        },
    };
}

type WorldlincoFoldSectionKey =
    | 'overview'
    | 'voip'
    | 'voip_bridge'
    | 'face_conversation'
    | 'sorisae_ai'
    | 'pstn_assist'
    | 'chat'
    | 'diff_cards'
    | 'artifacts'
    | 'telemetry'
    | 'history';

const WORLDLINCO_FOLD_SECTION_KEYS: WorldlincoFoldSectionKey[] = [
    'overview',
    'voip',
    'voip_bridge',
    'face_conversation',
    'sorisae_ai',
    'pstn_assist',
    'chat',
    'diff_cards',
    'artifacts',
    'telemetry',
    'history',
];

type AdminWorldlincoTuningPanelProps = {
    apiBaseUrl: string;
    getAdminToken: () => string | null;
};

function VolumeSlider(props: {
    spec: WorldlincoTuningFieldSpec;
    absoluteValue: number;
    baselineValue: number;
    onChange: (value: number) => void;
}) {
    const { spec, absoluteValue, baselineValue, onChange } = props;
    const deltaBounds = getDeltaBounds(spec, baselineValue, absoluteValue);
    const deltaValue = Number((absoluteValue - baselineValue).toFixed(spec.step < 1 ? 4 : 0));
    const tickValues = makeTickValues(deltaBounds.min, deltaBounds.max);
    const isPositiveDelta = deltaValue > 0;
    const isNegativeDelta = deltaValue < 0;
    const nudge = (direction: -1 | 1) => {
        const nextDelta = deltaValue + (spec.step * direction);
        const clampedDelta = Math.min(deltaBounds.max, Math.max(deltaBounds.min, nextDelta));
        const nextAbsolute = baselineValue + clampedDelta;
        onChange(Math.min(spec.max, Math.max(spec.min, Number(nextAbsolute.toFixed(spec.step < 1 ? 4 : 0)))));
    };
    const resetToBaseline = () => {
        onChange(Number(baselineValue.toFixed(spec.step < 1 ? 4 : 0)));
    };
    const deltaBadgeBackground = isPositiveDelta
        ? 'rgba(34, 197, 94, 0.2)'
        : isNegativeDelta
            ? 'rgba(248, 113, 113, 0.2)'
            : 'rgba(56, 189, 248, 0.14)';
    const deltaBadgeBorder = isPositiveDelta
        ? '1px solid rgba(74, 222, 128, 0.7)'
        : isNegativeDelta
            ? '1px solid rgba(252, 165, 165, 0.72)'
            : '1px solid rgba(125, 211, 252, 0.48)';
    const deltaBadgeColor = isPositiveDelta
        ? '#86efac'
        : isNegativeDelta
            ? '#fecaca'
            : '#7dd3fc';
    return (
        <div
            className="workspace-sidebar-card"
            data-testid={`worldlinco-tuning-${spec.group}-${spec.key}`}
            style={{
                padding: '6px 7px',
                border: deltaValue === 0
                    ? '1px solid rgba(125,211,252,0.2)'
                    : `1px solid ${isPositiveDelta ? 'rgba(74,222,128,0.55)' : 'rgba(252,165,165,0.55)'}`,
                boxShadow: deltaValue === 0
                    ? 'none'
                    : `0 0 0 1px ${isPositiveDelta ? 'rgba(74,222,128,0.15)' : 'rgba(252,165,165,0.15)'} inset`,
                background: 'linear-gradient(180deg, rgba(15,23,42,0.88) 0%, rgba(15,23,42,0.72) 100%)',
            }}
        >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 7 }}>
                <div>
                    <p className="workspace-card-kicker">{spec.label}</p>
                    <p style={{ margin: 0, fontSize: 9, color: 'rgba(255,255,255,0.5)' }}>{spec.hint}</p>
                </div>
                <strong style={{ color: '#7dd3fc', fontSize: 11, whiteSpace: 'nowrap', textAlign: 'right' }}>
                    {formatTuningValue(absoluteValue, spec)}{spec.unit}
                    <span
                        style={{
                            display: 'inline-flex',
                            marginTop: 2,
                            padding: '0 5px',
                            borderRadius: 999,
                            background: deltaBadgeBackground,
                            border: deltaBadgeBorder,
                            color: deltaBadgeColor,
                            fontSize: 9,
                            letterSpacing: 0.2,
                        }}
                    >
                        {formatDeltaValue(deltaValue, spec)}
                    </span>
                </strong>
            </div>
            <div style={{ marginTop: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 9, gap: 5 }}>
                <span
                    style={{
                        color: '#e2e8f0',
                        background: 'rgba(2,132,199,0.2)',
                        border: '1px solid rgba(125,211,252,0.45)',
                        borderRadius: 999,
                        padding: '0 5px',
                    }}
                >
                    중앙 기준 {formatTuningValue(baselineValue, spec)}{spec.unit}
                </span>
                <span style={{ color: '#fca5a5' }}>{deltaBounds.min < 0 ? `${formatDeltaValue(deltaBounds.min, spec)}` : `Δ 0${spec.unit}`}</span>
                <span style={{ color: '#86efac' }}>{deltaBounds.max > 0 ? `${formatDeltaValue(deltaBounds.max, spec)}` : `Δ 0${spec.unit}`}</span>
            </div>
            <input
                type="range"
                min={deltaBounds.min}
                max={deltaBounds.max}
                step={spec.step}
                value={deltaValue}
                onChange={(event) => {
                    const nextDelta = Number(event.target.value);
                    const nextAbsolute = baselineValue + nextDelta;
                    onChange(Math.min(spec.max, Math.max(spec.min, Number(nextAbsolute.toFixed(spec.step < 1 ? 4 : 0)))));
                }}
                style={{ width: '100%', marginTop: 4, accentColor: deltaValue < 0 ? '#f87171' : deltaValue > 0 ? '#4ade80' : '#38bdf8' }}
            />
            <div
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 4,
                    marginTop: 4,
                    padding: '2px 4px',
                    borderRadius: 7,
                    border: '1px solid rgba(148,163,184,0.3)',
                    background: 'rgba(2, 6, 23, 0.36)',
                }}
            >
                <button
                    type="button"
                    className="workspace-topbar-chip"
                    style={{ fontSize: 9, padding: '2px 5px' }}
                    onClick={() => nudge(-1)}
                    aria-label={`${spec.label} left micro adjust`}
                >
                    ← {formatTuningValue(spec.step, spec)}{spec.unit}
                </button>
                <button
                    type="button"
                    className="workspace-topbar-chip"
                    style={{
                        fontSize: 9,
                        padding: '2px 6px',
                        borderColor: deltaValue === 0 ? 'rgba(125,211,252,0.45)' : 'rgba(250,204,21,0.45)',
                        color: deltaValue === 0 ? '#bae6fd' : '#fde68a',
                    }}
                    onClick={resetToBaseline}
                    aria-label={`${spec.label} reset baseline`}
                >
                    기준(0) 복귀
                </button>
                <button
                    type="button"
                    className="workspace-topbar-chip"
                    style={{ fontSize: 9, padding: '2px 5px' }}
                    onClick={() => nudge(1)}
                    aria-label={`${spec.label} right micro adjust`}
                >
                    {formatTuningValue(spec.step, spec)}{spec.unit} →
                </button>
            </div>
            <div
                style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(5, minmax(0, 1fr))',
                    gap: 2,
                    marginTop: 4,
                    padding: '3px 2px',
                    borderRadius: 8,
                    background: 'rgba(2, 6, 23, 0.36)',
                    border: '1px dashed rgba(148, 163, 184, 0.32)',
                }}
            >
                {tickValues.map((tickValue) => {
                    const absoluteTickValue = baselineValue + tickValue;
                    const isCenterTick = tickValue === 0;
                    return (
                        <div
                            key={`${spec.key}-${tickValue}`}
                            style={{
                                textAlign: 'center',
                                minWidth: 0,
                                borderRadius: 6,
                                padding: '1px 1px',
                                background: isCenterTick ? 'rgba(56, 189, 248, 0.12)' : 'transparent',
                            }}
                        >
                            <div style={{ height: 7, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                <span
                                    style={{
                                        display: 'block',
                                        width: isCenterTick ? 2 : 1,
                                        height: isCenterTick ? 9 : 5,
                                        background: isCenterTick ? '#7dd3fc' : 'rgba(125,211,252,0.45)',
                                    }}
                                />
                            </div>
                            <div style={{ fontSize: isCenterTick ? 9 : 8, fontWeight: isCenterTick ? 700 : 500, color: isCenterTick ? '#e0f2fe' : 'rgba(255,255,255,0.62)', lineHeight: 1.1 }}>
                                {formatDeltaValue(tickValue, spec)}
                            </div>
                            <div style={{ fontSize: 8, color: isCenterTick ? 'rgba(186,230,253,0.8)' : 'rgba(255,255,255,0.38)', lineHeight: 1.1 }}>
                                {formatTuningValue(absoluteTickValue, spec)}{spec.unit}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

function FoldSection(props: {
    title: string;
    subtitle?: string;
    open: boolean;
    onToggle: () => void;
    children: React.ReactNode;
}) {
    const { title, subtitle, open, onToggle, children } = props;
    return (
        <section className="workspace-sidebar-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center' }}>
                <div>
                    <p className="workspace-card-kicker" style={{ marginBottom: 2 }}>{title}</p>
                    {subtitle ? <p style={{ margin: 0, fontSize: 12, color: 'rgba(255,255,255,0.55)' }}>{subtitle}</p> : null}
                </div>
                <button type="button" className="workspace-topbar-chip" onClick={onToggle}>
                    {open ? '▲ 접기' : '▼ 펼치기'}
                </button>
            </div>
            {open ? <div style={{ marginTop: 12 }}>{children}</div> : null}
        </section>
    );
}

export function AdminWorldlincoTuningPanel({ apiBaseUrl, getAdminToken }: AdminWorldlincoTuningPanelProps) {
    const [loading, setLoading] = React.useState(true);
    const [saving, setSaving] = React.useState(false);
    const [error, setError] = React.useState('');
    const [message, setMessage] = React.useState('');
    const [payload, setPayload] = React.useState<WorldlincoTuningPayload | null>(null);
    const [baselinePayload, setBaselinePayload] = React.useState<WorldlincoTuningPayload | null>(null);
    const [notes, setNotes] = React.useState('');
    const [thresholdAnalysis, setThresholdAnalysis] = React.useState<AdminThresholdAnalysisResponse | null>(null);
    const [telemetryPayload, setTelemetryPayload] = React.useState<AdminWorldlincoTelemetryPayload | null>(null);
    const [artifactPayload, setArtifactPayload] = React.useState<AdminWorldlincoCalibrationArtifactsPayload | null>(null);
    const [telemetryDraft, setTelemetryDraft] = React.useState('[\n  {\n    "source": "mobile",\n    "feature": "chat",\n    "metric": "message_latency_ms",\n    "value": 980,\n    "unit": "ms",\n    "device_id": "tab-s10",\n    "run_id": "build92-round1",\n    "tags": { "lang": "ko->ja", "network": "lte" }\n  }\n]');
    const [telemetryUploading, setTelemetryUploading] = React.useState(false);
    const [applyingCardId, setApplyingCardId] = React.useState<string | null>(null);
    const [openSections, setOpenSections] = React.useState<Record<WorldlincoFoldSectionKey, boolean>>({
        overview: true,
        voip: false,
        voip_bridge: true,
        face_conversation: false,
        sorisae_ai: false,
        pstn_assist: false,
        chat: false,
        diff_cards: true,
        artifacts: true,
        telemetry: true,
        history: true,
    });
    const panelRootRef = React.useRef<HTMLDivElement | null>(null);

    const load = React.useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const token = getAdminToken();
            const response = await fetch(`${apiBaseUrl.replace(/\/$/, '')}/api/admin/worldlinco/tuning`, {
                headers: token ? { Authorization: `Bearer ${token}` } : {},
            });
            if (!response.ok) {
                throw new Error(`튜닝 설정 로드 실패 (${response.status})`);
            }
            const data = await response.json() as WorldlincoTuningPayload;
            setPayload(data);
            setBaselinePayload(buildBaselinePayload(data));
            setNotes(String(data.calibration_notes || ''));

            if (token) {
                const [analysis, telemetry, artifacts] = await Promise.all([
                    loadAdminThresholdAnalysis({
                        apiBaseUrl: apiBaseUrl.replace(/\/$/, ''),
                        token,
                    }).catch(() => null),
                    loadAdminWorldlincoTelemetry({
                        apiBaseUrl: apiBaseUrl.replace(/\/$/, ''),
                        token,
                    }).catch(() => null),
                    loadAdminWorldlincoCalibrationArtifacts({
                        apiBaseUrl: apiBaseUrl.replace(/\/$/, ''),
                        token,
                    }).catch(() => null),
                ]);
                setThresholdAnalysis(analysis);
                setTelemetryPayload(telemetry);
                setArtifactPayload(artifacts);
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : '튜닝 설정 로드 실패');
        } finally {
            setLoading(false);
        }
    }, [apiBaseUrl, getAdminToken]);

    React.useEffect(() => {
        void load();
    }, [load]);

    const updateField = (group: WorldlincoTuningGroup, key: string, value: number) => {
        setPayload((prev) => {
            if (!prev) {
                return prev;
            }
            return {
                ...prev,
                [group]: {
                    ...(prev[group] || {}),
                    [key]: value,
                },
            };
        });
    };

    const save = async () => {
        if (!payload) {
            return;
        }
        setSaving(true);
        setError('');
        setMessage('');
        try {
            const token = getAdminToken();
            const response = await fetch(`${apiBaseUrl.replace(/\/$/, '')}/api/admin/worldlinco/tuning`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                },
                body: JSON.stringify({
                    calibration_notes: notes,
                    voip: payload.voip,
                    face_conversation: payload.face_conversation,
                    voip_bridge: payload.voip_bridge,
                    sorisae_ai: payload.sorisae_ai,
                    pstn_assist: payload.pstn_assist,
                    chat: payload.chat,
                }),
            });
            if (!response.ok) {
                const text = await response.text();
                throw new Error(text || `저장 실패 (${response.status})`);
            }
            const data = await response.json() as WorldlincoTuningPayload;
            setPayload(data);
            setBaselinePayload(buildBaselinePayload(data));
            setMessage(`저장됨 · ${data.updated_at || 'now'} · 서버 브리지는 통화 중 ~2초 내 실시간 반영 / 클라(VAD·에코)는 앱 포그라운드 시 반영`);
        } catch (err) {
            setError(err instanceof Error ? err.message : '저장 실패');
        } finally {
            setSaving(false);
        }
    };

    const uploadTelemetry = async () => {
        const token = getAdminToken();
        if (!token) {
            setError('관리자 토큰이 없어 텔레메트리를 업로드할 수 없습니다.');
            return;
        }
        let parsed: unknown;
        try {
            parsed = JSON.parse(telemetryDraft);
        } catch {
            setError('텔레메트리 JSON 파싱에 실패했습니다. JSON 배열 형식을 확인하세요.');
            return;
        }
        if (!Array.isArray(parsed)) {
            setError('텔레메트리 업로드는 JSON 배열만 허용됩니다.');
            return;
        }
        setTelemetryUploading(true);
        setError('');
        setMessage('');
        try {
            const items = parsed as AdminWorldlincoTelemetryItem[];
            const uploaded = await uploadAdminWorldlincoTelemetry({
                apiBaseUrl: apiBaseUrl.replace(/\/$/, ''),
                token,
                note: notes,
                items,
            });
            const telemetry = await loadAdminWorldlincoTelemetry({
                apiBaseUrl: apiBaseUrl.replace(/\/$/, ''),
                token,
            });
            const artifacts = await loadAdminWorldlincoCalibrationArtifacts({
                apiBaseUrl: apiBaseUrl.replace(/\/$/, ''),
                token,
            });
            setTelemetryPayload(telemetry);
            setArtifactPayload(artifacts);
            setMessage(`텔레메트리 업로드 완료 · accepted ${uploaded.accepted}건 · 누적 ${uploaded.total_items}건`);
        } catch (err) {
            setError(err instanceof Error ? err.message : '텔레메트리 업로드 실패');
        } finally {
            setTelemetryUploading(false);
        }
    };

    const applyDiffCard = async (group: string, key: string, cardId: string) => {
        const token = getAdminToken();
        if (!token) {
            setError('관리자 토큰이 없어 추천값을 적용할 수 없습니다.');
            return;
        }
        setApplyingCardId(cardId);
        setError('');
        setMessage('');
        try {
            const result = await applyWorldlincoRecommendationField({
                apiBaseUrl: apiBaseUrl.replace(/\/$/, ''),
                token,
                group,
                key,
            });
            setPayload((prev) => {
                if (!prev) {
                    return prev;
                }
                return {
                    ...prev,
                    ...(result.worldlinco as WorldlincoTuningPayload),
                };
            });
            setBaselinePayload((prev) => buildBaselinePayload({
                ...(prev || {}),
                ...(result.worldlinco as WorldlincoTuningPayload),
                fixed_baseline: (prev as WorldlincoTuningPayload | null)?.fixed_baseline
                    || (result.worldlinco as WorldlincoTuningPayload | undefined)?.fixed_baseline,
            }));
            setThresholdAnalysis(result.threshold_analysis || null);
            setMessage(`추천값 일부 적용 완료 · ${group}.${key}=${result.value}`);
        } catch (err) {
            setError(err instanceof Error ? err.message : '추천값 부분 적용 실패');
        } finally {
            setApplyingCardId(null);
        }
    };

    if (loading) {
        return <p style={{ color: 'rgba(255,255,255,0.7)' }}>WorldLinco 튜닝 설정 불러오는 중...</p>;
    }

    if (!payload) {
        return <p style={{ color: '#f87171' }}>{error || '튜닝 데이터 없음'}</p>;
    }

    const voipSpecs = WORLDLINGCO_TUNING_FIELD_SPECS.filter((spec) => spec.group === 'voip');
    const faceSpecs = WORLDLINGCO_TUNING_FIELD_SPECS.filter((spec) => spec.group === 'face_conversation');
    const bridgeSpecs = WORLDLINGCO_TUNING_FIELD_SPECS.filter((spec) => spec.group === 'voip_bridge');
    const sorisaeSpecs = WORLDLINGCO_TUNING_FIELD_SPECS.filter((spec) => spec.group === 'sorisae_ai');
    const pstnSpecs = WORLDLINGCO_TUNING_FIELD_SPECS.filter((spec) => spec.group === 'pstn_assist');
    const chatSpecs = WORLDLINGCO_TUNING_FIELD_SPECS.filter((spec) => spec.group === 'chat');
    const globalQuickSpecs = [...WORLDLINGCO_TUNING_FIELD_SPECS].sort((a, b) => {
        if (a.group === b.group) {
            return a.label.localeCompare(b.label, 'ko');
        }
        return a.group.localeCompare(b.group, 'ko');
    });
    const recommendedWorldlinco = thresholdAnalysis?.recommendations.worldlinco || {};
    const diffCards = WORLDLINGCO_TUNING_FIELD_SPECS
        .map((spec) => {
            const currentValueRaw = (payload as any)?.[spec.group]?.[spec.key];
            const recommendedValueRaw = (recommendedWorldlinco as any)?.[spec.group]?.[spec.key];
            if (typeof currentValueRaw !== 'number' || typeof recommendedValueRaw !== 'number') {
                return null;
            }
            const delta = Number((recommendedValueRaw - currentValueRaw).toFixed(3));
            if (Math.abs(delta) < 0.0001) {
                return null;
            }
            const ratio = currentValueRaw !== 0
                ? Number((((recommendedValueRaw - currentValueRaw) / currentValueRaw) * 100).toFixed(1))
                : null;
            return {
                id: `${spec.group}:${spec.key}`,
                group: spec.group,
                key: spec.key,
                label: spec.label,
                hint: spec.hint,
                unit: spec.unit,
                currentValue: currentValueRaw,
                recommendedValue: recommendedValueRaw,
                delta,
                ratio,
            };
        })
        .filter((item): item is NonNullable<typeof item> => Boolean(item))
        .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));

    const telemetrySummaryRows = Object.entries(telemetryPayload?.summary?.features || {}).flatMap(([feature, metrics]) => (
        Object.entries(metrics).map(([metric, stats]) => ({ feature, metric, stats }))
    ));
    const partialAppliedRows = Array.isArray(thresholdAnalysis?.worldlinco_partial_applied)
        ? [...(thresholdAnalysis?.worldlinco_partial_applied || [])].reverse().slice(0, 20)
        : [];
    const priorityCsvRows = (artifactPayload?.artifacts?.priority_csv || []).filter((item) => item.exists);
    const recommendationCoverage = artifactPayload?.artifacts?.recommendation?.sample_coverage as { all_features_satisfied?: boolean; missing_by_feature?: Record<string, unknown> } | undefined;

    const toggleSection = (key: WorldlincoFoldSectionKey) => {
        setOpenSections((prev) => ({
            ...prev,
            [key]: !prev[key],
        }));
    };

    const setAllSectionsOpen = (open: boolean) => {
        setOpenSections(
            WORLDLINCO_FOLD_SECTION_KEYS.reduce((acc, key) => {
                acc[key] = open;
                return acc;
            }, {} as Record<WorldlincoFoldSectionKey, boolean>)
        );
    };

    const scrollPanel = (position: 'top' | 'bottom') => {
        const target = panelRootRef.current;
        if (!target) {
            return;
        }
        target.scrollIntoView({ behavior: 'smooth', block: position === 'top' ? 'start' : 'end' });
    };

    return (
        <div className="workspace-section-stack" data-testid="admin-worldlinco-tuning-panel" ref={panelRootRef}>
            <div
                className="workspace-sidebar-card"
                style={{
                    position: 'sticky',
                    top: 6,
                    zIndex: 2,
                    padding: '6px 8px',
                    borderRadius: 14,
                    width: 'fit-content',
                    maxWidth: '100%',
                }}
            >
                <p className="workspace-card-kicker" style={{ fontSize: 11, marginBottom: 4 }}>패널 빠른 열기/닫기</p>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 4 }}>
                    <button type="button" className="workspace-topbar-chip" style={{ fontSize: 10, padding: '3px 6px' }} onClick={() => setAllSectionsOpen(true)}>모두 펼치기</button>
                    <button type="button" className="workspace-topbar-chip" style={{ fontSize: 10, padding: '3px 6px' }} onClick={() => setAllSectionsOpen(false)}>모두 접기</button>
                    <button type="button" className="workspace-topbar-chip" style={{ fontSize: 10, padding: '3px 6px' }} onClick={() => scrollPanel('bottom')}>맨 아래로</button>
                </div>
            </div>

            <section className="workspace-sidebar-card" data-testid="worldlinco-global-controls">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12 }}>
                    <div>
                        <p className="workspace-card-kicker" style={{ marginBottom: 2 }}>전체 튜닝샵 즉시 조절 (항상 표시)</p>
                        <p style={{ margin: 0, fontSize: 12, color: 'rgba(255,255,255,0.55)' }}>
                            접기/펼치기와 무관하게 모든 항목을 한 화면에서 확인하고 바로 조절
                        </p>
                    </div>
                    <span style={{ fontSize: 11, color: '#bae6fd' }}>총 {globalQuickSpecs.length}개 항목</span>
                </div>
                <div style={{ marginTop: 6, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 6 }}>
                    {globalQuickSpecs.map((spec) => (
                        <div key={`global-${spec.group}-${spec.key}`}>
                            <p style={{ margin: '0 0 4px', fontSize: 11, color: 'rgba(186,230,253,0.9)' }}>
                                {WORLDLINCO_GROUP_LABELS[spec.group]}
                            </p>
                            <VolumeSlider
                                spec={spec}
                                absoluteValue={Number((payload as any)?.[spec.group]?.[spec.key] ?? spec.min)}
                                baselineValue={Number((baselinePayload as any)?.[spec.group]?.[spec.key] ?? (payload as any)?.[spec.group]?.[spec.key] ?? spec.min)}
                                onChange={(value) => updateField(spec.group, spec.key, value)}
                            />
                        </div>
                    ))}
                </div>
            </section>

            <FoldSection
                title="WorldLinco 원격 튜닝"
                subtitle="기본 정보/메모"
                open={openSections.overview}
                onToggle={() => toggleSection('overview')}
            >
                <p style={{ margin: '0 0 8px', fontSize: 13, color: 'rgba(255,255,255,0.72)' }}>
                    현재 배포 버전의 고정 기준값을 baseline 으로 유지합니다. 슬라이더 조정 후 저장하면
                    {' '}
                    <code>{apiBaseUrl.replace(/\/$/, '')}/api/marketplace/worldlinco/tuning</code>
                    {' '}
                    으로 모바일에 전달됩니다.
                </p>
                <p style={{ margin: 0, fontSize: 12, color: 'rgba(255,255,255,0.5)' }}>
                    updated_at: {payload.updated_at || '—'} · by: {payload.updated_by || '—'}
                </p>
                <textarea
                    value={notes}
                    onChange={(event) => setNotes(event.target.value)}
                    placeholder="캘리브레이션 메모 (예: Tab S10 실측 2026-06-18)"
                    className="workspace-admin-command-textarea"
                    style={{ minHeight: 72, marginTop: 12 }}
                />
            </FoldSection>

            <FoldSection title="📞 VoIP 음성 통역" open={openSections.voip} onToggle={() => toggleSection('voip')}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 6 }}>
                    {voipSpecs.map((spec) => (
                        <VolumeSlider
                            key={`voip-${spec.key}`}
                            spec={spec}
                            absoluteValue={Number(payload.voip?.[spec.key] ?? spec.min)}
                            baselineValue={Number(baselinePayload?.voip?.[spec.key] ?? payload.voip?.[spec.key] ?? spec.min)}
                            onChange={(value) => updateField('voip', spec.key, value)}
                        />
                    ))}
                </div>
            </FoldSection>

            <FoldSection
                title="🌉 서버 브리지(MCU) 통역"
                subtitle="저장 즉시 통화 중에도 ~2초 내 실시간 반영"
                open={openSections.voip_bridge}
                onToggle={() => toggleSection('voip_bridge')}
            >
                <p style={{ margin: '0 0 8px', fontSize: 12, color: '#7dd3fc' }}>
                    서버측 통역 음량·대화 템포·환각필터. 저장 즉시 <strong>통화 중에도 ~2초 내 실시간 반영</strong>(재시작/재빌드 불필요).
                </p>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 6 }}>
                    {bridgeSpecs.map((spec) => (
                        <VolumeSlider
                            key={`bridge-${spec.key}`}
                            spec={spec}
                            absoluteValue={Number(payload.voip_bridge?.[spec.key] ?? spec.min)}
                            baselineValue={Number(baselinePayload?.voip_bridge?.[spec.key] ?? payload.voip_bridge?.[spec.key] ?? spec.min)}
                            onChange={(value) => updateField('voip_bridge', spec.key, value)}
                        />
                    ))}
                </div>
            </FoldSection>

            <FoldSection title="🤝 대면 통역" open={openSections.face_conversation} onToggle={() => toggleSection('face_conversation')}>
                <p style={{ margin: '0 0 8px', fontSize: 12, color: '#7dd3fc' }}>
                    대면 통역은 현재 테스트 단계입니다. 값 조정 후 실기기 10회 이상 반복 검증으로 기준을 잡습니다.
                </p>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 6 }}>
                    {faceSpecs.map((spec) => (
                        <VolumeSlider
                            key={`face-${spec.key}`}
                            spec={spec}
                            absoluteValue={Number(payload.face_conversation?.[spec.key] ?? spec.min)}
                            baselineValue={Number(baselinePayload?.face_conversation?.[spec.key] ?? payload.face_conversation?.[spec.key] ?? spec.min)}
                            onChange={(value) => updateField('face_conversation', spec.key, value)}
                        />
                    ))}
                </div>
            </FoldSection>

            <FoldSection
                title="🐦 소리새 AI 친구 모드"
                subtitle="횡설수설/지역 오답 정밀 튜닝"
                open={openSections.sorisae_ai}
                onToggle={() => toggleSection('sorisae_ai')}
            >
                <p style={{ margin: '0 0 8px', fontSize: 12, color: '#7dd3fc' }}>
                    여행 컨시어지 대화의 <strong>횡설수설(언어 오감지)·지역 오답(거친 GPS)</strong> 정밀 튜닝. 소리새 AI baseline 은 배포 고정 기준으로 유지되고, 저장 즉시 ~2초 내 반영됩니다.
                </p>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 6 }}>
                    {sorisaeSpecs.map((spec) => (
                        <VolumeSlider
                            key={`sorisae-${spec.key}`}
                            spec={spec}
                            absoluteValue={Number(payload.sorisae_ai?.[spec.key] ?? spec.min)}
                            baselineValue={Number(baselinePayload?.sorisae_ai?.[spec.key] ?? payload.sorisae_ai?.[spec.key] ?? spec.min)}
                            onChange={(value) => updateField('sorisae_ai', spec.key, value)}
                        />
                    ))}
                </div>
            </FoldSection>

            <FoldSection title="☎️ 일반 통역 전화" open={openSections.pstn_assist} onToggle={() => toggleSection('pstn_assist')}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 6 }}>
                    {pstnSpecs.map((spec) => (
                        <VolumeSlider
                            key={`pstn-${spec.key}`}
                            spec={spec}
                            absoluteValue={Number(payload.pstn_assist?.[spec.key] ?? spec.min)}
                            baselineValue={Number(baselinePayload?.pstn_assist?.[spec.key] ?? payload.pstn_assist?.[spec.key] ?? spec.min)}
                            onChange={(value) => updateField('pstn_assist', spec.key, value)}
                        />
                    ))}
                </div>
            </FoldSection>

            <FoldSection title="💬 채팅" open={openSections.chat} onToggle={() => toggleSection('chat')}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 6 }}>
                    {chatSpecs.map((spec) => (
                        <VolumeSlider
                            key={`chat-${spec.key}`}
                            spec={spec}
                            absoluteValue={Number(payload.chat?.[spec.key] ?? spec.min)}
                            baselineValue={Number(baselinePayload?.chat?.[spec.key] ?? payload.chat?.[spec.key] ?? spec.min)}
                            onChange={(value) => updateField('chat', spec.key, value)}
                        />
                    ))}
                </div>
            </FoldSection>

            <FoldSection
                title="추천값 Diff 카드"
                subtitle="임계치 추천값과 현재값 즉시 비교"
                open={openSections.diff_cards}
                onToggle={() => toggleSection('diff_cards')}
            >
                <div data-testid="worldlinco-recommendation-diff-cards">
                    {diffCards.length === 0 ? (
                        <p style={{ margin: 0, fontSize: 12, color: 'rgba(255,255,255,0.6)' }}>
                            현재 추천값과 동일하거나 추천 데이터가 아직 없습니다.
                        </p>
                    ) : (
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 8 }}>
                            {diffCards.map((card) => (
                                <div key={card.id} style={{ border: '1px solid rgba(125,211,252,0.35)', borderRadius: 10, padding: 10, background: 'rgba(15,23,42,0.55)' }}>
                                    <p style={{ margin: 0, color: '#bae6fd', fontSize: 12 }}>{card.group}</p>
                                    <p style={{ margin: '4px 0 2px', color: 'white', fontWeight: 600 }}>{card.label}</p>
                                    <p style={{ margin: '0 0 8px', color: 'rgba(255,255,255,0.55)', fontSize: 11 }}>{card.hint}</p>
                                    <p style={{ margin: 0, fontSize: 12, color: 'rgba(255,255,255,0.8)' }}>
                                        현재 {card.currentValue}{card.unit || ''} → 추천 {card.recommendedValue}{card.unit || ''}
                                    </p>
                                    <p style={{ margin: '4px 0 0', fontSize: 12, color: card.delta > 0 ? '#fca5a5' : '#86efac' }}>
                                        Δ {card.delta > 0 ? '+' : ''}{card.delta}{card.unit || ''}
                                        {card.ratio !== null ? ` (${card.ratio > 0 ? '+' : ''}${card.ratio}%)` : ''}
                                    </p>
                                    <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 8 }}>
                                        <button
                                            type="button"
                                            className="workspace-topbar-chip"
                                            onClick={() => void applyDiffCard(card.group, card.key, card.id)}
                                            disabled={Boolean(applyingCardId)}
                                        >
                                            {applyingCardId === card.id ? '적용 중...' : '이 카드만 적용'}
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </FoldSection>

            <FoldSection
                title="캘리브레이션 아티팩트 상태"
                subtitle=".runtime 산출물(telemetry/recommendation/csv) 최신 상태"
                open={openSections.artifacts}
                onToggle={() => toggleSection('artifacts')}
            >
                <div data-testid="worldlinco-calibration-artifacts" style={{ display: 'grid', gap: 8 }}>
                    <div style={{ border: '1px solid rgba(148,163,184,0.35)', borderRadius: 8, padding: 10 }}>
                        <p style={{ margin: 0, color: '#cbd5e1', fontSize: 12 }}>Telemetry JSON</p>
                        <p style={{ margin: '4px 0 0', fontSize: 12, color: 'rgba(255,255,255,0.78)' }}>
                            {artifactPayload?.artifacts.telemetry.exists ? '존재' : '없음'} · items {artifactPayload?.artifacts.telemetry.total_items ?? 0}
                        </p>
                        <p style={{ margin: '2px 0 0', fontSize: 11, color: 'rgba(255,255,255,0.55)' }}>
                            updated {artifactPayload?.artifacts.telemetry.updated_at || '—'}
                        </p>
                    </div>
                    <div style={{ border: '1px solid rgba(148,163,184,0.35)', borderRadius: 8, padding: 10 }}>
                        <p style={{ margin: 0, color: '#cbd5e1', fontSize: 12 }}>Recommendation JSON</p>
                        <p style={{ margin: '4px 0 0', fontSize: 12, color: 'rgba(255,255,255,0.78)' }}>
                            {artifactPayload?.artifacts.recommendation.exists ? '존재' : '없음'} · confidence {artifactPayload?.artifacts.recommendation.confidence || '—'}
                        </p>
                        <p style={{ margin: '2px 0 0', fontSize: 11, color: recommendationCoverage?.all_features_satisfied ? '#86efac' : '#fca5a5' }}>
                            sample coverage: {recommendationCoverage?.all_features_satisfied ? '충분' : '부족/미확인'}
                        </p>
                        {(artifactPayload?.artifacts.recommendation.warnings || []).length > 0 ? (
                            <p style={{ margin: '2px 0 0', fontSize: 11, color: '#fbbf24' }}>
                                warnings: {(artifactPayload?.artifacts.recommendation.warnings || []).slice(0, 2).join(' | ')}
                            </p>
                        ) : null}
                    </div>
                    <div style={{ border: '1px solid rgba(148,163,184,0.35)', borderRadius: 8, padding: 10 }}>
                        <p style={{ margin: 0, color: '#cbd5e1', fontSize: 12 }}>Priority CSV</p>
                        {priorityCsvRows.length === 0 ? (
                            <p style={{ margin: '4px 0 0', fontSize: 12, color: 'rgba(255,255,255,0.6)' }}>CSV 산출물이 없습니다.</p>
                        ) : (
                            <div style={{ marginTop: 6, display: 'grid', gap: 4 }}>
                                {priorityCsvRows.map((row) => (
                                    <p key={row.path} style={{ margin: 0, fontSize: 11, color: 'rgba(255,255,255,0.7)' }}>
                                        {row.path} · rows {row.rows ?? 0} · modified {row.modified_at || '—'}
                                    </p>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </FoldSection>

            <FoldSection
                title="월드린코 텔레메트리 업로드"
                subtitle="모바일 실측값(JSON 배열) 업로드"
                open={openSections.telemetry}
                onToggle={() => toggleSection('telemetry')}
            >
                <div data-testid="worldlinco-telemetry-upload">
                    <p style={{ margin: '0 0 8px', fontSize: 12, color: 'rgba(255,255,255,0.6)' }}>
                        모바일 실측(latency, confidence, segment) 값을 JSON 배열로 올리면 추천 근거에 반영됩니다.
                    </p>
                    <textarea
                        value={telemetryDraft}
                        onChange={(event) => setTelemetryDraft(event.target.value)}
                        className="workspace-admin-command-textarea"
                        style={{ minHeight: 140 }}
                    />
                    <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                        <button type="button" className="workspace-primary-button" onClick={() => void uploadTelemetry()} disabled={telemetryUploading}>
                            {telemetryUploading ? '업로드 중...' : '텔레메트리 업로드'}
                        </button>
                    </div>
                    <p style={{ margin: '8px 0 0', fontSize: 12, color: 'rgba(255,255,255,0.55)' }}>
                        누적: {telemetryPayload?.summary?.total_items ?? 0}건 · updated: {telemetryPayload?.updated_at || '—'}
                    </p>
                    {telemetrySummaryRows.length > 0 ? (
                        <div style={{ marginTop: 8, display: 'grid', gap: 6 }}>
                            {telemetrySummaryRows.slice(0, 10).map((row) => (
                                <div key={`${row.feature}:${row.metric}`} style={{ border: '1px solid rgba(148,163,184,0.3)', borderRadius: 8, padding: 8 }}>
                                    <p style={{ margin: 0, color: '#cbd5e1', fontSize: 12 }}>{row.feature} · {row.metric}</p>
                                    <p style={{ margin: '2px 0 0', color: 'rgba(255,255,255,0.75)', fontSize: 12 }}>
                                        avg {row.stats.avg} / p95 {row.stats.p95} / min {row.stats.min} / max {row.stats.max} (n={row.stats.count})
                                    </p>
                                </div>
                            ))}
                        </div>
                    ) : null}
                </div>
            </FoldSection>

            <FoldSection
                title="카드 단위 적용 이력"
                subtitle="누가/언제/어떤 키를 부분 적용했는지 최근 기록"
                open={openSections.history}
                onToggle={() => toggleSection('history')}
            >
                <div data-testid="worldlinco-diff-apply-history">
                    {partialAppliedRows.length === 0 ? (
                        <p style={{ margin: 0, fontSize: 12, color: 'rgba(255,255,255,0.6)' }}>
                            아직 카드 단위 적용 이력이 없습니다.
                        </p>
                    ) : (
                        <div style={{ overflowX: 'auto' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                                <thead>
                                    <tr style={{ color: '#bae6fd', textAlign: 'left', borderBottom: '1px solid rgba(148,163,184,0.35)' }}>
                                        <th style={{ padding: '6px 4px' }}>적용시각</th>
                                        <th style={{ padding: '6px 4px' }}>적용자</th>
                                        <th style={{ padding: '6px 4px' }}>group.key</th>
                                        <th style={{ padding: '6px 4px' }}>값</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {partialAppliedRows.map((row, index) => (
                                        <tr key={`${row.group}:${row.key}:${row.applied_at}:${index}`} style={{ borderBottom: '1px solid rgba(71,85,105,0.25)' }}>
                                            <td style={{ padding: '6px 4px', color: 'rgba(255,255,255,0.7)', whiteSpace: 'nowrap' }}>{row.applied_at || '—'}</td>
                                            <td style={{ padding: '6px 4px', color: 'rgba(255,255,255,0.85)' }}>{row.applied_by || '—'}</td>
                                            <td style={{ padding: '6px 4px', color: '#e2e8f0' }}>{row.group}.{row.key}</td>
                                            <td style={{ padding: '6px 4px', color: '#86efac' }}>{row.value}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </FoldSection>

            {error ? <p style={{ color: '#f87171' }}>{error}</p> : null}
            {message ? <p style={{ color: '#86efac' }}>{message}</p> : null}

            <div className="workspace-sidebar-card">
                <p className="workspace-card-kicker">하단 빠른 제어</p>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
                    <button type="button" className="workspace-topbar-chip" onClick={() => scrollPanel('top')}>맨 위로</button>
                    <button type="button" className="workspace-topbar-chip" onClick={() => setAllSectionsOpen(true)}>모두 펼치기</button>
                    <button type="button" className="workspace-topbar-chip" onClick={() => setAllSectionsOpen(false)}>모두 접기</button>
                </div>
            </div>

            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button type="button" className="workspace-primary-button" onClick={() => void save()} disabled={saving}>
                    {saving ? '저장 중...' : '튜닝 저장 · 모바일 반영'}
                </button>
                <button type="button" className="workspace-topbar-chip" onClick={() => void load()} disabled={loading || saving}>
                    새로고침
                </button>
            </div>
        </div>
    );
}

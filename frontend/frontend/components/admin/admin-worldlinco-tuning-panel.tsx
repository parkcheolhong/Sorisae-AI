'use client';

import * as React from 'react';

export type WorldlincoTuningFieldSpec = {
    key: string;
    label: string;
    hint: string;
    min: number;
    max: number;
    step: number;
    unit: string;
    group: 'voip' | 'face_conversation';
};

export const WORLDLINGCO_TUNING_FIELD_SPECS: WorldlincoTuningFieldSpec[] = [
    { key: 'silero_silence_ms', label: 'Silero 침묵 판정', hint: '말 끝 후 이 시간만큼 조용하면 구간 종료', min: 500, max: 2500, step: 50, unit: 'ms', group: 'voip' },
    { key: 'silero_min_speech_span_ms', label: '최소 발화 길이', hint: '이보다 짧으면 번역하지 않음', min: 800, max: 5000, step: 100, unit: 'ms', group: 'voip' },
    { key: 'silero_min_segment_ms', label: '최소 녹음 구간', hint: 'STT 전송 전 최소 캡처 길이', min: 1500, max: 6000, step: 100, unit: 'ms', group: 'voip' },
    { key: 'remote_echo_guard_ms', label: '에코 가드 (수화기)', hint: 'TTS 후 마이크 재개 대기', min: 1500, max: 10000, step: 100, unit: 'ms', group: 'voip' },
    { key: 'speaker_echo_guard_ms', label: '에코 가드 (스피커)', hint: '스피커폰 TTS 후 마이크 재개 대기', min: 2000, max: 12000, step: 100, unit: 'ms', group: 'voip' },
    { key: 'remote_listen_hold_ms', label: '상대 통역 수신 hold', hint: '상대 TTS 들을 때 마이크 hold', min: 1000, max: 8000, step: 100, unit: 'ms', group: 'voip' },
    { key: 'vad_silence_flush_ms', label: 'VAD 침묵 flush', hint: 'meter/RMS 기반 침묵 판정', min: 600, max: 3500, step: 50, unit: 'ms', group: 'voip' },
    { key: 'speech_meter_min_db', label: '음성 meter 임계', hint: 'dBFS — 높을수록 민감', min: -70, max: -35, step: 1, unit: 'dB', group: 'voip' },
    { key: 'file_speech_rms_db', label: 'VoIP file-RMS 임계', hint: 'meter dead 기기 fallback', min: -70, max: -35, step: 1, unit: 'dB', group: 'voip' },
    { key: 'silence_flush_ms', label: '대면 침묵 flush', hint: '대면 통역 말 끝 판정', min: 600, max: 3500, step: 50, unit: 'ms', group: 'face_conversation' },
    { key: 'min_segment_ms', label: '대면 최소 구간', hint: '너무 짧은 클립 STT 방지', min: 1200, max: 5000, step: 100, unit: 'ms', group: 'face_conversation' },
    { key: 'file_speech_rms_db', label: '대면 file-RMS 임계', hint: 'Tab 등 meter dead 기기', min: -70, max: -35, step: 1, unit: 'dB', group: 'face_conversation' },
    { key: 'restart_ms', label: '대면 재시작 지연', hint: '구간 후 마이크 재개', min: 100, max: 1500, step: 50, unit: 'ms', group: 'face_conversation' },
];

export type WorldlincoTuningPayload = {
    version?: number;
    updated_at?: string | null;
    updated_by?: string | null;
    calibration_notes?: string;
    voip?: Record<string, number>;
    face_conversation?: Record<string, number>;
};

type AdminWorldlincoTuningPanelProps = {
    apiBaseUrl: string;
    getAdminToken: () => string | null;
};

function VolumeSlider(props: {
    spec: WorldlincoTuningFieldSpec;
    value: number;
    onChange: (value: number) => void;
}) {
    const { spec, value, onChange } = props;
    return (
        <div className="workspace-sidebar-card" data-testid={`worldlinco-tuning-${spec.group}-${spec.key}`}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12 }}>
                <div>
                    <p className="workspace-card-kicker">{spec.label}</p>
                    <p style={{ margin: 0, fontSize: 12, color: 'rgba(255,255,255,0.55)' }}>{spec.hint}</p>
                </div>
                <strong style={{ color: '#7dd3fc', fontSize: 14, whiteSpace: 'nowrap' }}>
                    {value}
                    {spec.unit}
                </strong>
            </div>
            <input
                type="range"
                min={spec.min}
                max={spec.max}
                step={spec.step}
                value={value}
                onChange={(event) => onChange(Number(event.target.value))}
                style={{ width: '100%', marginTop: 12, accentColor: '#38bdf8' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>
                <span>{spec.min}{spec.unit}</span>
                <span>{spec.max}{spec.unit}</span>
            </div>
        </div>
    );
}

export function AdminWorldlincoTuningPanel({ apiBaseUrl, getAdminToken }: AdminWorldlincoTuningPanelProps) {
    const [loading, setLoading] = React.useState(true);
    const [saving, setSaving] = React.useState(false);
    const [error, setError] = React.useState('');
    const [message, setMessage] = React.useState('');
    const [payload, setPayload] = React.useState<WorldlincoTuningPayload | null>(null);
    const [notes, setNotes] = React.useState('');

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
            setNotes(String(data.calibration_notes || ''));
        } catch (err) {
            setError(err instanceof Error ? err.message : '튜닝 설정 로드 실패');
        } finally {
            setLoading(false);
        }
    }, [apiBaseUrl, getAdminToken]);

    React.useEffect(() => {
        void load();
    }, [load]);

    const updateField = (group: 'voip' | 'face_conversation', key: string, value: number) => {
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
                }),
            });
            if (!response.ok) {
                const text = await response.text();
                throw new Error(text || `저장 실패 (${response.status})`);
            }
            const data = await response.json() as WorldlincoTuningPayload;
            setPayload(data);
            setMessage(`저장됨 · ${data.updated_at || 'now'} · 모바일 앱 재시작/포그라운드 시 반영`);
        } catch (err) {
            setError(err instanceof Error ? err.message : '저장 실패');
        } finally {
            setSaving(false);
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

    return (
        <div className="workspace-section-stack" data-testid="admin-worldlinco-tuning-panel">
            <div className="workspace-sidebar-card">
                <p className="workspace-card-kicker">WorldLinco 원격 튜닝</p>
                <p style={{ margin: '0 0 8px', fontSize: 13, color: 'rgba(255,255,255,0.72)' }}>
                    ADB build101 기준값이 기본값입니다. 슬라이더 조정 후 저장하면
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
            </div>

            <h3 style={{ color: 'white', fontSize: 16, margin: '8px 0 0' }}>📞 VoIP 음성 통역</h3>
            {voipSpecs.map((spec) => (
                <VolumeSlider
                    key={`voip-${spec.key}`}
                    spec={spec}
                    value={Number(payload.voip?.[spec.key] ?? spec.min)}
                    onChange={(value) => updateField('voip', spec.key, value)}
                />
            ))}

            <h3 style={{ color: 'white', fontSize: 16, margin: '16px 0 0' }}>🤝 대면 통역</h3>
            {faceSpecs.map((spec) => (
                <VolumeSlider
                    key={`face-${spec.key}`}
                    spec={spec}
                    value={Number(payload.face_conversation?.[spec.key] ?? spec.min)}
                    onChange={(value) => updateField('face_conversation', spec.key, value)}
                />
            ))}

            {error ? <p style={{ color: '#f87171' }}>{error}</p> : null}
            {message ? <p style={{ color: '#86efac' }}>{message}</p> : null}

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

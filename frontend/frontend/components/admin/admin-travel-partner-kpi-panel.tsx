'use client';

import { useMemo, useState } from 'react';
import {
    loadAdminTravelPartnerKpi,
    loadAdminTravelPartnerKpiSettings,
    updateAdminTravelPartnerKpiSettings,
    type AdminTravelKpiThresholds,
    type AdminTravelPartnerKpiResponse,
} from '../../lib/admin-travel-partner-service';
import { getAdminToken } from '../../lib/admin-session';

function formatPercent(value: number) {
    return `${(value * 100).toFixed(1)}%`;
}

function formatMoney(value: number) {
    return `$${value.toFixed(2)}`;
}

type TravelThresholdSpec = {
    key: keyof AdminTravelKpiThresholds;
    label: string;
    hint: string;
    min: number;
    max: number;
    step: number;
    unit: string;
};

const DEFAULT_TRAVEL_KPI_THRESHOLDS: AdminTravelKpiThresholds = {
    ctr_min: 0.05,
    booking_confirm_rate_min: 0.5,
    cancel_rate_max: 0.2,
    rps_min: 5,
    partner_success_rate_min: 0.85,
    partner_error_rate_max: 0.1,
    partner_p95_processing_minutes_max: 30,
    fallback_country_ratio_max: 0.8,
    fallback_city_ratio_max: 0.8,
    default_partner_usage_ratio_max: 0.95,
};

const TRAVEL_KPI_THRESHOLD_SPECS: TravelThresholdSpec[] = [
    { key: 'ctr_min', label: 'CTR 최소값', hint: '클릭률이 이보다 낮으면 경고', min: 0, max: 1, step: 0.01, unit: '' },
    { key: 'booking_confirm_rate_min', label: '예약확정률 최소값', hint: '예약 확정 비율 하한', min: 0, max: 1, step: 0.01, unit: '' },
    { key: 'cancel_rate_max', label: '취소율 최대값', hint: '이보다 높으면 경고', min: 0, max: 1, step: 0.01, unit: '' },
    { key: 'rps_min', label: 'RPS 최소값', hint: '수익/세션 비율 하한', min: 0, max: 100, step: 0.1, unit: '' },
    { key: 'partner_success_rate_min', label: 'SLA 성공률 최소값', hint: '파트너 성공률 하한', min: 0, max: 1, step: 0.01, unit: '' },
    { key: 'partner_error_rate_max', label: 'SLA 오류율 최대값', hint: '파트너 오류율 상한', min: 0, max: 1, step: 0.01, unit: '' },
    { key: 'partner_p95_processing_minutes_max', label: 'SLA p95(분) 최대값', hint: '처리 지연 p95 상한', min: 0, max: 120, step: 0.1, unit: '분' },
    { key: 'fallback_country_ratio_max', label: '국가 fallback 비율 최대값', hint: '국가 fallback 비율 상한', min: 0, max: 1, step: 0.01, unit: '' },
    { key: 'fallback_city_ratio_max', label: '도시 fallback 비율 최대값', hint: '도시 fallback 비율 상한', min: 0, max: 1, step: 0.01, unit: '' },
    { key: 'default_partner_usage_ratio_max', label: '기본파트너 사용 비율 최대값', hint: '기본파트너 사용 비율 상한', min: 0, max: 1, step: 0.01, unit: '' },
];

function formatThresholdValue(value: number, spec: TravelThresholdSpec) {
    if (!Number.isFinite(value)) {
        return '—';
    }
    const decimals = spec.step < 1 ? Math.min(4, String(spec.step).split('.')[1]?.length || 0) : 0;
    return Number(value).toFixed(decimals);
}

function formatThresholdDelta(value: number, spec: TravelThresholdSpec) {
    const formatted = formatThresholdValue(Math.abs(value), spec);
    if (value === 0) {
        return `Δ 0${spec.unit}`;
    }
    return `Δ ${value > 0 ? '+' : '-'}${formatted}${spec.unit}`;
}

function getTravelDeltaBounds(spec: TravelThresholdSpec, baselineValue: number) {
    const microSpan = Math.max(spec.step * 10, spec.step);
    return {
        min: Math.max(spec.min - baselineValue, -microSpan),
        max: Math.min(spec.max - baselineValue, microSpan),
    };
}

function makeTravelTickValues(min: number, max: number) {
    if (min === max) {
        return [min];
    }
    if (min < 0 && max > 0) {
        return [min, min / 2, 0, max / 2, max];
    }
    const mid = min + ((max - min) / 2);
    return [min, min + ((mid - min) / 2), mid, mid + ((max - mid) / 2), max];
}

function TravelThresholdSlider(props: {
    spec: TravelThresholdSpec;
    value: number;
    baselineValue: number;
    onChange: (value: number) => void;
}) {
    const { spec, value, baselineValue, onChange } = props;
    const deltaBounds = getTravelDeltaBounds(spec, baselineValue);
    const deltaValue = value - baselineValue;
    const ticks = makeTravelTickValues(deltaBounds.min, deltaBounds.max);
    return (
        <div style={{ border: '1px solid rgba(148,163,184,0.28)', borderRadius: 12, padding: 12, background: 'rgba(15,23,42,0.35)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'baseline' }}>
                <div>
                    <p style={{ margin: 0, fontSize: 13, color: '#e2e8f0', fontWeight: 700 }}>{spec.label}</p>
                    <p style={{ margin: '4px 0 0', fontSize: 11, color: 'rgba(255,255,255,0.56)' }}>{spec.hint}</p>
                </div>
                <strong style={{ color: '#7dd3fc', fontSize: 14, whiteSpace: 'nowrap', textAlign: 'right' }}>
                    {formatThresholdValue(value, spec)}{spec.unit}
                    <span style={{ display: 'block', color: 'rgba(125,211,252,0.72)', fontSize: 11 }}>
                        {formatThresholdDelta(deltaValue, spec)}
                    </span>
                </strong>
            </div>
            <div style={{ marginTop: 10, display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'rgba(255,255,255,0.58)' }}>
                <span>중앙 기준: {formatThresholdValue(baselineValue, spec)}{spec.unit}</span>
                <span>{formatThresholdDelta(deltaBounds.min, spec)}</span>
                <span>{formatThresholdDelta(deltaBounds.max, spec)}</span>
            </div>
            <input
                type="range"
                min={deltaBounds.min}
                max={deltaBounds.max}
                step={spec.step}
                value={deltaValue}
                onChange={(event) => {
                    const nextDelta = Number(event.target.value);
                    const nextValue = baselineValue + nextDelta;
                    const decimals = spec.step < 1 ? Math.min(4, String(spec.step).split('.')[1]?.length || 0) : 0;
                    onChange(Math.min(spec.max, Math.max(spec.min, Number(nextValue.toFixed(decimals)))));
                }}
                style={{ width: '100%', marginTop: 12, accentColor: '#38bdf8' }}
            />
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, minmax(0, 1fr))', gap: 6, marginTop: 10 }}>
                {ticks.map((tickValue) => {
                    const absoluteTick = baselineValue + tickValue;
                    const isCenterTick = tickValue === 0;
                    return (
                        <div key={`${spec.key}-${tickValue}`} style={{ textAlign: 'center', minWidth: 0 }}>
                            <div style={{ height: 10, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                <span
                                    style={{
                                        display: 'block',
                                        width: 1,
                                        height: isCenterTick ? 10 : 7,
                                        background: isCenterTick ? '#7dd3fc' : 'rgba(125,211,252,0.45)',
                                    }}
                                />
                            </div>
                            <div style={{ fontSize: 10, color: isCenterTick ? '#bae6fd' : 'rgba(255,255,255,0.62)', lineHeight: 1.25 }}>
                                {formatThresholdDelta(tickValue, spec)}
                            </div>
                            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.38)', lineHeight: 1.25 }}>
                                {formatThresholdValue(absoluteTick, spec)}{spec.unit}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

export default function AdminTravelPartnerKpiPanel() {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [message, setMessage] = useState<string | null>(null);
    const [payload, setPayload] = useState<AdminTravelPartnerKpiResponse | null>(null);
    const [settingsSaving, setSettingsSaving] = useState(false);
    const [thresholds, setThresholds] = useState<AdminTravelKpiThresholds>(DEFAULT_TRAVEL_KPI_THRESHOLDS);
    const [baselineThresholds, setBaselineThresholds] = useState<AdminTravelKpiThresholds>(DEFAULT_TRAVEL_KPI_THRESHOLDS);

    const apiBaseUrl = useMemo(() => {
        const fromEnv = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE || '';
        if (fromEnv) {
            return fromEnv.replace(/\/$/, '');
        }
        if (typeof window !== 'undefined') {
            return window.location.origin;
        }
        return '';
    }, []);

    async function withAdminToken<T>(handler: (token: string) => Promise<T>) {
        const token = getAdminToken();
        if (!token) {
            throw new Error('관리자 토큰이 없습니다. 다시 로그인 후 시도하세요.');
        }
        return handler(token);
    }

    async function handleLoad() {
        setLoading(true);
        setError(null);
        setMessage(null);
        try {
            const data = await withAdminToken((token) =>
                loadAdminTravelPartnerKpi({ apiBaseUrl, token })
            );
            setPayload(data);
            if (data.ops?.settings?.thresholds) {
                setThresholds(data.ops.settings.thresholds);
                setBaselineThresholds(data.ops.settings.thresholds);
            }
            setMessage('KPI 대시보드를 갱신했습니다.');
        } catch (loadError: any) {
            if (String(loadError?.message || '').includes('__ADMIN_TRAVEL_PARTNER_UNAUTHORIZED__')) {
                setError('권한이 만료되었습니다. 관리자 로그인 후 다시 시도하세요.');
            } else {
                setError(String(loadError?.message || '여행 KPI 조회 실패'));
            }
        } finally {
            setLoading(false);
        }
    }

    async function handleLoadSettings() {
        setLoading(true);
        setError(null);
        setMessage(null);
        try {
            const data = await withAdminToken((token) =>
                loadAdminTravelPartnerKpiSettings({ apiBaseUrl, token })
            );
            setThresholds(data.thresholds);
            setBaselineThresholds(data.thresholds);
            setMessage('KPI 운영 임계치를 불러왔습니다.');
        } catch (loadError: any) {
            if (String(loadError?.message || '').includes('__ADMIN_TRAVEL_PARTNER_UNAUTHORIZED__')) {
                setError('권한이 만료되었습니다. 관리자 로그인 후 다시 시도하세요.');
            } else {
                setError(String(loadError?.message || 'KPI 설정 조회 실패'));
            }
        } finally {
            setLoading(false);
        }
    }

    async function handleSaveSettings() {
        setSettingsSaving(true);
        setError(null);
        setMessage(null);
        try {
            await withAdminToken((token) =>
                updateAdminTravelPartnerKpiSettings({ apiBaseUrl, token, thresholds })
            );
            const refreshed = await withAdminToken((token) =>
                loadAdminTravelPartnerKpi({ apiBaseUrl, token })
            );
            setPayload(refreshed);
            if (refreshed.ops?.settings?.thresholds) {
                setThresholds(refreshed.ops.settings.thresholds);
                setBaselineThresholds(refreshed.ops.settings.thresholds);
            }
            setMessage('KPI 운영 임계치를 저장했습니다.');
        } catch (saveError: any) {
            if (String(saveError?.message || '').includes('__ADMIN_TRAVEL_PARTNER_UNAUTHORIZED__')) {
                setError('권한이 만료되었습니다. 관리자 로그인 후 다시 시도하세요.');
            } else {
                setError(String(saveError?.message || 'KPI 설정 저장 실패'));
            }
        } finally {
            setSettingsSaving(false);
        }
    }

    function updateThreshold<K extends keyof AdminTravelKpiThresholds>(key: K, value: number) {
        setThresholds((prev) => ({ ...prev, [key]: value }));
    }

    const cards = payload
        ? [
            { label: 'CTR', value: formatPercent(payload.funnel.ctr), note: `click ${payload.funnel.counts.clicks} / rec ${payload.funnel.counts.recommendations}` },
            { label: '예약확정률', value: formatPercent(payload.funnel.booking_confirm_rate), note: `confirmed ${payload.funnel.counts.confirmed} / bookings ${payload.funnel.counts.bookings}` },
            { label: '취소율', value: formatPercent(payload.funnel.cancel_rate), note: `cancel+refund ${payload.funnel.counts.cancelled + payload.funnel.counts.refunded}` },
            { label: '커미션', value: formatMoney(payload.funnel.commission_total), note: 'commission ledger 합계' },
            { label: 'RPS', value: formatMoney(payload.funnel.rps), note: `commission / sessions ${payload.funnel.counts.trip_sessions}` },
        ]
        : [];

    return (
        <div className="workspace-section-stack" data-testid="admin-travel-partner-kpi-panel">
            <div className="workspace-sidebar-card">
                <p className="workspace-card-kicker">Travel Partner KPI Dashboard</p>
                <p style={{ margin: '4px 0 0', fontSize: 13, color: 'rgba(255,255,255,0.74)' }}>
                    Section 6 KPI 카드(CTR, 예약확정률, 취소율, 커미션, RPS)와 파트너 SLA, fallback 비율을 한 화면에서 점검합니다.
                </p>
                <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <button
                        type="button"
                        className="workspace-btn-secondary"
                        onClick={() => {
                            void handleLoadSettings();
                        }}
                        disabled={loading}
                        data-testid="travel-kpi-load-settings-btn"
                    >
                        {loading ? '로딩 중...' : '임계치 불러오기'}
                    </button>
                    <button
                        type="button"
                        className="workspace-btn-secondary"
                        onClick={() => {
                            void handleSaveSettings();
                        }}
                        disabled={settingsSaving}
                        data-testid="travel-kpi-save-settings-btn"
                    >
                        {settingsSaving ? '저장 중...' : '임계치 저장'}
                    </button>
                    <button
                        type="button"
                        className="workspace-btn-primary"
                        onClick={() => {
                            void handleLoad();
                        }}
                        disabled={loading}
                        data-testid="travel-kpi-load-btn"
                    >
                        {loading ? '갱신 중...' : 'KPI 갱신'}
                    </button>
                </div>
                {message ? <p style={{ marginTop: 8, color: '#86efac', fontSize: 12 }}>{message}</p> : null}
                {error ? <p style={{ marginTop: 8, color: '#fca5a5', fontSize: 12 }}>{error}</p> : null}
            </div>

            <div className="workspace-sidebar-card" data-testid="travel-kpi-threshold-settings">
                <p className="workspace-card-kicker">운영 임계치 설정</p>
                <div style={{ marginTop: 10, display: 'grid', gap: 10 }}>
                    {TRAVEL_KPI_THRESHOLD_SPECS.map((spec) => (
                        <TravelThresholdSlider
                            key={spec.key}
                            spec={spec}
                            value={thresholds[spec.key]}
                            baselineValue={baselineThresholds[spec.key]}
                            onChange={(value) => updateThreshold(spec.key, value)}
                        />
                    ))}
                </div>
            </div>

            <div className="workspace-sidebar-card" data-testid="travel-kpi-funnel-cards">
                <p className="workspace-card-kicker">수익 퍼널 핵심 카드</p>
                {cards.length === 0 ? (
                    <p style={{ marginTop: 8, fontSize: 13, color: 'rgba(255,255,255,0.68)' }}>
                        KPI 갱신을 눌러 최신 지표를 로드하세요.
                    </p>
                ) : (
                    <div style={{ marginTop: 10, display: 'grid', gap: 10, gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}>
                        {cards.map((card) => (
                            <article key={card.label} style={{ border: '1px solid rgba(148,163,184,0.35)', borderRadius: 10, padding: 12 }}>
                                <p style={{ margin: 0, fontSize: 12, color: 'rgba(255,255,255,0.68)' }}>{card.label}</p>
                                <p style={{ margin: '8px 0 4px', fontSize: 22, fontWeight: 700, color: '#e2e8f0' }}>{card.value}</p>
                                <p style={{ margin: 0, fontSize: 11, color: 'rgba(255,255,255,0.56)' }}>{card.note}</p>
                            </article>
                        ))}
                    </div>
                )}
            </div>

            <div className="workspace-sidebar-card" data-testid="travel-kpi-sla-card">
                <p className="workspace-card-kicker">파트너 SLA</p>
                {!payload || payload.sla.length === 0 ? (
                    <p style={{ marginTop: 8, fontSize: 13, color: 'rgba(255,255,255,0.68)' }}>
                        집계된 예약 이벤트가 없습니다.
                    </p>
                ) : (
                    <div style={{ marginTop: 8, overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                            <thead>
                                <tr style={{ textAlign: 'left', borderBottom: '1px solid rgba(148,163,184,0.35)' }}>
                                    <th style={{ padding: '6px 4px' }}>partner_id</th>
                                    <th style={{ padding: '6px 4px' }}>성공률</th>
                                    <th style={{ padding: '6px 4px' }}>오류율</th>
                                    <th style={{ padding: '6px 4px' }}>p95(분)</th>
                                    <th style={{ padding: '6px 4px' }}>이벤트수</th>
                                </tr>
                            </thead>
                            <tbody>
                                {payload.sla.map((row) => (
                                    <tr key={row.partner_id} style={{ borderBottom: '1px solid rgba(148,163,184,0.18)' }}>
                                        <td style={{ padding: '6px 4px', color: '#cbd5e1' }}>{row.partner_id}</td>
                                        <td style={{ padding: '6px 4px' }}>{formatPercent(row.success_rate)}</td>
                                        <td style={{ padding: '6px 4px' }}>{formatPercent(row.error_rate)}</td>
                                        <td style={{ padding: '6px 4px' }}>{row.p95_processing_minutes.toFixed(2)}</td>
                                        <td style={{ padding: '6px 4px' }}>{row.total_events}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            <div className="workspace-sidebar-card" data-testid="travel-kpi-fallback-cards">
                <p className="workspace-card-kicker">fallback 비율</p>
                {!payload ? (
                    <p style={{ marginTop: 8, fontSize: 13, color: 'rgba(255,255,255,0.68)' }}>
                        KPI 데이터가 없습니다.
                    </p>
                ) : (
                    <div style={{ marginTop: 10, display: 'grid', gap: 10, gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}>
                        <article style={{ border: '1px solid rgba(148,163,184,0.35)', borderRadius: 10, padding: 12 }}>
                            <p style={{ margin: 0, fontSize: 12, color: 'rgba(255,255,255,0.68)' }}>국가 fallback 비율</p>
                            <p style={{ margin: '8px 0 4px', fontSize: 22, fontWeight: 700, color: '#e2e8f0' }}>{formatPercent(payload.fallback.country_fallback_ratio)}</p>
                            <p style={{ margin: 0, fontSize: 11, color: 'rgba(255,255,255,0.56)' }}>rules {payload.fallback.country_rule_count}</p>
                        </article>
                        <article style={{ border: '1px solid rgba(148,163,184,0.35)', borderRadius: 10, padding: 12 }}>
                            <p style={{ margin: 0, fontSize: 12, color: 'rgba(255,255,255,0.68)' }}>도시 fallback 비율</p>
                            <p style={{ margin: '8px 0 4px', fontSize: 22, fontWeight: 700, color: '#e2e8f0' }}>{formatPercent(payload.fallback.city_fallback_ratio)}</p>
                            <p style={{ margin: 0, fontSize: 11, color: 'rgba(255,255,255,0.56)' }}>rules {payload.fallback.city_rule_count}</p>
                        </article>
                        <article style={{ border: '1px solid rgba(148,163,184,0.35)', borderRadius: 10, padding: 12 }}>
                            <p style={{ margin: 0, fontSize: 12, color: 'rgba(255,255,255,0.68)' }}>기본파트너 사용 비율</p>
                            <p style={{ margin: '8px 0 4px', fontSize: 22, fontWeight: 700, color: '#e2e8f0' }}>{formatPercent(payload.fallback.default_partner_usage_ratio)}</p>
                            <p style={{ margin: 0, fontSize: 11, color: 'rgba(255,255,255,0.56)' }}>recommendation 기반</p>
                        </article>
                    </div>
                )}
            </div>

            <div className="workspace-sidebar-card" data-testid="travel-kpi-alert-summary">
                <p className="workspace-card-kicker">운영 알림 요약</p>
                {!payload?.ops?.alert_summary ? (
                    <p style={{ marginTop: 8, fontSize: 13, color: 'rgba(255,255,255,0.68)' }}>
                        KPI를 갱신하면 알림 요약이 표시됩니다.
                    </p>
                ) : (
                    <>
                        <div style={{ marginTop: 10, display: 'grid', gap: 10, gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))' }}>
                            <article style={{ border: '1px solid rgba(248,113,113,0.45)', borderRadius: 10, padding: 12 }}>
                                <p style={{ margin: 0, fontSize: 12, color: 'rgba(255,255,255,0.68)' }}>critical</p>
                                <p style={{ margin: '8px 0 0', fontSize: 22, fontWeight: 700, color: '#fca5a5' }}>{payload.ops.alert_summary.critical_count}</p>
                            </article>
                            <article style={{ border: '1px solid rgba(251,191,36,0.45)', borderRadius: 10, padding: 12 }}>
                                <p style={{ margin: 0, fontSize: 12, color: 'rgba(255,255,255,0.68)' }}>warning</p>
                                <p style={{ margin: '8px 0 0', fontSize: 22, fontWeight: 700, color: '#fde68a' }}>{payload.ops.alert_summary.warning_count}</p>
                            </article>
                            <article style={{ border: '1px solid rgba(134,239,172,0.45)', borderRadius: 10, padding: 12 }}>
                                <p style={{ margin: 0, fontSize: 12, color: 'rgba(255,255,255,0.68)' }}>ok</p>
                                <p style={{ margin: '8px 0 0', fontSize: 22, fontWeight: 700, color: '#86efac' }}>{payload.ops.alert_summary.ok_count}</p>
                            </article>
                        </div>
                        <p style={{ marginTop: 8, fontSize: 12, color: 'rgba(255,255,255,0.72)' }}>
                            overall: <strong>{payload.ops.alert_summary.overall}</strong>
                        </p>
                        <ul style={{ marginTop: 8, paddingLeft: 18, color: 'rgba(255,255,255,0.82)', fontSize: 12 }}>
                            {(payload.ops.alerts || []).map((item) => (
                                <li key={item.id}>
                                    [{item.severity}] {item.label}: {item.value.toFixed(4)} ({item.operator} {item.threshold.toFixed(4)})
                                </li>
                            ))}
                        </ul>
                    </>
                )}
            </div>
        </div>
    );
}

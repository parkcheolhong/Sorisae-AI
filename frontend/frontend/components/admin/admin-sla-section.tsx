'use client';

import React from 'react';
import type { AdminRailSlaSettings } from '@/lib/admin-rail-settings-service';
import { getAdminToken } from '@/lib/admin-session';
import { loadAdminTravelPartnerKpi, type AdminTravelPartnerKpiResponse } from '@/lib/admin-travel-partner-service';

interface AdminSLASectionProps {
    settings?: AdminRailSlaSettings;
}

type SlaStatus = 'pass' | 'warning';

type SlaMetric = {
    service: string;
    goal: string;
    current: string;
    status: SlaStatus;
    uptime: string;
    breaches: number;
    downtime: string;
};

type SlaIncident = {
    service: string;
    date: string;
    duration: string;
    reason: string;
};

const STATUS_META: Record<SlaStatus, { icon: string; badge: string; rowClass: string; metricClass: string }> = {
    pass: {
        icon: '✓',
        badge: '정상',
        rowClass: 'border-emerald-500/20 bg-emerald-500/[0.06]',
        metricClass: 'text-emerald-300',
    },
    warning: {
        icon: '⚠',
        badge: '주의',
        rowClass: 'border-amber-500/20 bg-amber-500/[0.06]',
        metricClass: 'text-amber-300',
    },
};

function buildSlaMetrics(marketplaceGoal: string): SlaMetric[] {
    return [
        {
            service: '마켓플레이스',
            goal: marketplaceGoal,
            current: '99.82%',
            status: 'warning',
            uptime: '720h 56m',
            breaches: 1,
            downtime: '10m 48s',
        },
        {
            service: '관리 패널',
            goal: '99.5%',
            current: '99.95%',
            status: 'pass',
            uptime: '720h 59m 45s',
            breaches: 0,
            downtime: '15s',
        },
        {
            service: 'API 게이트웨이',
            goal: '99.99%',
            current: '99.98%',
            status: 'warning',
            uptime: '720h 57m 12s',
            breaches: 1,
            downtime: '5m 16s',
        },
        {
            service: 'LLM 서비스',
            goal: '95%',
            current: '97.3%',
            status: 'pass',
            uptime: '697h 0m',
            breaches: 0,
            downtime: '23h',
        },
        {
            service: '데이터 파이프라인',
            goal: '99%',
            current: '99.15%',
            status: 'pass',
            uptime: '714h 0m',
            breaches: 0,
            downtime: '6h',
        },
    ];
}

const SLA_INCIDENTS: SlaIncident[] = [
    { service: 'API Gateway', date: '2025-01-15', duration: '5m 16s', reason: 'DB 연결 풀 고갈' },
    { service: '마켓플레이스', date: '2025-01-08', duration: '10m 48s', reason: 'Redis 메모리 부족' },
    { service: 'API Gateway', date: '2024-12-28', duration: '3m 22s', reason: '네트워크 타임아웃' },
    { service: '마켓플레이스', date: '2024-12-15', duration: '2m 45s', reason: '예정된 유지보수' },
];

function formatPercent(value: number): string {
    if (!Number.isFinite(value)) {
        return '-';
    }
    return `${(value * 100).toFixed(2)}%`;
}

function buildSlaMetricsFromPayload(payload: AdminTravelPartnerKpiResponse | null, marketplaceGoal: string): SlaMetric[] {
    if (!payload) {
        return buildSlaMetrics(marketplaceGoal);
    }
    const partnerRows = (payload.sla || []).slice(0, 5).map((row) => {
        const status: SlaStatus = row.error_rate > 0.1 || row.success_rate < 0.85 ? 'warning' : 'pass';
        return {
            service: row.partner_id,
            goal: '성공률 85% 이상',
            current: formatPercent(row.success_rate),
            status,
            uptime: `event ${row.total_events}`,
            breaches: status === 'warning' ? 1 : 0,
            downtime: `p95 ${row.p95_processing_minutes.toFixed(2)}m`,
        } satisfies SlaMetric;
    });

    const marketplaceRow: SlaMetric = {
        service: '마켓플레이스',
        goal: marketplaceGoal,
        current: formatPercent(1 - Number(payload.funnel.cancel_rate || 0)),
        status: Number(payload.funnel.cancel_rate || 0) > 0.2 ? 'warning' : 'pass',
        uptime: `booking ${payload.funnel.counts.bookings}`,
        breaches: Number(payload.funnel.cancel_rate || 0) > 0.2 ? 1 : 0,
        downtime: `cancel ${(payload.funnel.cancel_rate * 100).toFixed(1)}%`,
    };

    return [marketplaceRow, ...partnerRows];
}

function buildSlaIncidentsFromPayload(payload: AdminTravelPartnerKpiResponse | null): SlaIncident[] {
    if (!payload) {
        return SLA_INCIDENTS;
    }
    const generatedAt = String(payload.generated_at || '').slice(0, 10) || '-';
    const alerts = payload.ops?.alerts || [];
    const incidents = alerts
        .filter((item) => item.severity === 'critical' || item.severity === 'warning')
        .slice(0, 4)
        .map((item) => ({
            service: item.label,
            date: generatedAt,
            duration: `threshold ${item.threshold}`,
            reason: `현재 ${item.value} (조건 ${item.operator} ${item.threshold})`,
        }));
    return incidents.length > 0 ? incidents : SLA_INCIDENTS;
}

export default function AdminSLASection({ settings }: AdminSLASectionProps) {
    const marketplaceGoal = `${settings?.availability_target_percent ?? 99.9}%`;
    const [loading, setLoading] = React.useState(false);
    const [error, setError] = React.useState<string | null>(null);
    const [payload, setPayload] = React.useState<AdminTravelPartnerKpiResponse | null>(null);

    const apiBaseUrl = React.useMemo(() => {
        const fromEnv = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE || '';
        if (fromEnv) {
            return fromEnv.replace(/\/$/, '');
        }
        if (typeof window !== 'undefined') {
            return window.location.origin;
        }
        return '';
    }, []);

    const withAdminToken = React.useCallback(async <T,>(handler: (token: string) => Promise<T>) => {
        const token = getAdminToken();
        if (!token) {
            throw new Error('관리자 토큰이 없습니다. 다시 로그인 후 시도하세요.');
        }
        return handler(token);
    }, []);

    const loadLiveSla = React.useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const nextPayload = await withAdminToken((token) =>
                loadAdminTravelPartnerKpi({ apiBaseUrl, token })
            );
            setPayload(nextPayload);
        } catch (loadError: any) {
            if (String(loadError?.message || '').includes('__ADMIN_TRAVEL_PARTNER_UNAUTHORIZED__')) {
                setError('권한이 만료되었습니다. 관리자 로그인 후 다시 시도하세요.');
            } else {
                setError(String(loadError?.message || 'SLA 운영 지표를 불러오지 못했습니다.'));
            }
        } finally {
            setLoading(false);
        }
    }, [apiBaseUrl, withAdminToken]);

    React.useEffect(() => {
        void loadLiveSla();
    }, [loadLiveSla]);

    const slaMetrics = React.useMemo(() => buildSlaMetricsFromPayload(payload, marketplaceGoal), [payload, marketplaceGoal]);
    const slaIncidents = React.useMemo(() => buildSlaIncidentsFromPayload(payload), [payload]);
    const warningCount = slaMetrics.filter((metric) => metric.status === 'warning').length;
    const avgHealthPercent = React.useMemo(() => {
        const values = (payload?.sla || []).map((item) => Number(item.success_rate || 0));
        if (!values.length) {
            return 99.63;
        }
        return Number(((values.reduce((sum, value) => sum + value, 0) / values.length) * 100).toFixed(2));
    }, [payload]);

    return (
        <div className="workspace-section-stack p-4" data-testid="admin-sla-window-panel">
            <section className="rounded-[24px] border border-cyan-500/20 bg-[radial-gradient(circle_at_top,_rgba(24,98,160,0.28),_rgba(9,14,24,0.96)_58%)] p-5 shadow-[0_28px_80px_rgba(0,0,0,0.32)]">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                    <div>
                        <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-cyan-200/80">SLA CONTROL</p>
                        <h3 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-white">SLA 정의 및 알림 구성</h3>
                        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">
                            SLA 목표를 설정하고 준수 여부를 실시간으로 모니터링합니다.
                        </p>
                        <p className="mt-2 text-sm text-slate-400">
                            가용성 목표 · 성능 기준 · 실시간 준수 현황
                        </p>
                    </div>
                    <div className="grid min-w-[260px] grid-cols-2 gap-3 text-xs sm:min-w-[320px]">
                        <div className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3">
                            <p className="text-slate-400">활성 서비스</p>
                            <p className="mt-1 text-lg font-semibold text-white">{slaMetrics.length}개</p>
                        </div>
                        <div className="rounded-2xl border border-amber-400/20 bg-amber-400/[0.06] px-4 py-3">
                            <p className="text-amber-100/70">주의 상태</p>
                            <p className="mt-1 text-lg font-semibold text-amber-200">{warningCount}개</p>
                        </div>
                    </div>
                </div>
                <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
                    <button
                        type="button"
                        onClick={() => {
                            void loadLiveSla();
                        }}
                        disabled={loading}
                        className="rounded-full border border-cyan-300/40 bg-cyan-400/[0.08] px-3 py-1 font-semibold text-cyan-100 hover:bg-cyan-400/[0.16] disabled:opacity-60"
                    >
                        {loading ? '지표 갱신 중...' : '실시간 SLA 갱신'}
                    </button>
                    <span className="text-slate-400">generated_at: {payload?.generated_at || '-'}</span>
                    {error && <span className="text-rose-300">{error}</span>}
                </div>
            </section>

            <section className="rounded-[24px] border border-slate-700/70 bg-slate-950/70 p-5 shadow-[0_20px_60px_rgba(0,0,0,0.24)]">
                <div className="mb-4 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                    <div>
                        <h4 className="text-base font-semibold text-white">SLA 모니터링 대시보드</h4>
                        <p className="mt-1 text-sm text-slate-400">월별 SLA 목표 달성율과 가동시간 추적. 위반 이력 및 근본 원인 분석.</p>
                    </div>
                    <div className="flex flex-wrap gap-2 text-xs">
                        <span className="rounded-full border border-cyan-400/25 bg-cyan-400/[0.08] px-3 py-1 font-medium text-cyan-100">
                            목표 가용성 {marketplaceGoal}
                        </span>
                        <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 font-medium text-slate-300">
                            알림 {settings?.alert_on_breach ? 'ON' : 'OFF'}
                        </span>
                    </div>
                </div>

                <div className="overflow-x-auto">
                    <table className="min-w-full border-separate border-spacing-y-2" data-testid="admin-sla-table">
                        <thead>
                            <tr className="text-left text-[11px] uppercase tracking-[0.18em] text-slate-500">
                                <th className="px-3 py-2 font-semibold">서비스</th>
                                <th className="px-3 py-2 font-semibold">목표</th>
                                <th className="px-3 py-2 font-semibold">현재</th>
                                <th className="px-3 py-2 font-semibold">상태</th>
                                <th className="px-3 py-2 font-semibold">가동시간</th>
                                <th className="px-3 py-2 font-semibold">위반</th>
                                <th className="px-3 py-2 font-semibold">다운타임</th>
                            </tr>
                        </thead>
                        <tbody>
                            {slaMetrics.map((metric) => {
                                const meta = STATUS_META[metric.status];
                                return (
                                    <tr key={metric.service} className={`${meta.rowClass}`}>
                                        <td className="rounded-l-2xl border-y border-l border-inherit px-3 py-3 text-sm font-semibold text-white">{metric.service}</td>
                                        <td className="border-y border-inherit px-3 py-3 text-sm text-slate-300">{metric.goal}</td>
                                        <td className={`border-y border-inherit px-3 py-3 text-sm font-semibold ${meta.metricClass}`}>{metric.current}</td>
                                        <td className="border-y border-inherit px-3 py-3">
                                            <span className={`inline-flex min-w-[64px] items-center justify-center gap-1 rounded-full border border-white/10 px-2.5 py-1 text-xs font-semibold ${meta.metricClass}`}>
                                                <span aria-hidden="true">{meta.icon}</span>
                                                {meta.badge}
                                            </span>
                                        </td>
                                        <td className="border-y border-inherit px-3 py-3 text-sm text-slate-300">{metric.uptime}</td>
                                        <td className={`border-y border-inherit px-3 py-3 text-sm font-semibold ${metric.breaches > 0 ? 'text-amber-200' : 'text-emerald-200'}`}>{metric.breaches}</td>
                                        <td className="rounded-r-2xl border-y border-r border-inherit px-3 py-3 text-sm text-slate-400">{metric.downtime}</td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </section>

            <section className="grid gap-4 xl:grid-cols-[1.55fr_0.9fr]">
                <div className="rounded-[24px] border border-slate-700/70 bg-slate-950/70 p-5 shadow-[0_20px_60px_rgba(0,0,0,0.24)]">
                    <div className="mb-4 flex items-center justify-between gap-4">
                        <h4 className="text-base font-semibold text-white">이달 SLA 위반 이력 (최근 4건)</h4>
                        <span className="rounded-full border border-red-400/20 bg-red-400/[0.06] px-3 py-1 text-xs font-semibold text-red-200">최근 4건</span>
                    </div>
                    <div className="space-y-3">
                        {slaIncidents.map((incident) => (
                            <article key={`${incident.service}-${incident.date}`} className="rounded-2xl border border-red-500/15 bg-[linear-gradient(135deg,rgba(127,29,29,0.14),rgba(15,23,42,0.72))] p-4">
                                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                                    <div>
                                        <p className="text-sm font-semibold text-white">{incident.service}</p>
                                        <p className="mt-1 text-xs text-slate-400">{incident.date}</p>
                                    </div>
                                    <div className="text-sm font-semibold text-red-200">{incident.duration}</div>
                                </div>
                                <p className="mt-3 text-sm text-slate-300">
                                    원인: <strong className="font-semibold text-white">{incident.reason}</strong>
                                </p>
                            </article>
                        ))}
                    </div>
                </div>

                <div className="space-y-4">
                    <section className="rounded-[24px] border border-emerald-500/20 bg-emerald-500/[0.07] p-5 shadow-[0_18px_50px_rgba(0,0,0,0.18)]">
                        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-emerald-100/80">MONTHLY HEALTH</p>
                        <p className="mt-3 text-lg font-semibold text-emerald-100">✓ 월별 평균 가동시간: {avgHealthPercent.toFixed(2)}%</p>
                        <p className="mt-2 text-sm text-emerald-50/80">월 기준 합산 지표로 전체 운영 레일의 평균 준수율을 표시합니다.</p>
                    </section>

                    <section className="rounded-[24px] border border-amber-500/20 bg-amber-500/[0.08] p-5 shadow-[0_18px_50px_rgba(0,0,0,0.18)]">
                        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-amber-100/80">ALERT ROUTING</p>
                        <p className="mt-3 text-lg font-semibold text-amber-100">
                            ⚠️ SLA 자동 Push {settings?.auto_push_on_breach ? '활성' : '비활성'} · 쿨다운 {settings?.breach_cooldown_minutes ?? 15}분
                        </p>
                        <p className="mt-2 text-sm text-amber-50/80">장애 감지 후 관리자 Push 재전송 전까지 중복 알림을 억제하는 운영 설정입니다.</p>
                    </section>
                </div>
            </section>
        </div>
    );
}

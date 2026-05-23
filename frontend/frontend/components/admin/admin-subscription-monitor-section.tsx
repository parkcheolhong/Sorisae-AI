'use client';

import * as React from 'react';
import type { AdminSubscriptionMonitorSummary } from '@/lib/admin-dashboard-types';
import { getAdminToken } from '@/lib/admin-session';

type AdminSubscriptionMonitorSectionProps = {
    apiBaseUrl: string;
};

function formatDate(value?: string | null): string {
    if (!value) {
        return '-';
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return value;
    }
    return date.toLocaleString();
}

export default function AdminSubscriptionMonitorSection({ apiBaseUrl }: AdminSubscriptionMonitorSectionProps) {
    const [data, setData] = React.useState<AdminSubscriptionMonitorSummary | null>(null);
    const [loading, setLoading] = React.useState<boolean>(false);
    const [error, setError] = React.useState<string>('');
    const [periodDays, setPeriodDays] = React.useState<number>(30);
    const [statusFilter, setStatusFilter] = React.useState<string>('all');
    const filtersInitializedRef = React.useRef(false);

    React.useEffect(() => {
        if (filtersInitializedRef.current || typeof window === 'undefined') {
            return;
        }
        filtersInitializedRef.current = true;

        const currentUrl = new URL(window.location.href);
        const periodFromQuery = Number.parseInt(currentUrl.searchParams.get('period_days') || '', 10);
        const statusFromQuery = (currentUrl.searchParams.get('status') || '').trim();

        if ([7, 30, 90].includes(periodFromQuery)) {
            setPeriodDays(periodFromQuery);
        }
        if (statusFromQuery) {
            setStatusFilter(statusFromQuery);
        }
    }, []);

    const loadData = React.useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const token = getAdminToken();
            const params = new URLSearchParams();
            params.set('period_days', String(periodDays));
            if (statusFilter !== 'all') {
                params.set('status', statusFilter);
            }
            const response = await fetch(`${apiBaseUrl}/api/admin/subscription-monitor-summary?${params.toString()}`, {
                headers: token ? { Authorization: `Bearer ${token}` } : undefined,
                cache: 'no-store',
            });
            if (!response.ok) {
                const payload = await response.text();
                throw new Error(payload || `요청 실패 (${response.status})`);
            }
            const payload = (await response.json()) as AdminSubscriptionMonitorSummary;
            setData(payload);
        } catch (fetchError) {
            const message = fetchError instanceof Error ? fetchError.message : '구독 모니터링 데이터를 불러오지 못했습니다.';
            setError(message);
        } finally {
            setLoading(false);
        }
    }, [apiBaseUrl, periodDays, statusFilter]);

    React.useEffect(() => {
        void loadData();
    }, [loadData]);

    const totals = data?.totals;
    const availableStatuses = React.useMemo(() => {
        const statuses = new Set<string>();
        for (const item of data?.status_breakdown ?? []) {
            if (item.status) {
                statuses.add(item.status);
            }
        }
        return ['all', ...Array.from(statuses).sort()];
    }, [data?.status_breakdown]);

    return (
        <div style={{ padding: '0 20px 20px 20px' }}>
            <div className="workspace-admin-command-actions" style={{ marginBottom: '12px', gap: '8px', flexWrap: 'wrap' }}>
                <label style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: '#cbd5e1', fontSize: '13px' }}>
                    기간
                    <select
                        value={String(periodDays)}
                        onChange={(event) => {
                            setPeriodDays(Number.parseInt(event.target.value, 10));
                        }}
                        className="workspace-input"
                        disabled={loading}
                        style={{ minWidth: '110px' }}
                    >
                        <option value="7">최근 7일</option>
                        <option value="30">최근 30일</option>
                        <option value="90">최근 90일</option>
                    </select>
                </label>
                <label style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: '#cbd5e1', fontSize: '13px' }}>
                    상태
                    <select
                        value={statusFilter}
                        onChange={(event) => {
                            setStatusFilter(event.target.value);
                        }}
                        className="workspace-input"
                        disabled={loading}
                        style={{ minWidth: '140px' }}
                    >
                        {availableStatuses.map((statusOption) => (
                            <option key={statusOption} value={statusOption}>
                                {statusOption === 'all' ? '전체 상태' : statusOption}
                            </option>
                        ))}
                    </select>
                </label>
                <button
                    type="button"
                    onClick={() => {
                        void loadData();
                    }}
                    className="workspace-secondary-button"
                    disabled={loading}
                >
                    {loading ? '갱신 중...' : '구독 모니터링 새로고침'}
                </button>
            </div>

            {error ? <p className="workspace-card-copy" style={{ color: '#fca5a5' }}>{error}</p> : null}

            <div className="workspace-list" style={{ marginBottom: '16px' }}>
                <div className="workspace-list-item">
                    <div><strong>전체 구독</strong><span>유효/만료 포함 전체</span></div>
                    <strong>{totals?.total_subscriptions ?? 0}</strong>
                </div>
                <div className="workspace-list-item">
                    <div><strong>활성 구독</strong><span>active/trialing/grace_period</span></div>
                    <strong>{totals?.active_subscriptions ?? 0}</strong>
                </div>
                <div className="workspace-list-item">
                    <div><strong>최근 {data?.filters?.period_days ?? periodDays}일 실패 결제</strong><span>renewal_failed 이벤트</span></div>
                    <strong>{totals?.failed_payment_count ?? 0}</strong>
                </div>
                <div className="workspace-list-item">
                    <div><strong>최근 {data?.filters?.period_days ?? periodDays}일 환불</strong><span>refund_applied 이벤트</span></div>
                    <strong>{totals?.refunds_count ?? 0}</strong>
                </div>
            </div>

            <h4 style={{ color: 'white', fontSize: '15px', fontWeight: 700, marginBottom: '8px' }}>상태 분포</h4>
            {data?.status_breakdown?.length ? (
                <ul className="workspace-list" style={{ marginBottom: '16px' }}>
                    {data.status_breakdown.map((item) => (
                        <li key={item.status} className="workspace-list-item">
                            <div><strong>{item.status}</strong><span>subscription status</span></div>
                            <strong>{item.count}</strong>
                        </li>
                    ))}
                </ul>
            ) : (
                <p className="workspace-card-copy" style={{ marginBottom: '16px' }}>집계된 상태 데이터가 없습니다.</p>
            )}

            <h4 style={{ color: 'white', fontSize: '15px', fontWeight: 700, marginBottom: '8px' }}>최근 상태 변경 이력</h4>
            {data?.recent_state_transitions?.length ? (
                <ul className="workspace-list" style={{ marginBottom: '16px' }}>
                    {data.recent_state_transitions.slice(0, 8).map((item) => (
                        <li key={item.id} className="workspace-list-item">
                            <div>
                                <strong>{item.from_status || '-'} → {item.to_status || '-'}</strong>
                                <span>reason: {item.reason_code || '-'} · actor: {item.actor_type || '-'} · sub #{item.subscription_id}</span>
                            </div>
                            <span>{formatDate(item.created_at)}</span>
                        </li>
                    ))}
                </ul>
            ) : (
                <p className="workspace-card-copy" style={{ marginBottom: '16px' }}>최근 상태 변경 이력이 없습니다.</p>
            )}

            <h4 style={{ color: 'white', fontSize: '15px', fontWeight: 700, marginBottom: '8px' }}>웹훅 실패/재시도 이력</h4>
            {data?.recent_webhook_failures?.length ? (
                <ul className="workspace-list">
                    {data.recent_webhook_failures.slice(0, 8).map((item) => (
                        <li key={item.id} className="workspace-list-item">
                            <div>
                                <strong>{item.provider} · {item.result}</strong>
                                <span>
                                    event: {item.event_id || '-'} · attempt: {item.attempt_number} · http: {item.http_status ?? '-'}
                                    {item.error_message ? ` · ${item.error_message}` : ''}
                                </span>
                            </div>
                            <span>{formatDate(item.created_at)}</span>
                        </li>
                    ))}
                </ul>
            ) : (
                <p className="workspace-card-copy">최근 웹훅 실패 이력이 없습니다.</p>
            )}
        </div>
    );
}

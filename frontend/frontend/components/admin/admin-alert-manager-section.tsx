'use client';

import React from 'react';
import { getAdminToken } from '@/lib/admin-session';
import {
    loadAdminTravelPartnerKpi,
    type AdminTravelKpiAlert,
    type AdminTravelPartnerKpiResponse,
} from '@/lib/admin-travel-partner-service';
import type { AdminRailSlaSettings } from '@/lib/admin-rail-settings-service';

interface AdminAlertManagerSectionProps {
    settings?: AdminRailSlaSettings;
}

type AlertRowStatus = 'active' | 'warning' | 'healthy';

type AlertRowSeverity = 'critical' | 'high' | 'medium' | 'low';

type AlertRow = {
    id: string;
    name: string;
    threshold: string;
    severity: AlertRowSeverity;
    status: AlertRowStatus;
    current: string;
    lastTriggered: string;
    escalation: string;
};

function formatMetricValue(value: number): string {
    if (!Number.isFinite(value)) {
        return '-';
    }
    if (Math.abs(value) <= 1) {
        return `${(value * 100).toFixed(1)}%`;
    }
    return value.toFixed(2);
}

function formatThreshold(operator: 'gte' | 'lte', threshold: number): string {
    const symbol = operator === 'gte' ? '>=' : '<=';
    return `${symbol} ${formatMetricValue(threshold)}`;
}

function toAlertRow(alert: AdminTravelKpiAlert, generatedAt?: string | null): AlertRow {
    const status: AlertRowStatus = alert.severity === 'critical'
        ? 'active'
        : alert.severity === 'warning'
            ? 'warning'
            : 'healthy';
    const severity: AlertRowSeverity = alert.severity === 'critical'
        ? 'critical'
        : alert.severity === 'warning'
            ? 'high'
            : 'low';
    return {
        id: alert.id,
        name: alert.label,
        threshold: formatThreshold(alert.operator, alert.threshold),
        severity,
        status,
        current: formatMetricValue(alert.value),
        lastTriggered: generatedAt || '-',
        escalation: '대시보드 알림 → 관리자 패널 → 운영 채널',
    };
}

export default function AdminAlertManagerSection({ settings }: AdminAlertManagerSectionProps) {
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

    const loadLiveAlerts = React.useCallback(async () => {
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
                setError(String(loadError?.message || '운영 알람 지표를 불러오지 못했습니다.'));
            }
        } finally {
            setLoading(false);
        }
    }, [apiBaseUrl, withAdminToken]);

    React.useEffect(() => {
        void loadLiveAlerts();
    }, [loadLiveAlerts]);

    const alerts = React.useMemo(() => {
        const source = payload?.ops?.alerts || [];
        return source.map((item) => toAlertRow(item, payload?.generated_at));
    }, [payload]);

    const summary = payload?.ops?.alert_summary;
    const healthyCount = summary?.ok_count ?? alerts.filter((item) => item.status === 'healthy').length;
    const warningCount = summary?.warning_count ?? alerts.filter((item) => item.status === 'warning').length;
    const activeCount = summary?.critical_count ?? alerts.filter((item) => item.status === 'active').length;

    const getSeverityColor = (severity: string) => {
        switch (severity) {
            case 'critical':
                return '#ef4444';
            case 'high':
                return '#f59e0b';
            case 'medium':
                return '#3b82f6';
            default:
                return '#10b981';
        }
    };

    const getSeverityLabel = (severity: string) => {
        switch (severity) {
            case 'critical':
                return '긴급';
            case 'high':
                return '높음';
            case 'medium':
                return '중간';
            default:
                return '낮음';
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'active':
                return '#ef4444';
            case 'warning':
                return '#f59e0b';
            default:
                return '#10b981';
        }
    };

    const getStatusLabel = (status: string) => {
        switch (status) {
            case 'active':
                return '활성';
            case 'warning':
                return '경고';
            default:
                return '정상';
        }
    };

    return (
        <div className="workspace-section-stack" style={{ padding: '16px' }}>
            <div style={{ marginBottom: '20px' }}>
                <h4 style={{ color: 'rgba(255,255,255,0.9)', marginBottom: '8px', fontSize: '14px', fontWeight: 600 }}>
                    Alert Manager - 규칙 및 정책
                </h4>
                <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: '13px', lineHeight: '1.5' }}>
                    운영 KPI API 기준 실시간 알람 규칙, 상태 모니터링, 에스컬레이션 정책 관리.
                </p>
                <div style={{ marginTop: '10px', display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
                    <button
                        type="button"
                        onClick={() => {
                            void loadLiveAlerts();
                        }}
                        disabled={loading}
                        className="workspace-btn-secondary"
                    >
                        {loading ? '갱신 중...' : '실시간 지표 새로고침'}
                    </button>
                    <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.55)' }}>
                        generated_at: {payload?.generated_at || '-'}
                    </span>
                </div>
                {error && (
                    <p style={{ marginTop: '8px', color: '#fca5a5', fontSize: '12px' }}>{error}</p>
                )}
            </div>

            {/* 요약 카드 */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '12px', marginBottom: '20px' }}>
                <div style={{ borderRadius: '8px', border: '1px solid rgba(239,68,68,0.3)', background: 'rgba(239,68,68,0.05)', padding: '12px' }}>
                    <div style={{ fontSize: '11px', color: 'rgba(239,68,68,0.7)', marginBottom: '4px' }}>
                        활성 알림
                    </div>
                    <div style={{ fontSize: '20px', fontWeight: 700, color: '#ef4444' }}>{activeCount}</div>
                </div>
                <div style={{ borderRadius: '8px', border: '1px solid rgba(245,158,11,0.3)', background: 'rgba(245,158,11,0.05)', padding: '12px' }}>
                    <div style={{ fontSize: '11px', color: 'rgba(245,158,11,0.7)', marginBottom: '4px' }}>
                        경고 상태
                    </div>
                    <div style={{ fontSize: '20px', fontWeight: 700, color: '#f59e0b' }}>{warningCount}</div>
                </div>
                <div style={{ borderRadius: '8px', border: '1px solid rgba(34,197,94,0.3)', background: 'rgba(34,197,94,0.05)', padding: '12px' }}>
                    <div style={{ fontSize: '11px', color: 'rgba(34,197,94,0.7)', marginBottom: '4px' }}>
                        정상 규칙
                    </div>
                    <div style={{ fontSize: '20px', fontWeight: 700, color: '#10b981' }}>{healthyCount}</div>
                </div>
                <div style={{ borderRadius: '8px', border: '1px solid rgba(168,85,247,0.3)', background: 'rgba(168,85,247,0.05)', padding: '12px' }}>
                    <div style={{ fontSize: '11px', color: 'rgba(168,85,247,0.7)', marginBottom: '4px' }}>
                        총 규칙
                    </div>
                    <div style={{ fontSize: '20px', fontWeight: 700, color: '#a855f7' }}>{alerts.length}</div>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
                <div style={{ borderRadius: '8px', border: '1px solid rgba(255,255,255,0.12)', background: 'rgba(255,255,255,0.04)', padding: '10px' }}>
                    <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.6)' }}>SLA breach alert</div>
                    <div style={{ marginTop: '4px', fontSize: '13px', color: 'rgba(255,255,255,0.85)', fontWeight: 600 }}>
                        {settings?.alert_on_breach ? 'ON' : 'OFF'}
                    </div>
                </div>
                <div style={{ borderRadius: '8px', border: '1px solid rgba(255,255,255,0.12)', background: 'rgba(255,255,255,0.04)', padding: '10px' }}>
                    <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.6)' }}>자동 Push · 쿨다운</div>
                    <div style={{ marginTop: '4px', fontSize: '13px', color: 'rgba(255,255,255,0.85)', fontWeight: 600 }}>
                        {settings?.auto_push_on_breach ? '활성' : '비활성'} / {settings?.breach_cooldown_minutes ?? 15}분
                    </div>
                </div>
            </div>

            {/* 규칙 목록 */}
            <div style={{ display: 'space-y-2' }}>
                {alerts.length === 0 && !loading && !error && (
                    <div style={{ borderRadius: '8px', border: '1px solid rgba(255,255,255,0.12)', background: 'rgba(255,255,255,0.03)', padding: '12px', fontSize: '12px', color: 'rgba(255,255,255,0.65)' }}>
                        표시할 실시간 알림 규칙이 없습니다.
                    </div>
                )}
                {alerts.map((alert, idx) => (
                    <div
                        key={`${alert.id}-${idx}`}
                        style={{
                            borderRadius: '8px',
                            border: `1px solid ${getStatusColor(alert.status)}20`,
                            background: `${getStatusColor(alert.status)}05`,
                            padding: '12px',
                            marginBottom: '8px',
                        }}
                    >
                        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                            {/* 상태 인디케이터 */}
                            <div
                                style={{
                                    width: '24px',
                                    height: '24px',
                                    borderRadius: '50%',
                                    background: getStatusColor(alert.status),
                                    opacity: 0.2,
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    flexShrink: 0,
                                }}
                            >
                                <div
                                    style={{
                                        width: '8px',
                                        height: '8px',
                                        borderRadius: '50%',
                                        background: getStatusColor(alert.status),
                                    }}
                                />
                            </div>

                            {/* 내용 */}
                            <div style={{ flex: 1 }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                                    <h5 style={{ margin: '0', fontSize: '13px', fontWeight: 600, color: 'rgba(255,255,255,0.9)' }}>
                                        {alert.name}
                                    </h5>
                                    <span
                                        style={{
                                            fontSize: '10px',
                                            fontWeight: 600,
                                            color: getSeverityColor(alert.severity),
                                            background: `${getSeverityColor(alert.severity)}20`,
                                            border: `1px solid ${getSeverityColor(alert.severity)}40`,
                                            padding: '2px 6px',
                                            borderRadius: '3px',
                                        }}
                                    >
                                        {getSeverityLabel(alert.severity)}
                                    </span>
                                    <span
                                        style={{
                                            fontSize: '10px',
                                            fontWeight: 600,
                                            color: getStatusColor(alert.status),
                                            background: `${getStatusColor(alert.status)}20`,
                                            border: `1px solid ${getStatusColor(alert.status)}40`,
                                            padding: '2px 6px',
                                            borderRadius: '3px',
                                        }}
                                    >
                                        {getStatusLabel(alert.status)}
                                    </span>
                                </div>

                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '8px', fontSize: '11px', color: 'rgba(255,255,255,0.6)' }}>
                                    <div>
                                        <span style={{ color: 'rgba(255,255,255,0.4)' }}>임계값:</span> {alert.threshold}
                                    </div>
                                    <div>
                                        <span style={{ color: 'rgba(255,255,255,0.4)' }}>현재:</span>{' '}
                                        <strong style={{ color: 'rgba(255,255,255,0.8)' }}>{alert.current}</strong>
                                    </div>
                                </div>

                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '11px' }}>
                                    <div style={{ color: 'rgba(255,255,255,0.5)' }}>
                                        마지막 호출: <strong style={{ color: 'rgba(255,255,255,0.7)' }}>{alert.lastTriggered}</strong>
                                    </div>
                                    <div style={{ color: 'rgba(255,255,255,0.5)' }}>
                                        에스컬레이션: <strong style={{ color: 'rgba(255,255,255,0.7)' }}>{alert.escalation}</strong>
                                    </div>
                                </div>
                            </div>

                            {/* 액션 버튼 */}
                            <div style={{ display: 'flex', gap: '6px', flexShrink: 0 }}>
                                <button
                                    type="button"
                                    style={{
                                        padding: '4px 8px',
                                        borderRadius: '4px',
                                        border: '1px solid rgba(255,255,255,0.2)',
                                        background: 'rgba(255,255,255,0.05)',
                                        color: 'rgba(255,255,255,0.6)',
                                        fontSize: '10px',
                                        cursor: 'pointer',
                                    }}
                                >
                                    편집
                                </button>
                                <button
                                    type="button"
                                    style={{
                                        padding: '4px 8px',
                                        borderRadius: '4px',
                                        border: '1px solid rgba(255,255,255,0.2)',
                                        background: 'rgba(255,255,255,0.05)',
                                        color: 'rgba(255,255,255,0.6)',
                                        fontSize: '10px',
                                        cursor: 'pointer',
                                    }}
                                >
                                    테스트
                                </button>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            <div style={{ borderRadius: '8px', border: '1px solid rgba(59,130,246,0.3)', background: 'rgba(59,130,246,0.05)', padding: '12px', marginTop: '16px' }}>
                <p style={{ fontSize: '12px', color: 'rgba(59,130,246,0.8)', margin: '0' }}>
                    💡 팁: 알림 규칙은 주기적으로 검토하여 임계값을 시스템 성능에 맞게 조정하세요.
                </p>
            </div>
        </div>
    );
}

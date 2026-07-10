'use client';

import React from 'react';
import type { AdminRailDataSettings } from '@/lib/admin-rail-settings-service';

interface AdminPrometheusSectionProps {
    apiBaseUrl?: string;
    settings?: AdminRailDataSettings;
}

export default function AdminPrometheusSection({
    apiBaseUrl = 'http://127.0.0.1:8000',
    settings,
}: AdminPrometheusSectionProps) {
    const [metrics, setMetrics] = React.useState<Record<string, number>>({});
    const [loading, setLoading] = React.useState(false);
    const [selectedQuery, setSelectedQuery] = React.useState(settings?.selected_metric_key || 'http_requests_total');

    React.useEffect(() => {
        loadMetrics();
    }, []);

    React.useEffect(() => {
        if (settings?.selected_metric_key) {
            setSelectedQuery(settings.selected_metric_key);
        }
    }, [settings?.selected_metric_key]);

    React.useEffect(() => {
        const refreshSeconds = Math.max(5, Number(settings?.metric_refresh_seconds || 20));
        const timer = window.setInterval(() => {
            void loadMetrics();
        }, refreshSeconds * 1000);
        return () => window.clearInterval(timer);
    }, [apiBaseUrl, settings?.metric_refresh_seconds]);

    const loadMetrics = async () => {
        try {
            setLoading(true);
            const response = await fetch(`${apiBaseUrl}/api/metrics/summary`);
            if (response.ok) {
                const data = await response.json();
                setMetrics(data);
            }
        } catch (error) {
            console.error('메트릭 로딩 실패:', error);
        } finally {
            setLoading(false);
        }
    };

    const queries = [
        { name: 'HTTP 요청 총합', key: 'http_requests_total', color: '#0ea5e9' },
        { name: '캐시 히트', key: 'cache_hits_total', color: '#10b981' },
        { name: '캐시 미스', key: 'cache_misses_total', color: '#ef4444' },
        { name: 'DB 쿼리', key: 'db_queries_total', color: '#f59e0b' },
        { name: '파일 업로드', key: 'file_uploads_total', color: '#8b5cf6' },
        { name: '구매 완료', key: 'purchases_total', color: '#ec4899' },
    ];
    const visibleMetrics = settings?.include_zero_metrics
        ? Object.entries(metrics)
        : Object.entries(metrics).filter(([, value]) => Number(value) !== 0);

    return (
        <div className="workspace-section-stack" style={{ padding: '16px' }}>
            <div style={{ marginBottom: '20px' }}>
                <h4 style={{ color: 'rgba(255,255,255,0.9)', marginBottom: '8px', fontSize: '14px', fontWeight: 600 }}>
                    Prometheus 시계열 데이터
                </h4>
                <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: '13px', lineHeight: '1.5' }}>
                    실시간 메트릭 데이터베이스. 모든 시스템 이벤트와 성능 지표가 시간에 따라 집계됩니다.
                </p>
            </div>

            <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', flexWrap: 'wrap' }}>
                {queries.map((query) => (
                    <button
                        key={query.key}
                        onClick={() => setSelectedQuery(query.key)}
                        style={{
                            padding: '6px 12px',
                            borderRadius: '6px',
                            border: selectedQuery === query.key ? `2px solid ${query.color}` : '1px solid rgba(255,255,255,0.2)',
                            background: selectedQuery === query.key ? `${query.color}20` : 'rgba(255,255,255,0.05)',
                            color: selectedQuery === query.key ? query.color : 'rgba(255,255,255,0.7)',
                            fontSize: '12px',
                            fontWeight: 500,
                            cursor: 'pointer',
                            transition: 'all 0.2s',
                        }}
                    >
                        {query.name}
                    </button>
                ))}
            </div>

            <div style={{ borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.02)', padding: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                    <div>
                        <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '4px' }}>
                            {queries.find(q => q.key === selectedQuery)?.name}
                        </div>
                        <div style={{ fontSize: '28px', fontWeight: 700, color: '#0ea5e9' }}>
                            {loading ? '...' : (metrics[selectedQuery as keyof typeof metrics] ?? 0).toLocaleString()}
                        </div>
                    </div>
                    <button
                        onClick={loadMetrics}
                        disabled={loading}
                        style={{
                            padding: '8px 16px',
                            borderRadius: '6px',
                            border: '1px solid rgba(255,255,255,0.2)',
                            background: 'rgba(255,255,255,0.05)',
                            color: 'rgba(255,255,255,0.7)',
                            fontSize: '12px',
                            fontWeight: 500,
                            cursor: loading ? 'not-allowed' : 'pointer',
                            opacity: loading ? 0.5 : 1,
                        }}
                    >
                        {loading ? '로딩 중...' : '새로고침'}
                    </button>
                </div>

                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.4)' }}>
                    <div style={{ marginBottom: '8px' }}>모든 메트릭 (현재 세션):</div>
                    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '4px', padding: '12px', maxHeight: '200px', overflowY: 'auto' }}>
                        {visibleMetrics.map(([key, value]) => (
                            <div key={key} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                                <span style={{ color: 'rgba(255,255,255,0.5)' }}>{key}:</span>
                                <span style={{ color: 'rgba(255,255,255,0.8)', fontWeight: 500 }}>
                                    {typeof value === 'number' ? value.toLocaleString() : String(value)}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}

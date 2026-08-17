'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { MarketplaceLeftRail, MarketplaceRightRail } from '@/components/marketplace/marketplace-rails';

interface MetricsSummary {
    http_requests_total: number;
    http_request_duration_count: number;
    active_connections: number;
    cache_hits_total: number;
    cache_misses_total: number;
    db_queries_total: number;
    file_uploads_total: number;
    purchases_total: number;
}

interface MetricHistory {
    timestamp: number;
    value: number;
}

export default function MetricsDashboardPage() {
    const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [autoRefresh, setAutoRefresh] = useState(true);
    const [lastUpdated, setLastUpdated] = useState<string>('');
    const [requestHistory, setRequestHistory] = useState<MetricHistory[]>([]);
    const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

    const fetchMetrics = useCallback(async () => {
        try {
            const res = await fetch('/api/marketplace/metrics/summary', { cache: 'no-store' });
            if (res.ok) {
                const data = await res.json() as MetricsSummary;
                setMetrics(data);
                setError(null);
                setLastUpdated(new Date().toLocaleTimeString('ko-KR'));
                setRequestHistory(prev => [
                    ...prev.slice(-59),
                    { timestamp: Date.now(), value: data.http_requests_total },
                ]);
            } else {
                setError(`메트릭 조회 실패 (${res.status})`);
            }
        } catch (err: any) {
            setError(err?.message || '메트릭 서버에 연결할 수 없습니다.');
        }
    }, []);

    useEffect(() => {
        fetchMetrics();
    }, [fetchMetrics]);

    useEffect(() => {
        if (!autoRefresh) {
            if (intervalRef.current) clearInterval(intervalRef.current);
            return;
        }
        intervalRef.current = setInterval(fetchMetrics, 5000);
        return () => {
            if (intervalRef.current) clearInterval(intervalRef.current);
        };
    }, [autoRefresh, fetchMetrics]);

    const cacheHitRate = metrics
        ? metrics.cache_hits_total + metrics.cache_misses_total > 0
            ? ((metrics.cache_hits_total / (metrics.cache_hits_total + metrics.cache_misses_total)) * 100).toFixed(1)
            : '0.0'
        : '-';

    const sparklineMax = Math.max(...requestHistory.map(h => h.value), 1);

    return (
        <div className="workspace-shell">
            <MarketplaceLeftRail activeRailId="market-home" />

            <main className="workspace-stage">
                <div className="workspace-topbar">
                    <div>
                        <p className="workspace-overline">Prometheus 메트릭</p>
                        <h1 className="workspace-page-title">시스템 메트릭 대시보드</h1>
                        <p className="workspace-page-description">
                            HTTP 요청, 캐시, 데이터베이스, 구매 메트릭을 실시간으로 모니터링합니다.
                        </p>
                    </div>
                    <div className="workspace-topbar-actions">
                        <span className="workspace-topbar-chip" style={{ fontSize: 11 }}>
                            마지막 갱신: {lastUpdated || '-'}
                        </span>
                        <button
                            onClick={() => setAutoRefresh(!autoRefresh)}
                            className={autoRefresh ? 'workspace-primary-button' : 'workspace-secondary-button'}
                            style={{ fontSize: 12 }}
                        >
                            {autoRefresh ? '🔄 자동 갱신 ON' : '⏸️ 자동 갱신 OFF'}
                        </button>
                    </div>
                </div>

                {error && (
                    <div style={{
                        padding: '12px 16px',
                        borderRadius: 'var(--workspace-radius-md)',
                        background: 'rgba(255, 107, 107, 0.1)',
                        border: '1px solid rgba(255, 107, 107, 0.3)',
                        color: 'var(--workspace-danger)',
                        fontSize: 13,
                        marginBottom: 18,
                    }}>
                        ⚠️ {error}
                    </div>
                )}

                {/* 메트릭 카드 그리드 */}
                <div className="workspace-metric-grid" style={{ marginBottom: 22 }}>
                    <div className="workspace-metric-card">
                        <div className="workspace-metric-label">HTTP 요청 합계</div>
                        <div className="workspace-metric-value" style={{ color: 'var(--workspace-accent)' }}>
                            {metrics?.http_requests_total?.toLocaleString() ?? '-'}
                        </div>
                        <div className="workspace-metric-note">누적 총 요청 수</div>
                    </div>
                    <div className="workspace-metric-card">
                        <div className="workspace-metric-label">활성 연결</div>
                        <div className="workspace-metric-value" style={{ color: 'var(--workspace-success)' }}>
                            {metrics?.active_connections ?? '-'}
                        </div>
                        <div className="workspace-metric-note">현재 처리 중</div>
                    </div>
                    <div className="workspace-metric-card">
                        <div className="workspace-metric-label">캐시 적중률</div>
                        <div className="workspace-metric-value" style={{
                            color: Number(cacheHitRate) > 80 ? 'var(--workspace-success)'
                                : Number(cacheHitRate) > 50 ? 'var(--workspace-warning)'
                                    : 'var(--workspace-danger)',
                        }}>
                            {cacheHitRate}%
                        </div>
                        <div className="workspace-metric-note">
                            적중 {metrics?.cache_hits_total ?? 0} / 미스 {metrics?.cache_misses_total ?? 0}
                        </div>
                    </div>
                    <div className="workspace-metric-card">
                        <div className="workspace-metric-label">DB 쿼리</div>
                        <div className="workspace-metric-value">
                            {metrics?.db_queries_total?.toLocaleString() ?? '-'}
                        </div>
                        <div className="workspace-metric-note">누적 쿼리 수</div>
                    </div>
                </div>

                <div className="workspace-content-grid workspace-content-grid-with-sidebar">
                    <div className="workspace-main-content" style={{ display: 'grid', gap: 18 }}>
                        {/* 요청 추이 차트 */}
                        <div className="workspace-card">
                            <h2 className="workspace-card-title">📈 요청 추이</h2>
                            <p className="workspace-card-copy">5초 간격으로 수집된 HTTP 요청 수 추이 (최근 60건)</p>
                            <div style={{
                                marginTop: 16,
                                height: 120,
                                display: 'flex',
                                alignItems: 'flex-end',
                                gap: 2,
                                padding: '0 4px',
                            }}>
                                {requestHistory.length === 0 ? (
                                    <div style={{ color: 'var(--workspace-muted)', fontSize: 13, margin: 'auto' }}>
                                        데이터 수집 중...
                                    </div>
                                ) : (
                                    requestHistory.map((point, i) => {
                                        const height = Math.max(2, (point.value / sparklineMax) * 110);
                                        return (
                                            <div
                                                key={i}
                                                title={`${point.value.toLocaleString()} 요청`}
                                                style={{
                                                    flex: 1,
                                                    height,
                                                    borderRadius: '4px 4px 0 0',
                                                    background: i === requestHistory.length - 1
                                                        ? 'var(--workspace-accent)'
                                                        : 'rgba(119, 212, 255, 0.3)',
                                                    transition: 'height 0.3s ease',
                                                    minWidth: 3,
                                                }}
                                            />
                                        );
                                    })
                                )}
                            </div>
                        </div>

                        {/* 상세 메트릭 카드 */}
                        <div className="workspace-board-grid">
                            <div className="workspace-board-card">
                                <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 12 }}>📦 파일 업로드</h3>
                                <div style={{ fontSize: 32, fontWeight: 800, color: 'var(--workspace-info)' }}>
                                    {metrics?.file_uploads_total?.toLocaleString() ?? '0'}
                                </div>
                                <div style={{ fontSize: 12, color: 'var(--workspace-muted)', marginTop: 6 }}>
                                    누적 업로드 건수
                                </div>
                            </div>
                            <div className="workspace-board-card">
                                <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 12 }}>💳 구매 트랜잭션</h3>
                                <div style={{ fontSize: 32, fontWeight: 800, color: 'var(--workspace-success)' }}>
                                    {metrics?.purchases_total?.toLocaleString() ?? '0'}
                                </div>
                                <div style={{ fontSize: 12, color: 'var(--workspace-muted)', marginTop: 6 }}>
                                    누적 구매 건수
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* 사이드바 */}
                    <aside className="workspace-sidebar">
                        <div className="workspace-sidebar-card">
                            <h3 className="workspace-card-title">🔗 엔드포인트</h3>
                            <div style={{ marginTop: 10, display: 'grid', gap: 8 }}>
                                <a
                                    href="/api/marketplace/metrics/prometheus"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={{
                                        display: 'block',
                                        padding: '10px 14px',
                                        borderRadius: 'var(--workspace-radius-sm)',
                                        border: '1px solid var(--workspace-border)',
                                        background: 'rgba(9, 14, 22, 0.7)',
                                        color: 'var(--workspace-accent)',
                                        fontSize: 13,
                                        textDecoration: 'none',
                                        fontWeight: 600,
                                    }}
                                >
                                    📊 /metrics (Prometheus)
                                </a>
                                <a
                                    href="/api/marketplace/metrics/summary"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={{
                                        display: 'block',
                                        padding: '10px 14px',
                                        borderRadius: 'var(--workspace-radius-sm)',
                                        border: '1px solid var(--workspace-border)',
                                        background: 'rgba(9, 14, 22, 0.7)',
                                        color: 'var(--workspace-accent)',
                                        fontSize: 13,
                                        textDecoration: 'none',
                                        fontWeight: 600,
                                    }}
                                >
                                    📋 /api/metrics/summary (JSON)
                                </a>
                            </div>
                        </div>

                        <div className="workspace-sidebar-card">
                            <h3 className="workspace-card-title">ℹ️ 수집 메트릭</h3>
                            <ul style={{ margin: '10px 0 0', paddingLeft: 18, fontSize: 12, color: 'var(--workspace-muted)', lineHeight: 2 }}>
                                <li>http_requests_total (메서드/경로/상태별)</li>
                                <li>http_request_duration_seconds</li>
                                <li>http_active_connections</li>
                                <li>cache_hits_total / cache_misses_total</li>
                                <li>db_queries_total</li>
                                <li>file_uploads_total</li>
                                <li>purchases_total</li>
                            </ul>
                        </div>
                    </aside>
                </div>
            </main>
            <MarketplaceRightRail activeRailId="popular" />
        </div>
    );
}

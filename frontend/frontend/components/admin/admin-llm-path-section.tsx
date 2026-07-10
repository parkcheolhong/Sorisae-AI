'use client';

import React from 'react';
import type { AdminRailLlmSettings } from '@/lib/admin-rail-settings-service';

interface AdminLlmPathSectionProps {
    settings?: AdminRailLlmSettings;
}

export default function AdminLlmPathSection({ settings }: AdminLlmPathSectionProps) {
    const [pathStats] = React.useState({
        avgLatency: 284,
        p95Latency: 520,
        throughput: 142,
        errorRate: 0.8,
        modelLoads: 3210,
        cacheHits: 1520,
        cacheMisses: 1690,
    });

    const stages = [
        {
            name: 'Request Parse',
            latency: 12,
            percentage: 4.2,
            status: '✓ Good',
            statusColor: '#10b981',
        },
        {
            name: 'Intent Detection',
            latency: 45,
            percentage: 15.8,
            status: '✓ Good',
            statusColor: '#10b981',
        },
        {
            name: 'LLM Inference',
            latency: 180,
            percentage: 63.4,
            status: '⚠ Slow',
            statusColor: '#f59e0b',
        },
        {
            name: 'Response Format',
            latency: 28,
            percentage: 9.9,
            status: '✓ Good',
            statusColor: '#10b981',
        },
        {
            name: 'Cache Write',
            latency: 19,
            percentage: 6.7,
            status: '✓ Good',
            statusColor: '#10b981',
        },
    ];

    return (
        <div className="workspace-section-stack" style={{ padding: '16px' }}>
            <div style={{ marginBottom: '20px' }}>
                <h4 style={{ color: 'rgba(255,255,255,0.9)', marginBottom: '8px', fontSize: '14px', fontWeight: 600 }}>
                    LLM 호출 경로 성능 분석
                </h4>
                <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: '13px', lineHeight: '1.5' }}>
                    엔드-투-엔드 LLM 추론 파이프라인의 각 단계별 성능 메트릭입니다.
                </p>
            </div>

            {/* 주요 지표 */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '12px', marginBottom: '20px' }}>
                <div style={{ borderRadius: '8px', border: '1px solid rgba(168,85,247,0.3)', background: 'rgba(168,85,247,0.05)', padding: '12px' }}>
                    <div style={{ fontSize: '11px', color: 'rgba(168,85,247,0.7)' }}>평균 지연</div>
                    <div style={{ fontSize: '20px', fontWeight: 700, color: '#a855f7', marginTop: '4px' }}>
                        {pathStats.avgLatency}ms
                    </div>
                </div>
                <div style={{ borderRadius: '8px', border: '1px solid rgba(239,68,68,0.3)', background: 'rgba(239,68,68,0.05)', padding: '12px' }}>
                    <div style={{ fontSize: '11px', color: 'rgba(239,68,68,0.7)' }}>p95 지연</div>
                    <div style={{ fontSize: '20px', fontWeight: 700, color: '#ef4444', marginTop: '4px' }}>
                        {pathStats.p95Latency}ms
                    </div>
                </div>
                <div style={{ borderRadius: '8px', border: '1px solid rgba(34,197,94,0.3)', background: 'rgba(34,197,94,0.05)', padding: '12px' }}>
                    <div style={{ fontSize: '11px', color: 'rgba(34,197,94,0.7)' }}>처리량</div>
                    <div style={{ fontSize: '20px', fontWeight: 700, color: '#10b981', marginTop: '4px' }}>
                        {pathStats.throughput}
                        <span style={{ fontSize: '12px', color: 'rgba(34,197,94,0.6)' }}>/min</span>
                    </div>
                </div>
                <div style={{ borderRadius: '8px', border: '1px solid rgba(59,130,246,0.3)', background: 'rgba(59,130,246,0.05)', padding: '12px' }}>
                    <div style={{ fontSize: '11px', color: 'rgba(59,130,246,0.7)' }}>에러율</div>
                    <div style={{ fontSize: '20px', fontWeight: 700, color: '#3b82f6', marginTop: '4px' }}>
                        {pathStats.errorRate}%
                    </div>
                </div>
            </div>

            {/* 스테이지별 분석 */}
            <div style={{ borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.02)', padding: '16px' }}>
                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)', marginBottom: '12px', fontWeight: 500 }}>
                    단계별 응답 시간 분해
                </div>
                {stages.map((stage, idx) => (
                    <div key={idx} style={{ marginBottom: '12px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                            <div>
                                <span style={{ fontSize: '12px', fontWeight: 500, color: 'rgba(255,255,255,0.8)' }}>
                                    {stage.name}
                                </span>
                                <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', marginLeft: '8px' }}>
                                    {stage.latency}ms
                                </span>
                            </div>
                            <span style={{ fontSize: '11px', color: stage.statusColor, fontWeight: 600 }}>
                                {stage.status}
                            </span>
                        </div>
                        <div style={{ height: '8px', background: 'rgba(0,0,0,0.3)', borderRadius: '4px', overflow: 'hidden' }}>
                            <div
                                style={{
                                    height: '100%',
                                    width: `${stage.percentage}%`,
                                    background: stage.statusColor,
                                    opacity: 0.8,
                                }}
                            />
                        </div>
                    </div>
                ))}
            </div>

            {/* 캐시 통계 */}
            <div
                style={{
                    borderRadius: '8px',
                    border: '1px solid rgba(255,255,255,0.1)',
                    background: 'rgba(255,255,255,0.02)',
                    padding: '16px',
                    marginTop: '16px',
                }}
            >
                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)', marginBottom: '12px', fontWeight: 500 }}>
                    LLM 캐시 성능
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
                    <div>
                        <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)', marginBottom: '4px' }}>
                            총 로드
                        </div>
                        <div style={{ fontSize: '18px', fontWeight: 700, color: 'rgba(255,255,255,0.9)' }}>
                            {pathStats.modelLoads.toLocaleString()}
                        </div>
                    </div>
                    <div>
                        <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)', marginBottom: '4px' }}>
                            캐시 히트
                        </div>
                        <div style={{ fontSize: '18px', fontWeight: 700, color: '#10b981' }}>
                            {pathStats.cacheHits.toLocaleString()}
                        </div>
                        <div style={{ fontSize: '10px', color: 'rgba(16,185,129,0.6)', marginTop: '2px' }}>
                            {((pathStats.cacheHits / pathStats.modelLoads) * 100).toFixed(1)}%
                        </div>
                    </div>
                    <div>
                        <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)', marginBottom: '4px' }}>
                            캐시 미스
                        </div>
                        <div style={{ fontSize: '18px', fontWeight: 700, color: '#ef4444' }}>
                            {pathStats.cacheMisses.toLocaleString()}
                        </div>
                        <div style={{ fontSize: '10px', color: 'rgba(239,68,68,0.6)', marginTop: '2px' }}>
                            {((pathStats.cacheMisses / pathStats.modelLoads) * 100).toFixed(1)}%
                        </div>
                    </div>
                </div>
            </div>

            <div style={{ borderRadius: '8px', border: '1px solid rgba(251,146,60,0.3)', background: 'rgba(251,146,60,0.05)', padding: '12px', marginTop: '16px' }}>
                <p style={{ fontSize: '12px', color: 'rgba(251,146,60,0.8)', margin: '0' }}>
                    ⚠️ timeout {settings?.route_timeout_ms ?? 45000}ms · fast path 우선 {settings?.prefer_fast_path ? 'ON' : 'OFF'} · 최대 재시도 {settings?.max_retry_count ?? 2}
                </p>
            </div>
        </div>
    );
}

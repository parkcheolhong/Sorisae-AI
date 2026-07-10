'use client';

import React from 'react';
import type { AdminRailLatencySettings } from '@/lib/admin-rail-settings-service';

interface AdminP50P95ChartSectionProps {
    settings?: AdminRailLatencySettings;
}

export default function AdminP50P95ChartSection({ settings }: AdminP50P95ChartSectionProps) {
    // 시뮬레이션 데이터: 시간별 응답 시간 분포
    const [chartData] = React.useState([
        { time: '00:00', p50: 120, p95: 280 },
        { time: '04:00', p50: 110, p95: 250 },
        { time: '08:00', p50: 150, p95: 350 },
        { time: '12:00', p50: 180, p95: 420 },
        { time: '16:00', p50: 160, p95: 390 },
        { time: '20:00', p50: 140, p95: 320 },
        { time: '현재', p50: 145, p95: 340 },
    ]);

    const maxValue = Math.max(...chartData.flatMap(d => [d.p50, d.p95]));
    const chartHeight = 200;
    const p50Budget = settings?.p50_budget_ms ?? 180;
    const p95Budget = settings?.p95_budget_ms ?? 700;
    const latestPoint = chartData[chartData.length - 1];
    const p50WithinBudget = latestPoint.p50 <= p50Budget;
    const p95WithinBudget = latestPoint.p95 <= p95Budget;

    return (
        <div className="workspace-section-stack" style={{ padding: '16px' }}>
            <div style={{ marginBottom: '20px' }}>
                <h4 style={{ color: 'rgba(255,255,255,0.9)', marginBottom: '8px', fontSize: '14px', fontWeight: 600 }}>
                    응답 시간 백분위수 분석
                </h4>
                <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: '13px', lineHeight: '1.5' }}>
                    p50(중앙값)은 일반적인 사용자 경험, p95는 느린 요청의 상한을 나타냅니다.
                </p>
            </div>

            {/* 메트릭 카드 */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px', marginBottom: '20px' }}>
                <div style={{ borderRadius: '8px', border: '1px solid rgba(106,200,242,0.3)', background: 'rgba(106,200,242,0.05)', padding: '12px' }}>
                    <div style={{ fontSize: '12px', color: 'rgba(106,200,242,0.7)', marginBottom: '4px' }}>중앙값 (p50)</div>
                    <div style={{ fontSize: '24px', fontWeight: 700, color: p50WithinBudget ? '#6ac8f2' : '#ef4444' }}>{latestPoint.p50}</div>
                    <div style={{ fontSize: '11px', color: 'rgba(106,200,242,0.5)', marginTop: '4px' }}>ms</div>
                </div>
                <div style={{ borderRadius: '8px', border: '1px solid rgba(34,197,94,0.3)', background: 'rgba(34,197,94,0.05)', padding: '12px' }}>
                    <div style={{ fontSize: '12px', color: 'rgba(34,197,94,0.7)', marginBottom: '4px' }}>최악의 5% (p95)</div>
                    <div style={{ fontSize: '24px', fontWeight: 700, color: p95WithinBudget ? '#22c55e' : '#ef4444' }}>{latestPoint.p95}</div>
                    <div style={{ fontSize: '11px', color: 'rgba(34,197,94,0.5)', marginTop: '4px' }}>ms</div>
                </div>
                <div style={{ borderRadius: '8px', border: '1px solid rgba(168,85,247,0.3)', background: 'rgba(168,85,247,0.05)', padding: '12px' }}>
                    <div style={{ fontSize: '12px', color: 'rgba(168,85,247,0.7)', marginBottom: '4px' }}>p95 / p50 비율</div>
                    <div style={{ fontSize: '24px', fontWeight: 700, color: '#a855f7' }}>2.34x</div>
                    <div style={{ fontSize: '11px', color: 'rgba(168,85,247,0.5)', marginTop: '4px' }}>(스파이크 정도)</div>
                </div>
            </div>

            {/* 간단한 바 차트 */}
            <div style={{ borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.02)', padding: '16px' }}>
                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)', marginBottom: '12px', fontWeight: 500 }}>
                    시간별 응답 시간 추이
                </div>
                <div style={{ height: `${chartHeight}px`, position: 'relative', marginBottom: '12px' }}>
                    <svg width="100%" height="100%" style={{ overflow: 'visible' }}>
                        {/* Y축 그리드 */}
                        {[0, 0.25, 0.5, 0.75, 1].map((ratio, idx) => (
                            <line
                                key={`grid-${idx}`}
                                x1="30"
                                y1={chartHeight * (1 - ratio)}
                                x2="100%"
                                y2={chartHeight * (1 - ratio)}
                                stroke="rgba(255,255,255,0.05)"
                                strokeWidth="1"
                            />
                        ))}

                        {/* 바 차트 */}
                        {chartData.map((d, idx) => {
                            const barWidth = (100 - 32) / chartData.length;
                            const p50Height = (d.p50 / maxValue) * (chartHeight * 0.9);
                            const p95Height = (d.p95 / maxValue) * (chartHeight * 0.9);
                            const x = 30 + (idx * barWidth) + barWidth * 0.1;

                            return (
                                <g key={`bar-${idx}`}>
                                    {/* p95 바 */}
                                    <rect
                                        x={x}
                                        y={chartHeight - p95Height}
                                        width={barWidth * 0.35}
                                        height={p95Height}
                                        fill="#22c55e"
                                        opacity="0.6"
                                    />
                                    {/* p50 바 */}
                                    <rect
                                        x={x + barWidth * 0.4}
                                        y={chartHeight - p50Height}
                                        width={barWidth * 0.35}
                                        height={p50Height}
                                        fill="#6ac8f2"
                                        opacity="0.8"
                                    />
                                    {/* 시간 레이블 */}
                                    <text
                                        x={x + barWidth * 0.35}
                                        y={chartHeight + 16}
                                        textAnchor="middle"
                                        fontSize="11"
                                        fill="rgba(255,255,255,0.4)"
                                    >
                                        {d.time}
                                    </text>
                                </g>
                            );
                        })}
                    </svg>
                </div>

                <div style={{ display: 'flex', gap: '16px', fontSize: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <div style={{ width: '12px', height: '12px', background: '#6ac8f2', borderRadius: '2px' }} />
                        <span style={{ color: 'rgba(255,255,255,0.6)' }}>p50 (중앙값)</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <div style={{ width: '12px', height: '12px', background: '#22c55e', borderRadius: '2px' }} />
                        <span style={{ color: 'rgba(255,255,255,0.6)' }}>p95 (상위 5%)</span>
                    </div>
                </div>
            </div>

            <div style={{ borderRadius: '8px', border: '1px solid rgba(59,130,246,0.3)', background: 'rgba(59,130,246,0.05)', padding: '12px', marginTop: '16px' }}>
                <p style={{ fontSize: '12px', color: 'rgba(59,130,246,0.8)', margin: '0' }}>
                    💡 현재 임계치: p50 {p50Budget}ms / p95 {p95Budget}ms · 샘플 윈도우 {settings?.sampling_window_minutes ?? 15}분
                </p>
            </div>
        </div>
    );
}

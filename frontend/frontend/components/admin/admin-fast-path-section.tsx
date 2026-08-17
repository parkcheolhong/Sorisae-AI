'use client';

import React from 'react';
import type { AdminRailCoverSettings } from '@/lib/admin-rail-settings-service';

interface AdminFastPathSectionProps {
    settings?: AdminRailCoverSettings;
}

export default function AdminFastPathSection({ settings }: AdminFastPathSectionProps) {
    const [fastPathStats] = React.useState({
        coveragePercent: 68.5,
        totalRequests: 12840,
        fastPathHits: 8795,
        slowPathHits: 4045,
        avgFastLatency: 45,
        avgSlowLatency: 240,
        savings: 286.5, // in seconds
    });

    const categories = [
        {
            name: '사용자 프로필 조회',
            coverage: 92,
            latencySave: '195ms',
            status: '✓ 우수',
        },
        {
            name: '프로젝트 목록',
            coverage: 85,
            latencySave: '150ms',
            status: '✓ 우수',
        },
        {
            name: '캐시된 분석',
            coverage: 72,
            latencySave: '280ms',
            status: '◐ 개선 중',
        },
        {
            name: '실시간 메트릭',
            coverage: 45,
            latencySave: '120ms',
            status: '△ 낮음',
        },
        {
            name: '추천 엔진',
            coverage: 28,
            latencySave: '300ms',
            status: '△ 낮음',
        },
    ];

    return (
        <div className="workspace-section-stack" style={{ padding: '16px' }}>
            <div style={{ marginBottom: '20px' }}>
                <h4 style={{ color: 'rgba(255,255,255,0.9)', marginBottom: '8px', fontSize: '14px', fontWeight: 600 }}>
                    Fast Path 커버리지 분석
                </h4>
                <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: '13px', lineHeight: '1.5' }}>
                    캐시 활용을 통한 직접 경로(fast path) 커버리지를 모니터링하고 확대 기회를 찾습니다.
                </p>
            </div>

            {/* 메인 메트릭 */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '20px' }}>
                {/* 커버리지 원형 게이지 */}
                <div style={{ borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.02)', padding: '16px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)', marginBottom: '12px' }}>
                        전체 커버리지
                    </div>
                    <svg width="120" height="120" style={{ marginBottom: '12px' }}>
                        {/* 배경 원 */}
                        <circle cx="60" cy="60" r="50" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="8" />
                        {/* 커버리지 원 */}
                        <circle
                            cx="60"
                            cy="60"
                            r="50"
                            fill="none"
                            stroke="#10b981"
                            strokeWidth="8"
                            strokeDasharray={`${(fastPathStats.coveragePercent / 100) * Math.PI * 100} ${Math.PI * 100}`}
                            strokeDashoffset="0"
                            transform="rotate(-90 60 60)"
                            style={{ transition: 'stroke-dasharray 0.5s' }}
                        />
                        {/* 중앙 텍스트 */}
                        <text x="60" y="60" textAnchor="middle" dy="0.3em" fontSize="24" fontWeight="700" fill="#10b981">
                            {fastPathStats.coveragePercent.toFixed(1)}%
                        </text>
                    </svg>
                    <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)' }}>
                        목표: {settings?.target_fastpath_percent ?? 85}%
                    </div>
                </div>

                {/* 통계 카드들 */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    <div style={{ borderRadius: '8px', border: '1px solid rgba(34,197,94,0.3)', background: 'rgba(34,197,94,0.05)', padding: '12px' }}>
                        <div style={{ fontSize: '11px', color: 'rgba(34,197,94,0.7)', marginBottom: '4px' }}>
                            Fast Path 요청
                        </div>
                        <div style={{ fontSize: '18px', fontWeight: 700, color: '#10b981' }}>
                            {fastPathStats.fastPathHits.toLocaleString()}
                        </div>
                        <div style={{ fontSize: '10px', color: 'rgba(34,197,94,0.6)' }}>
                            평균 {fastPathStats.avgFastLatency}ms
                        </div>
                    </div>
                    <div style={{ borderRadius: '8px', border: '1px solid rgba(239,68,68,0.3)', background: 'rgba(239,68,68,0.05)', padding: '12px' }}>
                        <div style={{ fontSize: '11px', color: 'rgba(239,68,68,0.7)', marginBottom: '4px' }}>
                            Slow Path 요청
                        </div>
                        <div style={{ fontSize: '18px', fontWeight: 700, color: '#ef4444' }}>
                            {fastPathStats.slowPathHits.toLocaleString()}
                        </div>
                        <div style={{ fontSize: '10px', color: 'rgba(239,68,68,0.6)' }}>
                            평균 {fastPathStats.avgSlowLatency}ms
                        </div>
                    </div>
                    <div style={{ borderRadius: '8px', border: '1px solid rgba(59,130,246,0.3)', background: 'rgba(59,130,246,0.05)', padding: '12px' }}>
                        <div style={{ fontSize: '11px', color: 'rgba(59,130,246,0.7)', marginBottom: '4px' }}>
                            누적 시간 절감
                        </div>
                        <div style={{ fontSize: '18px', fontWeight: 700, color: '#3b82f6' }}>
                            {fastPathStats.savings.toLocaleString()}초
                        </div>
                    </div>
                </div>
            </div>

            {/* 카테고리별 커버리지 */}
            <div style={{ borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.02)', padding: '16px' }}>
                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)', marginBottom: '12px', fontWeight: 500 }}>
                    카테고리별 Fast Path 커버리지
                </div>
                {categories.map((cat, idx) => (
                    <div key={idx} style={{ marginBottom: '12px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                            <span style={{ fontSize: '12px', fontWeight: 500, color: 'rgba(255,255,255,0.8)' }}>
                                {cat.name}
                            </span>
                            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)' }}>
                                    {cat.latencySave}
                                </span>
                                <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.4)' }}>
                                    {cat.coverage}%
                                </span>
                            </div>
                        </div>
                        <div style={{ height: '6px', background: 'rgba(0,0,0,0.3)', borderRadius: '3px', overflow: 'hidden' }}>
                            <div
                                style={{
                                    height: '100%',
                                    width: `${cat.coverage}%`,
                                    background: cat.coverage >= 80 ? '#10b981' : cat.coverage >= 50 ? '#f59e0b' : '#ef4444',
                                    opacity: 0.8,
                                }}
                            />
                        </div>
                    </div>
                ))}
            </div>

            <div style={{ borderRadius: '8px', border: '1px solid rgba(168,85,247,0.3)', background: 'rgba(168,85,247,0.05)', padding: '12px', marginTop: '16px' }}>
                <p style={{ fontSize: '12px', color: 'rgba(168,85,247,0.8)', margin: '0' }}>
                    💡 샘플 수 {settings?.sample_size ?? 25} · 실패 자동 오픈 {settings?.auto_open_failures ? 'ON' : 'OFF'} · 목표 {settings?.target_fastpath_percent ?? 85}%
                </p>
            </div>
        </div>
    );
}

'use client';

import React from 'react';
import type { AdminRailPerformanceSettings } from '@/lib/admin-rail-settings-service';

interface AdminPerformanceSectionProps {
    settings?: AdminRailPerformanceSettings;
}

export default function AdminPerformanceSection({ settings }: AdminPerformanceSectionProps) {
    const [recommendations] = React.useState([
        {
            id: 1,
            title: '캐시 히트율 개선',
            current: '62%',
            target: `${Math.max(70, Math.min(95, Math.round(((settings?.cache_ttl_seconds ?? 300) / 10) + 45)))}%`,
            impact: '요청 응답 시간 35% 단축',
            priority: 'high',
            action: 'Redis 캐시 TTL 조정 및 워밍',
        },
        {
            id: 2,
            title: 'DB 쿼리 최적화',
            current: '142 queries/s',
            target: `${Math.max(20, Math.round(1000 / Math.max(10, settings?.db_query_budget_ms ?? 250) * 25))} queries/s`,
            impact: '데이터베이스 CPU 40% 감소',
            priority: 'high',
            action: 'N+1 쿼리 제거 및 배치 처리',
        },
        {
            id: 3,
            title: '이미지 최적화',
            current: '평균 2.1MB',
            target: '평균 0.8MB',
            impact: '네트워크 대역폭 62% 절감',
            priority: 'medium',
            action: 'WebP 변환 및 최적 압축',
        },
        {
            id: 4,
            title: '번들 크기 축소',
            current: '456KB',
            target: '280KB',
            impact: '초기 로딩 시간 45% 단축',
            priority: 'medium',
            action: '코드 스플리팅 및 트리 쉐이킹',
        },
        {
            id: 5,
            title: '메모리 누수 제거',
            current: '평균 450MB',
            target: '평균 320MB',
            impact: 'OOM 위험도 70% 감소',
            priority: 'low',
            action: '이벤트 리스너 정리 및 프로파일링',
        },
    ]);

    const priorityColor = (p: string) => {
        switch (p) {
            case 'high':
                return '#ef4444';
            case 'medium':
                return '#f59e0b';
            default:
                return '#3b82f6';
        }
    };

    const priorityLabel = (p: string) => {
        switch (p) {
            case 'high':
                return '긴급';
            case 'medium':
                return '중요';
            default:
                return '참고';
        }
    };

    return (
        <div className="workspace-section-stack" style={{ padding: '16px' }}>
            <div style={{ marginBottom: '20px' }}>
                <h4 style={{ color: 'rgba(255,255,255,0.9)', marginBottom: '8px', fontSize: '14px', fontWeight: 600 }}>
                    성능 최적화 권장사항
                </h4>
                <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: '13px', lineHeight: '1.5' }}>
                    시스템 분석을 통해 발견된 성능 개선 기회를 우선순위별로 제시합니다.
                </p>
            </div>

            <div style={{ display: 'space-y-3' }}>
                {recommendations.map((rec, idx) => (
                    <div
                        key={rec.id}
                        style={{
                            borderRadius: '8px',
                            border: '1px solid rgba(255,255,255,0.1)',
                            background: 'rgba(255,255,255,0.02)',
                            padding: '16px',
                            marginBottom: '12px',
                        }}
                    >
                        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', marginBottom: '12px' }}>
                            <div
                                style={{
                                    width: '32px',
                                    height: '32px',
                                    borderRadius: '6px',
                                    background: `${priorityColor(rec.priority)}20`,
                                    border: `1px solid ${priorityColor(rec.priority)}40`,
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    fontSize: '16px',
                                    flexShrink: 0,
                                }}
                            >
                                {idx + 1}
                            </div>
                            <div style={{ flex: 1 }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                                    <h5 style={{ margin: '0', fontSize: '14px', fontWeight: 600, color: 'rgba(255,255,255,0.9)' }}>
                                        {rec.title}
                                    </h5>
                                    <span
                                        style={{
                                            fontSize: '11px',
                                            fontWeight: 600,
                                            color: priorityColor(rec.priority),
                                            background: `${priorityColor(rec.priority)}20`,
                                            border: `1px solid ${priorityColor(rec.priority)}40`,
                                            padding: '2px 8px',
                                            borderRadius: '4px',
                                        }}
                                    >
                                        {priorityLabel(rec.priority)}
                                    </span>
                                </div>
                                <p style={{ margin: '0', fontSize: '12px', color: 'rgba(255,255,255,0.6)' }}>
                                    현재: <strong style={{ color: 'rgba(255,255,255,0.8)' }}>{rec.current}</strong> →
                                    목표: <strong style={{ color: '#10b981' }}>{rec.target}</strong>
                                </p>
                            </div>
                        </div>

                        <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '6px', padding: '12px', marginBottom: '12px' }}>
                            <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)', marginBottom: '4px' }}>기대 효과</div>
                            <div style={{ fontSize: '12px', color: '#10b981', fontWeight: 500 }}>
                                ✓ {rec.impact}
                            </div>
                        </div>

                        <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)' }}>
                            <strong style={{ color: 'rgba(255,255,255,0.8)' }}>조치 방안:</strong> {rec.action}
                        </div>
                    </div>
                ))}
            </div>

            <div style={{ borderRadius: '8px', border: '1px solid rgba(34,197,94,0.3)', background: 'rgba(34,197,94,0.05)', padding: '12px', marginTop: '16px' }}>
                <p style={{ fontSize: '12px', color: 'rgba(34,197,94,0.8)', margin: '0' }}>
                    ✓ 현재 목표: 응답 예산 {settings?.response_budget_ms ?? 600}ms · DB 예산 {settings?.db_query_budget_ms ?? 250}ms · 캐시 TTL {settings?.cache_ttl_seconds ?? 300}초
                </p>
            </div>
        </div>
    );
}

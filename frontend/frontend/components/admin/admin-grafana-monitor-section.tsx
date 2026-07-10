'use client';

import React from 'react';
import type { AdminRailMonitoringSettings } from '@/lib/admin-rail-settings-service';

interface AdminGrafanaMonitorSectionProps {
    apiBaseUrl?: string;
    settings?: AdminRailMonitoringSettings;
}

export default function AdminGrafanaMonitorSection({
    apiBaseUrl = 'http://127.0.0.1:3000',
    settings,
}: AdminGrafanaMonitorSectionProps) {
    const grafanaUrl = settings?.grafana_base_url || apiBaseUrl;
    const refreshSeconds = settings?.auto_refresh_seconds ?? 20;
    return (
        <div className="workspace-section-stack" style={{ padding: '16px' }}>
            <div style={{ marginBottom: '20px' }}>
                <h4 style={{ color: 'rgba(255,255,255,0.9)', marginBottom: '8px', fontSize: '14px', fontWeight: 600 }}>
                    실시간 시스템 메트릭 대시보드
                </h4>
                <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: '13px', lineHeight: '1.5' }}>
                    Prometheus 데이터 기반 Grafana 대시보드입니다. 시스템 리소스, API 성능, 비즈니스 메트릭을 실시간으로 모니터링합니다.
                </p>
            </div>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px', marginBottom: '20px' }}>
                {[
                    { label: 'HTTP 요청/분', value: '5.2K', unit: 'req/m', color: '#0ea5e9' },
                    { label: '평균 응답 시간', value: '145', unit: 'ms', color: '#06b6d4' },
                    { label: '활성 연결', value: '342', unit: 'conns', color: '#10b981' },
                ].map((metric, idx) => (
                    <div
                        key={idx}
                        style={{
                            borderRadius: '8px',
                            border: '1px solid rgba(255,255,255,0.1)',
                            background: 'rgba(255,255,255,0.02)',
                            padding: '16px',
                            textAlign: 'center',
                        }}
                    >
                        <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '8px' }}>
                            {metric.label}
                        </div>
                        <div style={{ fontSize: '24px', fontWeight: 700, color: metric.color, marginBottom: '4px' }}>
                            {metric.value}
                        </div>
                        <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)' }}>
                            {metric.unit}
                        </div>
                    </div>
                ))}
            </div>

            <div style={{ borderRadius: '8px', border: '1px solid rgba(0,165,240,0.3)', background: 'rgba(0,165,240,0.05)', padding: '12px' }}>
                <p style={{ fontSize: '12px', color: 'rgba(0,165,240,0.8)', margin: '0' }}>
                    💡 Grafana URL: {grafanaUrl} · 자동 새로고침 기준 {refreshSeconds}초 · 채널 {settings?.alert_channel || 'admin'}
                </p>
            </div>
        </div>
    );
}

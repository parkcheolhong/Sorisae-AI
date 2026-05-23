'use client';

import * as React from 'react';
import WorkspaceChrome from '@/components/ui/workspace-chrome';
import SorisaeExpPanel, { type SorisaeEngineSpec } from '@/components/marketplace/sorisae-exp-panel';
import { buildMarketplaceWorkspaceRailItems } from '@/components/marketplace/marketplace-rails';

const SECURITY_ENGINES: SorisaeEngineSpec[] = [
    {
        engine_type: 'detective',
        label: '사이버 탐정 AI',
        description: '디지털 증거·로그·패턴을 분석해 사이버 범죄 수사를 지원합니다. 용의자 프로파일링과 증거 연결망을 자동 생성합니다.',
        default_entry_fn: 'main',
        default_context: { case_type: '피싱 사기', evidence: ['이상 IP 접속 로그', '의심 이메일 헤더'], priority: 'high' },
        adapter_entry_candidates: ['demo_cyber_detective', 'run', 'start'],
        badge: '실험적',
    },
    {
        engine_type: 'biometric',
        label: '생체인증 보안 시스템',
        description: '얼굴·홍채·지문·음성 등 다중 생체 정보를 AI가 통합 인증합니다. 위조 탐지 및 리플레이 공격 방어 기능 포함.',
        default_entry_fn: 'main',
        default_context: { auth_method: 'face+voice', security_level: 'high', anti_spoof: true },
        badge: '실험적',
    },
    {
        engine_type: 'gps_investigation',
        label: 'GPS 반경 수사 엔진',
        description: '특정 위치·시간대를 중심으로 반경 내 이동 패턴을 분석하고 수상 경로·접촉 지점을 시각화합니다.',
        default_entry_fn: 'main',
        default_context: { center_lat: 37.5665, center_lng: 126.9780, radius_km: 2, time_range_hours: 6 },
        badge: '실험적',
    },
];

export default function SecurityExpPage() {
    const railItems = buildMarketplaceWorkspaceRailItems('exp-security');

    return (
        <WorkspaceChrome
            brand="Marketplace Workspace"
            title="E: 보안·탐정 실험 기능"
            description="소리새 엔진 중 사이버탐정·생체인증·GPS수사 계열 3개를 실험적으로 실행해볼 수 있습니다."
            statusLabel="실험 기능 — 운영 비보장"
            pageTestId="exp-security-page"
            compactHeader
            hideHero
            railItems={railItems.railItems}
            rightRailItems={railItems.rightRailItems}
        >
            <SorisaeExpPanel
                engines={SECURITY_ENGINES}
                categoryLabel="E: 보안·탐정"
                categoryId="security"
            />
        </WorkspaceChrome>
    );
}

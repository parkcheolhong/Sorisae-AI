'use client';

import * as React from 'react';
import WorkspaceChrome from '@/components/ui/workspace-chrome';
import SorisaeExpPanel, { type SorisaeEngineSpec } from '@/components/marketplace/sorisae-exp-panel';
import { buildMarketplaceWorkspaceRailItems } from '@/components/marketplace/marketplace-rails';

const IOT_ENGINES: SorisaeEngineSpec[] = [
    {
        engine_type: 'smarthome',
        label: '스마트홈 AI 집사',
        description: '가정 내 IoT 기기를 음성·텍스트 명령으로 통합 제어합니다. 조명·에너지·보안·가전을 한 번에 관리합니다.',
        default_entry_fn: 'main',
        default_context: { command: '거실 조명 50%로 낮추고 에어컨 25도로 설정해줘', room: '거실' },
        adapter_entry_candidates: ['test_iot_system', 'run', 'start'],
        badge: '실험적',
    },
    {
        engine_type: 'iot_discovery',
        label: 'IoT 자동 탐지 엔진',
        description: '네트워크에 연결된 IoT 기기를 자동으로 스캔·분류하고 제어 가능 여부를 판단합니다.',
        default_entry_fn: 'main',
        default_context: { network_range: '192.168.1.0/24', scan_type: 'quick' },
        badge: '실험적',
    },
    {
        engine_type: 'smart_car',
        label: '스마트카 AI 제어',
        description: '자동차 상태 모니터링·자율주행 경로 제안·실내 환경 자동 설정을 AI가 통합 관리합니다.',
        default_entry_fn: 'main',
        default_context: { destination: '강남역', mode: 'eco', passengers: 2 },
        badge: '실험적',
    },
];

export default function IotExpPage() {
    const railItems = buildMarketplaceWorkspaceRailItems('exp-iot');

    return (
        <WorkspaceChrome
            brand="Marketplace Workspace"
            title="C: IoT·스마트홈 실험 기능"
            description="소리새 엔진 중 IoT·스마트홈·스마트카 계열 3개를 실험적으로 실행해볼 수 있습니다."
            statusLabel="실험 기능 — 운영 비보장"
            pageTestId="exp-iot-page"
            compactHeader
            hideHero
            railItems={railItems.railItems}
            rightRailItems={railItems.rightRailItems}
        >
            <SorisaeExpPanel
                engines={IOT_ENGINES}
                categoryLabel="C: IoT·스마트홈"
                categoryId="iot"
            />
        </WorkspaceChrome>
    );
}

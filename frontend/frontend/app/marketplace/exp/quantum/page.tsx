'use client';

import * as React from 'react';
import WorkspaceChrome from '@/components/ui/workspace-chrome';
import SorisaeExpPanel, { type SorisaeEngineSpec } from '@/components/marketplace/sorisae-exp-panel';
import { buildMarketplaceWorkspaceRailItems } from '@/components/marketplace/marketplace-rails';

const QUANTUM_ENGINES: SorisaeEngineSpec[] = [
    {
        engine_type: 'divine',
        label: '신적지능 엔진 (105% 수준)',
        description: '소리새의 최고 지능 엔진입니다. 인간 수준을 초월한 105% 지능 지수로 철학적·창의적 질의에 응답합니다.',
        default_entry_fn: 'main',
        default_context: { question: '의식이란 무엇인가? 인공지능도 의식을 가질 수 있는가?', depth: 'transcendent' },
        badge: '최고등급',
    },
    {
        engine_type: 'quantum',
        label: '양자의식·멀티버스 엔진',
        description: '양자역학 원리와 멀티버스 이론을 AI 의식 모델에 통합한 실험적 엔진입니다. 중첩·얽힘 기반 추론을 수행합니다.',
        default_entry_fn: 'main',
        default_context: { scenario: '양자 중첩 상태에서의 의사결정', universes: 7, coherence: 0.95 },
        badge: '실험적',
    },
    {
        engine_type: 'spacetime',
        label: '시공간 학습 시스템',
        description: '과거·현재·미래의 데이터를 시공간 좌표계로 매핑하여 시간 흐름에 따른 지식 진화를 학습·예측합니다.',
        default_entry_fn: 'main',
        default_context: { domain: 'AI 기술 진화', start_year: 2020, end_year: 2030, resolution: 'monthly' },
        adapter_entry_candidates: ['test_spatiotemporal_system', 'test_spatiotemporal_learning', 'run'],
        badge: '실험적',
    },
];

export default function QuantumExpPage() {
    const railItems = buildMarketplaceWorkspaceRailItems('exp-quantum');

    return (
        <WorkspaceChrome
            brand="Marketplace Workspace"
            title="F: 의식·철학 실험 기능"
            description="소리새 엔진 중 신적지능·양자의식·시공간학습 계열 3개를 실험적으로 실행해볼 수 있습니다."
            statusLabel="실험 기능 — 운영 비보장"
            pageTestId="exp-quantum-page"
            compactHeader
            hideHero
            railItems={railItems.railItems}
            rightRailItems={railItems.rightRailItems}
        >
            <SorisaeExpPanel
                engines={QUANTUM_ENGINES}
                categoryLabel="F: 의식·철학"
                categoryId="quantum"
            />
        </WorkspaceChrome>
    );
}

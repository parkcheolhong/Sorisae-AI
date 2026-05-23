'use client';

import * as React from 'react';
import WorkspaceChrome from '@/components/ui/workspace-chrome';
import SorisaeExpPanel, { type SorisaeEngineSpec } from '@/components/marketplace/sorisae-exp-panel';
import { buildMarketplaceWorkspaceRailItems } from '@/components/marketplace/marketplace-rails';

const PREDICT_ENGINES: SorisaeEngineSpec[] = [
    {
        engine_type: 'future_prediction',
        label: '미래 예측 엔진 (92% 정확도)',
        description: '입력한 주제·질문에 대해 소리새 AI가 데이터 패턴과 트렌드를 기반으로 미래 시나리오를 예측합니다.',
        default_entry_fn: 'main',
        default_context: { topic: 'AI 산업 2027년 전망', depth: 'detailed' },
        badge: '실험적',
    },
    {
        engine_type: 'dream',
        label: '꿈 해석기',
        description: '꿈에서 본 내용을 텍스트로 입력하면 심리·상징·메시지를 AI가 분석해 해석 결과를 제공합니다.',
        default_entry_fn: 'main',
        default_context: { dream_text: '하늘을 날아다니다가 갑자기 떨어지는 꿈을 꿨어요' },
        adapter_entry_candidates: ['run', 'analyze', 'start'],
        badge: '실험적',
    },
    {
        engine_type: 'emotion_therapy',
        label: '감정 색채 치료사 (98% 만족도)',
        description: '현재 감정 상태를 입력하면 감정 색채 분석 후 맞춤형 치유 방법·컬러·음악·활동을 처방합니다.',
        default_entry_fn: 'main',
        default_context: { emotion_state: '불안하고 긴장됨', intensity: 0.7, duration_days: 3 },
        adapter_entry_candidates: ['run', 'therapy', 'start'],
        badge: '실험적',
    },
];

export default function PredictExpPage() {
    const railItems = buildMarketplaceWorkspaceRailItems('exp-predict');

    return (
        <WorkspaceChrome
            brand="Marketplace Workspace"
            title="B: 예측·투자 실험 기능"
            description="소리새 엔진 중 미래예측·꿈해석·감정치료 계열 3개를 실험적으로 실행해볼 수 있습니다."
            statusLabel="실험 기능 — 운영 비보장"
            pageTestId="exp-predict-page"
            compactHeader
            hideHero
            railItems={railItems.railItems}
            rightRailItems={railItems.rightRailItems}
        >
            <SorisaeExpPanel
                engines={PREDICT_ENGINES}
                categoryLabel="B: 예측·투자"
                categoryId="predict"
            />
        </WorkspaceChrome>
    );
}

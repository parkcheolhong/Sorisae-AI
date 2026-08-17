'use client';

import * as React from 'react';
import WorkspaceChrome from '@/components/ui/workspace-chrome';
import SorisaeExpPanel, { type SorisaeEngineSpec } from '@/components/marketplace/sorisae-exp-panel';
import { buildMarketplaceWorkspaceRailItems } from '@/components/marketplace/marketplace-rails';

const GAME_ENGINES: SorisaeEngineSpec[] = [
    {
        engine_type: 'game',
        label: '실시간 게임 생성기',
        description: '장르·테마·규칙을 입력하면 플레이 가능한 게임 로직과 시나리오를 실시간으로 생성합니다.',
        default_entry_fn: 'main',
        default_context: { genre: 'RPG', theme: '우주 탐험', max_players: 4, difficulty: 'normal' },
        adapter_entry_candidates: ['create_game_response', 'run', 'start'],
        badge: '실험적',
    },
    {
        engine_type: 'vr',
        label: 'VR 무한우주 게임',
        description: '소리새 AI가 무한히 확장되는 우주 VR 게임 월드를 절차적으로 생성합니다. 씬·퀘스트·NPC가 자동 생성됩니다.',
        default_entry_fn: 'main',
        default_context: { world_seed: 42, universe_scale: 'galaxy', player_class: '탐험가' },
        adapter_entry_candidates: ['run', 'generate', 'start'],
        badge: '실험적',
    },
    {
        engine_type: 'earning_game',
        label: '수익 게임 엔진',
        description: '플레이어가 실제 보상을 획득할 수 있는 Play-to-Earn 게임 경제 구조와 토큰 메커니즘을 설계합니다.',
        default_entry_fn: 'main',
        default_context: { token_name: 'SORI', initial_supply: 1000000, reward_rate: 0.01 },
        adapter_entry_candidates: ['run', 'simulate', 'start'],
        badge: '실험적',
    },
];

export default function GameExpPage() {
    const railItems = buildMarketplaceWorkspaceRailItems('exp-game');

    return (
        <WorkspaceChrome
            brand="Marketplace Workspace"
            title="D: 게임 실험 기능"
            description="소리새 엔진 중 게임·VR·수익게임 계열 3개를 실험적으로 실행해볼 수 있습니다."
            statusLabel="실험 기능 — 운영 비보장"
            pageTestId="exp-game-page"
            compactHeader
            hideHero
            railItems={railItems.railItems}
            rightRailItems={railItems.rightRailItems}
        >
            <SorisaeExpPanel
                engines={GAME_ENGINES}
                categoryLabel="D: 게임"
                categoryId="game"
            />
        </WorkspaceChrome>
    );
}

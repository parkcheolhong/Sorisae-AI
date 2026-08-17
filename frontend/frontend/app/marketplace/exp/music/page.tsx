'use client';

import * as React from 'react';
import WorkspaceChrome from '@/components/ui/workspace-chrome';
import SorisaeExpPanel, { type SorisaeEngineSpec } from '@/components/marketplace/sorisae-exp-panel';
import { buildMarketplaceWorkspaceRailItems } from '@/components/marketplace/marketplace-rails';

const MUSIC_ENGINES: SorisaeEngineSpec[] = [
    {
        engine_type: 'emotion_music',
        label: '감정 기반 음악 생성기',
        description: '입력한 감정 상태(행복·슬픔·분노 등)를 분석해 어울리는 음악 구성과 멜로디 파라미터를 자동 생성합니다.',
        default_entry_fn: 'main',
        default_context: { emotion: '행복', intensity: 0.8 },
        badge: '실험적',
    },
    {
        engine_type: 'music_chat_friend',
        label: 'AI 음악 친구 채팅',
        description: '음악 취향과 감정을 공유하는 AI 친구 캐릭터와 대화하며 플레이리스트 및 추천 곡을 함께 만들어 나갑니다.',
        default_entry_fn: 'main',
        default_context: { message: '오늘 기분이 업되는 음악 추천해줘' },
        adapter_entry_candidates: ['get_friend_system', 'run', 'start'],
        badge: '실험적',
    },
    {
        engine_type: 'animation_theme',
        label: '애니메이션 테마곡 생성',
        description: '애니메이션 시나리오·세계관·캐릭터 정보를 바탕으로 오프닝/엔딩 테마곡 구조를 제안합니다.',
        default_entry_fn: 'main',
        default_context: { scenario: '우주 모험', mood: 'epic', characters: ['소리새', '나달'] },
        badge: '실험적',
    },
    {
        engine_type: 'animation',
        label: '애니메이션 스튜디오',
        description: '스토리보드·씬 설정·캐릭터 동작 스크립트를 AI가 자동으로 생성하는 경량 애니메이션 기획 도구입니다.',
        default_entry_fn: 'main',
        default_context: { title: '소리새의 모험', genre: 'fantasy', episodes: 3 },
        badge: '실험적',
    },
];

export default function MusicExpPage() {
    const railItems = buildMarketplaceWorkspaceRailItems('exp-music');

    return (
        <WorkspaceChrome
            brand="Marketplace Workspace"
            title="A: 음악·창작 실험 기능"
            description="소리새 엔진 중 음악·창작 계열 4개를 실험적으로 실행해볼 수 있습니다. 결과는 미리보기 전용이며 운영 출력과 다를 수 있습니다."
            statusLabel="실험 기능 — 운영 비보장"
            pageTestId="exp-music-page"
            compactHeader
            hideHero
            railItems={railItems.railItems}
            rightRailItems={railItems.rightRailItems}
        >
            <SorisaeExpPanel
                engines={MUSIC_ENGINES}
                categoryLabel="A: 음악·창작"
                categoryId="music"
            />
        </WorkspaceChrome>
    );
}

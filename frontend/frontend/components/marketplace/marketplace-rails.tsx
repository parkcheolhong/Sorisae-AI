'use client';

import * as React from 'react';
import Link from 'next/link';
import { Home, LayoutGrid, Briefcase, Star, ShieldCheck, CreditCard, FolderOpen, Music2, TrendingUp, Cpu, Gamepad2, Shield, Brain } from 'lucide-react';
import { resolveMarketplaceSiteHref } from '@/lib/canonical-site';

type MarketplaceRailConfig = {
    id: string;
    label: string;
    shortLabel: string;
    href: string;
    accent: 'blue' | 'violet' | 'emerald' | 'neutral' | 'amber';
    icon: React.ReactNode;
};

export type MarketplaceEngineRail = {
    rail_id: string;
    rail_index: number;
    slot_start: number;
    slot_end: number;
    rail_size: number;
    completed_slots?: number;
    pending_slots?: number;
};

export type MarketplaceRailId =
    | 'market-home'
    | 'code-generator'
    | 'orchestrator'
    | 'popular'
    | 'ml-detectors'
    | 'subscription'
    | 'office-tools'
    | 'exp-music'
    | 'exp-predict'
    | 'exp-iot'
    | 'exp-game'
    | 'exp-security'
    | 'exp-quantum';

const MARKETPLACE_LEFT_RAIL_ITEMS: MarketplaceRailConfig[] = [
    { id: 'market-home', label: '마켓 메인', shortLabel: '메인', href: resolveMarketplaceSiteHref('/marketplace'), accent: 'blue', icon: <Home size={18} /> },
    { id: 'code-generator', label: 'AI 엔진 코드', shortLabel: '코드', href: resolveMarketplaceSiteHref('/marketplace/code-generator'), accent: 'violet', icon: <LayoutGrid size={18} /> },
    { id: 'orchestrator', label: 'AI 엔진 오케스트레이터', shortLabel: '오케', href: resolveMarketplaceSiteHref('/marketplace/orchestrator'), accent: 'emerald', icon: <Briefcase size={18} /> },
    { id: 'subscription', label: '구독 관리', shortLabel: '구독', href: resolveMarketplaceSiteHref('/marketplace/subscription'), accent: 'emerald', icon: <CreditCard size={18} /> },
];

const MARKETPLACE_RIGHT_RAIL_ITEMS: MarketplaceRailConfig[] = [
    { id: 'office-tools', label: '사무도구 (문서·파워포인트·스프레드시트)', shortLabel: '사무', href: resolveMarketplaceSiteHref('/marketplace#office-tools-hub'), accent: 'blue', icon: <FolderOpen size={18} /> },
    { id: 'popular', label: '시스템 메트릭', shortLabel: '메트', href: resolveMarketplaceSiteHref('/marketplace/metrics'), accent: 'amber', icon: <Star size={18} /> },
    { id: 'ml-detectors', label: '외부 검증기', shortLabel: '검증', href: resolveMarketplaceSiteHref('/marketplace/ml-detectors'), accent: 'emerald', icon: <ShieldCheck size={18} /> },
    { id: 'exp-music', label: 'A: 음악·창작 실험', shortLabel: '♪창작', href: resolveMarketplaceSiteHref('/marketplace/exp/music'), accent: 'violet', icon: <Music2 size={18} /> },
    { id: 'exp-predict', label: 'B: 예측·투자 실험', shortLabel: '📈예측', href: resolveMarketplaceSiteHref('/marketplace/exp/predict'), accent: 'amber', icon: <TrendingUp size={18} /> },
    { id: 'exp-iot', label: 'C: IoT·스마트홈 실험', shortLabel: '🏠IoT', href: resolveMarketplaceSiteHref('/marketplace/exp/iot'), accent: 'emerald', icon: <Cpu size={18} /> },
    { id: 'exp-game', label: 'D: 게임 실험', shortLabel: '🎮게임', href: resolveMarketplaceSiteHref('/marketplace/exp/game'), accent: 'blue', icon: <Gamepad2 size={18} /> },
    { id: 'exp-security', label: 'E: 보안·탐정 실험', shortLabel: '🔒보안', href: resolveMarketplaceSiteHref('/marketplace/exp/security'), accent: 'neutral', icon: <Shield size={18} /> },
    { id: 'exp-quantum', label: 'F: 의식·철학 실험', shortLabel: '🧠의식', href: resolveMarketplaceSiteHref('/marketplace/exp/quantum'), accent: 'violet', icon: <Brain size={18} /> },
];

function buildFallbackEngineRails(): MarketplaceEngineRail[] {
    return Array.from({ length: 6 }).map((_, index) => {
        const slotStart = index * 20 + 1;
        const slotEnd = slotStart + 19;
        return {
            rail_id: `RAIL-${String(index + 1).padStart(2, '0')}`,
            rail_index: index + 1,
            slot_start: slotStart,
            slot_end: slotEnd,
            rail_size: 20,
            completed_slots: 0,
            pending_slots: 20,
        };
    });
}

function buildEngineRailItems(engineRails: MarketplaceEngineRail[]): MarketplaceRailConfig[] {
    const accents: Array<MarketplaceRailConfig['accent']> = ['blue', 'violet', 'emerald', 'amber', 'neutral', 'blue'];
    return engineRails.map((rail, index) => ({
        id: rail.rail_id,
        label: `120엔진 레일 ${rail.rail_index} (${rail.slot_start}-${rail.slot_end})`,
        shortLabel: `R${rail.rail_index}`,
        href: resolveMarketplaceSiteHref(`/marketplace/orchestrator?rail=${encodeURIComponent(rail.rail_id)}`),
        accent: accents[index % accents.length],
        icon: <Briefcase size={18} />,
    }));
}

function renderRailItems(
    items: MarketplaceRailConfig[],
    activeRailId: string,
    onRailSelect?: (railId: string) => void,
) {
    return items.map((item) => {
        const isActive = item.id === activeRailId;
        const selectableRail = Boolean(onRailSelect) && item.id.startsWith('RAIL-');
        if (selectableRail) {
            return (
                <button
                    key={item.id}
                    type="button"
                    onClick={() => onRailSelect?.(item.id)}
                    className={isActive ? 'workspace-rail-item workspace-rail-item-active' : 'workspace-rail-item'}
                    aria-current={isActive ? 'page' : undefined}
                    aria-label={item.label}
                >
                    <span className={`workspace-rail-item-dot workspace-rail-item-accent-${item.accent}`} />
                    <span className="workspace-rail-item-text">{item.shortLabel}</span>
                </button>
            );
        }
        return (
            <Link
                key={item.id}
                href={item.href}
                className={isActive ? 'workspace-rail-item workspace-rail-item-active' : 'workspace-rail-item'}
                aria-current={isActive ? 'page' : undefined}
            >
                <span className={`workspace-rail-item-dot workspace-rail-item-accent-${item.accent}`} />
                <span className="workspace-rail-item-text">{item.shortLabel}</span>
            </Link>
        );
    });
}

function buildWorkspaceChromeItems(items: MarketplaceRailConfig[], activeRailId: string) {
    return items.map((item) => ({
        id: item.id,
        label: item.label,
        shortLabel: item.shortLabel,
        href: item.href,
        active: item.id === activeRailId,
        accent: item.accent,
        icon: item.icon,
    }));
}

export function MarketplaceLeftRail({ activeRailId }: { activeRailId: MarketplaceRailId }) {
    return (
        <nav className="workspace-rail" aria-label="Marketplace primary rail">
            <div className="workspace-rail-brand">CA</div>
            <div className="workspace-rail-nav">{renderRailItems(MARKETPLACE_LEFT_RAIL_ITEMS, activeRailId)}</div>
        </nav>
    );
}

export function MarketplaceRightRail({
    activeRailId,
    engineRails,
    onRailSelect,
}: {
    activeRailId: string;
    engineRails?: MarketplaceEngineRail[];
    onRailSelect?: (railId: string) => void;
}) {
    const rightItems = React.useMemo(() => {
        if (!engineRails) {
            return MARKETPLACE_RIGHT_RAIL_ITEMS;
        }
        const source = engineRails.length > 0 ? engineRails : buildFallbackEngineRails();
        return buildEngineRailItems(source.slice(0, 6));
    }, [engineRails]);

    return (
        <aside className="workspace-rail workspace-rail-right" aria-label="Marketplace secondary rail">
            <div className="workspace-rail-brand">AI</div>
            <div className="workspace-rail-nav">{renderRailItems(rightItems, activeRailId, onRailSelect)}</div>
        </aside>
    );
}

export function buildMarketplaceWorkspaceRailItems(activeRailId: MarketplaceRailId) {
    return {
        railItems: buildWorkspaceChromeItems(MARKETPLACE_LEFT_RAIL_ITEMS, activeRailId),
        rightRailItems: buildWorkspaceChromeItems(MARKETPLACE_RIGHT_RAIL_ITEMS, activeRailId),
    };
}
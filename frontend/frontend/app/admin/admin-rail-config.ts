/**
 * Admin rail configuration — pure TypeScript (no JSX).
 * Contains regex, types, override maps, and helper functions for
 * deriving rail shortLabels from launcher item data.
 */

export const ADMIN_RAIL_EMOJI_REGEX =
    /[\u2700-\u27BF]|[\uE000-\uF8FF]|\uD83C[\uDC00-\uDFFF]|\uD83D[\uDC00-\uDFFF]|[\u2011-\u26FF]|\uD83E[\uDD10-\uDDFF]/;

export type AdminLauncherRailSource = {
    id: string;
    label: string;
    accent: 'blue' | 'violet' | 'emerald' | 'amber' | 'neutral' | 'slate' | 'cyan';
    onClick: () => void;
};

export const ADMIN_LEFT_SHORT_LABEL_OVERRIDES: Record<string, string> = {
    'admin-control-hub': '제어',
    'system-settings': '설정',
    'auto-connect': '연결',
    'health-overview': '건강',
    'ad-orders': '주문',
    'subscription-monitor': '구독',
    category: '카테',
};

export const ADMIN_RIGHT_SHORT_LABEL_OVERRIDES: Record<string, string> = {
    'manual-orchestrator': '오케',
    'live-logs': '로그',
    'top-projects': '인기',
    sample: '샘플',
    cost: '비용',
    'quick-links': '빠른',
    'ops-health': '건강',
    'ops-recovery': '복구',
    'ops-logs': '추적',
    'ops-extras-health': '익스',
    'ops-extras-catalog': '카탈',
    'ops-system-settings': '운영',
    'worldlinco-tuning': '링코',
};

export function extractAdminRailIconAndLabel(label: string): { emoji: string; plainLabel: string } {
    const match = label.match(ADMIN_RAIL_EMOJI_REGEX);
    const emoji = match ? match[0] : '●';
    const plainLabel = label.replace(emoji, '').trim();
    return { emoji, plainLabel };
}

export function buildAdminRailShortLabel(
    id: string,
    label: string,
    overrides: Record<string, string>,
): string {
    const override = overrides[id];
    if (override) return override;
    const headToken = (label.split(' ')[0] ?? '').trim();
    const twoChar = headToken.slice(0, 2) || label.slice(0, 2);
    return twoChar.toUpperCase() === 'AD' ? '제어' : twoChar;
}

/**
 * Admin rail item builder — React TSX.
 * Wraps pure config helpers to produce WorkspaceRailItem[] with icons.
 */
import * as React from 'react';
import type { WorkspaceRailItem } from '@/components/ui/workspace-chrome';
import {
    extractAdminRailIconAndLabel,
    buildAdminRailShortLabel,
    type AdminLauncherRailSource,
} from './admin-rail-config';

export function buildAdminLauncherRailItems(
    items: readonly AdminLauncherRailSource[],
    shortLabelOverrides: Record<string, string>,
): WorkspaceRailItem[] {
    return items.map((item) => {
        const { emoji, plainLabel } = extractAdminRailIconAndLabel(item.label);
        return {
            id: item.id,
            label: item.label,
            shortLabel: buildAdminRailShortLabel(item.id, plainLabel, shortLabelOverrides),
            accent: item.accent,
            onClick: item.onClick,
            testId: `admin-launcher-${item.id}`,
            icon: (
                <div className="flex items-center justify-center w-7 h-7 rounded-full bg-white/5 border border-white/10 mb-0.5 text-sm group-hover:bg-white/10 transition-colors">
                    {emoji}
                </div>
            ),
        };
    });
}

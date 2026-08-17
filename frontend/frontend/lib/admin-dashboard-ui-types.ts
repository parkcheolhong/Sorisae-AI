export type OrchestratorCapabilityState = 'standby' | 'active' | 'warning' | 'error';

export interface OrchestratorCapabilityActionGuide {
    title: string;
    summary: string;
    href: string;
}

export interface SystemResourceCard {
    id: string;
    title: string;
    icon: string;
    state: 'ok' | 'warning' | 'critical';
    value: string;
    detail: string;
    action: string;
    apiPath: string;
}

export interface CompactOverviewCard {
    key: string;
    label: string;
    value: string;
    icon: string;
    tone: 'slate' | 'violet' | 'emerald' | 'amber' | 'orange' | 'cyan';
    detail?: string;
}

export function assertAdminDashboardUiTypesContract() {
    const card: CompactOverviewCard = {
        key: 'sample',
        label: 'label',
        value: 'value',
        icon: 'icon',
        tone: 'slate',
    };
    if (card.tone !== 'slate') {
        throw new Error('admin dashboard ui types contract 누락: compact overview tone 기본값 필요');
    }
}

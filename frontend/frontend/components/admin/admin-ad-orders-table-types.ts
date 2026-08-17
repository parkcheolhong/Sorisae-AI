import type { AdminAdVideoOrderItem } from '@/lib/admin-dashboard-types';

export interface AdminAdStoryboardModalPayload {
    orderId: number;
    cut: number;
    src: string;
    title: string;
    status?: string;
}

export interface AdminAdOrderReviewProps {
    expandedOrderId: number | null;
    drafts: Record<number, Array<{ cut: number; status: 'pending' | 'approved' | 'needs-fix'; note?: string }>>;
    diffOnly: Record<number, boolean>;
    statusDiffOnly: Record<number, boolean>;
    noteDiffOnly: Record<number, boolean>;
    savingId: number | null;
    onOpenPanel: (order: AdminAdVideoOrderItem) => void;
    onToggleDiffOnly: (orderId: number) => void;
    onToggleStatusDiffOnly: (orderId: number) => void;
    onToggleNoteDiffOnly: (orderId: number) => void;
    onResetFilters: (orderId: number) => void;
    onStoryboardModalOpen: (modal: AdminAdStoryboardModalPayload) => void;
    matchesSceneFilter: (order: AdminAdVideoOrderItem, cut: number) => boolean;
    onUpdateDraft: (orderId: number, cut: number, field: 'status' | 'note', value: string) => void;
    onSave: (order: AdminAdVideoOrderItem) => void;
}

export interface AdminAdOrderActionsProps {
    previewLoadingId: number | null;
    retryingId: number | null;
    onPreview: (order: AdminAdVideoOrderItem) => void;
    onDownload: (order: AdminAdVideoOrderItem) => void;
    onRetry: (order: AdminAdVideoOrderItem) => void;
}

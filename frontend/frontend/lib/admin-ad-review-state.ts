import type { AdminAdVideoOrderItem } from '@/lib/admin-dashboard-types';

export const ADMIN_AD_REVIEW_FILTER_STORAGE_KEY = 'admin_ad_review_filters_v1';

export type AdminAdReviewFilterState = {
    diffOnly: Record<number, boolean>;
    statusDiffOnly: Record<number, boolean>;
    noteDiffOnly: Record<number, boolean>;
};

export type AdminStoryboardModalState = {
    orderId: number;
    cut: number;
    src: string;
    title: string;
    status?: string;
};

export function readAdminAdReviewFilterState(): AdminAdReviewFilterState {
    if (typeof window === 'undefined') {
        return { diffOnly: {}, statusDiffOnly: {}, noteDiffOnly: {} };
    }
    try {
        const raw = window.localStorage.getItem(ADMIN_AD_REVIEW_FILTER_STORAGE_KEY);
        if (!raw) {
            return { diffOnly: {}, statusDiffOnly: {}, noteDiffOnly: {} };
        }
        const parsed = JSON.parse(raw) as AdminAdReviewFilterState;
        return {
            diffOnly: parsed.diffOnly || {},
            statusDiffOnly: parsed.statusDiffOnly || {},
            noteDiffOnly: parsed.noteDiffOnly || {},
        };
    } catch {
        return { diffOnly: {}, statusDiffOnly: {}, noteDiffOnly: {} };
    }
}

export function writeAdminAdReviewFilterState(state: AdminAdReviewFilterState) {
    if (typeof window === 'undefined') {
        return;
    }
    window.localStorage.setItem(ADMIN_AD_REVIEW_FILTER_STORAGE_KEY, JSON.stringify(state));
}

export function toggleAdminAdReviewFilter(current: Record<number, boolean>, orderId: number) {
    return {
        ...current,
        [orderId]: !current[orderId],
    };
}

export function resetAdminAdReviewFilters(orderId: number, current: AdminAdReviewFilterState): AdminAdReviewFilterState {
    return {
        diffOnly: { ...current.diffOnly, [orderId]: false },
        statusDiffOnly: { ...current.statusDiffOnly, [orderId]: false },
        noteDiffOnly: { ...current.noteDiffOnly, [orderId]: false },
    };
}

export function matchesAdminAdReviewSceneFilter(options: {
    order: AdminAdVideoOrderItem;
    cut: number;
    filters: AdminAdReviewFilterState;
}) {
    const diffItems = (options.order.storyboard_review_history || [])
        .flatMap((history) => Array.isArray(history.diff) ? history.diff : [])
        .filter((item) => item.cut === options.cut);
    if (!options.filters.diffOnly[options.order.id] && !options.filters.statusDiffOnly[options.order.id] && !options.filters.noteDiffOnly[options.order.id]) {
        return true;
    }
    if (diffItems.length === 0) {
        return false;
    }
    const hasStatusDiff = diffItems.some((item) => (item.previous_status || 'pending') !== (item.current_status || 'pending'));
    const hasNoteDiff = diffItems.some((item) => (item.previous_note || '') !== (item.current_note || ''));
    if (options.filters.statusDiffOnly[options.order.id] && !hasStatusDiff) {
        return false;
    }
    if (options.filters.noteDiffOnly[options.order.id] && !hasNoteDiff) {
        return false;
    }
    return !options.filters.diffOnly[options.order.id] || diffItems.length > 0;
}

export function moveAdminStoryboardModalCut(options: {
    modal: AdminStoryboardModalState | null;
    orders: AdminAdVideoOrderItem[];
    direction: -1 | 1;
    resolvePreviewSource: (order: AdminAdVideoOrderItem, scene: NonNullable<AdminAdVideoOrderItem['storyboard']>[number]) => string;
}) {
    if (!options.modal) {
        return options.modal;
    }
    const order = options.orders.find((item) => item.id === options.modal?.orderId);
    const scenes = order?.storyboard || [];
    const currentIndex = scenes.findIndex((scene) => scene.cut === options.modal?.cut);
    if (currentIndex < 0) {
        return options.modal;
    }
    const nextScene = scenes[currentIndex + options.direction];
    if (!nextScene) {
        return options.modal;
    }
    const nextSrc = options.resolvePreviewSource(order!, nextScene);
    if (!nextSrc) {
        return options.modal;
    }
    return {
        orderId: options.modal.orderId,
        cut: nextScene.cut,
        src: nextSrc,
        title: `주문 #${order!.id} · 컷 ${nextScene.cut} · ${nextScene.title || '제목 없음'}`,
        status: (order!.storyboard_review || []).find((item) => item.cut === nextScene.cut)?.status,
    } satisfies AdminStoryboardModalState;
}

export function findCurrentAdStoryboardModalDiff(modal: AdminStoryboardModalState | null, orders: AdminAdVideoOrderItem[]) {
    if (!modal) {
        return null;
    }
    const order = orders.find((item) => item.id === modal.orderId);
    const historyEntries = [...(order?.storyboard_review_history || [])].reverse();
    for (const history of historyEntries) {
        const found = (history.diff || []).find((item) => item.cut === modal.cut);
        if (found) {
            return found;
        }
    }
    return null;
}

export function findCurrentAdStoryboardModalIndex(modal: AdminStoryboardModalState | null, orders: AdminAdVideoOrderItem[]) {
    if (!modal) {
        return null;
    }
    const order = orders.find((item) => item.id === modal.orderId);
    const scenes = order?.storyboard || [];
    const index = scenes.findIndex((scene) => scene.cut === modal.cut);
    if (index < 0) {
        return null;
    }
    return {
        current: index + 1,
        total: scenes.length,
    };
}

export function assertAdminAdReviewStateContract() {
    const state = readAdminAdReviewFilterState();
    if (!state.diffOnly || !state.statusDiffOnly || !state.noteDiffOnly) {
        throw new Error('admin ad review state contract 누락: filter state 3종 필요');
    }
}

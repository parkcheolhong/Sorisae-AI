import type { AdminAdVideoOrderItem } from '@/lib/admin-dashboard-types';

export type AdminAdVideoOrderReviewDraft = Array<{ cut: number; status: 'pending' | 'approved' | 'needs-fix'; note?: string }>;

function isUnauthorized(status: number) {
    return status === 401 || status === 403;
}

export async function previewAdminAdOrderVideo(options: {
    apiBaseUrl: string;
    token: string;
    orderId: number;
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const response = await fetcher(`${options.apiBaseUrl}/api/admin/ad-video-orders/${options.orderId}/download`, {
        headers: { Authorization: `Bearer ${options.token}` },
    });
    if (isUnauthorized(response.status)) {
        throw new Error('__ADMIN_AD_ORDER_UNAUTHORIZED__');
    }
    if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(data?.detail || '영상 미리보기에 실패했습니다.');
    }
    return response.blob();
}

export async function downloadAdminAdOrderVideo(options: {
    apiBaseUrl: string;
    token: string;
    order: AdminAdVideoOrderItem;
    buildApiErrorMessage: (apiPath: string, status: number, detail?: string | null, fallback?: string) => string;
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const apiPath = `/api/admin/ad-video-orders/${options.order.id}/download`;
    const response = await fetcher(`${options.apiBaseUrl}${apiPath}`, {
        headers: { Authorization: `Bearer ${options.token}` },
    });
    if (isUnauthorized(response.status)) {
        throw new Error('__ADMIN_AD_ORDER_UNAUTHORIZED__');
    }
    if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(options.buildApiErrorMessage(apiPath, response.status, data?.detail, '다운로드에 실패했습니다.'));
    }
    return response.blob();
}

export async function retryAdminAdOrder(options: {
    apiBaseUrl: string;
    token: string;
    orderId: number;
    buildApiErrorMessage: (apiPath: string, status: number, detail?: string | null, fallback?: string) => string;
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const apiPath = `/api/admin/ad-video-orders/${options.orderId}/retry`;
    const response = await fetcher(`${options.apiBaseUrl}${apiPath}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${options.token}` },
    });
    if (isUnauthorized(response.status)) {
        throw new Error('__ADMIN_AD_ORDER_UNAUTHORIZED__');
    }
    const data = await response.json().catch(() => null);
    if (!response.ok) {
        throw new Error(options.buildApiErrorMessage(apiPath, response.status, data?.detail, '광고 주문 재시도에 실패했습니다.'));
    }
    return data;
}

export async function saveAdminAdOrderStoryboardReview(options: {
    apiBaseUrl: string;
    token: string;
    orderId: number;
    draft: AdminAdVideoOrderReviewDraft;
    buildApiErrorMessage: (apiPath: string, status: number, detail?: string | null, fallback?: string) => string;
    fetchImpl?: typeof fetch;
}) {
    const fetcher = options.fetchImpl || fetch;
    const apiPath = `/api/admin/ad-video-orders/${options.orderId}/storyboard-review`;
    const response = await fetcher(`${options.apiBaseUrl}${apiPath}`, {
        method: 'PUT',
        headers: {
            Authorization: `Bearer ${options.token}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ storyboard_review: options.draft }),
    });
    if (isUnauthorized(response.status)) {
        throw new Error('__ADMIN_AD_ORDER_UNAUTHORIZED__');
    }
    const data = await response.json().catch(() => null);
    if (!response.ok) {
        throw new Error(options.buildApiErrorMessage(apiPath, response.status, data?.detail, '스토리보드 검수 저장에 실패했습니다.'));
    }
    return data;
}

export function createAdminAdReviewDraft(order: AdminAdVideoOrderItem): AdminAdVideoOrderReviewDraft {
    return (order.storyboard_review || order.storyboard?.map((scene) => ({ cut: scene.cut, status: 'pending' as const, note: '' })) || []);
}

export function updateAdminAdReviewDraftItems(
    current: Record<number, AdminAdVideoOrderReviewDraft>,
    orderId: number,
    cut: number,
    field: 'status' | 'note',
    value: string,
) {
    return {
        ...current,
        [orderId]: (current[orderId] || []).map((item) => item.cut === cut ? { ...item, [field]: value } : item),
    };
}

export function assertAdminAdOrderActionsContract() {
    const sample = createAdminAdReviewDraft({ id: 1, user_id: 1, title: 'sample', status: 'pending', storyboard: [{ cut: 1 }] });
    if (!Array.isArray(sample)) {
        throw new Error('admin ad order actions contract 누락: review draft 배열 반환 필요');
    }
}

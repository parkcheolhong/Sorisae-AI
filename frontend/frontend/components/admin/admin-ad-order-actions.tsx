'use client';

import type { AdminAdVideoOrderItem } from '@/lib/admin-dashboard-types';
import type { AdminAdOrderActionsProps } from '@/components/admin/admin-ad-orders-table-types';

interface AdminAdOrderActionsComponentProps {
    order: AdminAdVideoOrderItem;
    actions: AdminAdOrderActionsProps;
    productionWorkReady: boolean;
}

export default function AdminAdOrderActions({ order, actions, productionWorkReady }: AdminAdOrderActionsComponentProps) {
    return (
        <>
            <div className="flex items-center gap-2">
                <button type="button" onClick={() => actions.onPreview(order)} disabled={order.status !== 'completed' || actions.previewLoadingId === order.id} className="rounded-md border border-indigo-400 px-3 py-1 text-indigo-600 disabled:opacity-40">{actions.previewLoadingId === order.id ? '로딩...' : '미리보기'}</button>
                <button type="button" onClick={() => actions.onDownload(order)} disabled={order.status !== 'completed'} className="rounded-md bg-indigo-600 px-3 py-1 text-white disabled:opacity-40">다운로드</button>
                {['failed', 'queued', 'pending', 'processing', 'rendering'].includes(order.status) && <button type="button" onClick={() => actions.onRetry(order)} disabled={actions.retryingId === order.id || (order.engine_type === 'dedicated_engine' && !productionWorkReady)} className="rounded-md border border-amber-400 px-3 py-1 text-amber-700 disabled:opacity-40">{actions.retryingId === order.id ? '재큐 중...' : '재큐'}</button>}
            </div>
            {order.engine_type === 'dedicated_engine' && !productionWorkReady && <p className="mt-2 text-[10px] text-amber-700">체크리스트가 모두 차야 dedicated 재작업을 허용합니다.</p>}
        </>
    );
}

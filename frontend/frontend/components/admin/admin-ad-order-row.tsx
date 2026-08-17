'use client';

import { buildAdminAdProductionStages, getAdminAdProductionCurrentStage, getAdminMotionTempoLabel } from '@/lib/admin-ad-production-analysis';
import type { AdminAdVideoOrderItem } from '@/lib/admin-dashboard-types';
import AdminAdOrderActions from '@/components/admin/admin-ad-order-actions';
import AdminAdStoryboardReviewPanel from '@/components/admin/admin-ad-storyboard-review-panel';
import type { AdminAdOrderActionsProps, AdminAdOrderReviewProps } from '@/components/admin/admin-ad-orders-table-types';

interface AdminAdOrderRowProps {
    order: AdminAdVideoOrderItem;
    actionTemplateLabels: Record<string, string>;
    review: AdminAdOrderReviewProps;
    actions: AdminAdOrderActionsProps;
}

export default function AdminAdOrderRow({ order, actionTemplateLabels, review, actions }: AdminAdOrderRowProps) {
    const productionStages = order.engine_type === 'dedicated_engine' ? buildAdminAdProductionStages(order) : [];
    const productionReadyCount = productionStages.filter((stage) => stage.ready).length;
    const productionWorkReady = productionStages.length > 0 && productionStages.every((stage) => stage.ready);
    const productionCurrentStage = productionStages.length > 0 ? getAdminAdProductionCurrentStage(productionStages) : '비전용 엔진';

    return (
        <tr key={order.id} className="border-b hover:bg-gray-50" data-testid={`admin-storyboard-order-row-${order.id}`}>
            <td className="px-3 py-2 text-gray-600">#{order.id}</td>
            <td className="px-3 py-2 text-gray-700">{order.user_id}</td>
            <td className="max-w-[320px] px-3 py-2">
                <div className="truncate font-medium text-gray-900" title={order.title} data-testid={`admin-storyboard-order-title-${order.id}`}>{order.title}</div>
                {order.engine_type === 'dedicated_engine' && (
                    <div className="mt-2 flex flex-wrap gap-1 text-[10px]">
                        <span className="rounded-full border border-cyan-200 bg-cyan-50 px-2 py-0.5 text-cyan-700">4D dedicated</span>
                        <span className={`rounded-full border px-2 py-0.5 ${productionWorkReady ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-amber-200 bg-amber-50 text-amber-700'}`}>체크리스트 {productionReadyCount}/6</span>
                        <span className="rounded-full border border-violet-200 bg-violet-50 px-2 py-0.5 text-violet-700">현재 {productionCurrentStage}</span>
                        <span className="rounded-full border border-sky-200 bg-sky-50 px-2 py-0.5 text-sky-700">{actionTemplateLabels[order.action_template_key || ''] || '템플릿 미지정'}</span>
                        <span className="rounded-full border border-sky-200 bg-white px-2 py-0.5 text-sky-700">속도 {getAdminMotionTempoLabel(order.motion_tempo)}</span>
                    </div>
                )}
                <AdminAdStoryboardReviewPanel order={order} review={review} />
            </td>
            <td className="px-3 py-2 text-gray-700"><div className="flex flex-col gap-1"><span>{order.engine_type || 'internal_ffmpeg'}</span>{order.engine_type === 'dedicated_engine' && <span className={`inline-flex w-fit rounded-full px-2 py-0.5 text-[10px] ${productionWorkReady ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>{productionWorkReady ? '작업 가능' : '입력 보강 필요'}</span>}</div></td>
            <td className="px-3 py-2 text-gray-700">{order.engine_type === 'dedicated_engine' ? <div className="space-y-1 text-[11px]"><div className="font-semibold text-cyan-700">{productionCurrentStage}</div><div>{productionReadyCount}/6 완료</div><div className="text-sky-700">{actionTemplateLabels[order.action_template_key || ''] || '템플릿 미지정'} · {getAdminMotionTempoLabel(order.motion_tempo)}</div><div className={`${productionWorkReady ? 'text-emerald-700' : 'text-amber-700'}`}>{productionWorkReady ? '4D 작업 가능' : '선행 입력 필요'}</div></div> : <span className="text-[11px] text-gray-500">-</span>}</td>
            <td className="px-3 py-2 text-gray-700">{order.status}</td>
            <td className="px-3 py-2 text-gray-700">{order.progress_percent ?? 0}%</td>
            <td className="px-3 py-2 text-gray-700">{order.created_at?.slice(0, 19).replace('T', ' ') || '-'}</td>
            <td className="px-3 py-2">
                <AdminAdOrderActions order={order} actions={actions} productionWorkReady={productionWorkReady} />
            </td>
        </tr>
    );
}

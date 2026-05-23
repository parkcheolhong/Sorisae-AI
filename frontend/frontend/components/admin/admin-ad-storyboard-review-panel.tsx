'use client';

import { resolveAdminStoryboardPreviewSource } from '@/lib/admin-ad-production-analysis';
import type { AdminAdVideoOrderItem } from '@/lib/admin-dashboard-types';
import AdminAdStoryboardHistoryPanel from '@/components/admin/admin-ad-storyboard-history-panel';
import type { AdminAdOrderReviewProps } from '@/components/admin/admin-ad-orders-table-types';

interface AdminAdStoryboardReviewPanelProps {
    order: AdminAdVideoOrderItem;
    review: AdminAdOrderReviewProps;
}

export default function AdminAdStoryboardReviewPanel({ order, review }: AdminAdStoryboardReviewPanelProps) {
    if (!order.storyboard || order.storyboard.length === 0) {
        return null;
    }

    return (
        <div className="mt-1 space-y-1 text-[11px] text-gray-500">
            <div>storyboard {order.storyboard.length}씬 · 통과 {(order.storyboard_review || []).filter((item) => item.status === 'approved').length} · 수정필요 {(order.storyboard_review || []).filter((item) => item.status === 'needs-fix').length}</div>
            <div className="flex flex-wrap gap-1">{(order.storyboard_review || []).slice(0, 3).map((item) => <span key={`${order.id}-review-${item.cut}`} className={`rounded-full px-2 py-0.5 ${item.status === 'approved' ? 'bg-green-100 text-green-700' : item.status === 'needs-fix' ? 'bg-rose-100 text-rose-700' : 'bg-amber-100 text-amber-700'}`}>컷 {item.cut} · {item.status === 'approved' ? '통과' : item.status === 'needs-fix' ? '수정필요' : '대기'}</span>)}</div>
            <button type="button" onClick={() => review.onOpenPanel(order)} className="rounded-md border border-gray-300 px-2 py-1 text-[11px] text-gray-600 hover:bg-gray-50" data-testid={`admin-storyboard-order-expand-${order.id}`}>{review.expandedOrderId === order.id ? '컷별 검수 메모 접기' : '컷별 검수 메모 펼치기'}</button>
            {review.expandedOrderId === order.id && (
                <div className="space-y-2 rounded-lg border border-gray-200 bg-white p-2" data-testid="admin-storyboard-panel">
                    <div className="flex flex-wrap justify-end gap-2">
                        <button type="button" onClick={() => review.onToggleDiffOnly(order.id)} className="rounded-md border border-slate-300 px-2 py-1 text-[11px] text-slate-700 hover:bg-slate-50" data-testid={`admin-storyboard-filter-diff-only-${order.id}`}>{review.diffOnly[order.id] ? '전체 컷 보기' : '변경된 컷만 필터'}</button>
                        <button type="button" onClick={() => review.onToggleStatusDiffOnly(order.id)} className="rounded-md border border-sky-300 px-2 py-1 text-[11px] text-sky-700 hover:bg-sky-50" data-testid={`admin-storyboard-filter-status-only-${order.id}`}>{review.statusDiffOnly[order.id] ? '상태 필터 해제' : '상태 변경만'}</button>
                        <button type="button" onClick={() => review.onToggleNoteDiffOnly(order.id)} className="rounded-md border border-violet-300 px-2 py-1 text-[11px] text-violet-700 hover:bg-violet-50" data-testid={`admin-storyboard-filter-note-only-${order.id}`}>{review.noteDiffOnly[order.id] ? '메모 필터 해제' : '메모 변경만'}</button>
                        <button type="button" onClick={() => review.onResetFilters(order.id)} className="rounded-md border border-gray-300 px-2 py-1 text-[11px] text-gray-700 hover:bg-gray-50" data-testid={`admin-storyboard-filter-reset-${order.id}`}>필터 초기화</button>
                    </div>
                    <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
                        {(order.storyboard || []).slice(0, 6).map((scene) => {
                            const previewSource = resolveAdminStoryboardPreviewSource(order, scene);
                            return (
                                <div key={`${order.id}-thumb-${scene.cut}`} className="overflow-hidden rounded-md border border-gray-200 bg-gray-50">
                                    {previewSource ? <button type="button" onClick={() => review.onStoryboardModalOpen({ orderId: order.id, cut: scene.cut, src: previewSource, title: `주문 #${order.id} · 컷 ${scene.cut} · ${scene.title || '제목 없음'}`, status: (order.storyboard_review || []).find((item) => item.cut === scene.cut)?.status })} className="block w-full" data-testid={`admin-storyboard-scene-thumbnail-${scene.cut}`}><img src={previewSource} alt={`주문 ${order.id} 컷 ${scene.cut} 썸네일`} className="h-20 w-full object-cover" /></button> : <div className="flex h-20 items-center justify-center px-2 text-center text-[10px] text-gray-400">썸네일 없음</div>}
                                    <div className="px-2 py-1 text-[10px] text-gray-600">컷 {scene.cut} · {scene.title || '제목 없음'}</div>
                                </div>
                            );
                        })}
                    </div>
                    {(order.storyboard || []).filter((scene) => review.matchesSceneFilter(order, scene.cut)).map((scene) => {
                        const draft = (review.drafts[order.id] || []).find((item) => item.cut === scene.cut) || { cut: scene.cut, status: 'pending' as const, note: '' };
                        return <div key={`${order.id}-scene-${scene.cut}`} className="rounded-md border border-gray-100 bg-gray-50 p-2 text-[11px] text-gray-600" data-testid={`admin-storyboard-scene-card-${scene.cut}`}><div className="flex flex-wrap items-center justify-between gap-2"><span className="font-semibold text-gray-800">컷 {scene.cut} · {scene.title || '제목 없음'}</span><select value={draft.status} onChange={(event) => review.onUpdateDraft(order.id, scene.cut, 'status', event.target.value)} className="rounded-md border border-gray-300 px-2 py-1 text-[11px]" title={`컷 ${scene.cut} 검수 상태`} data-testid={`admin-storyboard-scene-status-${scene.cut}`}><option value="pending">대기</option><option value="approved">통과</option><option value="needs-fix">수정 필요</option></select></div><textarea value={draft.note || ''} onChange={(event) => review.onUpdateDraft(order.id, scene.cut, 'note', event.target.value)} rows={2} className="mt-2 w-full rounded-md border border-gray-300 px-2 py-1 text-[11px]" placeholder="컷별 검수 메모" data-testid={`admin-storyboard-scene-note-${scene.cut}`} /></div>;
                    })}
                    <div className="flex justify-end"><button type="button" onClick={() => review.onSave(order)} disabled={review.savingId === order.id} className="rounded-md bg-indigo-600 px-3 py-1.5 text-[11px] text-white disabled:opacity-40" data-testid={`admin-storyboard-save-${order.id}`}>{review.savingId === order.id ? '저장 중...' : '검수 저장'}</button></div>
                    <AdminAdStoryboardHistoryPanel order={order} matchesSceneFilter={review.matchesSceneFilter} />
                </div>
            )}
        </div>
    );
}

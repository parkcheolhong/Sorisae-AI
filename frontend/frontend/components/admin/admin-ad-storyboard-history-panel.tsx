'use client';

import type { AdminAdVideoOrderItem } from '@/lib/admin-dashboard-types';

interface AdminAdStoryboardHistoryPanelProps {
    order: AdminAdVideoOrderItem;
    matchesSceneFilter: (order: AdminAdVideoOrderItem, cut: number) => boolean;
}

export default function AdminAdStoryboardHistoryPanel({ order, matchesSceneFilter }: AdminAdStoryboardHistoryPanelProps) {
    return (
        <div className="rounded-md border border-slate-200 bg-slate-50 p-2 text-[11px] text-gray-600" data-testid="admin-storyboard-history-panel">
            <div className="font-semibold text-gray-800">검수 변경 이력 로그</div>
            {Array.isArray(order.storyboard_review_history) && order.storyboard_review_history.length > 0 ? (
                <div className="mt-2 space-y-2" data-testid="admin-storyboard-history-list">
                    {[...order.storyboard_review_history].slice().reverse().map((history, historyIndex) => (
                        <div key={`${order.id}-history-${historyIndex}`} className="rounded-md border border-slate-200 bg-white p-2" data-testid={`admin-storyboard-history-entry-${historyIndex}`}>
                            <div className="text-[10px] text-gray-500">{history.changed_at?.replace('T', ' ').slice(0, 19) || '-'} · 관리자 #{history.changed_by ?? '-'}</div>
                            <div className="mt-1 flex flex-wrap gap-1">{(history.storyboard_review || []).map((item) => <span key={`${order.id}-history-${historyIndex}-${item.cut}`} className={`rounded-full px-2 py-0.5 ${item.status === 'approved' ? 'bg-green-100 text-green-700' : item.status === 'needs-fix' ? 'bg-rose-100 text-rose-700' : 'bg-amber-100 text-amber-700'}`}>컷 {item.cut} · {item.status === 'approved' ? '통과' : item.status === 'needs-fix' ? '수정필요' : '대기'}</span>)}</div>
                            {Array.isArray(history.diff) && history.diff.length > 0 && <div className="mt-2 space-y-1">{history.diff.filter((diffItem) => matchesSceneFilter(order, diffItem.cut)).map((diffItem) => <div key={`${order.id}-history-${historyIndex}-diff-${diffItem.cut}`} className="rounded border border-dashed border-slate-200 bg-slate-50 px-2 py-1 text-[10px] text-slate-600" data-testid={`admin-storyboard-history-diff-${historyIndex}-${diffItem.cut}`}><div>컷 {diffItem.cut} · 상태 {diffItem.previous_status || 'pending'} → {diffItem.current_status || 'pending'}</div><div>메모 변경: {(diffItem.previous_note || '(없음)')} → {(diffItem.current_note || '(없음)')}</div></div>)}</div>}
                        </div>
                    ))}
                </div>
            ) : <div className="mt-2 rounded-md border border-dashed border-slate-300 bg-white px-3 py-2 text-[11px] text-slate-500">아직 검수 변경 이력이 없습니다.</div>}
        </div>
    );
}

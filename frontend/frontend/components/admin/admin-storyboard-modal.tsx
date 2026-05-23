'use client';

import type { AdminStoryboardModalState } from '@/lib/admin-ad-review-state';

interface StoryboardDiffLike {
    previous_status?: string;
    current_status?: string;
    previous_note?: string;
    current_note?: string;
}

interface StoryboardModalIndexLike {
    current: number;
    total: number;
}

interface AdminStoryboardModalProps {
    modal: AdminStoryboardModalState | null;
    currentDiff: StoryboardDiffLike | null;
    currentIndex: StoryboardModalIndexLike | null;
    onClose: () => void;
    onMoveCut: (direction: -1 | 1) => void;
}

export default function AdminStoryboardModal({
    modal,
    currentDiff,
    currentIndex,
    onClose,
    onMoveCut,
}: AdminStoryboardModalProps) {
    if (!modal) {
        return null;
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" data-testid="admin-storyboard-modal">
            <div className="w-full max-w-3xl rounded-xl border border-gray-700 bg-[#0d1117] p-4">
                <div className="mb-3 flex items-center justify-between gap-3">
                    <div>
                        <h3 className="text-base font-semibold text-gray-100" data-testid="admin-storyboard-modal-title">{modal.title}</h3>
                        <p className="mt-1 text-xs text-gray-400" data-testid="admin-storyboard-modal-status">검수 상태: {modal.status === 'approved' ? '통과' : modal.status === 'needs-fix' ? '수정 필요' : '대기'}</p>
                        {currentIndex && (
                            <p className="mt-1 text-xs text-indigo-300" data-testid="admin-storyboard-modal-index">컷 {currentIndex.current} / 전체 {currentIndex.total}</p>
                        )}
                        <p className="mt-1 text-[11px] text-gray-500">← / → 방향키로 이전/다음 컷 이동</p>
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        className="rounded-md border border-gray-600 px-3 py-1 text-sm text-gray-200 hover:bg-gray-800"
                        data-testid="admin-storyboard-modal-close"
                    >
                        닫기
                    </button>
                </div>
                <div className="mb-3 flex items-center justify-between gap-2">
                    <button
                        type="button"
                        onClick={() => onMoveCut(-1)}
                        className="rounded-md border border-gray-600 px-3 py-1 text-sm text-gray-200 hover:bg-gray-800"
                        data-testid="admin-storyboard-modal-prev"
                    >
                        이전 컷
                    </button>
                    <button
                        type="button"
                        onClick={() => onMoveCut(1)}
                        className="rounded-md border border-gray-600 px-3 py-1 text-sm text-gray-200 hover:bg-gray-800"
                        data-testid="admin-storyboard-modal-next"
                    >
                        다음 컷
                    </button>
                </div>
                <div className="overflow-hidden rounded-lg border border-gray-700 bg-black p-2">
                    <img src={modal.src} alt={modal.title} className="h-auto max-h-[70vh] w-full rounded object-contain" data-testid="admin-storyboard-modal-image" />
                </div>
                <div className="mt-3 rounded-lg border border-gray-700 bg-[#111827] p-3 text-sm text-gray-200" data-testid="admin-storyboard-diff-panel">
                    <p className="font-semibold text-gray-100">현재 컷 diff</p>
                    {currentDiff ? (
                        <div className="mt-2 space-y-2 text-xs text-gray-300">
                            <div className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2" data-testid="admin-storyboard-diff-status">
                                <p className="font-semibold text-amber-200">상태 변경</p>
                                <p className="mt-1">{currentDiff.previous_status || 'pending'} → {currentDiff.current_status || 'pending'}</p>
                            </div>
                            <div className="rounded-md border border-sky-500/40 bg-sky-500/10 px-3 py-2" data-testid="admin-storyboard-diff-note-before">
                                <p className="font-semibold text-sky-200">이전 메모</p>
                                <p className="mt-1 whitespace-pre-wrap">{currentDiff.previous_note || '(없음)'}</p>
                            </div>
                            <div className="rounded-md border border-emerald-500/40 bg-emerald-500/10 px-3 py-2" data-testid="admin-storyboard-diff-note-after">
                                <p className="font-semibold text-emerald-200">현재 메모</p>
                                <p className="mt-1 whitespace-pre-wrap">{currentDiff.current_note || '(없음)'}</p>
                            </div>
                        </div>
                    ) : (
                        <p className="mt-2 text-xs text-gray-400" data-testid="admin-storyboard-diff-empty">이 컷에 대한 최근 diff 기록이 없습니다.</p>
                    )}
                </div>
            </div>
        </div>
    );
}

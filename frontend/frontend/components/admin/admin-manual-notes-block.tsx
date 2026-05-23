'use client';

import type { AdminManualNotesBlockSlice } from '@/components/admin/admin-manual-orchestrator-types';

interface AdminManualNotesBlockProps {
    notes: AdminManualNotesBlockSlice;
}

export default function AdminManualNotesBlock({ notes }: AdminManualNotesBlockProps) {
    return (
        <>
            <label className="flex items-center gap-2 text-xs text-gray-700">
                <input type="checkbox" checked={notes.selectedStepState.completed} onChange={(event) => notes.onToggleStepCompleted(notes.selectedStepId, event.target.checked)} />
                현재 단계 완료 체크
            </label>
            <div>
                <p className="text-xs font-semibold text-gray-700">관리자 메모</p>
                <textarea value={notes.selectedStepState.note} onChange={(event) => notes.onUpdateStepNote(notes.selectedStepId, event.target.value)} rows={4} className="mt-2 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="단계별 점검 결과, 수동 수정 범위, 후속 조치 메모를 기록하세요." />
            </div>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <label className="block">
                    <span className="mb-2 block text-xs font-semibold text-gray-500">첨부 링크 추가</span>
                    <div className="flex gap-2">
                        <input value={notes.selectedStepState.attachmentDraft} onChange={(event) => notes.onUpdateStepField(notes.selectedStepId, 'attachmentDraft', event.target.value)} className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="예: https://storage.example.com/spec.pdf" />
                        <button type="button" onClick={() => notes.onAddAttachmentLink(notes.selectedStepId)} className="rounded-lg border border-blue-300 bg-blue-50 px-3 py-2 text-xs font-semibold text-blue-700 hover:bg-blue-100">추가</button>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2">
                        {notes.selectedStepState.attachmentLinks.map((link) => (
                            <div key={link} className="inline-flex items-center gap-2 rounded-full border border-gray-300 bg-white px-3 py-1 text-[11px] text-gray-700">
                                <span className="max-w-[240px] truncate">{link}</span>
                                <button type="button" onClick={() => notes.onRemoveAttachmentLink(notes.selectedStepId, link)} className="text-red-600 hover:text-red-700">삭제</button>
                            </div>
                        ))}
                        {notes.selectedStepState.attachmentLinks.length === 0 && <span className="text-[11px] text-gray-400">아직 등록된 첨부 링크가 없습니다.</span>}
                    </div>
                </label>
                <label className="block">
                    <span className="mb-2 block text-xs font-semibold text-gray-500">참고 URL</span>
                    <input value={notes.selectedStepState.referenceUrl} onChange={(event) => notes.onUpdateStepField(notes.selectedStepId, 'referenceUrl', event.target.value)} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="예: https://learn.microsoft.com/..." />
                </label>
                <label className="block">
                    <span className="mb-2 block text-xs font-semibold text-gray-500">시작일</span>
                    <input type="date" value={notes.selectedStepState.startedAt} onChange={(event) => notes.onUpdateStepField(notes.selectedStepId, 'startedAt', event.target.value)} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                </label>
                <label className="block">
                    <span className="mb-2 block text-xs font-semibold text-gray-500">종료일</span>
                    <input type="date" value={notes.selectedStepState.endedAt} onChange={(event) => notes.onUpdateStepField(notes.selectedStepId, 'endedAt', event.target.value)} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                </label>
            </div>
            {notes.selectedStepState.updatedAt && <p className="text-[11px] text-gray-500">최근 저장: {new Date(notes.selectedStepState.updatedAt).toLocaleString('ko-KR', { hour12: false })}</p>}
        </>
    );
}

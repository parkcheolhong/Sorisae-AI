'use client';

import type { AdminAdVideoOrderItem } from '@/lib/admin-dashboard-types';

interface AdminAdPreviewModalProps {
    order: AdminAdVideoOrderItem | null;
    previewUrl: string | null;
    previewError: string | null;
    onClose: () => void;
}

export default function AdminAdPreviewModal({ order, previewUrl, previewError, onClose }: AdminAdPreviewModalProps) {
    if (!order) {
        return null;
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
            <div className="w-full max-w-4xl rounded-xl border border-gray-700 bg-[#0d1117] p-4">
                <div className="mb-3 flex items-center justify-between">
                    <h3 className="text-base font-semibold text-gray-100">
                        관리자 영상 미리보기 #{order.id} - {order.title}
                    </h3>
                    <button onClick={onClose} className="rounded-md border border-gray-600 px-3 py-1 text-sm text-gray-200 hover:bg-gray-800">
                        닫기
                    </button>
                </div>

                <div className="rounded-lg border border-gray-700 bg-black p-2">
                    {previewError ? (
                        <div className="p-6 text-sm text-red-300">{previewError}</div>
                    ) : previewUrl ? (
                        <video
                            src={previewUrl}
                            controls
                            autoPlay
                            className="h-auto max-h-[70vh] w-full rounded"
                        />
                    ) : (
                        <div className="p-6 text-sm text-gray-300">미리보기 영상을 불러오는 중입니다...</div>
                    )}
                </div>
            </div>
        </div>
    );
}

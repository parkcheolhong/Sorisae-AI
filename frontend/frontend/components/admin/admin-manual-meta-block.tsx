'use client';

import type { AdminManualMetaBlockSlice } from '@/components/admin/admin-manual-orchestrator-types';

interface AdminManualMetaBlockProps {
    meta: AdminManualMetaBlockSlice;
}

export default function AdminManualMetaBlock({ meta }: AdminManualMetaBlockProps) {
    return (
        <div className="space-y-3 rounded-lg border border-gray-200 bg-gray-50 px-3 py-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <p className="text-xs font-semibold text-gray-700">도메인 / 호스팅 입력</p>
                    <p className="mt-1 text-[11px] text-gray-500">관리자 오케스트레이터 전용 구조 설계, 호스팅 라인, 도메인 연결 메모를 기록합니다.</p>
                </div>
                <div className="flex flex-wrap gap-2 text-xs">
                    <button type="button" onClick={() => meta.onDownloadWorklog('md')} className="rounded-md border border-gray-300 bg-white px-2 py-1 text-gray-700 hover:bg-gray-50">markdown</button>
                    <button type="button" onClick={() => meta.onDownloadWorklog('json')} className="rounded-md border border-gray-300 bg-white px-2 py-1 text-gray-700 hover:bg-gray-50">json</button>
                    <button type="button" onClick={() => meta.onDownloadWorklog('zip')} className="rounded-md border border-blue-300 bg-blue-50 px-2 py-1 text-blue-700 hover:bg-blue-100">zip 패키지</button>
                </div>
            </div>
            <div className="rounded-md border border-dashed border-gray-300 bg-white px-3 py-2 text-[11px] text-gray-600">
                `markdown`은 읽기용 보고서, `json`은 상태 복원/연동용, `zip`은 markdown + json + Mermaid `.mmd` + 섹션 맵을 함께 제공합니다.
            </div>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <label className="block">
                    <span className="mb-2 block text-xs font-semibold text-gray-500">도메인 연결</span>
                    <input value={meta.manualMeta.domain} onChange={(event) => meta.onManualMetaChange((prev) => ({ ...prev, domain: event.target.value }))} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="예: admin.example.com" />
                </label>
                <label className="block">
                    <span className="mb-2 block text-xs font-semibold text-gray-500">호스팅 라인</span>
                    <input value={meta.manualMeta.hostingLine} onChange={(event) => meta.onManualMetaChange((prev) => ({ ...prev, hostingLine: event.target.value }))} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="예: Azure App Service / VM / Docker / K8s" />
                </label>
            </div>
        </div>
    );
}

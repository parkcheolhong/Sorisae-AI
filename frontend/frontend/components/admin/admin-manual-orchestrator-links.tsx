'use client';

import Link from 'next/link';

export default function AdminManualOrchestratorLinks() {
    return (
        <div className="flex flex-wrap gap-2">
            <Link href="/admin/llm" className="rounded-lg border border-[#1f6feb] bg-[rgba(31,111,235,0.16)] px-4 py-2 text-sm font-semibold text-[#9ecbff] no-underline">
                관리자 오케스트레이터 독립공간 열기
            </Link>
            <Link href="/marketplace/orchestrator" className="rounded-lg border border-violet-300 bg-violet-50 px-4 py-2 text-sm font-semibold text-violet-700 no-underline hover:bg-violet-100">
                고객 오케스트레이터 독립공간 열기
            </Link>
        </div>
    );
}

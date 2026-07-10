'use client';

import Link from 'next/link';

interface AdminQuickLinksSectionProps {
    apiBaseUrl: string;
}

export default function AdminQuickLinksSection({ apiBaseUrl }: AdminQuickLinksSectionProps) {
    const apiDocsHref = `${apiBaseUrl}/docs`;

    return (
        <>
            <h2 className="mb-3 text-lg font-semibold text-gray-900">⚡ 빠른 이동</h2>
            <div className="flex flex-wrap gap-2">
                <Link href="/admin" data-testid="admin-quicklink-admin" className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700">
                    📤 관리자 상품 관리
                </Link>
                <Link href="/marketplace" data-testid="admin-quicklink-marketplace" className="rounded-lg border border-gray-300 px-4 py-2 text-sm hover:bg-gray-100">
                    📋 프로젝트 목록
                </Link>
                <Link href="/marketplace/orchestrator" data-testid="admin-quicklink-marketplace-orchestrator" className="rounded-lg border border-indigo-300 px-4 py-2 text-sm text-indigo-900 hover:bg-indigo-100">
                    🧠 고객 오케스트레이터
                </Link>
                <Link href="/admin/docs-viewer?path=docs%2Fidentity-provider-integration-contract.md" data-testid="admin-quicklink-pass-kmc-kcb" className="rounded-lg border border-violet-300 px-4 py-2 text-sm text-violet-900 hover:bg-violet-100">
                    📘 PASS/KMC/KCB 계약 문서
                </Link>
                <Link href="/admin/docs-viewer?path=docs%2Fidentity-provider-operations-transition-package.md" data-testid="admin-quicklink-operations-package" className="rounded-lg border border-violet-300 px-4 py-2 text-sm text-violet-900 hover:bg-violet-100">
                    🧾 운영 전환 패키지
                </Link>
                <Link href="/admin/docs-viewer?path=docs%2Fidentity-provider-business-type-guide.md" data-testid="admin-quicklink-business-type-guide" className="rounded-lg border border-violet-300 px-4 py-2 text-sm text-violet-900 hover:bg-violet-100">
                    🏢 사업자 유형 가이드
                </Link>
                <Link href="/admin/docs-viewer?path=docs%2Fidentity-provider-commercial-values-input-checklist.md" data-testid="admin-quicklink-commercial-values-input" className="rounded-lg border border-amber-300 px-4 py-2 text-sm text-amber-900 hover:bg-amber-100">
                    ✅ PASS/KMC/KCB 상용값 입력
                </Link>
                <Link href="/admin/docs-viewer?path=docs%2Fidentity-provider-commercial-terms-checklist.md" data-testid="admin-quicklink-commercial-terms" className="rounded-lg border border-emerald-300 px-4 py-2 text-sm text-emerald-900 hover:bg-emerald-100">
                    📑 상용화 계약·약관 기준
                </Link>
                <a href={`${apiBaseUrl}/api/llm/status`} data-testid="admin-quicklink-llm-status-api" target="_blank" rel="noreferrer" className="rounded-lg border border-gray-300 px-4 py-2 text-sm hover:bg-gray-100">
                    🤖 LLM 상태 API
                </a>
                <a href={apiDocsHref} data-testid="admin-quicklink-api-docs" target="_blank" rel="noreferrer" className="rounded-lg border border-gray-300 px-4 py-2 text-sm hover:bg-gray-100">
                    📖 Swagger UI
                </a>
            </div>
        </>
    );
}

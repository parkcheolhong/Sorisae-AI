'use client';

import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense, useEffect, useMemo, useState } from 'react';
import { resolveApiBaseUrl } from '@/lib/api';
import { fetchWithAdminBootstrapRetry } from '@/lib/admin-bootstrap-fetch';
import { getAdminToken } from '@/lib/admin-session';
import { redirectToAdminLogin } from '@/lib/admin-navigation';

type WorkspaceTextFileResponse = {
    path: string;
    size_bytes: number;
    content: string;
};

const DOC_LINKS = [
    { path: 'docs/identity-provider-integration-contract.md', title: 'PASS/KMC/KCB 기술 연동 계약서' },
    { path: 'docs/identity-provider-operations-transition-package.md', title: '운영 전환 패키지' },
    { path: 'docs/identity-provider-business-type-guide.md', title: '개인사업자 / 법인사업자 가이드' },
    { path: 'docs/identity-provider-commercial-terms-checklist.md', title: '상용화 기준 계약·약관 체크리스트' },
] as const;

const DOC_TITLE_MAP: Record<string, string> = Object.fromEntries(DOC_LINKS.map((item) => [item.path, item.title]));

function AdminDocsViewerPageContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const apiBaseUrl = resolveApiBaseUrl();
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [documentData, setDocumentData] = useState<WorkspaceTextFileResponse | null>(null);
    const requestedPath = useMemo(() => String(searchParams.get('path') || '').trim(), [searchParams]);
    const title = DOC_TITLE_MAP[requestedPath] || '관리자 문서 보기';

    useEffect(() => {
        const accessToken = getAdminToken();
        if (!accessToken) {
            redirectToAdminLogin(router);
            return;
        }
        if (!requestedPath) {
            setError('문서 경로가 필요합니다.');
            setLoading(false);
            return;
        }

        const loadDocument = async () => {
            setLoading(true);
            setError('');
            try {
                const url = new URL(`${apiBaseUrl}/api/admin/workspace-text-file`);
                url.searchParams.set('path', requestedPath);
                const response = await fetchWithAdminBootstrapRetry(url.toString(), {
                    headers: {
                        Authorization: `Bearer ${accessToken}`,
                    },
                });
                const data = await response.json().catch(() => null);
                if (response.status === 401 || response.status === 403) {
                    redirectToAdminLogin(router);
                    return;
                }
                if (!response.ok || !data) {
                    throw new Error((data as any)?.detail || `문서 조회 실패(${response.status})`);
                }
                setDocumentData(data as WorkspaceTextFileResponse);
            } catch (e: any) {
                setError(e.message || '문서를 불러오지 못했습니다.');
            } finally {
                setLoading(false);
            }
        };

        void loadDocument();
    }, [apiBaseUrl, requestedPath, router]);

    return (
        <div className="min-h-screen bg-[#0d1117] px-4 py-8 text-[#e6edf3]">
            <div className="mx-auto max-w-5xl">
                <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h1 className="text-2xl font-bold text-[#79c0ff]">📘 {title}</h1>
                        <p className="mt-1 text-sm text-[#8b949e]">관리자 대시보드에서 바로 여는 공급사 계약/운영 문서입니다.</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <Link href="/admin" className="rounded-lg border border-[#30363d] bg-[#161b22] px-4 py-2 text-sm text-[#e6edf3] hover:bg-[#21262d]">
                            관리자 대시보드
                        </Link>
                        <Link href="/admin/llm" className="rounded-lg border border-[#30363d] bg-[#161b22] px-4 py-2 text-sm text-[#e6edf3] hover:bg-[#21262d]">
                            LLM 제어 패널
                        </Link>
                    </div>
                </div>

                <div className="mb-4 flex flex-wrap gap-2">
                    {DOC_LINKS.map(({ path, title: label }) => (
                        <Link
                            key={path}
                            data-testid={`admin-doc-link-${path.split('/').pop()?.replace(/[^a-z0-9]+/gi, '-').replace(/^-|-$/g, '').toLowerCase()}`}
                            href={`/admin/docs-viewer?path=${encodeURIComponent(path)}`}
                            className={`rounded-lg px-3 py-2 text-sm ${requestedPath === path ? 'bg-[#1f6feb] text-white' : 'border border-[#30363d] bg-[#161b22] text-[#e6edf3] hover:bg-[#21262d]'}`}
                        >
                            {label}
                        </Link>
                    ))}
                </div>

                {loading ? (
                    <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-6 text-sm text-[#8b949e]">문서를 불러오는 중...</div>
                ) : error ? (
                    <div className="rounded-xl border border-[#f78166] bg-[rgba(247,129,102,0.12)] p-6 text-sm text-[#ffb3a7]">{error}</div>
                ) : (
                    <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-6">
                        <div className="mb-4 text-xs text-[#8b949e]">{documentData?.path} · {documentData?.size_bytes || 0} bytes</div>
                        <pre className="whitespace-pre-wrap break-words text-sm leading-7 text-[#e6edf3]">{documentData?.content || ''}</pre>
                    </div>
                )}
            </div>
        </div>
    );
}

export default function AdminDocsViewerPage() {
    return (
        <Suspense fallback={<div className="min-h-screen bg-[#0d1117] px-4 py-8 text-[#8b949e]">문서를 불러오는 중...</div>}>
            <AdminDocsViewerPageContent />
        </Suspense>
    );
}

import Link from 'next/link';
import { notFound } from 'next/navigation';

import { resolveApiBaseUrl } from '@/lib/api';

type EngineLanding = {
    title: string;
    summary: string;
    bundleKey: string;
};

const ENGINE_LANDING_MAP: Record<string, EngineLanding> = {
    document: {
        title: 'AI 문서작성 엔진',
        summary: '요구사항 문서, 제안서, 운영 문서 초안을 자동 생성하고 검토 흐름을 연결합니다.',
        bundleKey: 'document-writer-suite',
    },
    powerpoint: {
        title: 'AI 파워포인트 엔진',
        summary: '발표 목적에 맞춘 슬라이드 구성 preview와 최종 pptx 패키지 생성 흐름을 제공합니다.',
        bundleKey: 'powerpoint-deck-builder',
    },
};

type MarketplaceProjectDetail = {
    id: number;
    title: string;
    description?: string | null;
    price: number;
    downloads: number;
    rating: number;
    demo_url?: string | null;
    github_url?: string | null;
    image_url?: string | null;
    is_active: boolean;
    category?: {
        id: number;
        name: string;
        description?: string | null;
    } | null;
    tags?: Array<{ id: number; name: string }>;
};

function formatCurrency(value: number) {
    return new Intl.NumberFormat('ko-KR', {
        style: 'currency',
        currency: 'KRW',
        maximumFractionDigits: 0,
    }).format(Number(value || 0));
}

async function fetchProject(projectId: string): Promise<MarketplaceProjectDetail | null> {
    const apiBaseUrl = resolveApiBaseUrl();
    try {
        const response = await fetch(`${apiBaseUrl}/api/marketplace/projects/${encodeURIComponent(projectId)}`, {
            cache: 'no-store',
        });
        if (!response.ok) {
            return null;
        }
        return await response.json() as MarketplaceProjectDetail;
    } catch {
        return null;
    }
}

export default async function MarketplaceProjectDetailPage({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const { id } = await params;
    const engineLanding = ENGINE_LANDING_MAP[id];
    if (engineLanding) {
        return (
            <div className="min-h-screen bg-[#0b0f16] px-6 py-10 text-[#e6edf3]">
                <div className="mx-auto max-w-[1280px] space-y-6">
                    <div className="rounded-[28px] border border-[#30363d] bg-[#151b23] p-6">
                        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#58c9ff]">AI Engine</p>
                        <h1 className="mt-3 text-5xl font-bold text-white">{engineLanding.title}</h1>
                        <p className="mt-4 max-w-[960px] text-xl leading-relaxed text-[#aab4c0]">{engineLanding.summary}</p>
                        <div className="mt-6 flex flex-wrap gap-3">
                            <Link href="/marketplace" className="rounded-2xl border border-[#30363d] bg-[#11161d] px-5 py-3 text-base font-semibold text-white no-underline">
                                마켓으로 돌아가기
                            </Link>
                            <Link
                                href={`/marketplace/orchestrator?product=${encodeURIComponent(engineLanding.bundleKey)}&projectTitle=${encodeURIComponent(engineLanding.title)}&projectSummary=${encodeURIComponent(engineLanding.summary)}`}
                                className="rounded-2xl bg-[#2a7cff] px-5 py-3 text-base font-bold text-white no-underline"
                            >
                                이 엔진으로 주문 시작
                            </Link>
                        </div>
                    </div>
                </div>
            </div>
        );
    }
    const project = await fetchProject(id);

    if (!project) {
        notFound();
    }

    return (
        <div className="min-h-screen bg-[#0b0f16] px-6 py-10 text-[#e6edf3]">
            <div className="mx-auto max-w-[1280px] space-y-6">
                <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#58c9ff]">Marketplace Detail</p>
                        <h1 className="mt-3 text-5xl font-bold text-white">{project.title}</h1>
                        <p className="mt-4 max-w-[960px] text-xl leading-relaxed text-[#aab4c0]">
                            {project.description || '등록된 프로젝트 설명이 없습니다.'}
                        </p>
                    </div>
                    <div className="flex flex-wrap gap-3">
                        <Link href="/marketplace" className="rounded-2xl border border-[#30363d] bg-[#11161d] px-5 py-3 text-base font-semibold text-white no-underline">
                            목록으로 돌아가기
                        </Link>
                        <Link
                            href={`/marketplace/orchestrator?product=code-generator-deployment-kit&projectId=${project.id}&projectTitle=${encodeURIComponent(project.title)}&projectSummary=${encodeURIComponent(project.description || '')}`}
                            className="rounded-2xl bg-[#2a7cff] px-5 py-3 text-base font-bold text-white no-underline"
                        >
                            이 프로젝트로 주문하기
                        </Link>
                    </div>
                </div>

                <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
                    <section className="rounded-[28px] border border-[#30363d] bg-[#151b23] p-6">
                        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#58c9ff]">프로젝트 정보</p>
                        <div className="mt-5 grid gap-4 md:grid-cols-2">
                            <div className="rounded-2xl border border-[#25304a] bg-[#0f1523] p-4">
                                <p className="text-sm text-[#8b949e]">카테고리</p>
                                <p className="mt-2 text-lg font-semibold text-white">{project.category?.name || '미분류'}</p>
                            </div>
                            <div className="rounded-2xl border border-[#25304a] bg-[#0f1523] p-4">
                                <p className="text-sm text-[#8b949e]">가격</p>
                                <p className="mt-2 text-lg font-semibold text-[#f0b43f]">{formatCurrency(project.price)}</p>
                            </div>
                            <div className="rounded-2xl border border-[#25304a] bg-[#0f1523] p-4">
                                <p className="text-sm text-[#8b949e]">다운로드</p>
                                <p className="mt-2 text-lg font-semibold text-white">{project.downloads}</p>
                            </div>
                            <div className="rounded-2xl border border-[#25304a] bg-[#0f1523] p-4">
                                <p className="text-sm text-[#8b949e]">평점</p>
                                <p className="mt-2 text-lg font-semibold text-white">{Number(project.rating || 0).toFixed(1)}</p>
                            </div>
                        </div>
                        {!!project.tags?.length && (
                            <div className="mt-5 flex flex-wrap gap-2">
                                {project.tags.map((tag) => (
                                    <span key={`${project.id}-${tag.id}`} className="rounded-full border border-[#30363d] bg-[#0d1117] px-3 py-1.5 text-xs text-[#d2d9e3]">
                                        #{tag.name}
                                    </span>
                                ))}
                            </div>
                        )}
                    </section>

                    <section className="rounded-[28px] border border-[#30363d] bg-[#151b23] p-6">
                        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#58c9ff]">운영 연결</p>
                        <div className="mt-5 space-y-3 text-sm text-[#d2d9e3]">
                            <p>1. 상세 화면에서 프로젝트 설명과 가격, 카테고리, 태그를 확인합니다.</p>
                            <p>2. `이 프로젝트로 주문하기`를 누르면 프로젝트 제목/설명이 고객 오케스트레이터 주문 입력으로 자동 연결됩니다.</p>
                            <p>3. 주문 후 stage run, 실행 로그, 재시도 큐는 고객 오케스트레이터 화면에서 즉시 확인합니다.</p>
                        </div>
                        <div className="mt-5 flex flex-wrap gap-3">
                            {project.demo_url && (
                                project.demo_url.toLowerCase().endsWith('.apk')
                                  ? <a href={project.demo_url} download className="rounded-2xl px-5 py-2.5 text-sm font-bold text-white no-underline" style={{background:'#2a7cff',border:'none'}}>
                                        � APK 다운로드
                                    </a>
                                  : <a href={project.demo_url} target="_blank" rel="noreferrer" className="rounded-2xl border border-[#30363d] px-4 py-2.5 text-sm font-semibold text-white no-underline">
                                        데모 열기
                                    </a>
                            )}
                            {project.github_url && (
                                project.github_url.startsWith('/marketplace/')
                                  ? <a href={project.github_url} className="rounded-2xl px-5 py-2.5 text-sm font-bold no-underline" style={{background:'#31c45d22',color:'#31c45d',border:'1px solid #31c45d44'}}>
                                        🌐 웹에서 바로 사용
                                    </a>
                                  : <a href={project.github_url} target="_blank" rel="noreferrer" className="rounded-2xl border border-[#30363d] px-4 py-2.5 text-sm font-semibold text-white no-underline">
                                        GitHub 열기
                                    </a>
                            )}
                        </div>
                    </section>
                </div>
            </div>
        </div>
    );
}

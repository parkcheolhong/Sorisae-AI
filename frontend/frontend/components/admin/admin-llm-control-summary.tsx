'use client';

interface AdminLlmControlSummaryProps {
    llmPanelHeight: number;
}

const summaryCards = [
    {
        title: '핵심 런타임 제한',
        summary: '토큰, 단계 시간, 전체 작업 시간, 포렌식 출력량을 즉시 수정합니다.',
        accent: 'border-blue-200 bg-blue-50 text-blue-900',
    },
    {
        title: '대화/추론 보조',
        summary: '보충 질문, 근거 패널, 시스템 사고, 미래 기술 확장 강도를 나눠 관리합니다.',
        accent: 'border-emerald-200 bg-emerald-50 text-emerald-900',
    },
    {
        title: '기능별 모델 묶음',
        summary: '협업 대화, 추론, 코딩, 리뷰, 디자인 라우트를 기능별로 고정해 제어합니다.',
        accent: 'border-violet-200 bg-violet-50 text-violet-900',
    },
    {
        title: '실행 정책',
        summary: 'GPU/CPU 우선, num_gpu, num_thread 를 역할군별로 고정 패널에서 조정합니다.',
        accent: 'border-amber-200 bg-amber-50 text-amber-900',
    },
    {
        title: '전역 환경값',
        summary: '오케스트레이터 전역값과 identity provider 운영값을 같은 대시보드에서 확인·수정합니다.',
        accent: 'border-slate-200 bg-slate-50 text-slate-900',
    },
] as const;

export default function AdminLlmControlSummary({ llmPanelHeight }: AdminLlmControlSummaryProps) {
    return (
        <>
            <div className="mb-3 flex items-center justify-between">
                <div>
                    <h2 className="text-lg font-semibold text-gray-900">🤖 LLM 통합 제어 패널</h2>
                    <p className="mt-1 text-xs text-gray-500">앞으로 LLM runtime과 역할별 모델, 실행 정책, 오케스트레이터 전역값 조정은 이 관리자 대시보드 안에서 계속 관리합니다.</p>
                </div>
            </div>
            <div className="mb-4 grid gap-3 xl:grid-cols-5">
                {summaryCards.map((section) => (
                    <div key={section.title} className={`rounded-xl border px-4 py-3 ${section.accent}`}>
                        <p className="text-sm font-semibold">{section.title}</p>
                        <p className="mt-2 text-xs leading-5 opacity-90">{section.summary}</p>
                    </div>
                ))}
            </div>
            <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
                <iframe
                    src="/admin/llm?embedded=1"
                    title="LLM Admin Panel"
                    className="block w-full border-0"
                    style={{ height: `${llmPanelHeight}px` }}
                />
            </div>
        </>
    );
}

'use client';

type OrchestratorThreeTrackDiagramTone = 'admin' | 'customer';

interface OrchestratorThreeTrackDiagramProps {
    tone: OrchestratorThreeTrackDiagramTone;
    className?: string;
}

const toneClasses: Record<OrchestratorThreeTrackDiagramTone, {
    shell: string;
    track: string;
    arrow: string;
    caption: string;
}> = {
    admin: {
        shell: 'border-[#30363d] bg-[#0d1117]',
        track: 'border-[#244766] bg-[#132846] text-[#9ecbff]',
        arrow: 'text-[#58a6ff]',
        caption: 'text-[#8b949e]',
    },
    customer: {
        shell: 'border-slate-800 bg-slate-950/60',
        track: 'border-cyan-800/60 bg-cyan-950/30 text-cyan-200',
        arrow: 'text-cyan-400',
        caption: 'text-slate-400',
    },
};

export default function OrchestratorThreeTrackDiagram({
    tone,
    className = '',
}: OrchestratorThreeTrackDiagramProps) {
    const classes = toneClasses[tone];

    return (
        <div
            data-testid="orchestrator-three-track-diagram"
            className={`rounded-xl border px-4 py-3 ${classes.shell} ${className}`.trim()}
        >
            <p className={`text-[10px] font-semibold uppercase tracking-[0.16em] ${classes.caption}`}>
                3-track 실행 관계
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] font-semibold">
                <span className={`rounded-lg border px-3 py-2 ${classes.track}`}>
                    ① 주문하기 · `/run`
                </span>
                <span className={classes.arrow} aria-hidden="true">→</span>
                <span className={`rounded-lg border px-3 py-2 ${classes.track}`}>
                    ② 단계 카드 · 통과/보정
                </span>
                <span className={classes.arrow} aria-hidden="true">→</span>
                <span className={`rounded-lg border px-3 py-2 ${classes.track}`}>
                    ③ 협업 채팅 · discuss/execute
                </span>
            </div>
            <p className={`mt-2 text-[10px] leading-5 ${classes.caption}`}>
                주문은 파이프라인 실행, 단계 카드는 수동 승인, 채팅은 Live Flow · Decision Panel과 연동됩니다.
            </p>
        </div>
    );
}

'use client';

import * as React from 'react';

type OrchestratorDiscussBannerTone = 'admin' | 'customer';

interface OrchestratorDiscussBannerProps {
    tone: OrchestratorDiscussBannerTone;
    stageNumber?: number | null;
    className?: string;
}

const toneClasses: Record<OrchestratorDiscussBannerTone, string> = {
    admin: 'border-[#8957e5] bg-[#1f1630] text-[#e9d5ff]',
    customer: 'border-amber-500/40 bg-amber-950/30 text-amber-100',
};

export default function OrchestratorDiscussBanner({
    tone,
    stageNumber,
    className = '',
}: OrchestratorDiscussBannerProps) {
    const stageLabel = stageNumber !== null && stageNumber !== undefined
        ? `${stageNumber}단계`
        : '현재 단계';
    return (
        <div
            data-testid="orchestrator-discuss-banner"
            className={`rounded-xl border px-4 py-3 text-xs leading-5 ${toneClasses[tone]} ${className}`.trim()}
        >
            <p className="font-semibold">{stageLabel} 협업 Q&A 중</p>
            <p className="mt-1 opacity-90">
                아이디어·기술 제안은 대화로 이어가고, 코드 생성은 「N단계 진행해줘」로 시작하세요.
            </p>
        </div>
    );
}

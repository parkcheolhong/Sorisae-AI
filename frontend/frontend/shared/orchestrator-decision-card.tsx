'use client';

import * as React from 'react';
import { speakOrchestratorReply } from '@/lib/orchestrator-speech';
import { buildVoiceDecisionConfirmation } from '@/lib/orchestrator-voice-entry';

export type OrchestratorDecisionItem = {
    id: string;
    title: string;
    summary: string;
    category?: string;
    impactFiles?: string[];
    recommendedAction?: string;
    stageNumber?: number | null;
    source?: 'proposal' | 'technology' | 'next_action' | 'approval';
};

export type OrchestratorApprovalGate = {
    stageNumber?: number | null;
    hint?: string | null;
};

interface OrchestratorDecisionCardProps {
    tone: 'admin' | 'customer';
    item: OrchestratorDecisionItem;
    onApplyAndProceed: (item: OrchestratorDecisionItem) => void;
    onSaveIdeaOnly: (item: OrchestratorDecisionItem) => void;
    onRequestRevision: (item: OrchestratorDecisionItem) => void;
    disabled?: boolean;
}

export type OrchestratorEvidenceItem = {
    title: string;
    sourceLabel: string;
    whyItMatters: string;
    url?: string | null;
    trustScore?: number;
};

interface OrchestratorDecisionPanelProps {
    tone: 'admin' | 'customer';
    items: OrchestratorDecisionItem[];
    evidenceHighlights?: OrchestratorEvidenceItem[];
    approvalGate?: OrchestratorApprovalGate | null;
    onApplyAndProceed: (item: OrchestratorDecisionItem) => void;
    onSaveIdeaOnly: (item: OrchestratorDecisionItem) => void;
    onRequestRevision: (item: OrchestratorDecisionItem) => void;
    onApprovalProceed?: () => void;
    onApprovalRevise?: () => void;
    onApprovalReject?: () => void;
    disabled?: boolean;
    className?: string;
}

const toneClasses = {
    admin: {
        shell: 'border-[#30363d] bg-[#161b22]',
        card: 'border-[#244766] bg-[#0f1728]',
        title: 'text-[#9ecbff]',
        body: 'text-[#c9d1d9]',
        apply: 'border-[#238636] bg-[#12381f] text-[#9be9a8] hover:bg-[#1a4d2e]',
        save: 'border-[#8957e5] bg-[#1f1630] text-[#e9d5ff] hover:bg-[#2a1d45]',
        revise: 'border-[#d29922] bg-[#2d1f00] text-[#f2cc60] hover:bg-[#3d2a00]',
        approval: 'border-[#1f6feb] bg-[#132846] text-[#9ecbff]',
    },
    customer: {
        shell: 'border-slate-800 bg-slate-950/60',
        card: 'border-cyan-900/60 bg-slate-900/70',
        title: 'text-cyan-300',
        body: 'text-slate-200',
        apply: 'border-emerald-700 bg-emerald-950/50 text-emerald-200 hover:bg-emerald-900/40',
        save: 'border-violet-700 bg-violet-950/40 text-violet-200 hover:bg-violet-900/30',
        revise: 'border-amber-700 bg-amber-950/40 text-amber-200 hover:bg-amber-900/30',
        approval: 'border-cyan-700 bg-cyan-950/40 text-cyan-200',
    },
} as const;

function DecisionCardButtons({
    tone,
    item,
    onApplyAndProceed,
    onSaveIdeaOnly,
    onRequestRevision,
    disabled,
}: OrchestratorDecisionCardProps) {
    const classes = toneClasses[tone];
    const proceedLabel = item.stageNumber
        ? `반영하고 ${item.stageNumber}단계 진행`
        : '반영하고 진행';

    const handleApply = () => {
        void speakOrchestratorReply(buildVoiceDecisionConfirmation(item));
        onApplyAndProceed(item);
    };

    return (
        <div className="mt-3 flex flex-wrap gap-2">
            <button
                type="button"
                data-testid="orchestrator-decision-apply"
                disabled={disabled}
                onClick={handleApply}
                className={`rounded-lg border px-3 py-2 text-[11px] font-semibold transition disabled:opacity-50 ${classes.apply}`}
            >
                {proceedLabel}
            </button>
            <button
                type="button"
                data-testid="orchestrator-decision-save-idea"
                disabled={disabled}
                onClick={() => onSaveIdeaOnly(item)}
                className={`rounded-lg border px-3 py-2 text-[11px] font-semibold transition disabled:opacity-50 ${classes.save}`}
            >
                아이디어만 저장
            </button>
            <button
                type="button"
                data-testid="orchestrator-decision-revise"
                disabled={disabled}
                onClick={() => onRequestRevision(item)}
                className={`rounded-lg border px-3 py-2 text-[11px] font-semibold transition disabled:opacity-50 ${classes.revise}`}
            >
                수정 요청
            </button>
        </div>
    );
}

export function OrchestratorDecisionCard(props: OrchestratorDecisionCardProps) {
    const classes = toneClasses[props.tone];
    const { item } = props;

    return (
        <article
            data-testid="orchestrator-decision-card"
            className={`rounded-xl border px-4 py-3 ${classes.card}`}
        >
            <div className="flex flex-wrap items-start justify-between gap-2">
                <p className={`text-sm font-semibold ${classes.title}`}>{item.title}</p>
                {item.category && (
                    <span className="rounded-full border border-white/10 px-2 py-0.5 text-[10px] uppercase tracking-wide opacity-80">
                        {item.category}
                    </span>
                )}
            </div>
            <p className={`mt-2 text-xs leading-5 ${classes.body}`}>{item.summary}</p>
            {item.recommendedAction && (
                <p className="mt-2 text-[11px] text-white/60">권장: {item.recommendedAction}</p>
            )}
            {item.impactFiles && item.impactFiles.length > 0 && (
                <p className="mt-2 text-[10px] text-white/50">
                    영향 파일: {item.impactFiles.join(', ')}
                </p>
            )}
            <DecisionCardButtons {...props} />
        </article>
    );
}

export default function OrchestratorDecisionPanel({
    tone,
    items,
    evidenceHighlights = [],
    approvalGate,
    onApplyAndProceed,
    onSaveIdeaOnly,
    onRequestRevision,
    onApprovalProceed,
    onApprovalRevise,
    onApprovalReject,
    disabled = false,
    className = '',
}: OrchestratorDecisionPanelProps) {
    const classes = toneClasses[tone];
    const showApproval = Boolean(approvalGate);

    return (
        <section
            data-testid="orchestrator-decision-panel"
            className={`rounded-2xl border p-4 ${classes.shell} ${className}`.trim()}
        >
            <p className={`text-xs font-semibold uppercase tracking-[0.16em] ${classes.title}`}>
                개선 · 수정 확인
            </p>
            <p className="mt-1 text-[11px] opacity-80">
                제안을 반영할지, 아이디어만 남길지, 수정할지 선택하세요.
            </p>

            {evidenceHighlights.length > 0 && (
                <div
                    data-testid="orchestrator-decision-evidence"
                    className="mt-4 rounded-xl border border-white/10 px-4 py-3"
                >
                    <p className={`text-xs font-semibold uppercase tracking-[0.14em] ${classes.title}`}>
                        근거
                    </p>
                    <ul className="mt-2 space-y-2">
                        {evidenceHighlights.slice(0, 5).map((item) => (
                            <li key={`${item.title}-${item.sourceLabel}`} className="text-[11px] leading-5 opacity-90">
                                <p className={`font-semibold ${classes.title}`}>{item.title}</p>
                                <p className="opacity-80">{item.whyItMatters}</p>
                                <p className="mt-1 text-[10px] opacity-60">
                                    {item.sourceLabel}
                                    {typeof item.trustScore === 'number' ? ` · trust ${Math.round(item.trustScore * 100)}%` : ''}
                                </p>
                                {item.url && (
                                    <a
                                        href={item.url}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="mt-1 inline-block text-[10px] underline opacity-70"
                                    >
                                        {item.url}
                                    </a>
                                )}
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {!showApproval && items.length === 0 && evidenceHighlights.length === 0 && (
                <p
                    data-testid="orchestrator-decision-empty"
                    className="mt-3 rounded-xl border border-dashed border-white/10 px-3 py-3 text-[11px] opacity-70"
                >
                    협업 Q&A · 기술 제안 · 승인 게이트 응답이 오면 반영 / 저장 / 수정 버튼이 표시됩니다.
                </p>
            )}

            {showApproval && (
                <div
                    data-testid="orchestrator-approval-gate"
                    className={`mt-4 rounded-xl border px-4 py-3 ${classes.approval}`}
                >
                    <p className="text-sm font-semibold">승인 게이트</p>
                    <p className="mt-1 text-xs leading-5 opacity-90">
                        {approvalGate?.hint || '설계가 준비되었습니다. 코드 생성을 진행할까요?'}
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2">
                        <button
                            type="button"
                            data-testid="orchestrator-approval-proceed"
                            disabled={disabled}
                            onClick={() => onApprovalProceed?.()}
                            className={`rounded-lg border px-3 py-2 text-[11px] font-semibold ${classes.apply}`}
                        >
                            {approvalGate?.stageNumber
                                ? `${approvalGate.stageNumber}단계 진행해`
                                : '진행해'}
                        </button>
                        <button
                            type="button"
                            data-testid="orchestrator-approval-revise"
                            disabled={disabled}
                            onClick={() => onApprovalRevise?.()}
                            className={`rounded-lg border px-3 py-2 text-[11px] font-semibold ${classes.revise}`}
                        >
                            수정해
                        </button>
                        <button
                            type="button"
                            data-testid="orchestrator-approval-reject"
                            disabled={disabled}
                            onClick={() => onApprovalReject?.()}
                            className="rounded-lg border border-rose-800 bg-rose-950/40 px-3 py-2 text-[11px] font-semibold text-rose-200"
                        >
                            거절
                        </button>
                    </div>
                </div>
            )}

            {items.length > 0 && (
                <div className="mt-4 space-y-3">
                    {items.map((item) => (
                        <OrchestratorDecisionCard
                            key={item.id}
                            tone={tone}
                            item={item}
                            disabled={disabled}
                            onApplyAndProceed={onApplyAndProceed}
                            onSaveIdeaOnly={onSaveIdeaOnly}
                            onRequestRevision={onRequestRevision}
                        />
                    ))}
                </div>
            )}
        </section>
    );
}

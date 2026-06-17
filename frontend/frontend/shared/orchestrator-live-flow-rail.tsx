'use client';

import * as React from 'react';
import {
    LIVE_FLOW_STATUS_LABELS,
    isDiscussIntent,
    isDiscussLockedIntent,
    type LiveFlowAgentResult,
    type OrchestratorLiveFlowSnapshot,
} from '@/lib/orchestrator-live-flow';
import OrchestratorDiscussBanner from '@/shared/orchestrator-discuss-banner';

type OrchestratorLiveFlowRailTone = 'admin' | 'customer';

interface OrchestratorLiveFlowRailProps {
    tone: OrchestratorLiveFlowRailTone;
    snapshot: OrchestratorLiveFlowSnapshot;
    hintOverride?: string | null;
    className?: string;
}

const toneClasses: Record<OrchestratorLiveFlowRailTone, {
    shell: string;
    accent: string;
    chipPending: string;
    chipRunning: string;
    chipCompleted: string;
    chipApproval: string;
    chipDiscuss: string;
    chipFailed: string;
    agent: string;
}> = {
    admin: {
        shell: 'border-[#30363d] bg-[#0d1117]',
        accent: 'text-[#58a6ff]',
        chipPending: 'border-[#30363d] bg-[#161b22] text-[#8b949e]',
        chipRunning: 'border-[#1f6feb] bg-[#132846] text-[#9ecbff]',
        chipCompleted: 'border-[#238636] bg-[#12381f] text-[#9be9a8]',
        chipApproval: 'border-[#d29922] bg-[#2d1f00] text-[#f2cc60]',
        chipDiscuss: 'border-[#8957e5] bg-[#1f1630] text-[#e9d5ff]',
        chipFailed: 'border-[#da3633] bg-[#3d1214] text-[#ffb3ad]',
        agent: 'border-[#30363d] bg-[#161b22] text-[#c9d1d9]',
    },
    customer: {
        shell: 'border-slate-800 bg-slate-950/60',
        accent: 'text-cyan-300',
        chipPending: 'border-slate-700 bg-slate-900/70 text-slate-400',
        chipRunning: 'border-cyan-700 bg-cyan-950/40 text-cyan-200',
        chipCompleted: 'border-emerald-700 bg-emerald-950/40 text-emerald-200',
        chipApproval: 'border-amber-700 bg-amber-950/40 text-amber-200',
        chipDiscuss: 'border-violet-700 bg-violet-950/40 text-violet-200',
        chipFailed: 'border-rose-700 bg-rose-950/40 text-rose-200',
        agent: 'border-slate-700 bg-slate-900/70 text-slate-200',
    },
};

function chipClassName(status: OrchestratorLiveFlowSnapshot['stages'][number]['status'], tone: OrchestratorLiveFlowRailTone): string {
    const classes = toneClasses[tone];
    switch (status) {
        case 'completed':
            return classes.chipCompleted;
        case 'running':
            return classes.chipRunning;
        case 'awaiting_approval':
            return classes.chipApproval;
        case 'discuss':
            return classes.chipDiscuss;
        case 'failed':
            return classes.chipFailed;
        default:
            return classes.chipPending;
    }
}

function formatIntent(intent?: string | null): string {
    const normalized = String(intent || '').trim();
    if (!normalized) {
        return 'idle';
    }
    return normalized.replace(/_/g, ' ');
}

function renderAgentTimeline(agents: LiveFlowAgentResult[], tone: OrchestratorLiveFlowRailTone) {
    if (!agents.length) {
        return (
            <p className="text-[11px] opacity-80">
                에이전트 턴 대기 중 — 설계/진행/협업 명령을 입력하면 reasoner → planner → coder 흐름이 표시됩니다.
            </p>
        );
    }
    return (
        <div className="flex flex-wrap gap-2">
            {agents.map((item, index) => (
                <span
                    key={`${item.agent}-${index}`}
                    className={`rounded-full border px-2 py-1 text-[10px] ${toneClasses[tone].agent}`}
                >
                    {item.agent} · {item.status}
                </span>
            ))}
        </div>
    );
}

export default function OrchestratorLiveFlowRail({
    tone,
    snapshot,
    hintOverride,
    className = '',
}: OrchestratorLiveFlowRailProps) {
    const classes = toneClasses[tone];
    const discussMode = isDiscussIntent(snapshot.autonomousIntent);
    const discussLocked = Boolean(snapshot.discussLocked) || isDiscussLockedIntent(snapshot.autonomousIntent);
    const summaryHint = hintOverride
        || snapshot.stageCommandHint
        || (snapshot.requiresApproval
            ? '승인 또는 「진행해」로 다음 단계 코드 생성을 시작할 수 있습니다.'
            : '「설계해줘」 · 「N단계 진행해줘」 · 4단계+ 「아이디어/기술 제안」으로 진행하세요.');

    return (
        <section
            data-testid="orchestrator-live-flow-rail"
            className={`rounded-2xl border p-4 ${classes.shell} ${className}`.trim()}
        >
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <p className={`text-xs font-semibold uppercase tracking-[0.18em] ${classes.accent}`}>
                        Live Flow · 11 STAGE
                    </p>
                    <p className="mt-1 text-sm font-medium text-white/90">
                        {snapshot.stagesCompleted}/{snapshot.stagesTotal} 완료
                        {snapshot.stageNumber !== null && snapshot.stageNumber !== undefined
                            ? ` · ${snapshot.stageNumber}단계`
                            : ''}
                    </p>
                </div>
                <div className="flex flex-wrap gap-2 text-[10px]">
                    <span className={`rounded-full border px-2 py-1 ${classes.agent}`}>
                        core: {snapshot.orchestratorCore || 'legacy'}
                    </span>
                    <span className={`rounded-full border px-2 py-1 ${classes.agent}`}>
                        intent: {formatIntent(snapshot.autonomousIntent)}
                    </span>
                    {snapshot.stageCommand && (
                        <span className={`rounded-full border px-2 py-1 ${classes.agent}`}>
                            cmd: {snapshot.stageCommand}
                        </span>
                    )}
                    {snapshot.llmConnected !== null && snapshot.llmConnected !== undefined && (
                        <span className={`rounded-full border px-2 py-1 ${classes.agent}`}>
                            llm: {snapshot.llmConnected ? 'connected' : 'stub'}
                        </span>
                    )}
                    {snapshot.chatLoading && (
                        <span className={`rounded-full border px-2 py-1 ${classes.chipRunning}`}>
                            응답 수신 중…
                        </span>
                    )}
                    {snapshot.progressPolling && !snapshot.chatLoading && (
                        <span
                            data-testid="orchestrator-live-flow-progress-polling"
                            className={`rounded-full border px-2 py-1 ${classes.chipRunning}`}
                        >
                            실시간 갱신 중…
                        </span>
                    )}
                    {snapshot.activeSubstep && (
                        <span className={`rounded-full border px-2 py-1 ${classes.chipRunning}`}>
                            substep: {snapshot.activeSubstep}
                        </span>
                    )}
                    {snapshot.voiceEntry && (
                        <span
                            data-testid="orchestrator-live-flow-voice-entry"
                            className={`rounded-full border px-2 py-1 ${classes.chipDiscuss}`}
                        >
                            음성 입력{snapshot.voiceSpeaker ? ` · ${snapshot.voiceSpeaker}` : ''}
                        </span>
                    )}
                </div>
            </div>

            {discussLocked && (
                <div
                    data-testid="orchestrator-discuss-locked-banner"
                    className={`rounded-xl border px-4 py-3 text-xs leading-5 mt-4 ${tone === 'admin' ? 'border-[#d29922] bg-[#2d1f00] text-[#f2cc60]' : 'border-amber-600/50 bg-amber-950/30 text-amber-100'}`}
                >
                    {snapshot.stageCommandHint || '4단계부터 협업 Q&A·기술 제안이 가능합니다.'}
                </div>
            )}

            {discussMode && !discussLocked && (
                <OrchestratorDiscussBanner
                    tone={tone}
                    stageNumber={snapshot.stageNumber}
                    className="mt-4"
                />
            )}

            <div className="mt-4 overflow-x-auto pb-1">
                <div className="flex min-w-max gap-2">
                    {snapshot.stages.map((stage) => {
                        const active = stage.status !== 'pending';
                        const discussHighlight = discussMode && stage.status === 'discuss';
                        return (
                            <div
                                key={stage.id}
                                data-testid={discussHighlight ? 'orchestrator-live-flow-stage-discuss' : undefined}
                                className={`min-w-[88px] rounded-xl border px-2 py-2 text-center ${chipClassName(stage.status, tone)} ${active ? 'ring-1 ring-white/10' : ''} ${discussHighlight ? 'ring-2 ring-amber-400/70' : ''}`}
                                title={`${stage.id} · ${LIVE_FLOW_STATUS_LABELS[stage.status]}`}
                            >
                                <p className="text-[10px] font-semibold opacity-80">{stage.number}단계</p>
                                <p className="mt-1 text-[11px] font-medium leading-tight">{stage.label}</p>
                                <p className="mt-1 text-[9px] uppercase tracking-wide opacity-90">
                                    {LIVE_FLOW_STATUS_LABELS[stage.status]}
                                </p>
                            </div>
                        );
                    })}
                </div>
            </div>

            <div className="mt-4 grid gap-3 lg:grid-cols-[1fr_auto]">
                <div className="rounded-xl border border-white/5 bg-black/20 px-3 py-3">
                    <p className="text-[11px] font-semibold text-white/80">다음 안내</p>
                    <p className="mt-1 text-xs leading-5 text-white/75">{summaryHint}</p>
                    {(snapshot.executionState || snapshot.approvalState) && (
                        <p className="mt-2 text-[10px] text-white/50">
                            execution={snapshot.executionState || '-'} · approval={snapshot.approvalState || '-'}
                            {snapshot.progressUpdatedAt
                                ? ` · progress=${new Date(snapshot.progressUpdatedAt).toLocaleTimeString('ko-KR')}`
                                : ''}
                        </p>
                    )}
                </div>
                <div className="rounded-xl border border-white/5 bg-black/20 px-3 py-3 lg:min-w-[240px]">
                    <p className="text-[11px] font-semibold text-white/80">에이전트 타임라인</p>
                    <div className="mt-2">
                        {renderAgentTimeline(snapshot.agentResults, tone)}
                    </div>
                    {snapshot.substeps && snapshot.substeps.length > 0 && (
                        <div
                            data-testid="orchestrator-live-flow-substeps"
                            className="mt-3 space-y-1 border-t border-white/5 pt-2"
                        >
                            <p className="text-[10px] font-semibold text-white/70">substep</p>
                            {snapshot.substeps.slice(-4).map((step) => (
                                <p key={`${step.id}-${step.at || step.message}`} className="text-[10px] text-white/60">
                                    {step.id} · {step.status}
                                </p>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {snapshot.progressLogs && snapshot.progressLogs.length > 0 && (
                <div
                    data-testid="orchestrator-live-flow-progress-logs"
                    className="mt-4 rounded-xl border border-white/5 bg-black/20 px-3 py-3"
                >
                    <p className="text-[11px] font-semibold text-white/80">실시간 progress</p>
                    <ul className="mt-2 space-y-1">
                        {snapshot.progressLogs.slice(-3).map((log) => (
                            <li key={log.id} className="text-[10px] leading-5 text-white/65">
                                <span className="text-white/40">
                                    {log.timestamp
                                        ? new Date(log.timestamp).toLocaleTimeString('ko-KR')
                                        : '--:--'}
                                </span>
                                {' · '}
                                {log.message}
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </section>
    );
}

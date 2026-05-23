'use client';

import * as React from 'react';

export type SharedOrchestratorSubstep = {
    id: string;
    title: string;
    summary: string;
    sequence: number;
    status: 'pending' | 'running' | 'passed' | 'failed' | 'manual_correction';
    check_label: string;
    idea_template?: string;
    edit_template?: string;
    note?: string;
    updated_at?: string;
    checked?: boolean;
    revision_history?: Array<{
        at: string;
        status: string;
        note: string;
    }>;
};

export type SharedOrchestratorStageBox = {
    id: string;
    label: string;
    title: string;
    summary: string;
    sequence: number;
    status: 'pending' | 'running' | 'passed' | 'failed' | 'manual_correction';
    check_label: string;
    note?: string;
    manual_correction?: string;
    updated_at?: string;
    substeps?: SharedOrchestratorSubstep[];
};

export type SharedOrchestratorStageRun = {
    run_id: string;
    scope: string;
    project_name: string;
    mode: string;
    semi_auto_step_count?: number;
    semi_auto_mode?: string;
    command_modes?: string[];
    collaboration_modes?: string[];
    status: string;
    current_stage_id: string;
    final_completed: boolean;
    stages: SharedOrchestratorStageBox[];
};

export type SharedOrchestratorConversationMessage = {
    role: string;
    content: string;
    speaker?: string | null;
    timestamp?: string | null;
    step_title?: string | null;
};

interface OrchestratorStageCardPanelProps {
    tone: 'customer' | 'admin';
    title: string;
    description: string;
    stageRun: SharedOrchestratorStageRun | null;
    stageNoteDraft: string;
    onStageNoteDraftChange: (value: string) => void;
    substepChecks: Record<string, boolean>;
    onSubstepChecksChange: (next: Record<string, boolean>) => void;
    revisionNote: string;
    onRevisionNoteChange: (value: string) => void;
    stageUpdateLoading?: boolean;
    onMarkPassed?: () => void;
    onMarkManualCorrection?: () => void;
    onMarkFailed?: () => void;
    onRefresh?: () => void;
    ideaPresets?: string[];
    onApplyIdeaPreset?: (preset: string) => void;
    onRunOperationalVerification?: () => void;
    operationalVerificationLabel?: string;
    commandRules?: string[];
    conversation?: SharedOrchestratorConversationMessage[];
    chatInput?: string;
    onChatInputChange?: (value: string) => void;
    chatLoading?: boolean;
    onSubmitChat?: () => void;
}

const toneClasses = {
    customer: {
        shell: 'border-slate-800 bg-slate-950/60',
        accent: 'text-cyan-300',
        subPanel: 'border-cyan-900/60 bg-slate-900/70',
        sidePanel: 'border-violet-900/60 bg-slate-900/70',
        preset: 'border border-cyan-800 bg-cyan-950/30 text-cyan-200',
    },
    admin: {
        shell: 'border-[#30363d] bg-[#161b22]',
        accent: 'text-[#79c0ff]',
        subPanel: 'border-[#1f6feb] bg-[#0f2747]',
        sidePanel: 'border-[#8957e5] bg-[#1f1630]',
        preset: 'border border-[#1f6feb] bg-[rgba(31,111,235,0.16)] text-[#9ecbff]',
    },
} as const;

const substepStateClassName = (status: SharedOrchestratorSubstep['status'], tone: 'customer' | 'admin') => {
    if (tone === 'admin') {
        if (status === 'passed') return 'border-[#238636] bg-[rgba(35,134,54,0.16)] text-[#9be9a8]';
        if (status === 'manual_correction') return 'border-[#d29922] bg-[rgba(210,153,34,0.18)] text-[#f2cc60]';
        if (status === 'running') return 'border-[#1f6feb] bg-[rgba(31,111,235,0.16)] text-[#9ecbff]';
        if (status === 'failed') return 'border-[#da3633] bg-[rgba(218,54,51,0.18)] text-[#ffb3ad]';
        return 'border-[#30363d] bg-[#0d1117] text-[#c9d1d9]';
    }
    if (status === 'passed') return 'border-emerald-700 bg-emerald-950/20 text-emerald-100';
    if (status === 'manual_correction') return 'border-amber-600 bg-amber-950/20 text-amber-100';
    if (status === 'running') return 'border-cyan-600 bg-cyan-950/20 text-cyan-100';
    if (status === 'failed') return 'border-red-700 bg-red-950/20 text-red-100';
    return 'border-slate-800 bg-slate-950 text-slate-300';
};

export default function OrchestratorStageCardPanel({
    tone,
    title,
    description,
    stageRun,
    stageNoteDraft,
    onStageNoteDraftChange,
    substepChecks,
    onSubstepChecksChange,
    revisionNote,
    onRevisionNoteChange,
    stageUpdateLoading,
    onMarkPassed,
    onMarkManualCorrection,
    onMarkFailed,
    onRefresh,
    ideaPresets = [],
    onApplyIdeaPreset,
    onRunOperationalVerification,
    operationalVerificationLabel = '운영 API 실검증',
    commandRules = [],
    conversation = [],
    chatInput = '',
    onChatInputChange,
    chatLoading,
    onSubmitChat,
}: OrchestratorStageCardPanelProps) {
    const palette = toneClasses[tone];
    const fieldIdPrefix = React.useId().replace(/:/g, '');
    const textareaToneClassName = tone === 'admin'
        ? 'border-slate-700 !bg-slate-900 !text-slate-100 caret-slate-100 placeholder:!text-slate-400'
        : 'border-slate-700 !bg-white !text-slate-900 caret-slate-900 placeholder:!text-slate-600';
    const textareaToneStyle = tone === 'admin'
        ? {
            color: '#f8fafc',
            backgroundColor: '#111827',
            borderColor: '#334155',
            caretColor: '#f8fafc',
            colorScheme: 'dark' as const,
            WebkitTextFillColor: '#f8fafc',
        }
        : {
            color: '#0f172a',
            backgroundColor: '#ffffff',
            borderColor: '#334155',
            caretColor: '#0f172a',
            colorScheme: 'light' as const,
            WebkitTextFillColor: '#0f172a',
        };
    const activeStage = React.useMemo(() => (stageRun?.stages || []).find((stage) => stage.id === stageRun?.current_stage_id) || null, [stageRun]);
    const nextStageCard = React.useMemo(() => {
        const stages = stageRun?.stages || [];
        const currentIndex = stages.findIndex((stage) => stage.id === stageRun?.current_stage_id);
        if (currentIndex < 0) return null;
        return stages[currentIndex + 1] || null;
    }, [stageRun]);
    const activeSubsteps = activeStage?.substeps || [];
    const stageRunFieldPrefix = `${fieldIdPrefix}-${stageRun?.run_id || 'stage-panel'}`;
    const revisionNoteFieldId = `${stageRunFieldPrefix}-revision-note`;
    const stageChatInputFieldId = `${stageRunFieldPrefix}-chat-input`;
    const stageNoteFieldId = `${stageRunFieldPrefix}-stage-note`;
    const activeIdeaTemplate = activeSubsteps.find((item) => item.status === 'running')?.idea_template || activeSubsteps[0]?.idea_template || '';
    const activeEditTemplate = activeSubsteps.find((item) => item.status === 'manual_correction')?.edit_template || activeSubsteps[0]?.edit_template || '';
    const activeRevisionHistory = activeSubsteps.reduce<Array<{ at: string; status: string; note: string }>>((acc, item) => {
        const history = item.revision_history || [];
        history.forEach((entry) => acc.push(entry));
        return acc;
    }, []).slice(-10).reverse();
    const activePassedCount = activeSubsteps.filter((item) => item.status === 'passed').length;
    const activeCheckedCount = activeSubsteps.filter((item) => Boolean(substepChecks[item.id] ?? item.checked)).length;

    React.useEffect(() => {
        const checks = activeSubsteps.reduce<Record<string, boolean>>((acc, item) => {
            acc[item.id] = Boolean(item.checked);
            return acc;
        }, {});
        const existingKeys = Object.keys(substepChecks);
        const nextKeys = Object.keys(checks);
        const sameShape = existingKeys.length === nextKeys.length && nextKeys.every((key) => key in substepChecks);
        const sameValues = sameShape && nextKeys.every((key) => Boolean(substepChecks[key]) === Boolean(checks[key]));

        if (!sameValues) {
            onSubstepChecksChange(checks);
        }
    }, [activeStage?.id, activeSubsteps, onSubstepChecksChange, substepChecks]);

    return (
        <div className={`rounded-2xl border p-4 space-y-4 ${palette.shell}`}>
            <div className="flex items-center justify-between gap-3 flex-wrap">
                <div>
                    <p className={`text-sm font-semibold ${palette.accent}`}>{title}</p>
                    <p className="text-xs text-slate-400">{description}</p>
                </div>
                {stageRun?.final_completed && <span className="rounded-full border border-emerald-500/40 bg-emerald-500/10 px-3 py-1 text-xs text-emerald-300">완료</span>}
            </div>
            {activeStage && (
                <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
                    <div className={`rounded-xl border p-4 space-y-3 ${palette.subPanel}`}>
                        <div className="flex items-start justify-between gap-3">
                            <div>
                                <p className={`text-xs ${palette.accent}`}>현재 진행 카드</p>
                                <p className="mt-1 text-lg font-semibold text-white">{activeStage.label} · {activeStage.title}</p>
                                <p className="mt-2 text-sm text-slate-300">{activeStage.summary}</p>
                                <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
                                    <span className="rounded-full border border-slate-700 bg-slate-950 px-3 py-1 text-slate-200">구현 통과 {activePassedCount}/{activeSubsteps.length || 0}</span>
                                    <span className="rounded-full border border-slate-700 bg-slate-950 px-3 py-1 text-slate-200">체크 완료 {activeCheckedCount}/{activeSubsteps.length || 0}</span>
                                    <span className="rounded-full border border-slate-700 bg-slate-950 px-3 py-1 text-slate-200">최종 상태 {activeStage.status}</span>
                                </div>
                            </div>
                            <span className="rounded-full border border-cyan-700/60 bg-cyan-950/40 px-3 py-1 text-[11px] text-cyan-200">{activeStage.check_label}</span>
                        </div>
                        {activeSubsteps.length > 0 && (
                            <div className="grid gap-2 md:grid-cols-2">
                                {activeSubsteps.map((substep) => {
                                    const substepCheckboxId = `${stageRunFieldPrefix}-substep-${substep.id}-check`;
                                    return (
                                    <div key={substep.id} className={`rounded-xl border px-3 py-3 text-xs ${substepStateClassName(substep.status, tone)}`}>
                                        <div className="flex items-center justify-between gap-2">
                                            <span className="font-semibold">{substep.id}</span>
                                            <span>{substep.check_label}</span>
                                        </div>
                                        <p className="mt-2 text-sm font-medium">{substep.title}</p>
                                        <p className="mt-1 text-[11px] opacity-90">{substep.summary}</p>
                                        <div className="mt-2 flex flex-wrap gap-2 text-[10px]">
                                            <span className="rounded-full border border-slate-700 bg-slate-950 px-2 py-1">상태 {substep.status}</span>
                                            <span className="rounded-full border border-slate-700 bg-slate-950 px-2 py-1">체크 {Boolean(substepChecks[substep.id] ?? substep.checked) ? '완료' : '대기'}</span>
                                        </div>
                                        <label htmlFor={substepCheckboxId} className="mt-3 flex items-center gap-2 text-[11px]">
                                            <input id={substepCheckboxId} name={substepCheckboxId} type="checkbox" checked={Boolean(substepChecks[substep.id] ?? substep.checked)} onChange={(e) => onSubstepChecksChange({ ...substepChecks, [substep.id]: e.target.checked })} />
                                            이 카드 통과 체크
                                        </label>
                                    </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                    <div className={`rounded-xl border p-4 space-y-3 text-xs text-slate-200 ${palette.sidePanel}`}>
                        <p className={`text-sm font-semibold ${palette.accent}`}>다음 카드 / 아이디어 템</p>
                        <div className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-3">
                            <p className="text-[11px] text-slate-400">다음 추천 카드</p>
                            <p className="mt-1 font-semibold text-white">{nextStageCard ? `${nextStageCard.label} · ${nextStageCard.title}` : 'END'}</p>
                            <p className="mt-1 text-slate-400">{nextStageCard?.summary || '모든 카드가 통과되면 완료입니다.'}</p>
                        </div>
                        <div className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-3 space-y-2">
                            <p className={`font-semibold ${palette.accent}`}>아이디어 추가 템플릿</p>
                            <p className="whitespace-pre-wrap">{activeIdeaTemplate || '현재 카드에 맞는 아이디어 템플릿이 자동 표시됩니다.'}</p>
                            {ideaPresets.length > 0 && (
                                <div className="space-y-2 pt-1 text-[11px] text-slate-300">
                                    {ideaPresets.map((preset, index) => (
                                        <div key={preset} className={`rounded-lg px-3 py-2 ${palette.preset}`}>
                                            <p className="font-semibold">/preset {index + 1}</p>
                                            <p className="mt-1 whitespace-pre-wrap">{preset}</p>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                        <div className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-3 space-y-2">
                            <p className="font-semibold text-amber-300">수정 템플릿</p>
                            <p className="whitespace-pre-wrap">{activeEditTemplate || '수정 필요 상태가 되면 이 영역에 보정 템플릿을 사용하세요.'}</p>
                        </div>
                        <div className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-3 space-y-2">
                            <label htmlFor={revisionNoteFieldId} className="font-semibold text-slate-100">수정 이력 메모</label>
                            <textarea id={revisionNoteFieldId} name="revisionNote" value={revisionNote} onChange={(e) => onRevisionNoteChange(e.target.value)} rows={3} placeholder="이번 카드에서 수정한 내용, 아이디어 추가, 보정 이유를 기록하세요." className={`w-full rounded-lg px-3 py-2 text-xs ${textareaToneClassName}`} style={textareaToneStyle} />
                        </div>
                        <div className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-3 space-y-2">
                            <p className="font-semibold text-slate-100">운영 API 실검증</p>
                            <p>{operationalVerificationLabel}</p>
                            <p className="text-[11px] text-slate-400">Enter 입력창에서 `/verify` 로 실행합니다.</p>
                            {onRunOperationalVerification && (
                                <button
                                    type="button"
                                    onClick={onRunOperationalVerification}
                                    className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-[11px] font-semibold text-slate-100 hover:bg-slate-800"
                                >
                                    운영 API 실검증 실행
                                </button>
                            )}
                        </div>
                        <div className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-3 space-y-2">
                            <p className="font-semibold text-slate-100">단계별 방향 지시 규칙</p>
                            <div className="space-y-2 text-[11px] text-slate-300">
                                {(commandRules.length > 0 ? commandRules : [
                                    '일반 질문/명령은 그대로 입력하고 Enter로 전송합니다.',
                                    '`/run`은 현재 지시문 기준 실행, `/pass`는 현재 단계 통과, `/fix`는 수동 보정, `/fail`은 미통과 처리입니다.',
                                    '`/verify`는 운영 API 실검증, `/preset 번호`는 아이디어 프리셋을 현재 수정 메모에 반영합니다.',
                                    '`/search`, `/news`, `/ask`, `/revise`, `/resume` 으로 검색/뉴스/동료대화/중간설계변경/재개를 같은 패널에서 이어갑니다.',
                                ]).map((rule) => (<p key={rule}>• {rule}</p>))}
                            </div>
                        </div>
                        <div className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-3 space-y-2">
                            <p className="font-semibold text-slate-100">멀티 협업 대화</p>
                            <div className="max-h-56 overflow-y-auto space-y-2 pr-1 text-[11px] text-slate-300">
                                {conversation.length === 0 ? (
                                    <p>아직 대화가 없습니다. `/ask`, `/search`, `/news`, `/revise` 명령으로 바로 협업을 시작하세요.</p>
                                ) : conversation.slice(-8).map((message, index) => (
                                    <div key={`${message.timestamp || 'msg'}-${index}`} className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-2">
                                        <p className="font-semibold text-slate-100">{message.speaker || message.role}</p>
                                        {message.step_title && <p className="text-[10px] text-slate-400">{message.step_title}</p>}
                                        <p className="mt-1 whitespace-pre-wrap">{message.content}</p>
                                    </div>
                                ))}
                            </div>
                            {onChatInputChange && (
                                <textarea
                                    id={stageChatInputFieldId}
                                    name="stageChatInput"
                                    aria-label="멀티 협업 대화 입력"
                                    value={chatInput}
                                    onChange={(e) => onChatInputChange(e.target.value)}
                                    onKeyDown={async (event) => {
                                        if ((event.nativeEvent as KeyboardEvent).isComposing) {
                                            return;
                                        }
                                        if (!onSubmitChat || event.key !== 'Enter' || event.shiftKey) {
                                            return;
                                        }
                                        event.preventDefault();
                                        await onSubmitChat();
                                    }}
                                    rows={3}
                                    placeholder="예: /ask 이 단계 구조를 바꿔야 하나요? /search FastAPI background task pattern /revise 현재 엔진 계약을 주문 승인형으로 변경"
                                    className={`w-full rounded-lg px-3 py-2 text-xs ${textareaToneClassName}`}
                                    style={textareaToneStyle}
                                />
                            )}
                            {onSubmitChat && (
                                <p className="text-[11px] text-slate-400">Enter 실행 · Shift+Enter 줄바꿈</p>
                            )}
                            {onSubmitChat && (
                                <button
                                    type="button"
                                    onClick={onSubmitChat}
                                    disabled={Boolean(chatLoading)}
                                    className="rounded-lg border border-violet-700 bg-violet-950/20 px-3 py-2 text-[11px] font-semibold text-violet-100 disabled:opacity-50"
                                >
                                    {chatLoading ? '대화 처리 중...' : '협업 대화 전송'}
                                </button>
                            )}
                        </div>
                        <div className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-3 space-y-1">
                            <p>현재 카드를 통과시키면 stage run이 다음 카드로 자동 이동합니다.</p>
                            <p>버튼 한 번 전체 실행이 아니라 카드 단위 수동 승인 + 자동 다음 단계 연결 구조입니다.</p>
                        </div>
                        {activeRevisionHistory.length > 0 && (
                            <div className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-3 space-y-2">
                                <p className={`font-semibold ${palette.accent}`}>최근 수정 이력</p>
                                {activeRevisionHistory.map((item, index) => (
                                    <div key={`${item.at}-${index}`} className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-[11px] text-slate-300">
                                        <p>{item.at} · {item.status}</p>
                                        <p className="mt-1 whitespace-pre-wrap text-slate-100">{item.note}</p>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}
            {!activeStage && (onChatInputChange || onSubmitChat) && (
                <div className={`rounded-xl border p-4 space-y-3 text-xs ${palette.sidePanel}`}>
                    <p className={`text-sm font-semibold ${palette.accent}`}>대화형 터미널 실행</p>
                    <p className="text-[11px] text-slate-300">
                        현재 진행 카드가 없어도 협업 대화를 먼저 실행할 수 있습니다. Enter 또는 실행 버튼으로 전송하면, 답변은 바로 아래 출력창에 누적됩니다.
                    </p>
                    <div className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-3 space-y-2">
                        <p className="font-semibold text-slate-100">대화 내용 출력 (AI 답변 포함)</p>
                        <div className="max-h-56 overflow-y-auto space-y-2 pr-1 text-[11px] text-slate-300">
                            {conversation.length === 0 ? (
                                <p>아직 대화가 없습니다. 입력창에서 질문/명령을 보내면 이 영역에 대화가 누적됩니다.</p>
                            ) : conversation.slice(-8).map((message, index) => (
                                <div key={`${message.timestamp || 'msg'}-${index}`} className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-2">
                                    <p className="font-semibold text-slate-100">{message.speaker || message.role}</p>
                                    {message.step_title && <p className="text-[10px] text-slate-400">{message.step_title}</p>}
                                    <p className="mt-1 whitespace-pre-wrap">{message.content}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                    {onChatInputChange && (
                        <textarea
                            id={stageChatInputFieldId}
                            name="stageChatInput"
                            aria-label="대화형 터미널 입력"
                            value={chatInput}
                            onChange={(e) => onChatInputChange(e.target.value)}
                            onKeyDown={async (event) => {
                                if ((event.nativeEvent as KeyboardEvent).isComposing) {
                                    return;
                                }
                                if (!onSubmitChat || event.key !== 'Enter' || event.shiftKey) {
                                    return;
                                }
                                event.preventDefault();
                                await onSubmitChat();
                            }}
                            rows={3}
                            placeholder="예: /ask 현재 단계가 비어있을 때 먼저 무엇을 점검하면 좋을까요?"
                            className={`w-full rounded-lg px-3 py-2 text-xs ${textareaToneClassName}`}
                            style={textareaToneStyle}
                        />
                    )}
                    {onSubmitChat && (
                        <button
                            type="button"
                            onClick={onSubmitChat}
                            disabled={Boolean(chatLoading)}
                            className="rounded-lg border border-violet-700 bg-violet-950/20 px-3 py-2 text-[11px] font-semibold text-violet-100 disabled:opacity-50"
                        >
                            {chatLoading ? '대화 처리 중...' : '실행하기'}
                        </button>
                    )}
                    {onSubmitChat && <p className="text-[11px] text-slate-400">Enter 실행 · Shift+Enter 줄바꿈</p>}
                </div>
            )}
            {activeStage && (
                <>
                    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                        {(stageRun?.stages || []).map((stage) => (
                            <div key={stage.id} className={`rounded-xl border px-4 py-4 text-sm ${stage.status === 'passed' ? 'border-emerald-700 bg-emerald-950/20' : stage.status === 'failed' ? 'border-red-700 bg-red-950/20' : stage.status === 'manual_correction' ? 'border-amber-600 bg-amber-950/20' : stage.status === 'running' ? 'border-cyan-700 bg-cyan-950/20' : 'border-slate-800 bg-slate-900/60'}`}>
                                <div className="flex items-center justify-between gap-3">
                                    <span className={`text-xs font-semibold ${palette.accent}`}>{stage.label}</span>
                                    <span className="text-[11px] text-slate-300">{stage.check_label}</span>
                                </div>
                                <p className="mt-2 font-semibold text-white">{stage.title}</p>
                                <p className="mt-2 text-xs text-slate-400">{stage.summary}</p>
                                <p className="mt-2 text-[11px] text-slate-300">통과 마크 {(stage.substeps || []).filter((item) => item.status === 'passed').length}/{(stage.substeps || []).length}</p>
                                <p className="mt-1 text-[11px] text-slate-300">체크 마크 {(stage.substeps || []).filter((item) => Boolean(substepChecks[item.id] ?? item.checked)).length}/{(stage.substeps || []).length}</p>
                                {(stage.note || stage.manual_correction) && <p className="mt-2 text-xs text-slate-300 whitespace-pre-wrap">{stage.manual_correction || stage.note}</p>}
                            </div>
                        ))}
                    </div>
                    <label htmlFor={stageNoteFieldId} className="sr-only">현재 카드 메모</label>
                    <textarea id={stageNoteFieldId} name="stageNoteDraft" value={stageNoteDraft} onChange={(e) => onStageNoteDraftChange(e.target.value)} rows={3} placeholder="현재 카드에 대한 방향 지시, 수정 지시, 실패 이유, 보정 메모를 적으세요. Enter 입력창 명령과 함께 stage note로 기록됩니다." className={`w-full rounded-xl px-4 py-3 text-sm ${textareaToneClassName}`} style={textareaToneStyle} />
                    {(onMarkPassed || onMarkManualCorrection || onMarkFailed || onRefresh || onApplyIdeaPreset) && (
                        <div className="flex flex-wrap gap-2">
                            {onMarkPassed && (
                                <button
                                    type="button"
                                    onClick={onMarkPassed}
                                    disabled={stageUpdateLoading}
                                    className="rounded-lg border border-emerald-700 bg-emerald-950/20 px-3 py-2 text-xs font-semibold text-emerald-100 disabled:opacity-50"
                                >
                                    /pass 통과 처리
                                </button>
                            )}
                            {onMarkManualCorrection && (
                                <button
                                    type="button"
                                    onClick={onMarkManualCorrection}
                                    disabled={stageUpdateLoading}
                                    className="rounded-lg border border-amber-600 bg-amber-950/20 px-3 py-2 text-xs font-semibold text-amber-100 disabled:opacity-50"
                                >
                                    /fix 보정 처리
                                </button>
                            )}
                            {onMarkFailed && (
                                <button
                                    type="button"
                                    onClick={onMarkFailed}
                                    disabled={stageUpdateLoading}
                                    className="rounded-lg border border-red-700 bg-red-950/20 px-3 py-2 text-xs font-semibold text-red-100 disabled:opacity-50"
                                >
                                    /fail 미통과 처리
                                </button>
                            )}
                            {onRefresh && (
                                <button
                                    type="button"
                                    onClick={onRefresh}
                                    disabled={stageUpdateLoading}
                                    className="rounded-lg border border-cyan-700 bg-cyan-950/20 px-3 py-2 text-xs font-semibold text-cyan-100 disabled:opacity-50"
                                >
                                    /verify 새로고침
                                </button>
                            )}
                            {onApplyIdeaPreset && ideaPresets.length > 0 && ideaPresets.map((preset, index) => (
                                <button
                                    key={`${preset}-${index}`}
                                    type="button"
                                    onClick={() => onApplyIdeaPreset(preset)}
                                    className="rounded-lg border border-violet-700 bg-violet-950/20 px-3 py-2 text-xs font-semibold text-violet-100"
                                >
                                    /preset {index + 1}
                                </button>
                            ))}
                        </div>
                    )}
                </>
            )}
            <div className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-xs text-slate-300 space-y-1">
                {activeStage ? (
                    <>
                        <p>버튼식 처리 대신 Enter 명령형 규칙을 사용합니다.</p>
                        <p>`/pass`, `/fix`, `/fail`, `/verify`, `/preset 번호` 명령을 입력창에 적고 Enter를 누르세요.</p>
                    </>
                ) : (
                    <>
                        <p>현재 진행 카드가 없어 명령형 Enter 규칙은 대기 상태입니다.</p>
                        <p>위 대화형 터미널 실행 입력창에서 먼저 질문/명령을 전송하거나 단계 카드를 시작하세요.</p>
                    </>
                )}
                {stageUpdateLoading && <p>현재 stage 처리 중...</p>}
                {!stageUpdateLoading && stageRun?.run_id && <p>상태 새로고침은 `/verify` 또는 상단 명령 입력으로 수행합니다.</p>}
                {onRefresh && <p className="text-slate-400">새로고침 훅 연결됨</p>}
            </div>
        </div>
    );
}

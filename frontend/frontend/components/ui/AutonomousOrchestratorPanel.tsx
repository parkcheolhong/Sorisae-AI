'use client';

import { useCallback, useMemo, useState } from 'react';
import {
    getAutonomousSessionStatus,
    postAutonomousChat,
    type AutonomousChatResponse,
    type AutonomousExecutionMode,
} from '@/lib/autonomous-orchestrator-client';

type ChatLine = {
    id: string;
    role: 'user' | 'assistant' | 'system';
    text: string;
    intent?: string;
};

type AutonomousOrchestratorPanelProps = {
    apiBaseUrl: string;
    getAccessToken: () => string;
};

const MODE_OPTIONS: Array<{ id: AutonomousExecutionMode; label: string; hint: string }> = [
    { id: 'advisory', label: '조언', hint: '설계·분석만 (코드 실행 없음)' },
    { id: 'semi_auto', label: '반자동', hint: '코드 생성 전 승인 필요' },
    { id: 'full_auto', label: '완전자동', hint: '승인 없이 coder→validator 실행' },
];

export default function AutonomousOrchestratorPanel({
    apiBaseUrl,
    getAccessToken,
}: AutonomousOrchestratorPanelProps) {
    const [mode, setMode] = useState<AutonomousExecutionMode>('semi_auto');
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [message, setMessage] = useState('');
    const [lines, setLines] = useState<ChatLine[]>([]);
    const [lastResponse, setLastResponse] = useState<AutonomousChatResponse | null>(null);
    const [sessionSummary, setSessionSummary] = useState<string>('');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const requiresApproval = Boolean(lastResponse?.requires_approval);

    const statusLabel = useMemo(() => {
        if (!lastResponse) {
            return '대기';
        }
        const llmLabel = lastResponse.llm_connected ? 'LLM 연결' : 'LLM 스텁(GPU 검증 필요)';
        return `${lastResponse.execution_state} · 승인=${lastResponse.approval_state} · ${llmLabel}`;
    }, [lastResponse]);

    const pushLine = useCallback((line: Omit<ChatLine, 'id'>) => {
        setLines((prev) => [...prev, { ...line, id: `${Date.now()}-${prev.length}` }]);
    }, []);

    const refreshSession = useCallback(async (activeSessionId: string) => {
        const token = getAccessToken();
        if (!token) {
            return;
        }
        const status = await getAutonomousSessionStatus(apiBaseUrl, token, activeSessionId);
        setSessionSummary(
            `STAGE ${status.stages.filter((s) => s.status === 'completed').length}/${status.stages.length} · `
            + `대화 ${status.conversation_length} · 에이전트 ${status.agent_result_count}`,
        );
    }, [apiBaseUrl, getAccessToken]);

    const sendMessage = useCallback(async (text: string) => {
        const trimmed = text.trim();
        if (!trimmed || busy) {
            return;
        }
        const token = getAccessToken();
        if (!token) {
            setError('관리자 토큰이 없습니다. 다시 로그인해 주세요.');
            return;
        }

        setBusy(true);
        setError(null);
        pushLine({ role: 'user', text: trimmed });

        try {
            const response = await postAutonomousChat(apiBaseUrl, token, {
                message: trimmed,
                session_id: sessionId,
                mode,
            });
            setSessionId(response.session_id);
            setLastResponse(response);
            pushLine({
                role: 'assistant',
                text: response.content,
                intent: response.intent,
            });
            await refreshSession(response.session_id);
        } catch (sendError: unknown) {
            const messageText = sendError instanceof Error ? sendError.message : String(sendError);
            setError(messageText);
            pushLine({ role: 'system', text: `오류: ${messageText}` });
        } finally {
            setBusy(false);
            setMessage('');
        }
    }, [apiBaseUrl, busy, getAccessToken, mode, pushLine, refreshSession, sessionId]);

    const handleSubmit = useCallback(async (event: React.FormEvent) => {
        event.preventDefault();
        await sendMessage(message);
    }, [message, sendMessage]);

    return (
        <section
            className="rounded-xl border border-[#30363d] bg-[#161b22] p-5"
            data-testid="admin-autonomous-orchestrator-panel"
        >
            <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                <div>
                    <h2 className="text-lg font-semibold text-[#58a6ff]">멀티 에이전트 자율 오케스트레이터 (①)</h2>
                    <p className="mt-1 text-xs text-[#8b949e]">
                        SSOT: POST /api/llm/orchestrate/chat (surface adapter) ·
                        raw session probe: GET /api/llm/autonomous/session/&#123;id&#125;
                    </p>
                </div>
                <div className="flex flex-wrap gap-2">
                    {MODE_OPTIONS.map((option) => (
                        <button
                            key={option.id}
                            type="button"
                            disabled={busy || Boolean(sessionId)}
                            title={option.hint}
                            onClick={() => setMode(option.id)}
                            className={`rounded-lg px-3 py-2 text-xs font-semibold ${
                                mode === option.id
                                    ? 'border border-[#1f6feb] bg-[rgba(31,111,235,0.18)] text-[#9ecbff]'
                                    : 'border border-[#30363d] bg-[#21262d] text-[#8b949e]'
                            }`}
                        >
                            {option.label}
                        </button>
                    ))}
                </div>
            </div>

            <div className="mb-3 grid gap-2 text-xs text-[#8b949e] md:grid-cols-4">
                <div>세션: <span className="text-[#e6edf3]">{sessionId || '(신규)'}</span></div>
                <div>상태: <span className="text-[#79c0ff]">{statusLabel}</span></div>
                <div>STAGE 잔여: <span className="text-[#e3b341]">{lastResponse?.stages_remaining ?? '-'}</span></div>
                <div>진행: <span className="text-[#e3b341]">{sessionSummary || '-'}</span></div>
            </div>

            <div className="mb-3 max-h-72 overflow-y-auto rounded-lg border border-[#30363d] bg-[#0d1117] p-3">
                {lines.length === 0 ? (
                    <p className="text-sm text-[#8b949e]">예: &quot;FastAPI로 블로그 API 만들어줘&quot; · semi_auto면 승인 후 코드 생성</p>
                ) : (
                    lines.map((line) => (
                        <div key={line.id} className="mb-3 last:mb-0">
                            <p className="text-[11px] font-semibold uppercase tracking-wide text-[#8b949e]">
                                {line.role}{line.intent ? ` · ${line.intent}` : ''}
                            </p>
                            <pre className="mt-1 whitespace-pre-wrap text-sm text-[#e6edf3]">{line.text}</pre>
                        </div>
                    ))
                )}
            </div>

            {requiresApproval && (
                <div className="mb-3 flex flex-wrap gap-2">
                    <button
                        type="button"
                        disabled={busy}
                        onClick={() => sendMessage('승인')}
                        className="rounded-lg border border-[#238636] bg-[rgba(35,134,54,0.2)] px-4 py-2 text-sm font-semibold text-[#7ee787]"
                    >
                        승인
                    </button>
                    <button
                        type="button"
                        disabled={busy}
                        onClick={() => sendMessage('거절')}
                        className="rounded-lg border border-[#da3633] bg-[rgba(218,54,51,0.15)] px-4 py-2 text-sm font-semibold text-[#ffa198]"
                    >
                        거절
                    </button>
                </div>
            )}

            <form onSubmit={handleSubmit} className="flex flex-col gap-2 md:flex-row">
                <textarea
                    value={message}
                    onChange={(event) => setMessage(event.target.value)}
                    rows={2}
                    placeholder="요청 또는 승인/거절 메시지"
                    className="min-h-[52px] flex-1 rounded-lg border border-[#30363d] bg-[#0d1117] px-3 py-2 text-sm text-[#e6edf3]"
                    disabled={busy}
                />
                <button
                    type="submit"
                    disabled={busy || !message.trim()}
                    className="rounded-lg border border-[#1f6feb] bg-[#1f6feb] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
                >
                    {busy ? '처리 중…' : '전송'}
                </button>
            </form>

            {error && <p className="mt-2 text-xs text-[#ffa198]">{error}</p>}
        </section>
    );
}

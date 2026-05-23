import type { Dispatch, MutableRefObject, SetStateAction } from 'react';

type LiveStatus = 'idle' | 'running' | 'success' | 'failed';
type LiveApplyState = 'idle' | 'running' | 'applied' | 'response-only' | 'failed';

interface LiveSemanticAuditSnapshotLike {
    passed?: boolean;
    error?: string;
    summary?: string;
    score?: number;
    maxScore?: number;
    threshold?: number;
    checklist: any[];
}

interface AppendConversationMessageLike {
    role: string;
    content: string;
    speaker: string | null;
    step_id: string | null;
    step_title: string | null;
    timestamp: string;
}

interface LiveLogSeverityContext {
    eventType: string;
    message: string;
    semanticAuditPassed?: boolean;
}

export function normalizeLiveWebsocketEvent(data: Record<string, any>) {
    const eventType = String(data.event || 'unknown');
    const timestamp = String(data.timestamp || new Date().toISOString());
    const message = String(data.message || eventType);
    const nextState = typeof data.state === 'string' ? data.state : '';
    const nextHistory = Array.isArray(data.state_history)
        ? data.state_history.filter((item): item is string => typeof item === 'string')
        : [];
    const nextStage = typeof data.stage === 'string' ? data.stage : nextState || undefined;
    const nextOutputDir = typeof data.output_dir === 'string' ? data.output_dir : '';
    const nextSpec = data.orchestration_spec && typeof data.orchestration_spec === 'object'
        ? data.orchestration_spec
        : null;
    const semanticAuditPassed = typeof data.passed === 'boolean' ? data.passed : undefined;
    const semanticAuditScore = typeof data.score === 'number' ? data.score : undefined;
    const semanticAuditMaxScore = typeof data.max_score === 'number' ? data.max_score : undefined;
    const semanticAuditThreshold = typeof data.threshold === 'number' ? data.threshold : undefined;
    const semanticAuditChecklist = Array.isArray(data.checklist)
        ? data.checklist.filter((item): item is any => (
            !!item && typeof item === 'object' && typeof item.id === 'string' && typeof item.label === 'string'
        ))
        : [];
    const semanticAuditError = typeof data.error === 'string' ? data.error : '';
    const semanticAuditSummary = typeof data.summary === 'string' ? data.summary : '';

    return {
        eventType,
        timestamp,
        message,
        nextState,
        nextHistory,
        nextStage,
        nextOutputDir,
        nextSpec,
        semanticAuditPassed,
        semanticAuditScore,
        semanticAuditMaxScore,
        semanticAuditThreshold,
        semanticAuditChecklist,
        semanticAuditError,
        semanticAuditSummary,
    };
}

export function resolveLiveLogSeverity(context: LiveLogSeverityContext): 'info' | 'success' | 'warning' | 'error' {
    if (context.eventType === 'semantic_audit') {
        return context.semanticAuditPassed === false ? 'warning' : context.semanticAuditPassed === true ? 'success' : 'info';
    }
    if (context.message.startsWith('[done]')) {
        return context.message.includes('success') ? 'success' : 'error';
    }
    if (context.eventType === 'terminal_log' && /fail|error|실패/i.test(context.message)) {
        return 'error';
    }
    return 'info';
}

export function decorateLiveLogMessage(options: {
    eventType: string;
    message: string;
    semanticAuditScore?: number;
    semanticAuditMaxScore?: number;
    semanticAuditThreshold?: number;
}) {
    if (options.eventType !== 'semantic_audit') {
        return options.message;
    }
    return `${options.message}${options.semanticAuditScore != null && options.semanticAuditMaxScore != null ? `\nscore ${options.semanticAuditScore}/${options.semanticAuditMaxScore}${options.semanticAuditThreshold != null ? ` · cut ${options.semanticAuditThreshold}` : ''}` : ''}`;
}

export function applyLiveWsEventUpdate(options: {
    data: Record<string, any>;
    currentRunId: string;
    appendConversationMessage: (message: AppendConversationMessageLike) => void;
    setLiveStatus: Dispatch<SetStateAction<LiveStatus>>;
    setLiveApplyState: Dispatch<SetStateAction<LiveApplyState>>;
    setLiveMode: Dispatch<SetStateAction<string>>;
    setLivePipeline: Dispatch<SetStateAction<string[]>>;
    setLiveTask: Dispatch<SetStateAction<string>>;
    setLiveOrchestrationSpec: Dispatch<SetStateAction<any>>;
    setLiveOutputDir: Dispatch<SetStateAction<string>>;
    setLiveSemanticAudit: Dispatch<SetStateAction<LiveSemanticAuditSnapshotLike | null>>;
    setLiveCurrentState: Dispatch<SetStateAction<string>>;
    setLiveStateHistory: Dispatch<SetStateAction<string[]>>;
    appendLiveLog: (event: string, message: string, stage?: string, timestamp?: string, severity?: 'info' | 'success' | 'warning' | 'error') => void;
    mergeStageHistory: (history: string[], stage?: string) => string[];
    onConnectionMetric?: (metric: {
        stage: 'open' | 'close' | 'error';
        elapsedMs: number;
        reconnectDelayMs: number;
        url: string;
    }) => void;
}) {
    const eventRunId = String(options.data.run_id || '');
    if (!options.currentRunId || eventRunId !== options.currentRunId) {
        return false;
    }

    const normalized = normalizeLiveWebsocketEvent(options.data);
    if (normalized.eventType === 'connected' || normalized.eventType === 'pong' || normalized.eventType === 'echo') {
        return false;
    }

    if (normalized.eventType === 'chat_message') {
        options.appendConversationMessage({
            role: String(options.data.role || 'assistant'),
            content: String(options.data.message || ''),
            speaker: typeof options.data.speaker === 'string' ? options.data.speaker : null,
            step_id: typeof options.data.step_id === 'string' ? options.data.step_id : null,
            step_title: typeof options.data.step_title === 'string' ? options.data.step_title : null,
            timestamp: normalized.timestamp,
        });
    }

    if (normalized.eventType === 'orchestration_started') {
        options.setLiveStatus('running');
        options.setLiveApplyState('running');
        options.setLiveMode(String(options.data.mode || 'auto'));
        options.setLivePipeline(Array.isArray(options.data.pipeline) ? options.data.pipeline : []);
        options.setLiveTask(String(options.data.task || ''));
    }
    if (normalized.nextSpec) {
        options.setLiveOrchestrationSpec(normalized.nextSpec);
    }
    if (normalized.nextOutputDir) {
        options.setLiveOutputDir(normalized.nextOutputDir);
    }
    if (normalized.eventType === 'semantic_audit') {
        options.setLiveSemanticAudit({
            passed: normalized.semanticAuditPassed,
            error: normalized.semanticAuditError,
            summary: normalized.semanticAuditSummary || normalized.message,
            score: normalized.semanticAuditScore,
            maxScore: normalized.semanticAuditMaxScore,
            threshold: normalized.semanticAuditThreshold,
            checklist: normalized.semanticAuditChecklist,
        });
    }

    if (normalized.nextState) {
        options.setLiveCurrentState(normalized.nextState);
    } else if (normalized.nextStage) {
        options.setLiveCurrentState(normalized.nextStage);
    }
    if (normalized.nextHistory.length > 0) {
        options.setLiveStateHistory(normalized.nextHistory);
    } else if (normalized.nextStage) {
        options.setLiveStateHistory((prev) => options.mergeStageHistory(prev, normalized.nextStage));
    }
    if (normalized.message.startsWith('[done]')) {
        options.setLiveStatus(normalized.message.includes('success') ? 'success' : 'failed');
        options.setLiveApplyState(normalized.message.includes('success') ? 'applied' : 'failed');
    }

    const severity = resolveLiveLogSeverity({
        eventType: normalized.eventType,
        message: normalized.message,
        semanticAuditPassed: normalized.semanticAuditPassed,
    });
    options.appendLiveLog(
        normalized.eventType,
        decorateLiveLogMessage({
            eventType: normalized.eventType,
            message: normalized.message,
            semanticAuditScore: normalized.semanticAuditScore,
            semanticAuditMaxScore: normalized.semanticAuditMaxScore,
            semanticAuditThreshold: normalized.semanticAuditThreshold,
        }),
        normalized.nextStage,
        normalized.timestamp,
        severity,
    );
    return true;
}

export function bindAdminLiveWebSocket(options: {
    buildWsUrl: () => string;
    buildWsUrls?: () => string[];
    setWsConnected: Dispatch<SetStateAction<boolean>>;
    liveRunIdRef: MutableRefObject<string>;
    appendConversationMessage: (message: AppendConversationMessageLike) => void;
    setLiveStatus: Dispatch<SetStateAction<LiveStatus>>;
    setLiveApplyState: Dispatch<SetStateAction<LiveApplyState>>;
    setLiveMode: Dispatch<SetStateAction<string>>;
    setLivePipeline: Dispatch<SetStateAction<string[]>>;
    setLiveTask: Dispatch<SetStateAction<string>>;
    setLiveOrchestrationSpec: Dispatch<SetStateAction<any>>;
    setLiveOutputDir: Dispatch<SetStateAction<string>>;
    setLiveSemanticAudit: Dispatch<SetStateAction<LiveSemanticAuditSnapshotLike | null>>;
    setLiveCurrentState: Dispatch<SetStateAction<string>>;
    setLiveStateHistory: Dispatch<SetStateAction<string[]>>;
    appendLiveLog: (event: string, message: string, stage?: string, timestamp?: string, severity?: 'info' | 'success' | 'warning' | 'error') => void;
    mergeStageHistory: (history: string[], stage?: string) => string[];
    onConnectionMetric?: (metric: {
        stage: 'open' | 'close' | 'error';
        elapsedMs: number;
        reconnectDelayMs: number;
        url: string;
    }) => void;
}) {
    const rawCandidates = options.buildWsUrls
        ? options.buildWsUrls()
        : [options.buildWsUrl()];
    const wsUrlCandidates = Array.from(
        new Set(
            rawCandidates
                .map((item) => String(item || '').trim())
                .filter((item) => item.length > 0),
        ),
    );

    if (wsUrlCandidates.length === 0) {
        return () => {};
    }

    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let closedByUser = false;
    let reconnectDelayMs = 1500;
    let wsCandidateIndex = 0;

    const connect = () => {
        if (closedByUser) {
            return;
        }
        if (
            socket
            && (
                socket.readyState === WebSocket.OPEN
                || socket.readyState === WebSocket.CONNECTING
            )
        ) {
            return;
        }
        const wsUrl = wsUrlCandidates[wsCandidateIndex] || wsUrlCandidates[0];
        const startedAt = performance.now();
        socket = new WebSocket(wsUrl);

        socket.onopen = () => {
            reconnectDelayMs = 1500;
            options.setWsConnected(true);
            options.onConnectionMetric?.({
                stage: 'open',
                elapsedMs: Math.round(performance.now() - startedAt),
                reconnectDelayMs,
                url: wsUrl,
            });
        };

        socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data) as Record<string, any>;
                applyLiveWsEventUpdate({
                    data,
                    currentRunId: options.liveRunIdRef.current,
                    appendConversationMessage: options.appendConversationMessage,
                    setLiveStatus: options.setLiveStatus,
                    setLiveApplyState: options.setLiveApplyState,
                    setLiveMode: options.setLiveMode,
                    setLivePipeline: options.setLivePipeline,
                    setLiveTask: options.setLiveTask,
                    setLiveOrchestrationSpec: options.setLiveOrchestrationSpec,
                    setLiveOutputDir: options.setLiveOutputDir,
                    setLiveSemanticAudit: options.setLiveSemanticAudit,
                    setLiveCurrentState: options.setLiveCurrentState,
                    setLiveStateHistory: options.setLiveStateHistory,
                    appendLiveLog: options.appendLiveLog,
                    mergeStageHistory: options.mergeStageHistory,
                });
            } catch {
            }
        };

        socket.onclose = () => {
            options.setWsConnected(false);
            options.onConnectionMetric?.({
                stage: 'close',
                elapsedMs: Math.round(performance.now() - startedAt),
                reconnectDelayMs,
                url: wsUrl,
            });
            socket = null;
            if (!closedByUser) {
                if (wsUrlCandidates.length > 1) {
                    wsCandidateIndex = (wsCandidateIndex + 1) % wsUrlCandidates.length;
                }
                reconnectTimer = setTimeout(connect, reconnectDelayMs);
                reconnectDelayMs = Math.min(reconnectDelayMs * 2, 15000);
            }
        };

        socket.onerror = () => {
            options.setWsConnected(false);
            options.onConnectionMetric?.({
                stage: 'error',
                elapsedMs: Math.round(performance.now() - startedAt),
                reconnectDelayMs,
                url: wsUrl,
            });
            if (wsUrlCandidates.length > 1) {
                wsCandidateIndex = (wsCandidateIndex + 1) % wsUrlCandidates.length;
            }
            if (socket?.readyState === WebSocket.OPEN || socket?.readyState === WebSocket.CONNECTING) {
                socket.close();
            }
        };
    };

    connect();

    return () => {
        closedByUser = true;
        if (reconnectTimer) clearTimeout(reconnectTimer);
        socket?.close();
    };
}

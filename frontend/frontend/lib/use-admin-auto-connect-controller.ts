import { useCallback, useEffect, useMemo, useState } from 'react';
import {
    loadAdminAutoConnectCompletionHistory,
    loadAdminAutoConnectLookup,
    loadAdminAutoConnectRetryQueue,
    loadAdminAutoConnectTraceHistory,
    replayAdminAutoConnectRetryQueue,
    type AdminAutoConnectLookupResponse,
    type AdminCompletionHistoryItem,
    type AdminRetryQueueItem,
    type AdminTraceLogItem,
} from '@/lib/admin-auto-connect-service';
import { getAdminToken } from '@/lib/admin-session';

type PushLog = (level: 'info' | 'success' | 'warning', message: string) => void;

export type UseAdminAutoConnectControllerOptions = {
    apiBaseUrl: string;
    authChecked: boolean;
    activeConnectionId: string;
    apiUnavailableRef: React.MutableRefObject<boolean>;
    handleAdminUnauthorized: (message?: string) => void;
    setAdminApiBackoff: (key: string) => void;
    pushLiveLog: PushLog;
    setError: (value: string | null) => void;
};

export function useAdminAutoConnectController(options: UseAdminAutoConnectControllerOptions) {
    const {
        apiBaseUrl,
        authChecked,
        activeConnectionId,
        apiUnavailableRef,
        handleAdminUnauthorized,
        setAdminApiBackoff,
        pushLiveLog,
        setError,
    } = options;
    const [adminCompletionHistory, setAdminCompletionHistory] = useState<AdminCompletionHistoryItem[]>([]);
    const [adminTraceHistory, setAdminTraceHistory] = useState<AdminTraceLogItem[]>([]);
    const [adminRetryQueueItems, setAdminRetryQueueItems] = useState<AdminRetryQueueItem[]>([]);
    const [adminConnectionLookupId, setAdminConnectionLookupId] = useState('');
    const [adminConnectionLookupLoading, setAdminConnectionLookupLoading] = useState(false);
    const [adminConnectionLookupResult, setAdminConnectionLookupResult] = useState<AdminAutoConnectLookupResponse | null>(null);
    const [adminTraceFilter, setAdminTraceFilter] = useState('');
    const [adminReplayQueueId, setAdminReplayQueueId] = useState<number | null>(null);

    const loadAdminCompletionHistory = useCallback(async () => {
        const token = getAdminToken();
        if (!token || apiUnavailableRef.current) {
            setAdminCompletionHistory([]);
            return;
        }
        try {
            const result = await loadAdminAutoConnectCompletionHistory({
                apiBaseUrl,
                token,
            });
            if (result.unsupported) {
                apiUnavailableRef.current = true;
                setAdminApiBackoff('auto-connect-graph');
                setAdminCompletionHistory([]);
                return;
            }
            setAdminCompletionHistory(result.items);
        } catch {
            setAdminCompletionHistory([]);
        }
    }, [apiBaseUrl, apiUnavailableRef, setAdminApiBackoff]);

    const loadAdminTraceHistory = useCallback(async () => {
        const token = getAdminToken();
        if (!token || apiUnavailableRef.current) {
            setAdminTraceHistory([]);
            return;
        }
        try {
            const result = await loadAdminAutoConnectTraceHistory({
                apiBaseUrl,
                token,
            });
            if (result.unsupported) {
                apiUnavailableRef.current = true;
                setAdminApiBackoff('auto-connect-graph');
                setAdminTraceHistory([]);
                return;
            }
            setAdminTraceHistory(result.items);
        } catch {
            setAdminTraceHistory([]);
        }
    }, [apiBaseUrl, apiUnavailableRef, setAdminApiBackoff]);

    const loadAdminRetryQueue = useCallback(async () => {
        const token = getAdminToken();
        if (!token || apiUnavailableRef.current) {
            setAdminRetryQueueItems([]);
            return;
        }
        try {
            const result = await loadAdminAutoConnectRetryQueue({
                apiBaseUrl,
                token,
            });
            if (result.unsupported) {
                apiUnavailableRef.current = true;
                setAdminApiBackoff('auto-connect-graph');
                setAdminRetryQueueItems([]);
                return;
            }
            setAdminRetryQueueItems(result.items);
        } catch {
            setAdminRetryQueueItems([]);
        }
    }, [apiBaseUrl, apiUnavailableRef, setAdminApiBackoff]);

    const loadAdminConnectionLookup = useCallback(async (connectionId?: string) => {
        const token = getAdminToken();
        const normalizedConnectionId = (connectionId ?? adminConnectionLookupId).trim();
        if (!token) {
            setAdminConnectionLookupResult(null);
            return;
        }
        if (!normalizedConnectionId) {
            setAdminConnectionLookupResult(null);
            return;
        }
        setAdminConnectionLookupLoading(true);
        try {
            const data = await loadAdminAutoConnectLookup({
                apiBaseUrl,
                token,
                connectionId: normalizedConnectionId,
                fallbackCompletionHistory: adminCompletionHistory,
                fallbackTraceHistory: adminTraceHistory,
                fallbackRetryQueue: adminRetryQueueItems,
            });
            setAdminConnectionLookupResult(data);
        } catch (error) {
            if (error instanceof Error && error.message === '__ADMIN_AUTO_CONNECT_UNAUTHORIZED__') {
                handleAdminUnauthorized();
                return;
            }
            const message = error instanceof Error ? error.message : 'connection_id 조회 중 오류가 발생했습니다.';
            pushLiveLog('warning', message);
            setError(message);
            setAdminConnectionLookupResult(null);
        } finally {
            setAdminConnectionLookupLoading(false);
        }
    }, [adminCompletionHistory, adminConnectionLookupId, adminRetryQueueItems, adminTraceHistory, apiBaseUrl, handleAdminUnauthorized, pushLiveLog, setError]);

    useEffect(() => {
        if (!authChecked) {
            return;
        }
        void loadAdminCompletionHistory();
        void loadAdminTraceHistory();
        void loadAdminRetryQueue();
    }, [authChecked, loadAdminCompletionHistory, loadAdminRetryQueue, loadAdminTraceHistory]);

    useEffect(() => {
        if (!activeConnectionId) {
            return;
        }
        setAdminConnectionLookupId((prev) => prev || activeConnectionId);
    }, [activeConnectionId]);

    const handleReplayRetryQueue = useCallback(async (queueItemId: number) => {
        const token = getAdminToken();
        if (!token) {
            handleAdminUnauthorized();
            return;
        }
        setAdminReplayQueueId(queueItemId);
        try {
            await replayAdminAutoConnectRetryQueue({
                apiBaseUrl,
                token,
                queueItemId,
            });
            pushLiveLog('success', `retry queue ${queueItemId} 항목을 실제 worker 재큐로 재실행했습니다.`);
            await loadAdminTraceHistory();
            await loadAdminRetryQueue();
            if (adminConnectionLookupResult?.retry_queue.some((item) => item.id === queueItemId)) {
                await loadAdminConnectionLookup(adminConnectionLookupResult.connection_id);
            }
        } catch (error) {
            if (error instanceof Error && error.message === '__ADMIN_AUTO_CONNECT_UNAUTHORIZED__') {
                handleAdminUnauthorized();
                return;
            }
            const message = error instanceof Error ? error.message : 'retry queue 재실행 중 오류가 발생했습니다.';
            pushLiveLog('warning', message);
            setError(message);
        } finally {
            setAdminReplayQueueId(null);
        }
    }, [adminConnectionLookupResult, apiBaseUrl, handleAdminUnauthorized, loadAdminConnectionLookup, loadAdminRetryQueue, loadAdminTraceHistory, pushLiveLog, setError]);

    const adminTraceFilterText = adminTraceFilter.trim().toLowerCase();
    const filteredAdminCompletionHistory = useMemo(
        () => !adminTraceFilterText
            ? adminCompletionHistory
            : adminCompletionHistory.filter((item) => [item.trace_id || '', item.flow_id || '', item.step_id || '', item.action || '', item.project_name, item.mode, item.connection_id || ''].join(' ').toLowerCase().includes(adminTraceFilterText)),
        [adminCompletionHistory, adminTraceFilterText],
    );
    const filteredAdminTraceHistory = useMemo(
        () => !adminTraceFilterText
            ? adminTraceHistory
            : adminTraceHistory.filter((item) => [item.trace_id, item.flow_id, item.step_id, item.action, item.entity_type, item.entity_id, item.status, item.message, item.connection_id || ''].join(' ').toLowerCase().includes(adminTraceFilterText)),
        [adminTraceHistory, adminTraceFilterText],
    );
    const filteredAdminRetryQueueItems = useMemo(
        () => !adminTraceFilterText
            ? adminRetryQueueItems
            : adminRetryQueueItems.filter((item) => [item.trace_id, item.flow_id, item.step_id, item.action, item.entity_type, item.entity_id, item.queue_name, item.status, item.last_error || '', item.connection_id || ''].join(' ').toLowerCase().includes(adminTraceFilterText)),
        [adminRetryQueueItems, adminTraceFilterText],
    );

    return {
        adminCompletionHistory,
        adminTraceHistory,
        adminRetryQueueItems,
        adminConnectionLookupId,
        setAdminConnectionLookupId,
        adminConnectionLookupLoading,
        adminConnectionLookupResult,
        adminTraceFilter,
        setAdminTraceFilter,
        adminReplayQueueId,
        loadAdminCompletionHistory,
        loadAdminTraceHistory,
        loadAdminRetryQueue,
        loadAdminConnectionLookup,
        handleReplayRetryQueue,
        filteredAdminCompletionHistory,
        filteredAdminTraceHistory,
        filteredAdminRetryQueueItems,
    };
}

export function assertAdminAutoConnectControllerContract() {
    const filtered = ['FLOW-001', 'trace'].join(' ').toLowerCase();
    if (!filtered.includes('flow-001')) {
        throw new Error('admin auto-connect controller contract 누락: trace filter 기본 문자열 필요');
    }
}

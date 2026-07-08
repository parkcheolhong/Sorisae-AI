'use client';

import { useEffect, useRef, useState } from 'react';

import {
    mapProgressPayloadToSnapshot,
    saveLiveProgressSnapshot,
    type OrchestratorLiveProgressSnapshot,
} from '@/lib/orchestrator-live-progress';

export type OrchestratorProgressTransport = 'idle' | 'sse' | 'ws' | 'poll';

type UseOrchestratorLiveProgressStreamOptions = {
    enabled: boolean;
    streamUrl: string | null;
    wsUrl?: string | null;
    accessToken?: string | null;
    preferWebSocket?: boolean;
    onProgressUpdate?: (snapshot: OrchestratorLiveProgressSnapshot) => void;
    onTransportChange?: (transport: OrchestratorProgressTransport) => void;
};

function appendAccessToken(url: string, accessToken?: string | null): string {
    const token = String(accessToken || '').trim();
    if (!token || url.includes('token=')) {
        return url;
    }
    const separator = url.includes('?') ? '&' : '?';
    return `${url}${separator}token=${encodeURIComponent(token)}`;
}

function toWebSocketUrl(httpUrl: string): string {
    return httpUrl.replace(/^http:\/\//i, 'ws://').replace(/^https:\/\//i, 'wss://');
}

function applySnapshot(
    payload: Record<string, unknown>,
    setSnapshot: (value: OrchestratorLiveProgressSnapshot) => void,
    onProgressUpdate?: (snapshot: OrchestratorLiveProgressSnapshot) => void,
) {
    const next = mapProgressPayloadToSnapshot(payload);
    setSnapshot(next);
    saveLiveProgressSnapshot(next);
    onProgressUpdate?.(next);
}

export function useOrchestratorLiveProgressStream({
    enabled,
    streamUrl,
    wsUrl,
    accessToken,
    preferWebSocket = false,
    onProgressUpdate,
    onTransportChange,
}: UseOrchestratorLiveProgressStreamOptions) {
    const [snapshot, setSnapshot] = useState<OrchestratorLiveProgressSnapshot | null>(null);
    const [transport, setTransport] = useState<OrchestratorProgressTransport>('idle');
    const [streamFailed, setStreamFailed] = useState(false);
    const updateRef = useRef(onProgressUpdate);
    const transportRef = useRef(onTransportChange);
    updateRef.current = onProgressUpdate;
    transportRef.current = onTransportChange;

    const setActiveTransport = (next: OrchestratorProgressTransport) => {
        setTransport(next);
        transportRef.current?.(next);
    };

    useEffect(() => {
        if (!enabled || !streamUrl) {
            setStreamFailed(false);
            setActiveTransport('idle');
            return;
        }

        let cancelled = false;
        let eventSource: EventSource | null = null;
        let webSocket: WebSocket | null = null;
        let reconnectTimer: number | null = null;

        const finish = () => {
            if (cancelled) {
                return;
            }
            setStreamFailed(true);
            setActiveTransport('idle');
        };

        const handleProgressPayload = (payload: Record<string, unknown>) => {
            if (cancelled) {
                return;
            }
            applySnapshot(payload, setSnapshot, updateRef.current);
        };

        const connectEventSource = () => {
            if (cancelled || preferWebSocket) {
                return;
            }
            const resolvedUrl = appendAccessToken(streamUrl, accessToken);
            eventSource = new EventSource(resolvedUrl);
            setActiveTransport('sse');

            eventSource.addEventListener('progress', (event) => {
                try {
                    const payload = JSON.parse((event as MessageEvent).data) as Record<string, unknown>;
                    handleProgressPayload(payload);
                } catch {
                }
            });
            eventSource.addEventListener('heartbeat', () => {
                if (!cancelled) {
                    setActiveTransport('sse');
                }
            });
            eventSource.addEventListener('done', () => {
                eventSource?.close();
            });
            eventSource.addEventListener('error', () => {
                eventSource?.close();
                finish();
            });
            eventSource.onerror = () => {
                eventSource?.close();
                finish();
            };
        };

        const connectWebSocket = () => {
            if (cancelled) {
                return;
            }
            const baseWsUrl = wsUrl || streamUrl.replace('/progress/stream/', '/progress/ws/').replace('/stream/', '/progress/ws/');
            const resolvedUrl = appendAccessToken(toWebSocketUrl(baseWsUrl), accessToken);
            webSocket = new WebSocket(resolvedUrl);
            setActiveTransport('ws');

            webSocket.onopen = () => {
                if (!cancelled) {
                    setActiveTransport('ws');
                }
            };
            webSocket.onmessage = (event) => {
                try {
                    const payload = JSON.parse(String(event.data || '{}')) as Record<string, unknown>;
                    const eventName = String(payload.event || '');
                    if (eventName === 'progress') {
                        handleProgressPayload(payload);
                    }
                    if (eventName === 'done' || eventName === 'error') {
                        webSocket?.close();
                    }
                } catch {
                }
            };
            webSocket.onerror = () => {
                webSocket?.close();
                finish();
            };
            webSocket.onclose = () => {
                if (!cancelled && preferWebSocket) {
                    reconnectTimer = window.setTimeout(connectWebSocket, 1500);
                } else {
                    finish();
                }
            };
        };

        if (preferWebSocket) {
            connectWebSocket();
        } else {
            connectEventSource();
        }

        return () => {
            cancelled = true;
            if (reconnectTimer) {
                window.clearTimeout(reconnectTimer);
            }
            eventSource?.close();
            if (webSocket && (webSocket.readyState === WebSocket.OPEN || webSocket.readyState === WebSocket.CONNECTING)) {
                webSocket.close();
            }
            setActiveTransport('idle');
        };
    }, [accessToken, enabled, preferWebSocket, streamUrl, wsUrl]);

    return {
        snapshot,
        transport,
        streamFailed,
    };
}

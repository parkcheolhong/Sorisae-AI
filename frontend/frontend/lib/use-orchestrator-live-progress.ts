'use client';

import { useMemo } from 'react';

import {
    type OrchestratorLiveProgressSnapshot,
} from '@/lib/orchestrator-live-progress';
import {
    useOrchestratorLiveProgressPoll,
} from '@/lib/use-orchestrator-live-progress-poll';
import {
    type OrchestratorProgressTransport,
    useOrchestratorLiveProgressStream,
} from '@/lib/use-orchestrator-live-progress-stream';

type UseOrchestratorLiveProgressOptions = {
    enabled: boolean;
    progressUrl: string | null;
    streamUrl?: string | null;
    wsUrl?: string | null;
    accessToken?: string | null;
    authHeaders?: Record<string, string>;
    pollIntervalMs?: number;
    preferStream?: boolean;
    preferWebSocket?: boolean;
    onProgressUpdate?: (snapshot: OrchestratorLiveProgressSnapshot) => void;
};

function extractBearerToken(authHeaders?: Record<string, string>, explicitToken?: string | null): string | null {
    const direct = String(explicitToken || '').trim();
    if (direct) {
        return direct;
    }
    const authorization = String(authHeaders?.Authorization || authHeaders?.authorization || '').trim();
    if (authorization.toLowerCase().startsWith('bearer ')) {
        return authorization.slice(7).trim();
    }
    return null;
}

function deriveStreamUrl(progressUrl: string | null, explicitStreamUrl?: string | null): string | null {
    if (explicitStreamUrl) {
        return explicitStreamUrl;
    }
    if (!progressUrl) {
        return null;
    }
    if (progressUrl.includes('/progress/stream/')) {
        return progressUrl;
    }
    if (progressUrl.includes('/orchestrate/progress/')) {
        return progressUrl.replace('/orchestrate/progress/', '/orchestrate/stream/');
    }
    if (progressUrl.includes('/customer-orchestrate/progress/')) {
        return progressUrl.replace('/customer-orchestrate/progress/', '/customer-orchestrate/progress/stream/');
    }
    return null;
}

function deriveWsUrl(progressUrl: string | null, explicitWsUrl?: string | null): string | null {
    if (explicitWsUrl) {
        return explicitWsUrl;
    }
    if (!progressUrl) {
        return null;
    }
    if (progressUrl.includes('/orchestrate/progress/')) {
        return progressUrl.replace('/orchestrate/progress/', '/orchestrate/progress/ws/');
    }
    if (progressUrl.includes('/customer-orchestrate/progress/')) {
        return progressUrl.replace('/customer-orchestrate/progress/', '/customer-orchestrate/progress/ws/');
    }
    return null;
}

export function useOrchestratorLiveProgress({
    enabled,
    progressUrl,
    streamUrl,
    wsUrl,
    accessToken,
    authHeaders,
    pollIntervalMs = 2000,
    preferStream = true,
    preferWebSocket = false,
    onProgressUpdate,
}: UseOrchestratorLiveProgressOptions) {
    const resolvedStreamUrl = deriveStreamUrl(progressUrl, streamUrl);
    const resolvedWsUrl = deriveWsUrl(progressUrl, wsUrl);
    const resolvedToken = extractBearerToken(authHeaders, accessToken);
    const streamEnabled = Boolean(enabled && preferStream && resolvedStreamUrl);

    const stream = useOrchestratorLiveProgressStream({
        enabled: streamEnabled,
        streamUrl: resolvedStreamUrl,
        wsUrl: resolvedWsUrl,
        accessToken: resolvedToken,
        preferWebSocket,
        onProgressUpdate,
    });

    const pollEnabled = Boolean(
        enabled
        && progressUrl
        && (!streamEnabled || stream.streamFailed || !stream.snapshot),
    );

    const pollSnapshot = useOrchestratorLiveProgressPoll({
        enabled: pollEnabled,
        progressUrl,
        authHeaders,
        pollIntervalMs,
        onProgressUpdate: streamEnabled && !stream.streamFailed ? undefined : onProgressUpdate,
    });

    const snapshot = useMemo(() => {
        if (stream.snapshot && stream.transport !== 'idle') {
            return stream.snapshot;
        }
        return pollSnapshot;
    }, [pollSnapshot, stream.snapshot, stream.transport]);

    const transport: OrchestratorProgressTransport = stream.transport !== 'idle'
        ? stream.transport
        : pollEnabled
            ? 'poll'
            : 'idle';

    return {
        snapshot,
        transport,
        streamFailed: stream.streamFailed,
    };
}

export type { OrchestratorProgressTransport };

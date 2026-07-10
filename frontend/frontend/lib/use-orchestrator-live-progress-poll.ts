'use client';

import { useEffect, useRef, useState } from 'react';

import {
    fetchOrchestratorProgress,
    loadLiveProgressSnapshot,
    saveLiveProgressSnapshot,
    type OrchestratorLiveProgressSnapshot,
} from '@/lib/orchestrator-live-progress';

type UseOrchestratorLiveProgressPollOptions = {
    enabled: boolean;
    progressUrl: string | null;
    authHeaders?: Record<string, string>;
    pollIntervalMs?: number;
    onProgressUpdate?: (snapshot: OrchestratorLiveProgressSnapshot) => void;
};

export function useOrchestratorLiveProgressPoll({
    enabled,
    progressUrl,
    authHeaders,
    pollIntervalMs = 2000,
    onProgressUpdate,
}: UseOrchestratorLiveProgressPollOptions) {
    const [snapshot, setSnapshot] = useState<OrchestratorLiveProgressSnapshot | null>(() => loadLiveProgressSnapshot());
    const updateRef = useRef(onProgressUpdate);
    updateRef.current = onProgressUpdate;

    useEffect(() => {
        if (!enabled || !progressUrl) {
            return;
        }

        let cancelled = false;

        const poll = async () => {
            const next = await fetchOrchestratorProgress(progressUrl, authHeaders);
            if (cancelled || !next) {
                return;
            }
            setSnapshot(next);
            saveLiveProgressSnapshot(next);
            updateRef.current?.(next);
        };

        void poll();
        const timer = window.setInterval(() => {
            void poll();
        }, pollIntervalMs);

        return () => {
            cancelled = true;
            window.clearInterval(timer);
        };
    }, [authHeaders, enabled, pollIntervalMs, progressUrl]);

    return snapshot;
}

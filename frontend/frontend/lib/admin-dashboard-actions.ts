import type { Dispatch, MutableRefObject, SetStateAction } from 'react';
import { getAdminToken } from '@/lib/admin-session';
import { fetchWithAdminBootstrapRetry } from '@/lib/admin-bootstrap-fetch';
import type { SharedOrchestratorStageRun } from '@shared/orchestrator-stage-card-panel';
import type { AdminCostSimulatorResponse, LiveLogItem } from '@/lib/admin-runtime-types';

export type AdminStageRunResponse = SharedOrchestratorStageRun & {
    updated_at?: string;
};

export async function refreshAdminStageRunAction(options: {
    apiBaseUrl: string;
    runId: string;
    onUnauthorized: () => void;
    setAdminStageRun: Dispatch<SetStateAction<AdminStageRunResponse | null>>;
    setAdminStageSubstepChecks: Dispatch<SetStateAction<Record<string, boolean>>>;
}) {
    const accessToken = getAdminToken();
    if (!accessToken || !options.runId) {
        return null;
    }
    const response = await fetchWithAdminBootstrapRetry(`${options.apiBaseUrl}/api/marketplace/customer-orchestrate/stage-runs/${encodeURIComponent(options.runId)}`, {
        headers: { Authorization: `Bearer ${accessToken}` },
        cache: 'no-store',
    });
    if (response.status === 401 || response.status === 403) {
        options.onUnauthorized();
        return null;
    }
    const payload = await response.json().catch(() => null);
    if (!response.ok || !payload) {
        return null;
    }
    const nextStageRun = payload as AdminStageRunResponse;
    options.setAdminStageRun(nextStageRun);
    const activeStagePayload = (nextStageRun.stages || []).find((stage) => stage.id === nextStageRun.current_stage_id);
    const checks = Object.fromEntries(((activeStagePayload?.substeps || []).map((item) => [item.id, Boolean(item.checked)])));
    options.setAdminStageSubstepChecks(checks);
    return nextStageRun;
}

export async function updateAdminStageStatusAction(options: {
    apiBaseUrl: string;
    adminStageRun: AdminStageRunResponse | null;
    adminStageNoteDraft: string;
    adminStageRevisionNote: string;
    adminStageSubstepChecks: Record<string, boolean>;
    status: 'passed' | 'failed' | 'manual_correction';
    onUnauthorized: () => void;
    pushLiveLog: (level: LiveLogItem['level'], message: string) => void;
    setAdminStageRun: Dispatch<SetStateAction<AdminStageRunResponse | null>>;
    setAdminStageSubstepChecks: Dispatch<SetStateAction<Record<string, boolean>>>;
    setAdminStageRevisionNote: Dispatch<SetStateAction<string>>;
    setAdminStageNoteDraft: Dispatch<SetStateAction<string>>;
    setAdminStageUpdateLoading: Dispatch<SetStateAction<boolean>>;
}) {
    const accessToken = getAdminToken();
    if (!accessToken || !options.adminStageRun?.run_id || !options.adminStageRun.current_stage_id) {
        return;
    }
    options.setAdminStageUpdateLoading(true);
    try {
        const response = await fetch(`${options.apiBaseUrl}/api/marketplace/customer-orchestrate/stage-runs/update`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${accessToken}`,
            },
            body: JSON.stringify({
                run_id: options.adminStageRun.run_id,
                stage_id: options.adminStageRun.current_stage_id,
                status: options.status,
                note: options.adminStageNoteDraft,
                manual_correction: options.status === 'manual_correction' ? options.adminStageNoteDraft : '',
                substep_checks: options.adminStageSubstepChecks,
                revision_note: options.adminStageRevisionNote,
            }),
        });
        if (response.status === 401 || response.status === 403) {
            options.onUnauthorized();
            return;
        }
        const payload = await response.json().catch(() => null);
        if (!response.ok || !payload) {
            throw new Error((payload && typeof payload.detail === 'string' && payload.detail) || '관리자 stage 상태 업데이트에 실패했습니다.');
        }
        const nextStageRun = payload as AdminStageRunResponse;
        options.setAdminStageRun(nextStageRun);
        const activeStagePayload = (nextStageRun.stages || []).find((stage) => stage.id === nextStageRun.current_stage_id);
        const checks = Object.fromEntries(((activeStagePayload?.substeps || []).map((item) => [item.id, Boolean(item.checked)])));
        options.setAdminStageSubstepChecks(checks);
        options.setAdminStageRevisionNote('');
        options.setAdminStageNoteDraft('');
    } catch (error: any) {
        options.pushLiveLog('warning', error?.message || '관리자 stage 상태 업데이트에 실패했습니다.');
    } finally {
        options.setAdminStageUpdateLoading(false);
    }
}

export async function runCostSimulationAction(options: {
    apiBaseUrl: string;
    costSimulatorForm: Record<string, unknown>;
    onUnauthorized: () => void;
    setCostSimulatorLoading: Dispatch<SetStateAction<boolean>>;
    setCostSimulatorError: Dispatch<SetStateAction<string>>;
    setCostSimulatorResult: Dispatch<SetStateAction<AdminCostSimulatorResponse | null>>;
}) {
    const token = getAdminToken();
    if (!token) {
        options.onUnauthorized();
        return;
    }

    options.setCostSimulatorLoading(true);
    options.setCostSimulatorError('');
    try {
        const response = await fetch(`${options.apiBaseUrl}/api/admin/marketplace/cost-simulator`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify(options.costSimulatorForm),
        });
        if (response.status === 401) {
            options.onUnauthorized();
            return;
        }
        const data = await response.json().catch(() => null);
        if (!response.ok) {
            throw new Error(data?.detail || '비용 시뮬레이션 계산에 실패했습니다.');
        }
        options.setCostSimulatorResult(data as AdminCostSimulatorResponse);
    } catch (error: any) {
        options.setCostSimulatorError(error?.message || '비용 시뮬레이션 실행 중 오류가 발생했습니다.');
    } finally {
        options.setCostSimulatorLoading(false);
    }
}

export function bindAutoConnectGraphSnapshot(options: {
    setAutoConnectGraph: Dispatch<SetStateAction<{ active_connection_id: string; events: any[] }>>;
    readSnapshot: () => { active_connection_id: string; events: any[] };
    storageKey?: string;
}) {
    if (typeof window === 'undefined') {
        return () => undefined;
    }
    const key = options.storageKey || 'admin_auto_connect_graph_v1';
    const syncSnapshot = () => {
        options.setAutoConnectGraph(options.readSnapshot());
    };
    syncSnapshot();
    const handleStorage = (event: StorageEvent) => {
        if (!event.key || event.key === key) {
            syncSnapshot();
        }
    };
    const handleCustomUpdate = () => syncSnapshot();
    window.addEventListener('storage', handleStorage);
    window.addEventListener('admin-auto-connect-updated', handleCustomUpdate as EventListener);
    return () => {
        window.removeEventListener('storage', handleStorage);
        window.removeEventListener('admin-auto-connect-updated', handleCustomUpdate as EventListener);
    };
}

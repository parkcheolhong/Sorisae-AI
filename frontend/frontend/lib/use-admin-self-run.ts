import { useEffect, useRef, useState } from 'react';

import {
    buildSelfRunComparisonRows,
    buildSelfRunPreview,
    SELF_RUN_MODE_LABELS,
} from '@/lib/admin-self-run-presets';

export type SelfPrepareMode = 'self-diagnosis' | 'self-improvement' | 'self-expansion';
export type SelfRunDirectiveTemplate = '' | 'debug_remediation_loop' | 'video_ad_clarity' | 'video_ad_conversion' | 'video_ad_speed_optimization' | 'video_ad_storytelling' | 'video_ad_quality_upgrade' | 'video_ad_new_tech' | 'admin_ops_efficiency' | 'marketplace_conversion' | 'llm_cost_latency';
export type SelfRunDirectiveScope = 'preset_default' | 'diagnosis_only' | 'targeted_implementation' | 'feature_expansion' | 'modernization';

interface UseAdminSelfRunOptions {
    apiBaseUrl: string;
    adminFetch: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;
    adminFinalPassGuide: string;
    selfRunRecordStorageKey: string;
    parseApprovalIdTimestamp: (approvalId?: string | null) => number | null;
    getEffectiveTaskInput: () => string;
    setUnifiedPrompt: (value: string) => void;
    pushAssistantNotice: (stepTitle: string, content: string) => void;
    resolveWorkspacePath: (...fallbackCandidates: Array<string | null | undefined>) => string;
    syncWorkspacePath: (path?: string) => Promise<any>;
    workOutputDir: string;
    liveOutputDir: string;
    setWorkOutputDir: (value: string) => void;
    setLiveOutputDir: (value: string) => void;
    applyPreparedMode: (requestedMode: SelfPrepareMode, prepared: any) => void;
    applyExecutedMode: (requestedMode: SelfPrepareMode, executed: any) => void;
    getDirectiveTemplateLabel: (value?: string) => string;
    getDirectiveScopeLabel: (value?: string) => string;
}

export function useAdminSelfRun(options: UseAdminSelfRunOptions) {
    const selfRunInvocationKeyRef = useRef('');
    const [selfPrepareLoading, setSelfPrepareLoading] = useState(false);
    const [selfPrepareMessage, setSelfPrepareMessage] = useState('');
    const [selfPrepareResult, setSelfPrepareResult] = useState<any | null>(null);
    const [selfRunLoading, setSelfRunLoading] = useState(false);
    const [selfRunApproveLoading, setSelfRunApproveLoading] = useState(false);
    const [selfRunMessage, setSelfRunMessage] = useState('');
    const [selfRunResult, setSelfRunResult] = useState<any | null>(null);
    const [selfRunDirectiveTemplate, setSelfRunDirectiveTemplate] = useState<SelfRunDirectiveTemplate>('');
    const [selfRunDirectiveScope, setSelfRunDirectiveScope] = useState<SelfRunDirectiveScope>('preset_default');
    const [selfRunDirectiveRequest, setSelfRunDirectiveRequest] = useState('');

    const buildSelfRunStatusMessage = (executed: any) => {
        if (executed.status === 'running') {
            const runningTimeText = typeof executed.running_seconds === 'number'
                ? ` 현재 ${executed.running_seconds}초 경과했습니다.`
                : '';
            const diagnosticText = executed.runtime_diagnostic
                ? ` ${executed.runtime_diagnostic}`
                : '';
            const workerLogText = executed.worker_log_path
                ? ` worker 로그: ${executed.worker_log_path}`
                : '';
            return `복제본 생성 후 백그라운드 자가 실행을 시작했습니다. 완료되면 자동으로 결과를 다시 불러옵니다.${runningTimeText}${diagnosticText}${workerLogText}`;
        }
        if (executed.status === 'pending_approval') {
            return `분석, 복제, 실험 실행이 1차 검증 기준으로 승인 대기 상태입니다. ${options.adminFinalPassGuide}`;
        }
        if (executed.status === 'no_changes') {
            return '실행은 완료됐지만 승인 대기할 변경 결과물이 없습니다.';
        }
        if (executed.status === 'failed') {
            return executed.orchestration_error
                ? `실행이 실패했습니다: ${executed.orchestration_error}${executed.worker_log_path ? ` · worker 로그 ${executed.worker_log_path}` : ''}`
                : '실행은 완료됐지만 승인 대기 상태로 올라가지 못했습니다. 리포트를 확인해 주세요.';
        }
        return `원본 반영까지 완료됐습니다. ${options.adminFinalPassGuide}`;
    };

    const createSuggestedSelfRunNotice = (requestedMode: SelfPrepareMode, directiveTemplate: SelfRunDirectiveTemplate, directiveScope: SelfRunDirectiveScope) => {
        const preview = buildSelfRunPreview(requestedMode, directiveScope, directiveTemplate);
        return `${preview.title} · ${preview.executionMode} · ${preview.estimatedDuration} · ${preview.note}`;
    };

    const buildSelfRunStatusLabel = (status: any) => {
        if (status === 'running') return '자가 실행 중';
        if (status === 'pending_approval') return '1차 검증 승인 대기';
        if (status === 'no_changes') return '변경 없음';
        if (status === 'failed') return '실행 실패';
        return '원본 반영 완료(최종 통과 전)';
    };

    const persistSelfRunRecord = (record: any | null) => {
        try {
            if (record?.approval_id) {
                localStorage.setItem(
                    options.selfRunRecordStorageKey,
                    JSON.stringify({ approval_id: record.approval_id, status: record.status }),
                );
            } else {
                localStorage.removeItem(options.selfRunRecordStorageKey);
            }
        } catch {
        }
    };

    const fetchSelfRunRecord = async (request?: {
        approvalId?: string;
        latest?: boolean;
        pendingOnly?: boolean;
        signal?: AbortSignal;
    }) => {
        const url = new URL(`${options.apiBaseUrl}/api/admin/workspace-self-run-record`);
        if (request?.approvalId) url.searchParams.set('approval_id', request.approvalId);
        if (request?.latest) url.searchParams.set('latest', 'true');
        if (request?.pendingOnly) url.searchParams.set('pending_only', 'true');
        const response = await options.adminFetch(url.toString(), { signal: request?.signal });
        if (response.status === 204 || response.status === 404) {
            return null;
        }
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error((data as any).detail || `HTTP ${response.status}`);
        }
        return data;
    };

    const resolveSelfWorkflowSourcePath = async () => {
        const currentPath = options.resolveWorkspacePath(
            selfRunResult?.source_path,
            options.workOutputDir,
            options.liveOutputDir,
        ).trim();
        if (currentPath) {
            return currentPath;
        }
        const listing = await options.syncWorkspacePath();
        return String(listing?.current_path || listing?.root_path || '').trim();
    };

    const restoreLatestSelfRunRecord = async () => {
        try {
            const storedRaw = localStorage.getItem(options.selfRunRecordStorageKey);
            const stored = storedRaw ? JSON.parse(storedRaw) as { approval_id?: string; status?: string } : null;
            const storedApprovalTimestamp = options.parseApprovalIdTimestamp(stored?.approval_id);
            const isFreshStoredApproval = storedApprovalTimestamp != null
                ? (Date.now() - storedApprovalTimestamp) <= (1000 * 60 * 60 * 6)
                : false;
            const restored = stored?.approval_id
                ? (isFreshStoredApproval
                    ? await fetchSelfRunRecord({ approvalId: stored.approval_id })
                    : await fetchSelfRunRecord({ latest: true, pendingOnly: true }))
                : await fetchSelfRunRecord({ latest: true, pendingOnly: true });
            if (!restored?.approval_id) {
                setSelfRunResult(null);
                persistSelfRunRecord(null);
                return null;
            }
            setSelfRunResult(restored);
            const restoredPath = restored.experiment_clone_path || restored.source_path || '';
            options.setWorkOutputDir(restoredPath);
            options.setLiveOutputDir(restoredPath);
            if (restoredPath) {
                await options.syncWorkspacePath(restoredPath);
            }
            persistSelfRunRecord(restored);
            return restored;
        } catch {
            return null;
        }
    };

    const prepareSelfWorkspace = async (
        requestedMode: SelfPrepareMode,
        createExperimentClone: boolean,
    ) => {
        const sourcePath = options.resolveWorkspacePath(options.workOutputDir, options.liveOutputDir).trim();
        if (!sourcePath) {
            setSelfPrepareMessage('분석할 폴더 경로를 먼저 선택해 주세요.');
            return null;
        }

        setSelfPrepareLoading(true);
        setSelfPrepareMessage('');
        try {
            const response = await options.adminFetch(`${options.apiBaseUrl}/api/admin/workspace-self-prepare`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    source_path: sourcePath,
                    mode: requestedMode,
                    create_experiment_clone: createExperimentClone,
                }),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error((data as any).detail || `HTTP ${response.status}`);
            }
            const prepared = data as any;
            setSelfPrepareResult(prepared);
            options.setUnifiedPrompt(prepared.suggested_task || '');
            options.applyPreparedMode(requestedMode, prepared);
            if (prepared.experiment_clone_path) {
                options.setWorkOutputDir(prepared.experiment_clone_path);
                options.setLiveOutputDir(prepared.experiment_clone_path);
                await options.syncWorkspacePath(prepared.experiment_clone_path);
            }
            setSelfPrepareMessage(
                createExperimentClone
                    ? `구조 분석과 실험 복제본 준비가 완료되었습니다. ${prepared.experiment_clone_path || ''}`
                    : '구조 분석 기반 자가 작업문 준비가 완료되었습니다.',
            );
            return prepared;
        } catch (e: any) {
            setSelfPrepareMessage(`자가 작업 준비 실패: ${e.message}`);
            return null;
        } finally {
            setSelfPrepareLoading(false);
        }
    };

    const createExperimentCloneOnly = async () => {
        const sourcePath = options.resolveWorkspacePath(options.workOutputDir, options.liveOutputDir).trim();
        if (!sourcePath) {
            setSelfPrepareMessage('복제할 폴더 경로를 먼저 선택해 주세요.');
            return null;
        }
        setSelfPrepareLoading(true);
        setSelfPrepareMessage('');
        try {
            const response = await options.adminFetch(`${options.apiBaseUrl}/api/admin/workspace-experiment-clone`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ source_path: sourcePath }),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error((data as any).detail || `HTTP ${response.status}`);
            }
            if ((data as any).clone_path) {
                const clonePath = String((data as any).clone_path);
                options.setWorkOutputDir(clonePath);
                options.setLiveOutputDir(clonePath);
                await options.syncWorkspacePath(clonePath);
            }
            setSelfPrepareMessage(`실험 복제본 생성 완료: ${(data as any).clone_path || '-'}`);
            return data;
        } catch (e: any) {
            setSelfPrepareMessage(`실험 복제본 생성 실패: ${e.message}`);
            return null;
        } finally {
            setSelfPrepareLoading(false);
        }
    };

    const executeSelfWorkflow = async (
        requestedMode: SelfPrepareMode,
        overrides?: {
            directiveTemplate?: SelfRunDirectiveTemplate;
            directiveScope?: SelfRunDirectiveScope;
            directiveRequest?: string;
        },
    ) => {
        setSelfRunLoading(true);
        setSelfRunMessage('');
        setSelfRunResult(null);
        const directiveTemplate = overrides?.directiveTemplate ?? selfRunDirectiveTemplate;
        const directiveScope = overrides?.directiveScope ?? selfRunDirectiveScope;
        const directiveRequest = overrides?.directiveRequest ?? (selfRunDirectiveRequest.trim() || options.getEffectiveTaskInput());
        const invocationKey = [requestedMode, directiveTemplate, directiveScope, directiveRequest.trim()].join('||');

        if (selfRunInvocationKeyRef.current === invocationKey || selfRunLoading || selfRunApproveLoading) {
            setSelfRunMessage('동일한 자가 실행 요청이 이미 진행 중입니다. 현재 실행 상태가 갱신될 때까지 기다려 주세요.');
            return null;
        }
        selfRunInvocationKeyRef.current = invocationKey;

        setSelfRunDirectiveTemplate(directiveTemplate);
        setSelfRunDirectiveScope(directiveScope);
        setSelfRunDirectiveRequest(directiveRequest);
        options.pushAssistantNotice(
            SELF_RUN_MODE_LABELS[requestedMode],
            createSuggestedSelfRunNotice(requestedMode, directiveTemplate, directiveScope),
        );
        try {
            const sourcePath = await resolveSelfWorkflowSourcePath();
            const response = await options.adminFetch(`${options.apiBaseUrl}/api/admin/workspace-self-run`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    source_path: sourcePath,
                    mode: requestedMode,
                    directive_template: directiveTemplate,
                    directive_scope: directiveScope,
                    directive_request: directiveRequest,
                }),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error((data as any).detail || `HTTP ${response.status}`);
            }
            const executed = data as any;
            setSelfRunResult(executed);
            persistSelfRunRecord(executed);
            options.setUnifiedPrompt(executed.executed_task || '');
            options.applyExecutedMode(requestedMode, executed);
            const nextPath = executed.experiment_clone_path || sourcePath;
            options.setWorkOutputDir(nextPath);
            options.setLiveOutputDir(nextPath);
            await options.syncWorkspacePath(nextPath);
            setSelfRunMessage(buildSelfRunStatusMessage(executed));
            options.pushAssistantNotice(`${SELF_RUN_MODE_LABELS[requestedMode]} 결과`, buildSelfRunStatusMessage(executed));
            return executed;
        } catch (e: any) {
            setSelfRunMessage(`자가 실행 실패: ${e.message}`);
            options.pushAssistantNotice(`${SELF_RUN_MODE_LABELS[requestedMode]} 실패`, `자가 실행 실패: ${e.message}`);
            return null;
        } finally {
            selfRunInvocationKeyRef.current = '';
            setSelfRunLoading(false);
        }
    };

    const updateAdminStageStatus = async (
        status: 'passed' | 'failed' | 'manual_correction',
        stagePayload: {
            stageNote: string;
            manualCorrection: string;
            substepChecks: Record<string, boolean>;
            revisionNote: string;
            onSuccess?: () => void;
        },
    ) => {
        const stageRun = selfRunResult?.stage_run;
        if (!stageRun?.run_id || !stageRun.current_stage_id) {
            setSelfRunMessage('관리자 stage run이 없습니다. 먼저 self-run을 실행하세요.');
            return null;
        }
        try {
            const response = await options.adminFetch(`${options.apiBaseUrl}/api/admin/workspace-self-run-record/stage-update`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    approval_id: selfRunResult?.approval_id,
                    stage_status: status,
                    stage_note: stagePayload.stageNote,
                    manual_correction: status === 'manual_correction' ? stagePayload.manualCorrection : '',
                    substep_checks: stagePayload.substepChecks,
                    revision_note: stagePayload.revisionNote,
                }),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error((data as any).detail || `HTTP ${response.status}`);
            }
            if ((data as any).latest) {
                setSelfRunResult((data as any).latest);
                persistSelfRunRecord((data as any).latest);
            }
            stagePayload.onSuccess?.();
            return (data as any).latest || null;
        } catch (e: any) {
            setSelfRunMessage(`관리자 단계 상태 업데이트 실패: ${e.message}`);
            return null;
        }
    };

    const runAdminOperationalVerification = async () => {
        try {
            const refreshed = await fetchSelfRunRecord({ approvalId: selfRunResult?.approval_id || '' });
            if (refreshed) {
                setSelfRunResult(refreshed);
                persistSelfRunRecord(refreshed);
                setSelfRunMessage(`운영 API 실검증 완료: ${buildSelfRunStatusMessage(refreshed)}`);
            }
            return refreshed;
        } catch (e: any) {
            setSelfRunMessage(`운영 API 실검증 실패: ${e.message}`);
            return null;
        }
    };

    const approveSelfWorkflow = async () => {
        setSelfRunApproveLoading(true);
        setSelfRunMessage('');
        try {
            const activeRecord = selfRunResult?.approval_id
                ? selfRunResult
                : await fetchSelfRunRecord({ latest: true, pendingOnly: true });
            if (!activeRecord?.approval_id) {
                throw new Error('승인할 실행 결과가 없습니다.');
            }
            if (activeRecord.status !== 'pending_approval') {
                throw new Error('승인 대기 상태의 실행 결과가 없습니다.');
            }
            const response = await options.adminFetch(`${options.apiBaseUrl}/api/admin/workspace-self-run/approve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ approval_id: activeRecord.approval_id }),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error((data as any).detail || `HTTP ${response.status}`);
            }
            const approved = {
                ...(selfRunResult || activeRecord),
                status: 'applied_to_source',
            };
            setSelfRunResult(approved);
            persistSelfRunRecord(approved);
            const sourcePath = activeRecord.source_path || '';
            options.setWorkOutputDir(sourcePath);
            options.setLiveOutputDir(sourcePath);
            await options.syncWorkspacePath(sourcePath);
            setSelfRunMessage(`원본 반영 완료. 백업 경로: ${String((data as any).backup_path || '-')}`);
            options.pushAssistantNotice('승인 반영 완료', `원본 반영 완료. 백업 경로: ${String((data as any).backup_path || '-')}`);
            return approved;
        } catch (e: any) {
            setSelfRunMessage(`승인 적용 실패: ${e.message}`);
            options.pushAssistantNotice('승인 반영 실패', `승인 적용 실패: ${e.message}`);
            return null;
        } finally {
            setSelfRunApproveLoading(false);
        }
    };

    useEffect(() => {
        const approvalId = selfRunResult?.approval_id || '';
        if (!approvalId || selfRunResult?.status !== 'running') {
            return;
        }

        let cancelled = false;
        let pollInFlight = false;
        let activeController: AbortController | null = null;
        const poll = async () => {
            if (pollInFlight) return;
            pollInFlight = true;
            const controller = new AbortController();
            activeController = controller;
            try {
                const latest = await fetchSelfRunRecord({ approvalId, signal: controller.signal });
                if (cancelled) return;
                if (!latest?.approval_id) {
                    setSelfRunResult(null);
                    persistSelfRunRecord(null);
                    return;
                }
                setSelfRunResult(latest);
                persistSelfRunRecord(latest);
                options.setUnifiedPrompt(latest.executed_task || '');
                const nextPath = latest.experiment_clone_path || latest.source_path || '';
                options.setWorkOutputDir(nextPath);
                options.setLiveOutputDir(nextPath);
                if (nextPath) {
                    await options.syncWorkspacePath(nextPath);
                }
                setSelfRunMessage(buildSelfRunStatusMessage(latest));
            } catch (error: any) {
                if (cancelled || controller.signal.aborted) return;
                if (error?.message) {
                    setSelfRunMessage(`자가 실행 기록 조회 실패: ${error.message}`);
                }
            } finally {
                if (activeController === controller) {
                    activeController = null;
                }
                pollInFlight = false;
            }
        };

        void poll();
        const intervalId = window.setInterval(() => {
            void poll();
        }, 3000);
        return () => {
            cancelled = true;
            activeController?.abort();
            window.clearInterval(intervalId);
        };
    }, [selfRunResult?.approval_id, selfRunResult?.status]);

    return {
        selfPrepareLoading,
        selfPrepareMessage,
        selfPrepareResult,
        selfRunLoading,
        selfRunApproveLoading,
        selfRunMessage,
        selfRunResult,
        selfRunDirectiveTemplate,
        selfRunDirectiveScope,
        selfRunDirectiveRequest,
        selfRunBusy: selfRunLoading || selfRunApproveLoading || selfRunResult?.status === 'running',
        setSelfPrepareMessage,
        setSelfRunMessage,
        setSelfRunResult,
        setSelfRunDirectiveTemplate,
        setSelfRunDirectiveScope,
        setSelfRunDirectiveRequest,
        fetchSelfRunRecord,
        persistSelfRunRecord,
        restoreLatestSelfRunRecord,
        resolveSelfWorkflowSourcePath,
        buildSelfRunStatusMessage,
        buildSelfRunStatusLabel,
        buildSelfRunPreview,
        buildSelfRunComparisonRows,
        prepareSelfWorkspace,
        createExperimentCloneOnly,
        executeSelfWorkflow,
        updateAdminStageStatus,
        runAdminOperationalVerification,
        approveSelfWorkflow,
    };
}

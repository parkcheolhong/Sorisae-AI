import { useCallback, useEffect, useMemo, useState } from 'react';
import {
    ADMIN_MANUAL_ORCHESTRATOR_STEPS,
    ADMIN_MANUAL_SECTION_ID_MAP,
    createDefaultAdminManualStepState,
    hasAdminManualStepProgressEvidence,
    normalizeAdminManualStepState,
    type AdminDurationDays,
    type AdminManualMeta,
    type AdminManualStepState,
    type AdminRouterStage,
    type AdminManualStepDefinition,
} from '@/lib/admin-manual-orchestrator';
import { buildAdminManualWorklogMarkdown } from '@/lib/admin-manual-worklog';
import { ADMIN_LLM_PRESET_TASK_KEY, MARKETPLACE_ORCHESTRATOR_BRIDGE_KEY, buildAdminLLMBridgePayload, buildMarketplaceOrchestratorBridgePayload } from '@/lib/admin-orchestrator-bridge';
import type { AdminAdVideoOrderItem } from '@/lib/admin-dashboard-types';
import { downloadZipPackage } from '@/lib/zip-package';

type AdminManualControllerLogLevel = 'info' | 'success' | 'warning';

type AdminManualControllerPushLog = (level: AdminManualControllerLogLevel, message: string) => void;

type ManualTraceOverride = {
    architectureId?: string;
    flowId?: string;
    stepId?: string;
    action?: string;
    bridgeNote?: string;
};

type ExternalStageMirrorPayload = {
    stageRunId: string;
    stageId: string;
    status: string;
    label: string;
    title: string;
    summary: string;
    updatedAt: string;
};

export type UseAdminManualOrchestratorControllerOptions = {
    storageKey: string;
    metaStorageKey: string;
    initialStepId: string;
    latestDedicatedOrder: AdminAdVideoOrderItem | null;
    onOpenAdminLlm: () => void;
    onOpenMarketplaceOrchestrator: () => void;
    pushLiveLog: AdminManualControllerPushLog;
};

export function useAdminManualOrchestratorController(options: UseAdminManualOrchestratorControllerOptions) {
    const [adminManualOrchestratorStepId, setAdminManualOrchestratorStepId] = useState(options.initialStepId);
    const [adminManualStepState, setAdminManualStepState] = useState<Record<string, AdminManualStepState>>({});
    const [adminManualMeta, setAdminManualMeta] = useState<AdminManualMeta>({ domain: '', hostingLine: '' });

    const selectedAdminManualStep = useMemo(
        () => ADMIN_MANUAL_ORCHESTRATOR_STEPS.find((step) => step.id === adminManualOrchestratorStepId) || ADMIN_MANUAL_ORCHESTRATOR_STEPS[0],
        [adminManualOrchestratorStepId],
    );
    const selectedAdminManualStepState = useMemo(
        () => normalizeAdminManualStepState(adminManualStepState[selectedAdminManualStep.id]),
        [adminManualStepState, selectedAdminManualStep.id],
    );
    const selectedAdminManualStepIndex = useMemo(
        () => ADMIN_MANUAL_ORCHESTRATOR_STEPS.findIndex((step) => step.id === selectedAdminManualStep.id),
        [selectedAdminManualStep.id],
    );
    const previousAdminManualStep = selectedAdminManualStepIndex > 0 ? ADMIN_MANUAL_ORCHESTRATOR_STEPS[selectedAdminManualStepIndex - 1] : null;
    const nextAdminManualStep = selectedAdminManualStepIndex >= 0 && selectedAdminManualStepIndex < ADMIN_MANUAL_ORCHESTRATOR_STEPS.length - 1
        ? ADMIN_MANUAL_ORCHESTRATOR_STEPS[selectedAdminManualStepIndex + 1]
        : null;
    const completedManualStepCount = useMemo(
        () => ADMIN_MANUAL_ORCHESTRATOR_STEPS.filter((step) => adminManualStepState[step.id]?.completed).length,
        [adminManualStepState],
    );

    useEffect(() => {
        try {
            const raw = localStorage.getItem(options.storageKey);
            if (raw) {
                const parsed = JSON.parse(raw) as Record<string, Partial<AdminManualStepState>>;
                const normalized = Object.fromEntries(
                    Object.entries(parsed || {}).map(([key, value]) => [key, normalizeAdminManualStepState(value)]),
                ) as Record<string, AdminManualStepState>;
                setAdminManualStepState(normalized);
            }
        } catch {
            setAdminManualStepState({});
        }

        try {
            const metaRaw = localStorage.getItem(options.metaStorageKey);
            if (metaRaw) {
                const parsedMeta = JSON.parse(metaRaw) as AdminManualMeta;
                setAdminManualMeta({
                    domain: parsedMeta?.domain || '',
                    hostingLine: parsedMeta?.hostingLine || '',
                });
            }
        } catch {
            setAdminManualMeta({ domain: '', hostingLine: '' });
        }
    }, [options.metaStorageKey, options.storageKey]);

    useEffect(() => {
        try {
            localStorage.setItem(options.storageKey, JSON.stringify(adminManualStepState));
        } catch {
        }
    }, [adminManualStepState, options.storageKey]);

    useEffect(() => {
        try {
            localStorage.setItem(options.metaStorageKey, JSON.stringify(adminManualMeta));
        } catch {
        }
    }, [adminManualMeta, options.metaStorageKey]);

    const updateAdminManualStepState = useCallback((stepId: string, updater: (prev: AdminManualStepState) => AdminManualStepState) => {
        setAdminManualStepState((prev) => {
            const current = normalizeAdminManualStepState(prev[stepId]);
            return {
                ...prev,
                [stepId]: updater(current),
            };
        });
    }, []);

    const toggleAdminManualAction = useCallback((stepId: string, actionId: string) => {
        updateAdminManualStepState(stepId, (prev) => {
            const exists = prev.doneActionIds.includes(actionId);
            return {
                ...prev,
                doneActionIds: exists ? prev.doneActionIds.filter((item) => item !== actionId) : [...prev.doneActionIds, actionId],
                updatedAt: new Date().toISOString(),
            };
        });
    }, [updateAdminManualStepState]);

    const toggleAdminManualStepCompleted = useCallback((stepId: string, checked: boolean) => {
        updateAdminManualStepState(stepId, (prev) => {
            const hasEvidence = hasAdminManualStepProgressEvidence(prev);
            const nextCompleted = checked && hasEvidence;
            return {
                ...prev,
                completed: nextCompleted,
                routeStage: nextCompleted ? 'completed' : prev.routeStage === 'completed' ? (hasEvidence ? 'review' : 'queued') : prev.routeStage,
                updatedAt: new Date().toISOString(),
            };
        });
    }, [updateAdminManualStepState]);

    const updateAdminManualStepNote = useCallback((stepId: string, note: string) => {
        updateAdminManualStepState(stepId, (prev) => ({
            ...prev,
            note,
            updatedAt: new Date().toISOString(),
        }));
    }, [updateAdminManualStepState]);

    const updateAdminManualStepField = useCallback((stepId: string, field: 'attachmentDraft' | 'referenceUrl' | 'startedAt' | 'endedAt', value: string) => {
        updateAdminManualStepState(stepId, (prev) => ({
            ...prev,
            [field]: value,
            updatedAt: new Date().toISOString(),
        }));
    }, [updateAdminManualStepState]);

    const addAdminManualAttachmentLink = useCallback((stepId: string) => {
        updateAdminManualStepState(stepId, (prev) => {
            const trimmed = prev.attachmentDraft.trim();
            if (!trimmed) return prev;
            if (prev.attachmentLinks.includes(trimmed)) {
                return {
                    ...prev,
                    attachmentDraft: '',
                    updatedAt: new Date().toISOString(),
                };
            }
            return {
                ...prev,
                attachmentLinks: [...prev.attachmentLinks, trimmed],
                attachmentDraft: '',
                updatedAt: new Date().toISOString(),
            };
        });
    }, [updateAdminManualStepState]);

    const removeAdminManualAttachmentLink = useCallback((stepId: string, link: string) => {
        updateAdminManualStepState(stepId, (prev) => ({
            ...prev,
            attachmentLinks: prev.attachmentLinks.filter((item) => item !== link),
            updatedAt: new Date().toISOString(),
        }));
    }, [updateAdminManualStepState]);

    const updateAdminManualStepRouteStage = useCallback((stepId: string, routeStage: AdminRouterStage) => {
        updateAdminManualStepState(stepId, (prev) => {
            const hasEvidence = hasAdminManualStepProgressEvidence(prev);
            const nextCompleted = routeStage === 'completed' ? hasEvidence : false;
            return {
                ...prev,
                routeStage: routeStage === 'completed' && !hasEvidence ? 'queued' : routeStage,
                completed: nextCompleted,
                updatedAt: new Date().toISOString(),
            };
        });
    }, [updateAdminManualStepState]);

    const updateAdminManualStepDuration = useCallback((stepId: string, durationDays: AdminDurationDays) => {
        updateAdminManualStepState(stepId, (prev) => ({
            ...prev,
            durationDays,
            updatedAt: new Date().toISOString(),
        }));
    }, [updateAdminManualStepState]);

    const updateAdminManualExternalStageMirror = useCallback((payload: ExternalStageMirrorPayload) => {
        updateAdminManualStepState(payload.stageId, (prev) => ({
            ...prev,
            externalStageRunId: payload.stageRunId,
            externalStageStatus: payload.status,
            externalStageLabel: payload.label,
            externalStageTitle: payload.title,
            externalStageSummary: payload.summary,
            externalStageUpdatedAt: payload.updatedAt,
            updatedAt: new Date().toISOString(),
        }));
    }, [updateAdminManualStepState]);

    const moveAdminManualStep = useCallback((direction: 'prev' | 'next') => {
        const target = direction === 'prev' ? previousAdminManualStep : nextAdminManualStep;
        if (!target) return;
        setAdminManualOrchestratorStepId(target.id);
    }, [nextAdminManualStep, previousAdminManualStep]);

    const buildAdminManualWorklogPayload = useCallback(() => ({
        generatedAt: new Date().toISOString(),
        currentArchitectureId: selectedAdminManualStep.id,
        currentFlowId: selectedAdminManualStep.flowId,
        currentStepId: selectedAdminManualStep.stepId,
        currentAction: selectedAdminManualStep.action,
        domain: adminManualMeta.domain,
        hostingLine: adminManualMeta.hostingLine,
        sectionMap: ADMIN_MANUAL_SECTION_ID_MAP,
        steps: ADMIN_MANUAL_ORCHESTRATOR_STEPS.map((step) => {
            const state = adminManualStepState[step.id] || createDefaultAdminManualStepState();
            return {
                id: step.id,
                label: step.label,
                title: step.title,
                flowId: step.flowId,
                stepId: step.stepId,
                action: step.action,
                routeStage: state.routeStage,
                durationDays: state.durationDays,
                completed: state.completed,
                note: state.note,
                doneActionIds: state.doneActionIds,
                attachmentLinks: state.attachmentLinks,
                referenceUrl: state.referenceUrl,
                startedAt: state.startedAt,
                endedAt: state.endedAt,
            };
        }),
    }), [adminManualMeta.domain, adminManualMeta.hostingLine, adminManualStepState, selectedAdminManualStep.action, selectedAdminManualStep.flowId, selectedAdminManualStep.id, selectedAdminManualStep.stepId]);

    const downloadAdminManualWorklog = useCallback((format: 'md' | 'json' | 'zip') => {
        if (typeof window === 'undefined') return;
        const payload = buildAdminManualWorklogPayload();
        const markdown = buildAdminManualWorklogMarkdown(payload);
        if (format === 'zip') {
            downloadZipPackage('admin_manual_orchestrator_package.zip', [
                { name: 'admin_manual_worklog.md', content: markdown },
                { name: 'admin_manual_worklog.json', content: JSON.stringify(payload, null, 2) },
                { name: 'admin_manual_flow.mmd', content: markdown.split('## Mermaid Flow\n```mermaid\n')[1]?.split('\n```')[0] || '' },
                { name: 'admin_section_id_map.json', content: JSON.stringify(ADMIN_MANUAL_SECTION_ID_MAP, null, 2) },
            ]);
            return;
        }
        const content = format === 'json' ? JSON.stringify(payload, null, 2) : markdown;
        const blob = new Blob([content], { type: format === 'json' ? 'application/json;charset=utf-8' : 'text/markdown;charset=utf-8' });
        const url = window.URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = `admin_manual_worklog.${format}`;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        window.URL.revokeObjectURL(url);
    }, [buildAdminManualWorklogPayload]);

    const openMarketplaceOrchestratorBridge = useCallback((order: AdminAdVideoOrderItem, traceOverride?: ManualTraceOverride) => {
        try {
            localStorage.setItem(
                MARKETPLACE_ORCHESTRATOR_BRIDGE_KEY,
                JSON.stringify(buildMarketplaceOrchestratorBridgePayload(order, traceOverride)),
            );
            options.pushLiveLog('success', `${(traceOverride?.flowId || 'FLOW-002')} / ${(traceOverride?.stepId || 'FLOW-002-4')} / ${(traceOverride?.action || 'ORDER_RECORD')} 기준으로 전용 주문 #${order.id}를 마켓플레이스 오케스트레이터로 전달했습니다.`);
            options.onOpenMarketplaceOrchestrator();
        } catch (error) {
            console.error('Failed to bridge orchestrator payload:', error);
            options.pushLiveLog('warning', '오케스트레이터 연결 payload 저장에 실패했습니다.');
        }
    }, [options]);

    const openAdminLlmOrchestratorBridge = useCallback((step: AdminManualStepDefinition, state: AdminManualStepState) => {
        try {
            const payload = buildAdminLLMBridgePayload(step, state, adminManualMeta);
            localStorage.setItem(ADMIN_LLM_PRESET_TASK_KEY, JSON.stringify(payload));
            options.pushLiveLog('success', `${step.flowId} / ${step.stepId} / ${step.action} 기준으로 관리자 LLM 오케스트레이터 실행을 시작합니다.`);
            options.onOpenAdminLlm();
        } catch (error) {
            console.error('Failed to bridge admin llm payload:', error);
            options.pushLiveLog('warning', '관리자 LLM 오케스트레이터 연결 payload 저장에 실패했습니다.');
        }
    }, [adminManualMeta, options]);

    return {
        adminManualOrchestratorStepId,
        setAdminManualOrchestratorStepId,
        adminManualStepState,
        adminManualMeta,
        setAdminManualMeta,
        selectedAdminManualStep,
        selectedAdminManualStepState,
        previousAdminManualStep,
        nextAdminManualStep,
        completedManualStepCount,
        latestDedicatedOrder: options.latestDedicatedOrder,
        toggleAdminManualAction,
        toggleAdminManualStepCompleted,
        updateAdminManualStepNote,
        updateAdminManualStepField,
        addAdminManualAttachmentLink,
        removeAdminManualAttachmentLink,
        updateAdminManualStepRouteStage,
        updateAdminManualStepDuration,
        updateAdminManualExternalStageMirror,
        moveAdminManualStep,
        buildAdminManualWorklogPayload,
        downloadAdminManualWorklog,
        openMarketplaceOrchestratorBridge,
        openAdminLlmOrchestratorBridge,
    };
}

export function assertAdminManualOrchestratorControllerContract() {
    if (ADMIN_MANUAL_ORCHESTRATOR_STEPS.length !== 10 || ADMIN_MANUAL_SECTION_ID_MAP.length !== 10) {
        throw new Error('admin manual orchestrator controller contract 누락: Refiner/Fixer 포함 10개 단계 오케스트레이터/섹션 맵 필요');
    }
}

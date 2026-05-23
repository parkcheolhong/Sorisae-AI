import type { AdminAdVideoOrderItem } from '@/lib/admin-dashboard-types';
import type { AdminManualMeta, AdminManualStepDefinition, AdminManualStepState } from '@/lib/admin-manual-orchestrator';

export const ADMIN_LLM_PRESET_TASK_KEY = 'admin_llm_preset_task_v1';
export const MARKETPLACE_ORCHESTRATOR_BRIDGE_KEY = 'marketplace_orchestrator_bridge_v1';

export type MarketplaceOrchestratorOrderBridgePayload = {
    source: 'admin-dashboard';
    bridgedAt: string;
    architectureId?: string;
    flowId: string;
    stepId: string;
    action: string;
    bridgeNote?: string;
    orderId: number;
    title: string;
    imagePrompt: string;
    portraitImagePrompt: string;
    productImagePrompts: string[];
    backgroundPrompt: string;
    captionText: string;
    scenarioScript: string;
    actionTemplateKey: string;
    motionTempo: 'slow' | 'normal' | 'fast' | 'run';
    durationSeconds: number;
    storyboard: NonNullable<AdminAdVideoOrderItem['storyboard']>;
};

export type MarketplaceOrchestratorAdminLlmBridgePayload = {
    source: 'admin-llm';
    bridgedAt: string;
    productId: string;
    projectName: string;
    task: string;
    capabilityId?: string;
    presetId?: string;
    note?: string;
};

export type MarketplaceOrchestratorBridgePayload =
    | MarketplaceOrchestratorOrderBridgePayload
    | MarketplaceOrchestratorAdminLlmBridgePayload;

export type AdminLLMBridgePayload = {
    id: string;
    title: string;
    mode: string;
    task: string;
    description: string;
    source: 'admin-dashboard';
    architectureId: string;
    flowId: string;
    stepId: string;
    action: string;
    autoRun?: boolean;
};

export function buildAdminManualExecutionTask(
    step: AdminManualStepDefinition,
    state: AdminManualStepState,
    meta: AdminManualMeta,
): string {
    const doneLabels = step.manualActions
        .filter((item) => state.doneActionIds.includes(item.id))
        .map((item) => item.label);
    const noteBlock = String(state.note || '').trim()
        ? `\n[관리자 메모]\n${String(state.note || '').trim()}`
        : '';
    const doneBlock = doneLabels.length > 0
        ? `\n[완료된 수동 확인]\n- ${doneLabels.join('\n- ')}`
        : '';
    const refBlock = String(state.referenceUrl || '').trim()
        ? `\n[참고 URL]\n${String(state.referenceUrl || '').trim()}`
        : '';
    const hostingBlock = [meta.domain, meta.hostingLine].filter(Boolean).join(' / ');
    return [
        `[관리자 수동 오케스트레이터 실행]`,
        `- architecture_id: ${step.id}`,
        `- flow_id: ${step.flowId}`,
        `- step_id: ${step.stepId}`,
        `- action: ${step.action}`,
        `- 단계 제목: ${step.title}`,
        `- 단계 설명: ${step.detail}`,
        hostingBlock ? `- 운영 환경: ${hostingBlock}` : '',
        '',
        `위 trace 기준으로 관리자 수동 오케스트레이터 점검 내용을 실행 가능한 작업 계획으로 정리하고 필요한 구현/검증 순서를 제안해줘.`,
        doneBlock,
        noteBlock,
        refBlock,
    ].filter(Boolean).join('\n');
}

export function buildAdminLLMBridgePayload(
    step: AdminManualStepDefinition,
    state: AdminManualStepState,
    meta: AdminManualMeta,
): AdminLLMBridgePayload {
    return {
        id: `manual-${step.id.toLowerCase()}`,
        title: `${step.label} ${step.title}`,
        mode: step.mode || 'full',
        task: buildAdminManualExecutionTask(step, state, meta),
        description: `${step.flowId} / ${step.stepId} / ${step.action} 기준 관리자 수동 실행 브리지`,
        source: 'admin-dashboard',
        architectureId: step.id,
        flowId: step.flowId,
        stepId: step.stepId,
        action: step.action,
        autoRun: true,
    };
}

export function buildMarketplaceOrchestratorBridgePayload(
    order: AdminAdVideoOrderItem,
    traceOverride?: {
        architectureId?: string;
        flowId?: string;
        stepId?: string;
        action?: string;
        bridgeNote?: string;
    },
): MarketplaceOrchestratorOrderBridgePayload {
    return {
        source: 'admin-dashboard',
        bridgedAt: new Date().toISOString(),
        architectureId: traceOverride?.architectureId,
        flowId: traceOverride?.flowId || 'FLOW-002',
        stepId: traceOverride?.stepId || 'FLOW-002-4',
        action: traceOverride?.action || 'ORDER_RECORD',
        bridgeNote: traceOverride?.bridgeNote,
        orderId: order.id,
        title: order.title || '전용 광고 주문',
        imagePrompt: String(order.image_prompt || '').trim(),
        portraitImagePrompt: String(order.portrait_image_prompt || '').trim(),
        productImagePrompts: Array.isArray(order.product_image_prompts) ? order.product_image_prompts.filter(Boolean) : [],
        backgroundPrompt: String(order.background_prompt || '').trim(),
        captionText: String(order.caption_text || '').trim(),
        scenarioScript: String(order.scenario_script || '').trim(),
        actionTemplateKey: String(order.action_template_key || 'cup_lift_drink').trim() || 'cup_lift_drink',
        motionTempo: (order.motion_tempo || 'normal'),
        durationSeconds: Math.max(1, Number(order.duration_seconds || 0) || Math.ceil((order.storyboard || []).reduce((sum, scene) => sum + Number(scene.duration_sec || 0), 0)) || 5),
        storyboard: Array.isArray(order.storyboard) ? order.storyboard.map((scene) => ({
            cut: Number(scene.cut || 0),
            title: String(scene.title || '').trim(),
            duration_sec: Number(scene.duration_sec || 0),
            narration_line: String(scene.narration_line || '').trim(),
            visual_focus: String(scene.visual_focus || '').trim(),
            scene_prompt: String(scene.scene_prompt || '').trim(),
            designer_prompt: String(scene.designer_prompt || '').trim(),
            motion_speed_percent: Number(scene.motion_speed_percent || 100),
            source_scenario: String(scene.source_scenario || '').trim(),
            start_sec: Number(scene.start_sec || 0),
            end_sec: Number(scene.end_sec || 0),
            asset_source: scene.asset_source || 'auto',
            product_index: scene.product_index ?? null,
            asset_ref: String(scene.asset_ref || '').trim(),
        })) : [],
    };
}

export function buildMarketplaceOrchestratorAdminLlmBridgePayload(payload: {
    productId: string;
    projectName: string;
    task: string;
    capabilityId?: string;
    presetId?: string;
    note?: string;
}): MarketplaceOrchestratorAdminLlmBridgePayload {
    return {
        source: 'admin-llm',
        bridgedAt: new Date().toISOString(),
        productId: String(payload.productId || 'code-generator-deployment-kit').trim() || 'code-generator-deployment-kit',
        projectName: String(payload.projectName || 'admin-llm-bridge').trim() || 'admin-llm-bridge',
        task: String(payload.task || '').trim(),
        capabilityId: String(payload.capabilityId || '').trim() || undefined,
        presetId: String(payload.presetId || '').trim() || undefined,
        note: String(payload.note || '').trim() || undefined,
    };
}

export function assertAdminOrchestratorBridgeContract() {
    const payload = buildAdminLLMBridgePayload({
        id: 'ARCH-001',
        label: '1 구조 설계',
        title: '구조 설계 고정',
        detail: 'detail',
        flowId: 'FLOW-001',
        stepId: 'FLOW-001-1',
        action: 'STRUCTURE_DESIGN',
        mode: 'full',
        manualActions: [],
    }, {
        completed: false,
        note: '',
        doneActionIds: [],
        routeStage: 'queued',
        durationDays: '1일',
        attachmentLinks: [],
        attachmentDraft: '',
        referenceUrl: '',
        startedAt: '',
        endedAt: '',
    }, {
        domain: '',
        hostingLine: '',
    });
    if (!payload.task.includes('[관리자 수동 오케스트레이터 실행]')) {
        throw new Error('admin orchestrator bridge contract 누락: 관리자 수동 실행 태스크 헤더 필요');
    }
}

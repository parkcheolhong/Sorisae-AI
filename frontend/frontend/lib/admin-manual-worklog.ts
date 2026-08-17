import {
    ADMIN_MANUAL_SECTION_ID_MAP,
    ADMIN_ROUTER_STAGE_LABELS,
    type AdminDurationDays,
    type AdminRouterStage,
} from '@/lib/admin-manual-orchestrator';

export type AdminManualWorklogPayload = {
    generatedAt: string;
    currentArchitectureId: string;
    currentFlowId: string;
    currentStepId: string;
    currentAction: string;
    domain: string;
    hostingLine: string;
    steps: Array<{
        id: string;
        label: string;
        title: string;
        flowId: string;
        stepId: string;
        action: string;
        routeStage: AdminRouterStage;
        durationDays: AdminDurationDays;
        completed: boolean;
        note: string;
        doneActionIds: string[];
        attachmentLinks: string[];
        referenceUrl: string;
        startedAt: string;
        endedAt: string;
    }>;
};

export function buildAdminManualWorklogMarkdown(payload: AdminManualWorklogPayload) {
    const mermaidLines = [
        'flowchart LR',
        '    classDef queued fill:#eef2ff,stroke:#6366f1,color:#1e1b4b,stroke-width:1px;',
        '    classDef active fill:#dbeafe,stroke:#2563eb,color:#1e3a8a,stroke-width:2px;',
        '    classDef review fill:#fef3c7,stroke:#d97706,color:#78350f,stroke-width:2px;',
        '    classDef blocked fill:#fee2e2,stroke:#dc2626,color:#7f1d1d,stroke-width:2px;',
        '    classDef completed fill:#dcfce7,stroke:#16a34a,color:#14532d,stroke-width:2px;',
        ...payload.steps.flatMap((step, index) => {
            const nodeId = `step${index + 1}`;
            const nextNodeId = payload.steps[index + 1] ? `step${index + 2}` : null;
            const lines = [
                `    ${nodeId}["${step.id}<br/>${step.title}<br/>${ADMIN_ROUTER_STAGE_LABELS[step.routeStage]} · ${step.durationDays}"]`,
                `    class ${nodeId} ${step.routeStage};`,
            ];
            if (nextNodeId) {
                lines.push(`    ${nodeId} -->|${step.flowId}/${step.stepId}/${step.action}| ${nextNodeId}`);
            }
            return lines;
        }),
    ];
    return [
        '# 관리자 오케스트레이터 설계도/작업일지',
        '',
        '## Summary',
        `- generated_at: ${payload.generatedAt}`,
        `- current_architecture_id: ${payload.currentArchitectureId}`,
        `- current_flow_id: ${payload.currentFlowId}`,
        `- current_step_id: ${payload.currentStepId}`,
        `- current_action: ${payload.currentAction}`,
        `- domain: ${payload.domain || '-'}`,
        `- hosting_line: ${payload.hostingLine || '-'}`,
        '',
        '## Section ID Assembly Map',
        ...ADMIN_MANUAL_SECTION_ID_MAP.flatMap((section) => [
            `- ${section.sectionId} ${section.title}`,
            `  - architecture_id: ${section.architectureId}`,
            `  - flow_id: ${section.flowId}`,
            `  - step_id: ${section.stepId}`,
            `  - action: ${section.action}`,
            `  - assembly_ids: ${section.assemblyIds.join(', ')}`,
            `  - features: ${section.featureSummary}`,
        ]),
        '',
        '## Step Worklog',
        ...payload.steps.flatMap((step) => [
            `- ${step.id} ${step.label} ${step.title}`,
            `  - route_stage: ${step.routeStage}`,
            `  - duration_days: ${step.durationDays}`,
            `  - completed: ${step.completed}`,
            `  - flow_step_action: ${step.flowId} / ${step.stepId} / ${step.action}`,
            `  - done_actions: ${step.doneActionIds.join(', ') || '-'}`,
            `  - attachment_links: ${step.attachmentLinks.join(', ') || '-'}`,
            `  - reference_url: ${step.referenceUrl || '-'}`,
            `  - started_at: ${step.startedAt || '-'}`,
            `  - ended_at: ${step.endedAt || '-'}`,
            `  - note: ${step.note || '-'}`,
        ]),
        '',
        '## Mermaid Flow',
        '```mermaid',
        ...mermaidLines,
        '```',
        '',
    ].join('\n');
}

export function assertAdminManualWorklogContract() {
    const markdown = buildAdminManualWorklogMarkdown({
        generatedAt: new Date(0).toISOString(),
        currentArchitectureId: 'ARCH-001',
        currentFlowId: 'FLOW-001',
        currentStepId: 'FLOW-001-1',
        currentAction: 'STRUCTURE_DESIGN',
        domain: '',
        hostingLine: '',
        steps: [],
    });
    if (!markdown.includes('## Section ID Assembly Map') || !markdown.includes('## Mermaid Flow')) {
        throw new Error('admin manual worklog contract 누락: markdown 핵심 섹션 필요');
    }
}

import type { SelfRunDirectiveScope, SelfRunDirectiveTemplate } from '@/lib/use-admin-self-run';

export type ExpansionExperimentRecommendedSelfRun = {
    endpoint?: string;
    mode?: string;
    execution_mode?: string;
    directive_template?: string;
    directive_scope?: string;
    directive_request?: string;
    create_experiment_clone?: boolean;
};

export type ExpansionExperimentPayload = {
    work_document_title?: string;
    work_document?: string;
    focus_path?: string;
    proposal_id?: string;
    recommended_self_run?: ExpansionExperimentRecommendedSelfRun;
};

export type ExpansionExperimentDetailLike = {
    expansion_experiment?: ExpansionExperimentPayload | null;
};

export function extractExpansionExperiment(
    detail: ExpansionExperimentDetailLike | null | undefined,
): ExpansionExperimentPayload | null {
    const payload = detail?.expansion_experiment;
    if (!payload || typeof payload !== 'object') {
        return null;
    }
    if (!payload.work_document && !payload.recommended_self_run) {
        return null;
    }
    return payload;
}

export function buildExpansionExperimentRunOverrides(
    detail: ExpansionExperimentDetailLike | null | undefined,
) {
    const expansion = extractExpansionExperiment(detail);
    const recommended = expansion?.recommended_self_run || {};
    const directiveRequest = String(
        recommended.directive_request
        || expansion?.work_document
        || 'Tower Crane 균형형(B) self-expansion full 실험을 복제본에서 실행하고 검증 후 승인 대기하세요.',
    ).trim();

    return {
        directiveTemplate: (recommended.directive_template || 'tower_crane_expansion') as SelfRunDirectiveTemplate,
        directiveScope: (recommended.directive_scope || 'feature_expansion') as SelfRunDirectiveScope,
        directiveRequest,
        unifiedPrompt: expansion?.work_document || directiveRequest,
    };
}

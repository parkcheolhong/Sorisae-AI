import type { AdvisoryNextAction, SuggestedSelfRunPreview } from '@/lib/use-orchestrator-chat';
import type { SelfRunDirectiveScope, SelfRunDirectiveTemplate } from '@/lib/use-admin-self-run';

interface SuggestedSelfRunPreviewLike extends SuggestedSelfRunPreview {
    directiveTemplate: SelfRunDirectiveTemplate;
    directiveScope: SelfRunDirectiveScope;
}

export function createSelfRunDraftFlow(options: {
    inferSuggestionDirectiveTemplate: (action: AdvisoryNextAction) => SelfRunDirectiveTemplate;
    buildSuggestionDirectiveRequest: (action: AdvisoryNextAction) => string;
    buildSuggestedSelfRunPreview: (options: {
        action: AdvisoryNextAction;
        directiveTemplate: SelfRunDirectiveTemplate;
        directiveRequest: string;
    }) => SuggestedSelfRunPreviewLike;
    setSuggestedSelfRunPreview: (value: SuggestedSelfRunPreviewLike | null) => void;
    executeSelfWorkflow: (requestedMode: SuggestedSelfRunPreviewLike['requestedMode'], overrides: {
        directiveTemplate: SelfRunDirectiveTemplate;
        directiveScope: SelfRunDirectiveScope;
        directiveRequest: string;
    }) => Promise<unknown>;
    setSelfRunDirectiveTemplate: (value: SelfRunDirectiveTemplate) => void;
    setSelfRunDirectiveScope: (value: SelfRunDirectiveScope) => void;
    setSelfRunDirectiveRequest: (value: string) => void;
}) {
    const runSuggestedSelfWorkflow = async (action: AdvisoryNextAction) => {
        const directiveTemplate = options.inferSuggestionDirectiveTemplate(action);
        const directiveRequest = options.buildSuggestionDirectiveRequest(action);
        options.setSuggestedSelfRunPreview(options.buildSuggestedSelfRunPreview({
            action,
            directiveTemplate,
            directiveRequest,
        }));
    };

    const confirmSuggestedSelfWorkflow = async (preview: SuggestedSelfRunPreviewLike | null) => {
        if (!preview) {
            return;
        }

        await options.executeSelfWorkflow(preview.requestedMode, {
            directiveTemplate: preview.directiveTemplate,
            directiveScope: preview.directiveScope,
            directiveRequest: preview.directiveRequest,
        });
        options.setSuggestedSelfRunPreview(null);
    };

    const cancelSuggestedSelfWorkflow = () => {
        options.setSuggestedSelfRunPreview(null);
    };

    const applySuggestedSelfWorkflowDraft = (preview: SuggestedSelfRunPreviewLike | null) => {
        if (!preview) {
            return;
        }

        options.setSelfRunDirectiveTemplate(preview.directiveTemplate);
        options.setSelfRunDirectiveScope(preview.directiveScope);
        options.setSelfRunDirectiveRequest(preview.directiveRequest);
        options.setSuggestedSelfRunPreview(null);
    };

    return {
        runSuggestedSelfWorkflow,
        confirmSuggestedSelfWorkflow,
        cancelSuggestedSelfWorkflow,
        applySuggestedSelfWorkflowDraft,
    };
}

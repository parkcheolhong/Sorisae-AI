import type { ChatFunctionMode } from '@/lib/use-orchestrator-chat';
import type { SelfPrepareMode, SelfRunDirectiveScope } from '@/lib/use-admin-self-run';
import { resolveGeneratorSelfRunDirectiveScope } from '@/lib/admin-self-run-presets';

export interface GeneratorCapabilityDefinitionLike {
    id: string;
    title: string;
    modalKey: 'capability' | 'runtime' | 'directive' | 'verification';
    presetId: SelfPrepareMode;
    featureMode: ChatFunctionMode;
    defaultDirective: string;
    marketplaceOfferId: string;
}

export interface GeneratorPresetLike {
    task?: string;
    mode?: string;
}

export interface GeneratorOfferLike {
    title: string;
    description: string;
    priceLabel: string;
    tags: string[];
    generatorId: string;
}

export interface GeneratorControlDraft {
    directivePreview: string;
    directiveScope: SelfRunDirectiveScope;
    directiveRequest: string;
    shouldOpenRuntimeEditor: boolean;
}

export const buildGeneratorDirectivePreview = (
    definition: GeneratorCapabilityDefinitionLike,
    preset: GeneratorPresetLike | null,
) => ([
    preset?.task || '',
    `[${definition.title} 주특기 활성화]`,
    definition.defaultDirective,
].filter(Boolean).join('\n\n'));

export const buildGeneratorControlDraft = (
    definition: GeneratorCapabilityDefinitionLike,
    preset: GeneratorPresetLike | null,
): GeneratorControlDraft => {
    const directivePreview = buildGeneratorDirectivePreview(definition, preset);
    return {
        directivePreview,
        directiveScope: resolveGeneratorSelfRunDirectiveScope(definition.presetId),
        directiveRequest: directivePreview,
        shouldOpenRuntimeEditor: definition.modalKey === 'runtime',
    };
};

export const buildGeneratorMarketplaceAppendix = (offer: GeneratorOfferLike) => (
    `\n[마켓플레이스 상품 진열]\n상품명: ${offer.title}\n설명: ${offer.description}\n가격: ${offer.priceLabel}\n태그: ${offer.tags.join(', ')}`
);

export function applyGeneratorControlOrchestration(options: {
    generatorId: string;
    getGeneratorDefinition: (generatorId: string) => GeneratorCapabilityDefinitionLike | null;
    getPresetById: (presetId: SelfPrepareMode) => GeneratorPresetLike | null;
    setActiveGeneratorId: (value: string) => void;
    setActiveGeneratorModal: (value: GeneratorCapabilityDefinitionLike['modalKey']) => void;
    setSelectedPreset: (preset: GeneratorPresetLike | null) => void;
    setSelectedCapabilityActionId: (value: string) => void;
    setChatFunctionMode: (value: ChatFunctionMode) => void;
    setUnifiedPrompt: (value: string) => void;
    setSelfRunDirectiveTemplate: (value: '') => void;
    setSelfRunDirectiveScope: (value: SelfRunDirectiveScope) => void;
    setSelfRunDirectiveRequest: (value: string) => void;
    setMode: (value: string) => void;
    setRuntimeEditorOpen: (value: boolean) => void;
}) {
    const definition = options.getGeneratorDefinition(options.generatorId);
    if (!definition) {
        return null;
    }
    const preset = options.getPresetById(definition.presetId);
    const controlDraft = buildGeneratorControlDraft(definition, preset);

    options.setActiveGeneratorId(options.generatorId);
    options.setActiveGeneratorModal(definition.modalKey);
    options.setSelectedPreset(preset);
    options.setSelectedCapabilityActionId(definition.id);
    options.setChatFunctionMode(definition.featureMode);
    options.setUnifiedPrompt(controlDraft.directivePreview);
    options.setSelfRunDirectiveTemplate('');
    options.setSelfRunDirectiveScope(controlDraft.directiveScope);
    options.setSelfRunDirectiveRequest(controlDraft.directiveRequest);
    if (preset) {
        options.setMode(preset.mode || 'review');
    }
    if (controlDraft.shouldOpenRuntimeEditor) {
        options.setRuntimeEditorOpen(true);
    }

    return { definition, preset, controlDraft };
}

export function applyGeneratorModalActionOrchestration(options: {
    actionId: 'open-capability' | 'open-runtime' | 'open-directive' | 'apply-marketplace';
    activeGeneratorId: string;
    getGeneratorDefinition: (generatorId: string) => GeneratorCapabilityDefinitionLike | null;
    applyGeneratorControl: (generatorId: string) => void;
    applyGeneratorMarketplaceOffer: (offerId: string) => void;
    setActiveGeneratorModal: (value: GeneratorCapabilityDefinitionLike['modalKey']) => void;
    setRuntimeEditorOpen: (value: boolean) => void;
}) {
    const definition = options.getGeneratorDefinition(options.activeGeneratorId);
    if (!definition) {
        return null;
    }
    if (options.actionId === 'apply-marketplace') {
        options.applyGeneratorMarketplaceOffer(definition.marketplaceOfferId);
        return definition;
    }
    const nextModalKey = options.actionId === 'open-capability'
        ? 'capability'
        : options.actionId === 'open-runtime'
            ? 'runtime'
            : 'directive';
    options.setActiveGeneratorModal(nextModalKey);
    if (nextModalKey === 'runtime') {
        options.setRuntimeEditorOpen(true);
    }
    options.applyGeneratorControl(definition.id);
    return definition;
}

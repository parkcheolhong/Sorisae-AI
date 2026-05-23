import type { AdminGeneratorDetailModalData } from '@/components/admin/admin-generator-detail-modal';
import { buildAdminGeneratorDetailModalData } from '@/lib/admin-generator-modal-data';

interface GeneratorDefinitionLike {
    id: string;
    marketplaceOfferId: string;
    presetId: string;
    featureMode: string;
}

interface GeneratorCapabilityStatusRowLike {
    id: string;
    state: string;
    metric: string;
    detail: string;
}

interface GeneratorOfferLike {
    id: string;
}

interface GeneratorPresetLike {
    title?: string;
    task?: string;
}

interface GeneratorFeatureLike {
    title: string;
}

export function buildActiveAdminGeneratorData<TDefinition extends GeneratorDefinitionLike, TOffer extends GeneratorOfferLike, TPreset extends GeneratorPresetLike, TFeature extends GeneratorFeatureLike>(options: {
    activeGeneratorId: string;
    getGeneratorDefinition: (generatorId: string) => TDefinition | null;
    generatorOffers: TOffer[];
    generatorStatusRows: GeneratorCapabilityStatusRowLike[];
    getPresetById: (presetId: string) => TPreset | null;
    features: Array<TFeature & { key: string }>;
}) {
    const activeGeneratorDefinition = options.getGeneratorDefinition(options.activeGeneratorId);
    const activeGeneratorOffer = activeGeneratorDefinition
        ? options.generatorOffers.find((item) => item.id === activeGeneratorDefinition.marketplaceOfferId) || null
        : null;
    const activeGeneratorStatus = activeGeneratorDefinition
        ? options.generatorStatusRows.find((item) => item.id === activeGeneratorDefinition.id) || null
        : null;
    const activeGeneratorPreset = activeGeneratorDefinition
        ? options.getPresetById(activeGeneratorDefinition.presetId)
        : null;
    const activeGeneratorFeature = activeGeneratorDefinition
        ? options.features.find((feature) => feature.key === activeGeneratorDefinition.featureMode) || null
        : null;
    const activeGeneratorDetailModalData: AdminGeneratorDetailModalData | null = buildAdminGeneratorDetailModalData({
        definition: activeGeneratorDefinition as any,
        offer: activeGeneratorOffer as any,
        status: activeGeneratorStatus || null,
        preset: activeGeneratorPreset || null,
        feature: activeGeneratorFeature || null,
    });

    return {
        activeGeneratorDefinition,
        activeGeneratorOffer,
        activeGeneratorStatus,
        activeGeneratorPreset,
        activeGeneratorFeature,
        activeGeneratorDetailModalData,
    };
}

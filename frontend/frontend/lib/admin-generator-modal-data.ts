import type { AdminGeneratorDetailModalData } from '@/components/admin/admin-generator-detail-modal';
import { buildGeneratorDirectivePreview } from '@/lib/admin-generator-adapter';
import type { ChatFunctionMode } from '@/lib/use-orchestrator-chat';
import type { SelfPrepareMode } from '@/lib/use-admin-self-run';

interface GeneratorDefinitionLike {
    id: string;
    title: string;
    summary: string;
    modalKey: 'capability' | 'runtime' | 'directive' | 'verification';
    finalStage: string;
    presetId: SelfPrepareMode;
    featureMode: ChatFunctionMode;
    defaultDirective: string;
    marketplaceOfferId: string;
}

interface GeneratorOfferLike {
    title: string;
    priceLabel: string;
    badge: string;
    tags: string[];
}

interface GeneratorStatusLike {
    state: string;
    metric: string;
    detail: string;
}

interface GeneratorPresetLike {
    title?: string;
    task?: string;
}

interface GeneratorFeatureLike {
    title: string;
}

export function buildAdminGeneratorDetailModalData(options: {
    definition: GeneratorDefinitionLike | null;
    offer: GeneratorOfferLike | null;
    status: GeneratorStatusLike | null;
    preset: GeneratorPresetLike | null;
    feature: GeneratorFeatureLike | null;
}): AdminGeneratorDetailModalData | null {
    const { definition, offer, status, preset, feature } = options;
    if (!definition || !offer || !status) {
        return null;
    }

    return {
        id: definition.id,
        title: definition.title,
        summary: definition.summary,
        finalStage: definition.finalStage,
        presetLabel: preset?.title || definition.presetId,
        featureLabel: feature?.title || definition.featureMode,
        currentState: status.state,
        metric: status.metric,
        detail: status.detail,
        directivePreview: buildGeneratorDirectivePreview(definition, preset),
        marketplaceOfferTitle: offer.title,
        marketplaceOfferPrice: offer.priceLabel,
        marketplaceOfferBadge: offer.badge,
        tags: offer.tags,
        actions: [
            {
                id: 'open-capability',
                label: 'Capability 점검 열기',
                summary: '기능 상세/검증 결과 패널로 바로 전환합니다.',
            },
            {
                id: 'open-runtime',
                label: 'Runtime 제어 열기',
                summary: '이 코드생성기에 맞는 runtime/모델 제어 패널을 엽니다.',
            },
            {
                id: 'open-directive',
                label: '지시형 챗봇 고정',
                summary: '전용 directive를 입력창에 주입하고 작업 모드를 고정합니다.',
            },
            {
                id: 'apply-marketplace',
                label: '마켓 상품 반영',
                summary: '연결 상품 설명을 작업문과 마켓 진열 흐름에 동시에 반영합니다.',
            },
        ],
    };
}

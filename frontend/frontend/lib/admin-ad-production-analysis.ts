import type { AdminAdVideoOrderItem } from '@/lib/admin-dashboard-types';

export type AdminAdProductionStage = {
    id: string;
    label: string;
    title: string;
    ready: boolean;
    detail: string;
};

export function isAdminPreviewableImage(value?: string | null): boolean {
    const text = (value || '').trim();
    if (!text) return false;
    if (/^data:image\//i.test(text)) return true;
    if (/^https?:\/\//i.test(text)) return true;
    return /\.(png|jpe?g|webp|gif|bmp|svg)(\?|#|$)/i.test(text);
}

export function buildAdminAdProductionStages(order?: AdminAdVideoOrderItem | null): AdminAdProductionStage[] {
    if (!order) {
        return [
            { id: 'scenario', label: '01', title: '시나리오', ready: false, detail: '선택된 dedicated 주문이 없습니다.' },
            { id: 'background', label: '02', title: '배경', ready: false, detail: '배경 입력 대기' },
            { id: 'caption', label: '03', title: '자막', ready: false, detail: '자막 입력 대기' },
            { id: 'image', label: '04', title: '이미지', ready: false, detail: '레퍼런스 입력 대기' },
            { id: 'stitch', label: '05', title: '컷 이음', ready: false, detail: 'scene prompt 대기' },
            { id: 'continuity', label: '06', title: '연속성', ready: false, detail: '검수 승인 대기' },
        ];
    }

    const storyboard = order.storyboard || [];
    const reviewMap = new Map((order.storyboard_review || []).map((item) => [item.cut, item.status]));
    const approvedScenes = storyboard.filter((scene) => reviewMap.get(scene.cut) === 'approved').length;
    const validProductImages = (order.product_image_prompts || []).filter((item) => isAdminPreviewableImage(item));
    const hasPortrait = isAdminPreviewableImage(order.portrait_image_prompt);
    const hasHeroImage = isAdminPreviewableImage(order.image_prompt);
    const durationSeconds = Math.max(1, Number(order.duration_seconds || 60));
    const minimumContinuityFrameCount = Math.ceil(durationSeconds * 8);
    const totalFrameHint = storyboard.reduce((acc, scene) => acc + getAdminSceneFrameHint(scene.duration_sec, scene.motion_speed_percent), 0);
    const hasScenario = !!order.title?.trim() && storyboard.length > 0 && storyboard.every((scene) => String(scene.title || '').trim());
    const hasBackground = !!String(order.background_prompt || '').trim() && storyboard.every((scene) => String(scene.visual_focus || '').trim());
    const hasCaption = !!String(order.caption_text || '').trim() && storyboard.every((scene) => String(scene.narration_line || '').trim());
    const hasImages = (hasPortrait || hasHeroImage) && validProductImages.length >= 3;
    const hasCutLinks = storyboard.length > 0
        && totalFrameHint >= minimumContinuityFrameCount
        && storyboard.every((scene) => Number(scene.duration_sec || 0) > 0 && Number(scene.motion_speed_percent || 0) > 0 && String(scene.scene_prompt || '').trim() && String(scene.designer_prompt || '').trim());
    const continuityReady = storyboard.length > 0 && approvedScenes === storyboard.length;

    return [
        { id: 'scenario', label: '01', title: '시나리오', ready: hasScenario, detail: hasScenario ? `${storyboard.length}개 씬 구성 완료` : '제목/씬 제목/스토리보드 입력 필요' },
        { id: 'background', label: '02', title: '배경', ready: hasBackground, detail: hasBackground ? '배경 프롬프트와 비주얼 포인트 연결 완료' : '배경 프롬프트 또는 visual focus 누락' },
        { id: 'caption', label: '03', title: '자막', ready: hasCaption, detail: hasCaption ? 'caption_text와 컷별 narration 연결 완료' : '자막 초안 또는 컷별 narration 누락' },
        { id: 'image', label: '04', title: '이미지', ready: hasImages, detail: hasImages ? `상품 ${validProductImages.length}장 + 레퍼런스 준비` : '인물/대표 이미지와 상품 3장 이상 필요' },
        { id: 'stitch', label: '05', title: '컷 이음', ready: hasCutLinks, detail: hasCutLinks ? `${totalFrameHint}장 / duration / designer_prompt / speed% 연결 완료` : `컷 길이, scene_prompt, designer_prompt, speed%, 최소 ${minimumContinuityFrameCount}장(초당 8매) 기준 필요` },
        { id: 'continuity', label: '06', title: '연속성', ready: continuityReady, detail: continuityReady ? `전 컷 승인 완료 (${approvedScenes}/${storyboard.length})` : `검수 승인 ${approvedScenes}/${storyboard.length}` },
    ];
}

export function getAdminAdProductionCurrentStage(stages: AdminAdProductionStage[]): string {
    const pendingStage = stages.find((stage) => !stage.ready);
    return pendingStage ? `${pendingStage.label} ${pendingStage.title}` : '작업 가능';
}

export function getAdminMotionTempoLabel(value?: string | null): string {
    if (value === 'slow') return '느리게';
    if (value === 'fast') return '빠르게';
    if (value === 'run') return '뛰기';
    return '보통';
}

export function getAdminSceneFrameHint(durationSec?: number, motionSpeedPercent?: number): number {
    const safeDuration = Math.max(1, Number(durationSec || 1));
    const safeSpeed = Math.max(25, Math.min(300, Number(motionSpeedPercent || 100)));
    return Math.max(1, Math.ceil(safeDuration * 8 * (safeSpeed / 100)));
}

export function resolveAdminStoryboardPreviewSource(order: AdminAdVideoOrderItem, scene: NonNullable<AdminAdVideoOrderItem['storyboard']>[number]): string {
    if (scene.asset_source === 'custom' && isAdminPreviewableImage(scene.asset_ref)) {
        return scene.asset_ref || '';
    }
    if (scene.asset_source === 'portrait' && isAdminPreviewableImage(order.portrait_image_prompt)) {
        return order.portrait_image_prompt || '';
    }
    if (scene.asset_source === 'product') {
        const productImage = order.product_image_prompts?.[scene.product_index ?? 0] || '';
        if (isAdminPreviewableImage(productImage)) {
            return productImage;
        }
    }
    if (isAdminPreviewableImage(order.image_prompt)) {
        return order.image_prompt || '';
    }
    if (isAdminPreviewableImage(order.portrait_image_prompt)) {
        return order.portrait_image_prompt || '';
    }
    return '';
}

export function assertAdminAdProductionAnalysisContract() {
    const stages = buildAdminAdProductionStages(null);
    if (stages.length !== 6 || getAdminAdProductionCurrentStage(stages) !== '01 시나리오') {
        throw new Error('admin ad production analysis contract 누락: 6단 생산라인과 기본 현재 단계 필요');
    }
}

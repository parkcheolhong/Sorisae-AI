/**
 * [기능 분리 Phase5.6b] 수익화(결제/구독) 도메인 SSOT.
 *
 * App.tsx 인라인에 있던 플랜 정의·결제 상태 판정·구매→플랜 매핑을 분리한다.
 * 모두 순수(부수효과 없음)하여 단위 테스트로 회귀 가드한다.
 *  - 플랜 키/설정: `MonetizationPlanKey` / `MONETIZATION_PLAN_CONFIG`
 *  - 결제 완료 판정: `isPurchaseSettled`
 *  - 금액→플랜 역매핑: `resolvePlanKeyFromPurchase`
 *  - 보유 플랜 집계: `collectOwnedPlanKeys`
 */

export type MonetizationPlanKey = 'voip_lite' | 'voip_pro' | 'song_pass';

export interface MonetizationPlanConfig {
    amount: number;
    title: string;
    shortLabel: string;
    billingLabel: string;
    usageLabel: string;
    formulaLabel: string;
    description: string;
}

export const MONETIZATION_PLAN_CONFIG: Record<MonetizationPlanKey, MonetizationPlanConfig> = {
    voip_lite: {
        amount: 9900,
        title: 'VoIP Premium Lite',
        shortLabel: 'Lite',
        billingLabel: '월 9,900원',
        usageLabel: '월 60분 통역 통화 권장',
        formulaLabel: '기준 원가식: (월 고정비 + 통역분당변동비 x 60분) / 60분',
        description: '가벼운 여행/상담용 실시간 통역 통화를 위한 월정액입니다.',
    },
    voip_pro: {
        amount: 19900,
        title: 'VoIP Premium Pro',
        shortLabel: 'Pro',
        billingLabel: '월 19,900원',
        usageLabel: '월 300분 통역 통화 권장',
        formulaLabel: '기준 원가식: (월 고정비 + 통역분당변동비 x 300분) / 300분',
        description: '상시 통화가 필요한 고객 상담/업무형 통역 사용자를 위한 월정액입니다.',
    },
    song_pass: {
        amount: 2900,
        title: 'Song Translation Pass',
        shortLabel: '1곡',
        billingLabel: '건당 2,900원',
        usageLabel: '노래 파일 1건 처리',
        formulaLabel: '기준 원가식: 업로드/자막처리/검수 계산량을 1곡 기준으로 회수',
        description: '노래 번역은 사용 편차가 커서 건당 과금으로 분리합니다.',
    },
};

/** 결제 완료로 간주하는 상태값(소문자 정규화 비교). */
export const PREMIUM_PURCHASE_STATUSES = new Set(['paid', 'completed', 'success', 'succeeded', 'approved']);

export interface PremiumPurchase {
    id: number;
    amount: number;
    status: string;
    payment_method: string;
}

/** 구매 상태가 결제 완료 집합에 속하는지 판정. */
export function isPurchaseSettled(status: string | null | undefined): boolean {
    return PREMIUM_PURCHASE_STATUSES.has(String(status || '').trim().toLowerCase());
}

/** 결제 금액으로 플랜 키를 역매핑(일치 금액 없으면 null). 추천 3% 할인 금액도 허용. */
export function resolvePlanKeyFromPurchase(amount: number, referralDiscountPercent = 3): MonetizationPlanKey | null {
    const planEntries = Object.entries(MONETIZATION_PLAN_CONFIG) as Array<[MonetizationPlanKey, MonetizationPlanConfig]>;
    const matchedEntry = planEntries.find(([, config]) => {
        if (config.amount === amount) {
            return true;
        }
        const discounted = Math.round(config.amount * (100 - referralDiscountPercent) / 100);
        return discounted === amount;
    });
    return matchedEntry ? matchedEntry[0] : null;
}

/** 구매 목록에서 결제 완료 + 금액 매칭되는 보유 플랜 집합을 산출. */
export function collectOwnedPlanKeys(purchases: PremiumPurchase[] | null): Set<MonetizationPlanKey> {
    const ownedPlans = new Set<MonetizationPlanKey>();
    if (!purchases) {
        return ownedPlans;
    }
    for (const purchase of purchases) {
        if (!isPurchaseSettled(purchase.status)) {
            continue;
        }
        const planKey = resolvePlanKeyFromPurchase(Number(purchase.amount));
        if (planKey) {
            ownedPlans.add(planKey);
        }
    }
    return ownedPlans;
}

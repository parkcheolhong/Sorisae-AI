import { describe, expect, it } from '@jest/globals';

import {
    MONETIZATION_PLAN_CONFIG,
    PREMIUM_PURCHASE_STATUSES,
    isPurchaseSettled,
    resolvePlanKeyFromPurchase,
    collectOwnedPlanKeys,
    type PremiumPurchase,
} from '../features/monetization/monetization';

describe('MONETIZATION_PLAN_CONFIG — 플랜 금액 SSOT', () => {
    it('각 플랜 금액이 회귀 없이 고정값을 유지한다', () => {
        expect(MONETIZATION_PLAN_CONFIG.voip_lite.amount).toBe(9900);
        expect(MONETIZATION_PLAN_CONFIG.voip_pro.amount).toBe(19900);
        expect(MONETIZATION_PLAN_CONFIG.song_pass.amount).toBe(2900);
    });

    it('플랜 키 3종을 모두 포함한다', () => {
        expect(Object.keys(MONETIZATION_PLAN_CONFIG).sort()).toEqual(['song_pass', 'voip_lite', 'voip_pro']);
    });
});

describe('isPurchaseSettled — 결제 완료 판정', () => {
    it('완료 상태 집합은 대소문자/공백을 정규화해 판정한다', () => {
        for (const status of PREMIUM_PURCHASE_STATUSES) {
            expect(isPurchaseSettled(status)).toBe(true);
            expect(isPurchaseSettled(`  ${status.toUpperCase()} `)).toBe(true);
        }
    });

    it('미완료/누락 상태는 false 를 반환한다', () => {
        expect(isPurchaseSettled('pending')).toBe(false);
        expect(isPurchaseSettled('failed')).toBe(false);
        expect(isPurchaseSettled('')).toBe(false);
        expect(isPurchaseSettled(null)).toBe(false);
        expect(isPurchaseSettled(undefined)).toBe(false);
    });
});

describe('resolvePlanKeyFromPurchase — 금액→플랜 역매핑', () => {
    it('정확한 금액은 해당 플랜으로 매핑한다', () => {
        expect(resolvePlanKeyFromPurchase(9900)).toBe('voip_lite');
        expect(resolvePlanKeyFromPurchase(19900)).toBe('voip_pro');
        expect(resolvePlanKeyFromPurchase(2900)).toBe('song_pass');
    });

    it('일치 금액이 없으면 null 을 반환한다', () => {
        expect(resolvePlanKeyFromPurchase(0)).toBeNull();
        expect(resolvePlanKeyFromPurchase(10000)).toBeNull();
    });
});

describe('collectOwnedPlanKeys — 보유 플랜 집계', () => {
    const purchase = (over: Partial<PremiumPurchase>): PremiumPurchase => ({
        id: 1,
        amount: 9900,
        status: 'paid',
        payment_method: 'card',
        ...over,
    });

    it('null 입력은 빈 집합을 반환한다', () => {
        expect(collectOwnedPlanKeys(null).size).toBe(0);
    });

    it('결제 완료 + 금액 매칭된 플랜만 집계한다', () => {
        const owned = collectOwnedPlanKeys([
            purchase({ id: 1, amount: 9900, status: 'paid' }),
            purchase({ id: 2, amount: 19900, status: 'completed' }),
            purchase({ id: 3, amount: 2900, status: 'pending' }), // 미완료 → 제외
            purchase({ id: 4, amount: 12345, status: 'paid' }), // 금액 미매칭 → 제외
        ]);
        expect([...owned].sort()).toEqual(['voip_lite', 'voip_pro']);
    });

    it('중복 구매는 집합으로 1개만 보유 처리한다', () => {
        const owned = collectOwnedPlanKeys([
            purchase({ id: 1, amount: 9900, status: 'paid' }),
            purchase({ id: 2, amount: 9900, status: 'success' }),
        ]);
        expect([...owned]).toEqual(['voip_lite']);
    });
});

import { API_BASE } from '../app/appConstants';
import type { MonetizationPlanKey } from '../features/monetization/monetization';

export type ReferralDiscountQuote = {
    eligible: boolean;
    enabled: boolean;
    percent: number;
    reason: string;
    original_amount_minor: number;
    discount_amount_minor: number;
    final_amount_minor: number;
    applies_to?: string;
    google_offer_id?: string | null;
    apple_offer_id?: string | null;
    stripe_coupon_id?: string | null;
    referrer_code?: string;
};

export type WorldlincoMobileOffer = {
    plan_key: MonetizationPlanKey;
    product_code: string;
    plan_code: string;
    provider: 'stripe' | 'google' | 'apple';
    platform: string;
    external_product_id: string;
    external_price_id: string;
    external_offer_id?: string | null;
    amount_minor: number;
    referral_discount: ReferralDiscountQuote;
};

export async function fetchReferralDiscountQuote(token: string, amountMinor: number): Promise<ReferralDiscountQuote> {
    const query = new URLSearchParams({ amount_minor: String(amountMinor) });
    const res = await fetch(`${API_BASE}/api/marketplace/worldlinco/referral/discount-quote?${query.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        throw new Error(typeof data.detail === 'string' ? data.detail : `할인 견적 조회 실패 (HTTP ${res.status})`);
    }
    return data as ReferralDiscountQuote;
}

export async function fetchWorldlincoMobileOffer(
    token: string,
    planKey: MonetizationPlanKey,
    platform: 'android' | 'ios' | 'stripe',
): Promise<WorldlincoMobileOffer> {
    const query = new URLSearchParams({ plan_key: planKey, platform });
    const res = await fetch(`${API_BASE}/api/marketplace/worldlinco/billing/mobile-offer?${query.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        throw new Error(typeof data.detail === 'string' ? data.detail : `스토어 오퍼 조회 실패 (HTTP ${res.status})`);
    }
    return data as WorldlincoMobileOffer;
}

export async function verifyWorldlincoMobileSubscription(
    token: string,
    payload: {
        platform: 'android' | 'ios';
        product_code: string;
        plan_code: string;
        purchase_token_or_receipt: string;
        transaction_id?: string;
        external_product_id?: string;
        external_price_id?: string;
    },
): Promise<Record<string, unknown>> {
    const res = await fetch(`${API_BASE}/api/marketplace/v1/billing/mobile/verify`, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        throw new Error(typeof data.detail === 'string' ? data.detail : `스토어 결제 검증 실패 (HTTP ${res.status})`);
    }
    return data as Record<string, unknown>;
}

export function formatReferralDiscountLabel(quote: ReferralDiscountQuote | null | undefined): string | null {
    if (!quote?.eligible) {
        return null;
    }
    const original = Math.round(Number(quote.original_amount_minor || 0));
    const finalAmount = Math.round(Number(quote.final_amount_minor || 0));
    return `추천 첫 결제 ${quote.percent}% 할인 · ${original.toLocaleString()}원 → ${finalAmount.toLocaleString()}원`;
}

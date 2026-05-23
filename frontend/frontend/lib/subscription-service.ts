/**
 * 마켓플레이스 월구독 프런트엔드 서비스
 * 백엔드 /api/marketplace/v1/ 구독 API 와 연동합니다.
 */
import { resolveApiBaseUrl } from '@/lib/api';

// ─── 타입 정의 ────────────────────────────────────────────────────────────────

export type SubscriptionStatus =
    | 'none'
    | 'trialing'
    | 'active'
    | 'grace_period'
    | 'past_due'
    | 'canceled'
    | 'refunded'
    | 'suspended';

export type SubscriptionStatusResponse = {
    user_id: number;
    subscription_status: SubscriptionStatus;
    product_code: string | null;
    plan_code: string | null;
    entitlement_set: string[];
    period_end: string | null;
    cancel_at_period_end: boolean;
    device_limit: number;
    active_device_count: number;
    source: string | null;
};

export type SubscriptionActionResponse = SubscriptionStatusResponse & {
    applied: boolean;
    ignored: boolean;
    reason_code: string;
};

export type CheckoutSessionCreateRequest = {
    product_code: string;
    plan_code: string;
    provider?: 'stripe';
    success_url: string;
    cancel_url: string;
};

export type CheckoutSessionResponse = {
    provider: string;
    checkout_url: string;
    session_id: string;
    expires_in: number;
    verification_mode: string;
    verification_simulated: boolean;
};

export type SubscriptionCatalogPlanSummary = {
    plan_code: string;
    plan_name: string;
    billing_period: string;
    provider: string;
    currency: string;
    amount_minor: number;
};

export type SubscriptionCatalogItem = {
    product_code: string;
    product_name: string;
    product_description: string | null;
    product_family: string;
    subscription_status: SubscriptionStatus;
    cancel_at_period_end: boolean;
    period_end: string | null;
    active_plan: SubscriptionCatalogPlanSummary | null;
    entitlement_set: string[];
};

// ─── 상태 레이블/배지 헬퍼 ────────────────────────────────────────────────────

export const SUBSCRIPTION_STATUS_LABEL: Record<SubscriptionStatus, string> = {
    none: '구독 없음',
    trialing: '체험 중',
    active: '활성',
    grace_period: '유예 기간',
    past_due: '결제 지연',
    canceled: '해지됨',
    refunded: '환불됨',
    suspended: '정지됨',
};

export const SUBSCRIPTION_STATUS_VARIANT: Record<SubscriptionStatus, 'success' | 'warning' | 'danger' | 'neutral'> = {
    none: 'neutral',
    trialing: 'success',
    active: 'success',
    grace_period: 'warning',
    past_due: 'danger',
    canceled: 'neutral',
    refunded: 'danger',
    suspended: 'danger',
};

export function isAccessAllowed(status: SubscriptionStatus): boolean {
    return ['active', 'trialing', 'grace_period', 'canceled'].includes(status);
}

// ─── API 함수 ─────────────────────────────────────────────────────────────────

/**
 * 현재 로그인 사용자의 구독 상태 조회
 * @param productCode 제품 코드 (예: 'stock-ai-suite')
 * @param token 인증 토큰
 */
export async function fetchMySubscription(
    productCode: string,
    token: string,
): Promise<SubscriptionStatusResponse> {
    const base = resolveApiBaseUrl();
    const url = `${base}/api/marketplace/v1/me/subscription?product_code=${encodeURIComponent(productCode)}`;
    const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-store',
    });
    if (!res.ok) throw new Error(`구독 조회 실패: ${res.status}`);
    return res.json();
}

/**
 * 월정액 서비스군 카탈로그 조회
 */
export async function fetchSubscriptionCatalog(token: string): Promise<SubscriptionCatalogItem[]> {
    const base = resolveApiBaseUrl();
    const res = await fetch(`${base}/api/marketplace/v1/subscription/catalog`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-store',
    });
    if (!res.ok) throw new Error(`구독 카탈로그 조회 실패: ${res.status}`);
    return res.json();
}

/**
 * 구독 해지 예약 (기간 종료 시 해지)
 */
export async function cancelSubscription(
    token: string,
    productCode?: string,
): Promise<SubscriptionActionResponse> {
    const base = resolveApiBaseUrl();
    const res = await fetch(`${base}/api/marketplace/v1/me/subscription/cancel`, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ product_code: productCode ?? null }),
    });
    if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail ?? `구독 해지 실패: ${res.status}`);
    }
    return res.json();
}

/**
 * 해지 예약 취소 (재개)
 */
export async function resumeSubscription(
    token: string,
    productCode?: string,
): Promise<SubscriptionActionResponse> {
    const base = resolveApiBaseUrl();
    const res = await fetch(`${base}/api/marketplace/v1/me/subscription/resume`, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ product_code: productCode ?? null }),
    });
    if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail ?? `구독 재개 실패: ${res.status}`);
    }
    return res.json();
}

/**
 * Stripe 체크아웃 세션 생성 (PC/Web 결제)
 */
export async function createCheckoutSession(
    req: CheckoutSessionCreateRequest,
    token: string,
): Promise<CheckoutSessionResponse> {
    const base = resolveApiBaseUrl();
    const res = await fetch(`${base}/api/marketplace/v1/billing/checkout/sessions`, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ provider: 'stripe', ...req }),
    });
    if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail ?? `체크아웃 세션 생성 실패: ${res.status}`);
    }
    return res.json();
}

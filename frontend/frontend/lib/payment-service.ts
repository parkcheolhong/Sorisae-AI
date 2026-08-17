/**
 * P1-3: 결제 서비스 프론트엔드 연동 유틸리티
 * 
 * 백엔드 payment_service.py 와 연동하여
 * 마켓플레이스에서 구매 → 결제 → 다운로드 흐름을 처리합니다.
 */
import { resolveApiBaseUrl } from '@/lib/api';

export type PurchaseStatus = 'pending' | 'completed' | 'failed' | 'refunded';

export type PurchaseRecord = {
    id: number;
    project_id: number;
    buyer_id: number;
    amount: number;
    payment_method: string;
    status: PurchaseStatus;
    transaction_id?: string;
    receipt_url?: string;
    created_at?: string;
};

export type PaymentInitResult = {
    payment_url: string;
    order_id: string;
    transaction_id: string;
};

/**
 * 구매 기록 생성
 */
export async function createPurchase(
    projectId: number,
    amount: number,
    paymentMethod: string = 'card',
): Promise<PurchaseRecord> {
    const base = resolveApiBaseUrl();
    const res = await fetch(`${base}/api/marketplace/purchase`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
            project_id: projectId,
            amount,
            payment_method: paymentMethod,
        }),
    });
    if (!res.ok) throw new Error(`구매 생성 실패: ${res.status}`);
    return res.json();
}

/**
 * 결제 초기화 (PG사 결제 URL 반환)
 */
export async function initiatePayment(purchaseId: number): Promise<PaymentInitResult> {
    const base = resolveApiBaseUrl();
    const res = await fetch(`${base}/api/marketplace/purchase/${purchaseId}/pay`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
    });
    if (!res.ok) throw new Error(`결제 초기화 실패: ${res.status}`);
    return res.json();
}

/**
 * 사용자 구매 내역 조회
 */
export async function getUserPurchases(
    skip: number = 0,
    limit: number = 20,
): Promise<{ purchases: PurchaseRecord[]; total: number }> {
    const base = resolveApiBaseUrl();
    const res = await fetch(
        `${base}/api/marketplace/purchases?skip=${skip}&limit=${limit}`,
        { credentials: 'include' },
    );
    if (!res.ok) throw new Error(`구매 내역 조회 실패: ${res.status}`);
    return res.json();
}

/**
 * 구매 환불 요청
 */
export async function requestRefund(
    purchaseId: number,
    reason: string = '사용자 요청',
): Promise<PurchaseRecord> {
    const base = resolveApiBaseUrl();
    const res = await fetch(`${base}/api/marketplace/purchase/${purchaseId}/refund`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ reason }),
    });
    if (!res.ok) throw new Error(`환불 요청 실패: ${res.status}`);
    return res.json();
}

/**
 * 다운로드 토큰 생성
 */
export async function createDownloadToken(projectId: number): Promise<{ token: string; expires_at: string }> {
    const base = resolveApiBaseUrl();
    const res = await fetch(`${base}/api/marketplace/download-token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ project_id: projectId }),
    });
    if (!res.ok) throw new Error(`다운로드 토큰 생성 실패: ${res.status}`);
    return res.json();
}

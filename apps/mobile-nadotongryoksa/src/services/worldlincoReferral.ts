import { API_BASE } from '../app/appConstants';

export type ReferralMePayload = {
    code: string;
    invite_url: string;
    deeplink: string;
    qr_url: string;
    signup_count: number;
    updated_at?: string;
    discount_policy?: {
        enabled?: boolean;
        percent?: number;
        applies_to?: string;
    };
};

export async function fetchReferralMe(token: string): Promise<ReferralMePayload> {
    const res = await fetch(`${API_BASE}/api/marketplace/worldlinco/referral/me`, {
        headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        throw new Error(typeof data.detail === 'string' ? data.detail : `추천 정보 조회 실패 (HTTP ${res.status})`);
    }
    return data as ReferralMePayload;
}

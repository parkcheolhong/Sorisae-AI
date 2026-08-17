import { API_BASE } from '../app/appConstants';
import { loadStoredAuthState } from '../app/appStorage';
import { buildBearerAuthHeader, normalizeAuthToken } from '../features/shared/authToken';

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
    const candidateTokens: string[] = [];
    const addCandidate = (raw: string | null | undefined) => {
        const normalized = normalizeAuthToken(raw);
        if (normalized && !candidateTokens.includes(normalized)) {
            candidateTokens.push(normalized);
        }
    };

    addCandidate(token);
    try {
        const stored = await loadStoredAuthState();
        addCandidate(stored?.token);
    } catch {
        // 저장소 조회 실패 시 전달받은 토큰만 사용
    }

    let lastError: Error | null = null;
    for (const candidate of candidateTokens) {
        const res = await fetch(`${API_BASE}/api/marketplace/worldlinco/referral/me`, {
            headers: { Authorization: buildBearerAuthHeader(candidate) },
        });
        const data = await res.json().catch(() => ({}));
        if (res.ok) {
            return data as ReferralMePayload;
        }

        const message = typeof data.detail === 'string' ? data.detail : `추천 정보 조회 실패 (HTTP ${res.status})`;
        lastError = new Error(message);
        if (res.status !== 401 && res.status !== 403) {
            break;
        }
    }

    throw lastError ?? new Error('추천 정보를 불러오지 못했습니다.');
}

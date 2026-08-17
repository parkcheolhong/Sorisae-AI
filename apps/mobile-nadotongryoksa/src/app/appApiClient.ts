// App.tsx 에서 분리한 REST API 클라이언트(인증/마켓/여행/VoIP 콜 제어).
import { API_BASE, AUTH_API_ERROR_TEXT } from './appConstants';
import { buildBearerAuthHeader, normalizeAuthToken } from '../features/shared/authToken';
import { extractApiErrorMessage } from '../features/shared/textFormat';
import { resolveWorldLincoProjectId } from '../utils/worldlincoProject';
import type { UserInfo, SignupPayload, SignupRequestCodeResponse, UserProfileUpdatePayload, PurchaseResult } from './appTypes';
import type { SearchCategory, NearbyPlace, BookingResponse } from '../features/travel-booking/types';
import type { CallInitResponse } from '../services/voipCallClient';

export async function requestEndVoipCall(
    apiBase: string,
    token: string,
    callId: string,
    callQuality: string,
): Promise<void> {
    const normalizedToken = normalizeAuthToken(token);
    try {
        await fetch(`${apiBase}/api/v1/voip/calls/${callId}/end`, {
            method: 'POST',
            headers: {
                Authorization: buildBearerAuthHeader(normalizedToken),
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                duration_sec: 0,
                call_quality: callQuality,
            }),
        });
    } catch (error) {
        console.warn('[VoIP] Failed to end stale call cleanly', error);
    }
}

export async function fetchVoipCallResumeSnapshot(
    apiBase: string,
    authToken: string,
    callId: string,
): Promise<CallInitResponse | null> {
    const normalizedToken = normalizeAuthToken(authToken);
    try {
        const response = await fetch(
            `${apiBase}/api/v1/voip/calls/active-current?last_call_id=${encodeURIComponent(callId)}`,
            { headers: { Authorization: buildBearerAuthHeader(normalizedToken) } },
        );
        if (!response.ok) {
            return null;
        }
        const payload = await response.json() as CallInitResponse | null;
        if (!payload?.call_id) {
            return null;
        }
        return payload;
    } catch {
        return null;
    }
}

export async function callLoginApi(email: string, password: string): Promise<string> {
    console.log('[AUTH_FLOW]', JSON.stringify({
        event: 'LOGIN_API_REQUEST',
        endpoint: `${API_BASE}/api/auth/login`,
        email: email.trim().toLowerCase(),
    }));
    const form = new URLSearchParams({ username: email, password });
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10_000);
    let res: Response;
    try {
        res = await fetch(`${API_BASE}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: form.toString(),
            signal: controller.signal,
        });
    } catch (err: unknown) {
        const isAbort = err instanceof Error && err.name === 'AbortError';
        throw new Error(isAbort ? '서버 응답이 너무 늦습니다. 네트워크를 확인하고 다시 시도해 주세요.' : (err instanceof Error ? err.message : '네트워크 오류'));
    } finally {
        clearTimeout(timeout);
    }
    const data = await res.json().catch(() => ({}));
    console.log('[AUTH_FLOW]', JSON.stringify({
        event: res.ok ? 'LOGIN_API_SUCCESS' : 'LOGIN_API_FAIL',
        endpoint: `${API_BASE}/api/auth/login`,
        email: email.trim().toLowerCase(),
        status: res.status,
    }));
    if (!res.ok) {
        if (res.status === 409) {
            throw new Error(AUTH_API_ERROR_TEXT.duplicateLoginBlocked);
        }
        throw new Error(extractApiErrorMessage(data.detail, AUTH_API_ERROR_TEXT.loginFailed(res.status)));
    }
    return data.access_token as string;
}

export async function callSignupApi(payload: SignupPayload): Promise<UserInfo> {
    const res = await fetch(`${API_BASE}/api/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(extractApiErrorMessage(data.detail, `회원가입 실패 (HTTP ${res.status})`));
    return data as UserInfo;
}

export async function callSignupRequestCodeApi(payload: SignupPayload): Promise<SignupRequestCodeResponse> {
    const res = await fetch(`${API_BASE}/api/auth/signup/request-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            ...payload,
            verificationChannel: payload.verificationChannel || 'email',
        }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(extractApiErrorMessage(data.detail, `인증 코드 요청 실패 (HTTP ${res.status})`));
    return data as SignupRequestCodeResponse;
}

export async function callSignupConfirmApi(
    signupSessionToken: string,
    verificationCode: string,
    profile: Pick<SignupPayload, 'preferred_language' | 'country_code' | 'full_name'>,
    referralCode?: string,
    salesAgentCode?: string,
): Promise<UserInfo> {
    const res = await fetch(`${API_BASE}/api/auth/signup/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            signupSessionToken,
            verificationCode,
            preferred_language: profile.preferred_language,
            country_code: profile.country_code,
            full_name: profile.full_name,
            referral_code: referralCode || undefined,
            sales_agent_code: salesAgentCode || undefined,
        }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(extractApiErrorMessage(data.detail, `이메일 인증 확인 실패 (HTTP ${res.status})`));
    return data as UserInfo;
}

export async function callMeApi(token: string): Promise<UserInfo> {
    const normalizedToken = normalizeAuthToken(token);
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8_000);
    let res: Response;
    try {
        res = await fetch(`${API_BASE}/api/auth/me`, {
            headers: { Authorization: buildBearerAuthHeader(normalizedToken) },
            signal: controller.signal,
        });
    } catch (err: unknown) {
        const isAbort = err instanceof Error && err.name === 'AbortError';
        const error = new Error(isAbort ? '세션 복구 타임아웃' : (err instanceof Error ? err.message : '네트워크 오류')) as Error & { status?: number };
        error.status = isAbort ? 0 : undefined;
        throw error;
    } finally {
        clearTimeout(timeout);
    }
    if (!res.ok) {
        const error = new Error(`내 정보 조회 실패 (HTTP ${res.status})`) as Error & { status?: number };
        error.status = res.status;
        throw error;
    }
    return res.json();
}

export async function callLogoutApi(token: string): Promise<void> {
    const normalizedToken = normalizeAuthToken(token);
    if (!normalizedToken) {
        return;
    }
    const res = await fetch(`${API_BASE}/api/auth/logout`, {
        method: 'POST',
        headers: { Authorization: buildBearerAuthHeader(normalizedToken) },
    });
    if (res.status === 401 || res.status === 403) {
        return;
    }
    if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(extractApiErrorMessage(data?.detail, `로그아웃 실패 (HTTP ${res.status})`));
    }
}

export async function callUpdateMeApi(token: string, payload: UserProfileUpdatePayload): Promise<UserInfo> {
    const normalizedToken = normalizeAuthToken(token);
    const res = await fetch(`${API_BASE}/api/auth/me`, {
        method: 'PATCH',
        headers: {
            'Content-Type': 'application/json',
            Authorization: buildBearerAuthHeader(normalizedToken),
        },
        body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(extractApiErrorMessage(data.detail, `내 정보 저장 실패 (HTTP ${res.status})`));
    return data as UserInfo;
}

export async function callNearbyPlacesApi(params: {
    lat: string;
    lon: string;
    category: SearchCategory;
    radiusM: number;
    targetLang: string;
}): Promise<NearbyPlace[]> {
    const query = new URLSearchParams({
        lat: params.lat,
        lon: params.lon,
        category: params.category,
        radius_m: String(params.radiusM),
        target_lang: params.targetLang,
        limit: '12',
    });
    const requestUrl = `${API_BASE}/api/marketplace/nadotongryoksa/lbs/nearby?${query.toString()}`;
    console.log('[TRAVEL_NEARBY_PROBE]', JSON.stringify({
        event: 'NEARBY_REQUEST',
        request_url: requestUrl,
        lat: params.lat,
        lon: params.lon,
        category: params.category,
        radius_m: params.radiusM,
        target_lang: params.targetLang,
    }));
    const response = await fetch(requestUrl);
    console.log('[TRAVEL_NEARBY_PROBE]', JSON.stringify({
        event: 'NEARBY_RESPONSE',
        status: response.status,
        ok: response.ok,
    }));
    if (!response.ok) throw new Error(`주변검색 실패: HTTP ${response.status}`);
    const payload = await response.json();
    console.log('[TRAVEL_NEARBY_PROBE]', JSON.stringify({
        event: 'NEARBY_PAYLOAD',
        total: Array.isArray(payload.places) ? payload.places.length : 0,
        first_place_id: Array.isArray(payload.places) && payload.places.length > 0 ? payload.places[0]?.id ?? null : null,
    }));
    return Array.isArray(payload.places) ? payload.places : [];
}

export async function callBookingApi(token: string, payload: {
    placeId: string;
    customerName: string;
    checkinDate: string;
    checkoutDate: string;
    guests: number;
    roomCount: number;
    note: string;
    targetLang: string;
}): Promise<BookingResponse> {
    console.log('[TRAVEL_BOOKING_PROBE]', JSON.stringify({
        event: 'BOOKING_API_REQUEST',
        place_id: payload.placeId,
        customer_name: payload.customerName,
        checkin_date: payload.checkinDate,
        checkout_date: payload.checkoutDate,
        guests: payload.guests,
        room_count: payload.roomCount,
        target_lang: payload.targetLang,
    }));
    const response = await fetch(`${API_BASE}/api/marketplace/nadotongryoksa/lbs/bookings`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
            place_id: payload.placeId,
            customer_name: payload.customerName,
            checkin_date: payload.checkinDate,
            checkout_date: payload.checkoutDate,
            guests: payload.guests,
            room_count: payload.roomCount,
            note: payload.note,
            target_lang: payload.targetLang,
        }),
    });
    const result = await response.json().catch(() => ({}));
    console.log('[TRAVEL_BOOKING_PROBE]', JSON.stringify({
        event: response.ok ? 'BOOKING_API_SUCCESS' : 'BOOKING_API_FAIL',
        status: response.status,
        place_id: payload.placeId,
        confirmation_id: typeof result?.confirmation_id === 'string' ? result.confirmation_id : null,
        detail: typeof result?.detail === 'string' ? result.detail : null,
    }));
    if (!response.ok) throw new Error(result.detail || `HTTP ${response.status}`);
    return result;
}

export async function callCreatePurchaseApi(token: string, amount: number): Promise<PurchaseResult> {
    const projectId = await resolveWorldLincoProjectId(API_BASE);
    const res = await fetch(`${API_BASE}/api/marketplace/purchase`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ project_id: projectId, amount, payment_method: 'card' }),
    });
    const result = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(result.detail || `구매 생성 실패 HTTP ${res.status}`);
    return result;
}

export async function callInitiatePaymentApi(token: string, purchaseId: number): Promise<{ payment_url: string }> {
    const res = await fetch(`${API_BASE}/api/marketplace/purchase/${purchaseId}/pay`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
    });
    const result = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(result.detail || `결제 초기화 실패 HTTP ${res.status}`);
    return result;
}

export async function callMyPurchasesApi(token: string): Promise<Array<{ id: number; amount: number; status: string; payment_method: string }>> {
    const res = await fetch(`${API_BASE}/api/marketplace/purchases`, {
        headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return Array.isArray(data) ? data : (data.items ?? []);
}

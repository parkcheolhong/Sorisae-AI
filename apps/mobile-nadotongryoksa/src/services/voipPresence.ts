/**
 * VoIP Presence / 착신(Incoming Call) 클라이언트 — P3-A 모바일 연동.
 *
 * 의존성 주의: Firebase/FCM 네이티브 모듈을 직접 import하지 않는다(미설치 시 Metro 번들 실패 방지).
 * 메시징 어댑터(토큰 획득/푸시 구독)는 앱이 Firebase 설치 후 주입(inject)한다.
 *
 * 백엔드 계약:
 *  - POST /api/v1/voip/devices/register  { fcm_token, platform }
 *  - POST /api/v1/voip/calls/{call_id}/accept  → CallInitResponse(role=callee)
 *  - 착신 data 푸시: { type: 'incoming_call', call_id, caller_label }
 */
import { Platform } from 'react-native';
import type { CallInitResponse } from './voipCallClient';

export type IncomingCallPush = {
    callId: string;
    callerLabel: string;
};

/** 주입형 메시징 어댑터(Firebase 설치 후 앱이 제공). */
export interface VoipMessagingAdapter {
    /** FCM/푸시 토큰 획득(없으면 null). */
    getToken: () => Promise<string | null>;
    /** 포그라운드 착신 data 푸시 구독. unsubscribe 함수 반환. */
    subscribe: (handler: (data: Record<string, unknown>) => void) => () => void;
    /** 알림 탭으로 앱 복귀 시 data 페이로드. */
    onNotificationOpened?: (handler: (data: Record<string, unknown>) => void) => () => void;
    /** cold start 시 알림 탭으로 열린 data 페이로드. */
    getInitialNotification?: () => Promise<Record<string, unknown> | null>;
    /** Android 13+ POST_NOTIFICATIONS 등. */
    requestNotificationPermission?: () => Promise<boolean>;
}

/** 디바이스 토큰 등록(+presence 갱신). 성공 시 true. */
export async function registerVoipDevice(
    apiBaseUrl: string,
    authToken: string,
    fcmToken: string,
    platform?: string,
): Promise<boolean> {
    if (!authToken || !fcmToken) {
        return false;
    }
    try {
        const res = await fetch(`${apiBaseUrl}/api/v1/voip/devices/register`, {
            method: 'POST',
            headers: {
                Authorization: `Bearer ${authToken}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ fcm_token: fcmToken, platform: platform ?? Platform.OS }),
        });
        return res.ok;
    } catch (err) {
        console.warn('[VoIP] registerVoipDevice 실패', err);
        return false;
    }
}

/** 디바이스 토큰 해제(로그아웃). 해제 단말은 더 이상 착신 벨을 울리지 않는다. */
export async function unregisterVoipDevice(
    apiBaseUrl: string,
    authToken: string,
    fcmToken: string,
): Promise<boolean> {
    if (!authToken || !fcmToken) {
        return false;
    }
    try {
        const res = await fetch(`${apiBaseUrl}/api/v1/voip/devices/unregister`, {
            method: 'POST',
            headers: {
                Authorization: `Bearer ${authToken}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ fcm_token: fcmToken, platform: Platform.OS }),
        });
        return res.ok;
    } catch (err) {
        console.warn('[VoIP] unregisterVoipDevice 실패', err);
        return false;
    }
}

/** 부재중 통화 1건. 백엔드 GET /api/v1/voip/calls/missed/recent 응답 항목. */
export type MissedCallRecord = {
    id: number;
    callId: string;
    createdAt: string;
    callerLabel: string;
    callerVoiceId?: string | null;
};

/**
 * 최근 부재중 통화 목록 조회(최신순, 최대 20건). 미로그인/실패 시 빈 배열.
 * 부재중 전화 음성 안내(자동 발화)의 데이터 소스.
 */
export async function fetchRecentMissedCalls(
    apiBaseUrl: string,
    authToken: string,
): Promise<MissedCallRecord[]> {
    if (!authToken) {
        return [];
    }
    try {
        const res = await fetch(`${apiBaseUrl}/api/v1/voip/calls/missed/recent`, {
            method: 'GET',
            headers: {
                Authorization: `Bearer ${authToken}`,
                'Content-Type': 'application/json',
            },
        });
        if (!res.ok) {
            return [];
        }
        const rows = await res.json();
        if (!Array.isArray(rows)) {
            return [];
        }
        return rows
            .filter((r) => r && (r.id != null) && r.callId)
            .map((r) => ({
                id: Number(r.id),
                callId: String(r.callId),
                createdAt: String(r.createdAt ?? ''),
                callerLabel: String(r.callerLabel ?? '알 수 없는 발신자'),
                callerVoiceId: r.callerVoiceId ?? null,
            }));
    } catch (err) {
        console.warn('[VoIP] fetchRecentMissedCalls 실패', err);
        return [];
    }
}

/** 착신 data 푸시 페이로드 파싱. incoming_call이 아니거나 call_id 없으면 null. */
export function parseIncomingCallPush(data: Record<string, unknown> | undefined | null): IncomingCallPush | null {
    if (!data) {
        return null;
    }
    if (String(data.type ?? '') !== 'incoming_call') {
        return null;
    }
    const callId = String(data.call_id ?? '').trim();
    if (!callId) {
        return null;
    }
    return { callId, callerLabel: String(data.caller_label ?? '') };
}

const ACCEPT_INCOMING_TIMEOUT_MS = 20_000;

/** 착신 수락: call_id로 콜리 합류해 시그널링 URL(CallInitResponse) 수신. */
export async function acceptIncomingCall(
    apiBaseUrl: string,
    authToken: string,
    callId: string,
    options: { timeoutMs?: number } = {},
): Promise<CallInitResponse> {
    const timeoutMs = options.timeoutMs ?? ACCEPT_INCOMING_TIMEOUT_MS;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const res = await fetch(`${apiBaseUrl}/api/v1/voip/calls/${callId}/accept`, {
            method: 'POST',
            headers: {
                Authorization: `Bearer ${authToken}`,
                'Content-Type': 'application/json',
            },
            signal: controller.signal,
        });
        if (!res.ok) {
            throw new Error(`착신 수락 실패: HTTP ${res.status}`);
        }
        return (await res.json()) as CallInitResponse;
    } catch (error: any) {
        if (error?.name === 'AbortError') {
            throw new Error(`착신 수락 시간 초과 (${Math.round(timeoutMs / 1000)}초)`);
        }
        throw error;
    } finally {
        clearTimeout(timer);
    }
}

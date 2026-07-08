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

/** 착신 수락: call_id로 콜리 합류해 시그널링 URL(CallInitResponse) 수신. */
export async function acceptIncomingCall(
    apiBaseUrl: string,
    authToken: string,
    callId: string,
): Promise<CallInitResponse> {
    const res = await fetch(`${apiBaseUrl}/api/v1/voip/calls/${callId}/accept`, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${authToken}`,
            'Content-Type': 'application/json',
        },
    });
    if (!res.ok) {
        throw new Error(`착신 수락 실패: HTTP ${res.status}`);
    }
    return (await res.json()) as CallInitResponse;
}

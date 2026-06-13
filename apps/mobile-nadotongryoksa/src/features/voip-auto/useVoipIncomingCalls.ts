/**
 * P3-A 모바일 훅: FCM 디바이스 토큰 등록 + 착신(incoming call) 수신 처리.
 *
 * messaging 어댑터(Firebase 설치 후 주입)가 없으면 안전하게 no-op.
 * 착신 푸시 수신 시 백엔드 accept를 호출해 콜리 CallInitResponse를 얻고 onIncomingCall로 전달.
 */
import { useEffect } from 'react';
import type { CallInitResponse } from '../../services/voipCallClient';
import {
    acceptIncomingCall,
    parseIncomingCallPush,
    registerVoipDevice,
    type VoipMessagingAdapter,
} from '../../services/voipPresence';

interface UseVoipIncomingCallsOptions {
    apiBaseUrl: string;
    authToken: string;
    messaging?: VoipMessagingAdapter | null;
    onIncomingCall: (callInit: CallInitResponse, callerLabel: string) => void;
}

export function useVoipIncomingCalls(options: UseVoipIncomingCallsOptions): void {
    const { apiBaseUrl, authToken, messaging, onIncomingCall } = options;

    // 1) 로그인(토큰) + messaging 어댑터가 있으면 디바이스 토큰 등록.
    useEffect(() => {
        if (!authToken || !messaging) {
            return;
        }
        let cancelled = false;
        (async () => {
            try {
                const fcmToken = await messaging.getToken();
                if (!cancelled && fcmToken) {
                    await registerVoipDevice(apiBaseUrl, authToken, fcmToken);
                }
            } catch (err) {
                console.warn('[VoIP] 디바이스 토큰 등록 실패', err);
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [apiBaseUrl, authToken, messaging]);

    // 2) 착신 푸시 구독 → accept → onIncomingCall.
    useEffect(() => {
        if (!authToken || !messaging) {
            return;
        }
        const unsubscribe = messaging.subscribe((data) => {
            const incoming = parseIncomingCallPush(data);
            if (!incoming) {
                return;
            }
            (async () => {
                try {
                    const callInit = await acceptIncomingCall(apiBaseUrl, authToken, incoming.callId);
                    onIncomingCall(callInit, incoming.callerLabel);
                } catch (err) {
                    console.warn('[VoIP] 착신 수락 실패', err);
                }
            })();
        });
        return unsubscribe;
    }, [apiBaseUrl, authToken, messaging, onIncomingCall]);
}

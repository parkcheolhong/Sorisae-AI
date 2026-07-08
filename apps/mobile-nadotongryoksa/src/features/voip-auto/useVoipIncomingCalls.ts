/**
 * P3-A 모바일 훅: FCM 디바이스 토큰 등록 + 착신(incoming call) 수신 처리.
 *
 * - 포그라운드: messaging.onMessage
 * - 백그라운드/종료: index.js setBackgroundMessageHandler → AsyncStorage → consume on resume
 * - 알림 탭 cold/warm start: getInitialNotification / onNotificationOpenedApp
 */
import { useEffect } from 'react';
import { AppState } from 'react-native';
import * as Notifications from 'expo-notifications';
import type { CallInitResponse } from '../../services/voipCallClient';
import { parseIncomingCallFcmData } from '../../services/voipIncomingPushBridge';
import { consumePendingIncomingPush } from '../../services/voipIncomingPushStore';
import { parseChatMessageFcmData } from '../../services/worldlincoPushBridge';
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
    onIncomingCallPayload?: (
        payload: CallInitResponse & { caller_label?: string; caller_voice_id?: string },
        source: string,
    ) => void;
    onChatMessageOpened?: (roomId: string, source: string) => void;
}

async function dispatchIncomingPush(
    apiBaseUrl: string,
    authToken: string,
    data: Record<string, unknown>,
    source: string,
    onIncomingCall: (callInit: CallInitResponse, callerLabel: string) => void,
    onIncomingCallPayload?: (
        payload: CallInitResponse & { caller_label?: string; caller_voice_id?: string },
        source: string,
    ) => void,
    onChatMessageOpened?: (roomId: string, source: string) => void,
): Promise<void> {
    const chatMessage = parseChatMessageFcmData(data);
    if (chatMessage?.room_id) {
        const shouldOpenChatRoom = source.includes('notification') || source.includes('deeplink');
        if (shouldOpenChatRoom) {
            onChatMessageOpened?.(chatMessage.room_id, source);
        }
        return;
    }

    const parsedPayload = parseIncomingCallFcmData(data);
    if (parsedPayload?.signaling_server && onIncomingCallPayload) {
        onIncomingCallPayload(parsedPayload, source);
        return;
    }

    const incoming = parseIncomingCallPush(data);
    if (!incoming) {
        return;
    }
    try {
        const callInit = await acceptIncomingCall(apiBaseUrl, authToken, incoming.callId);
        onIncomingCall(callInit, incoming.callerLabel);
    } catch (err) {
        console.warn(`[VoIP] 착신 수락 실패 (${source})`, err);
        if (parsedPayload && onIncomingCallPayload) {
            onIncomingCallPayload(parsedPayload, `${source}_accept_fallback`);
        }
    }
}

export function useVoipIncomingCalls(options: UseVoipIncomingCallsOptions): void {
    const {
        apiBaseUrl,
        authToken,
        messaging,
        onIncomingCall,
        onIncomingCallPayload,
        onChatMessageOpened,
    } = options;

    useEffect(() => {
        if (!authToken || !messaging) {
            return;
        }
        let cancelled = false;
        (async () => {
            try {
                if (messaging.requestNotificationPermission) {
                    await messaging.requestNotificationPermission();
                }
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

    useEffect(() => {
        if (!authToken || !messaging) {
            return;
        }
        const handler = (data: Record<string, unknown>) => {
            void dispatchIncomingPush(
                apiBaseUrl,
                authToken,
                data,
                'fcm_foreground',
                onIncomingCall,
                onIncomingCallPayload,
                onChatMessageOpened,
            );
        };
        const unsubscribe = messaging.subscribe(handler);
        return unsubscribe;
    }, [apiBaseUrl, authToken, messaging, onChatMessageOpened, onIncomingCall, onIncomingCallPayload]);

    useEffect(() => {
        if (!authToken || !messaging?.onNotificationOpened) {
            return;
        }
        return messaging.onNotificationOpened((data) => {
            void dispatchIncomingPush(
                apiBaseUrl,
                authToken,
                data,
                'fcm_notification_opened',
                onIncomingCall,
                onIncomingCallPayload,
                onChatMessageOpened,
            );
        });
    }, [apiBaseUrl, authToken, messaging, onChatMessageOpened, onIncomingCall, onIncomingCallPayload]);

    useEffect(() => {
        if (!authToken || !messaging?.getInitialNotification) {
            return;
        }
        const getInitialNotification = messaging.getInitialNotification;
        let cancelled = false;
        (async () => {
            const data = await getInitialNotification();
            if (!cancelled && data) {
                await dispatchIncomingPush(
                    apiBaseUrl,
                    authToken,
                    data,
                    'fcm_initial_notification',
                    onIncomingCall,
                    onIncomingCallPayload,
                    onChatMessageOpened,
                );
                return;
            }
            const lastResponse = await Notifications.getLastNotificationResponseAsync();
            const localData = lastResponse?.notification.request.content.data as
                | Record<string, unknown>
                | undefined;
            if (!cancelled && localData && Object.keys(localData).length > 0) {
                await dispatchIncomingPush(
                    apiBaseUrl,
                    authToken,
                    localData,
                    'expo_initial_notification',
                    onIncomingCall,
                    onIncomingCallPayload,
                    onChatMessageOpened,
                );
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [apiBaseUrl, authToken, messaging, onChatMessageOpened, onIncomingCall, onIncomingCallPayload]);

    useEffect(() => {
        if (!authToken) {
            return;
        }
        const subscription = Notifications.addNotificationResponseReceivedListener((response) => {
            const data = response.notification.request.content.data as Record<string, unknown> | undefined;
            if (!data || Object.keys(data).length === 0) {
                return;
            }
            void dispatchIncomingPush(
                apiBaseUrl,
                authToken,
                data,
                'expo_notification_opened',
                onIncomingCall,
                onIncomingCallPayload,
                onChatMessageOpened,
            );
        });
        return () => subscription.remove();
    }, [apiBaseUrl, authToken, onChatMessageOpened, onIncomingCall, onIncomingCallPayload]);

    useEffect(() => {
        if (!authToken) {
            return;
        }
        let cancelled = false;
        (async () => {
            const stored = await consumePendingIncomingPush();
            if (!cancelled && stored?.data) {
                await dispatchIncomingPush(
                    apiBaseUrl,
                    authToken,
                    stored.data,
                    'fcm_background_store',
                    onIncomingCall,
                    onIncomingCallPayload,
                    onChatMessageOpened,
                );
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [apiBaseUrl, authToken, onChatMessageOpened, onIncomingCall, onIncomingCallPayload]);

    useEffect(() => {
        if (!authToken) {
            return;
        }
        const subscription = AppState.addEventListener('change', (nextState) => {
            if (nextState !== 'active') {
                return;
            }
            void (async () => {
                const stored = await consumePendingIncomingPush();
                if (stored?.data) {
                    await dispatchIncomingPush(
                        apiBaseUrl,
                        authToken,
                        stored.data,
                        'fcm_background_store_active',
                        onIncomingCall,
                        onIncomingCallPayload,
                        onChatMessageOpened,
                    );
                }
            })();
        });
        return () => subscription.remove();
    }, [apiBaseUrl, authToken, onChatMessageOpened, onIncomingCall, onIncomingCallPayload]);
}

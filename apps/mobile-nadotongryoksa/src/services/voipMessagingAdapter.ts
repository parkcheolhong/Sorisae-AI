/**
 * Firebase FCM adapter for VoIP incoming-call push (P3-A / D-1-3).
 * Injected into useVoipIncomingCalls — keeps voipPresence.ts free of native imports.
 */
import messaging from '@react-native-firebase/messaging';

import type { VoipMessagingAdapter } from './voipPresence';

export function createVoipMessagingAdapter(
    ensureFirebaseReady: () => Promise<boolean>,
): VoipMessagingAdapter {
    return {
        getToken: async () => {
            const ready = await ensureFirebaseReady();
            if (!ready) {
                return null;
            }
            try {
                await messaging().registerDeviceForRemoteMessages();
                return await messaging().getToken();
            } catch (error) {
                console.log('[VoIPFCM] getToken failed', error);
                return null;
            }
        },
        subscribe: (handler) => {
            return messaging().onMessage(async (remoteMessage) => {
                const data = remoteMessage?.data as Record<string, unknown> | undefined;
                if (data && Object.keys(data).length > 0) {
                    handler(data);
                }
            });
        },
    };
}

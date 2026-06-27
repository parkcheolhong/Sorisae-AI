/**

 * Firebase FCM adapter for VoIP incoming-call + chat message push.

 * Foreground onMessage + background store (index.js) + notification tap handlers.

 */

import { PermissionsAndroid, Platform } from 'react-native';

import messaging from '@react-native-firebase/messaging';



import type { VoipMessagingAdapter } from './voipPresence';

import { parseIncomingCallFcmData } from './voipIncomingPushBridge';

import { handleWorldlincoPushData } from './worldlincoPushHandler';



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

                if (!data || Object.keys(data).length === 0) {

                    return;

                }

                try {

                    await handleWorldlincoPushData(data, 'foreground');

                } catch (error) {

                    console.log('[WorldlincoFCM] foreground push handler failed', error);

                }

                if (parseIncomingCallFcmData(data)) {

                    handler(data);

                }

            });

        },

        onNotificationOpened: (handler) => {

            return messaging().onNotificationOpenedApp((remoteMessage) => {

                const data = remoteMessage?.data as Record<string, unknown> | undefined;

                if (data && Object.keys(data).length > 0) {

                    handler(data);

                }

            });

        },

        getInitialNotification: async () => {

            const ready = await ensureFirebaseReady();

            if (!ready) {

                return null;

            }

            const remoteMessage = await messaging().getInitialNotification();

            const data = remoteMessage?.data as Record<string, unknown> | undefined;

            if (!data || Object.keys(data).length === 0) {

                return null;

            }

            return data;

        },

        requestNotificationPermission: async () => {

            const ready = await ensureFirebaseReady();

            if (!ready) {

                return false;

            }

            try {

                if (Platform.OS === 'android' && Number(Platform.Version) >= 33) {

                    const result = await PermissionsAndroid.request(

                        PermissionsAndroid.PERMISSIONS.POST_NOTIFICATIONS,

                    );

                    if (result !== PermissionsAndroid.RESULTS.GRANTED) {

                        return false;

                    }

                }

                const authStatus = await messaging().requestPermission();

                return (

                    authStatus === messaging.AuthorizationStatus.AUTHORIZED

                    || authStatus === messaging.AuthorizationStatus.PROVISIONAL

                );

            } catch (error) {

                console.log('[VoIPFCM] requestNotificationPermission failed', error);

                return false;

            }

        },

    };

}


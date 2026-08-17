/**

 * Firebase FCM adapter for VoIP incoming-call + chat message push.

 * Foreground onMessage + background store (index.js) + notification tap handlers.

 */

import { PermissionsAndroid, Platform } from 'react-native';

import messaging from '@react-native-firebase/messaging';

import { runExclusivePermissionTask } from '../hooks/permissionRequestGate';
import { checkPermissionStatus } from '../hooks/usePermissionCheck';



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
            let unsubscribe: () => void = () => {};

            void ensureFirebaseReady().then((ready) => {
                if (!ready) {
                    return;
                }

                try {
                    unsubscribe = messaging().onMessage(async (remoteMessage) => {
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
                } catch (error) {
                    console.log('[VoIPFCM] subscribe bootstrap failed', error);
                }
            });

            return () => {
                unsubscribe();
            };

        },

        onNotificationOpened: (handler) => {
            let unsubscribe: () => void = () => {};

            void ensureFirebaseReady().then((ready) => {
                if (!ready) {
                    return;
                }

                try {
                    unsubscribe = messaging().onNotificationOpenedApp((remoteMessage) => {
                        const data = remoteMessage?.data as Record<string, unknown> | undefined;

                        if (data && Object.keys(data).length > 0) {
                            handler(data);
                        }
                    });
                } catch (error) {
                    console.log('[VoIPFCM] notification-open bootstrap failed', error);
                }
            });

            return () => {
                unsubscribe();
            };

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
            return runExclusivePermissionTask(async () => {
            const ready = await ensureFirebaseReady();

            if (!ready) {

                return false;

            }

            try {

                if (Platform.OS === 'android' && Number(Platform.Version) >= 33) {

                    const notificationPermission = PermissionsAndroid.PERMISSIONS.POST_NOTIFICATIONS;

                    const alreadyGranted = await checkPermissionStatus('POST_NOTIFICATIONS');

                    if (!alreadyGranted && notificationPermission) {

                        const result = await PermissionsAndroid.request(

                            notificationPermission,

                        );

                        if (result !== PermissionsAndroid.RESULTS.GRANTED) {

                            return false;

                        }

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
            });
        },

    };

}

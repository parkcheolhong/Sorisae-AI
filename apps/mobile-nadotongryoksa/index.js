import AsyncStorage from '@react-native-async-storage/async-storage';

import messaging from '@react-native-firebase/messaging';

import { registerRootComponent } from 'expo';



import App from './App';

import { handleWorldlincoPushData } from './src/services/worldlincoPushHandler';

import { shouldPersistWorldlincoFcmData } from './src/services/worldlincoPushBridge';

import { VOIP_FCM_PENDING_STORAGE_KEY } from './src/services/voipIncomingPushStore';



/**

 * Android background/killed: persist VoIP + chat FCM and play prominent local alerts.

 */

messaging().setBackgroundMessageHandler(async (remoteMessage) => {

    const data = remoteMessage?.data;

    if (!shouldPersistWorldlincoFcmData(data)) {

        return;

    }

    await AsyncStorage.setItem(

        VOIP_FCM_PENDING_STORAGE_KEY,

        JSON.stringify({

            stored_at: new Date().toISOString(),

            data,

        }),

    );

    try {

        await handleWorldlincoPushData(data, 'background');

    } catch (error) {

        console.log('[WorldlincoFCM] background push handler failed', error);

    }

});



registerRootComponent(App);


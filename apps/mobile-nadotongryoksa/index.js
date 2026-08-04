import AsyncStorage from '@react-native-async-storage/async-storage';

import firebase from '@react-native-firebase/app';
import messaging from '@react-native-firebase/messaging';

import { registerRootComponent } from 'expo';



import App from './App';

import { handleWorldlincoPushData } from './src/services/worldlincoPushHandler';

import { shouldPersistWorldlincoFcmData } from './src/services/worldlincoPushBridge';

import { VOIP_FCM_PENDING_STORAGE_KEY } from './src/services/voipIncomingPushStore';

const FIREBASE_ANDROID_OPTIONS = {
    apiKey: 'AIzaSyA90Rs93geo1Sz94HmdHL94X34r7eH8wGo',
    appId: '1:409873234227:android:094e3ebdb0001592b0a646',
    messagingSenderId: '409873234227',
    projectId: 'studio-9080238625-9cec3',
    storageBucket: 'studio-9080238625-9cec3.firebasestorage.app',
};

if (firebase.apps.length === 0) {
    try {
        firebase.initializeApp(FIREBASE_ANDROID_OPTIONS);
    } catch (error) {
        if (firebase.apps.length === 0) {
            console.log('[WorldlincoFCM] firebase bootstrap failed', error);
        }
    }
}

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

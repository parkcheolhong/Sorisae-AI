import { describe, expect, it, jest } from '@jest/globals';

const mockStopIncomingAlert = jest.fn(async () => true);

jest.mock('react-native', () => ({
    __esModule: true,
    AppState: { currentState: 'active' },
    Platform: { OS: 'android', Version: 34 },
    NativeModules: {
        VoipIncomingAlert: {
            stopIncomingAlert: mockStopIncomingAlert,
        },
    },
    Vibration: { cancel: jest.fn(), vibrate: jest.fn() },
}));

jest.mock('expo-notifications', () => ({
    setNotificationHandler: jest.fn(),
    dismissNotificationAsync: jest.fn(async () => undefined),
    getPresentedNotificationsAsync: jest.fn(async () => []),
    setNotificationChannelAsync: jest.fn(async () => undefined),
    scheduleNotificationAsync: jest.fn(async () => 'notification-id'),
    AndroidImportance: { MAX: 5 },
    AndroidNotificationPriority: { MAX: 5 },
    AndroidNotificationVisibility: { PUBLIC: 1 },
}));

jest.mock('../native/voipIncomingAlert', () => ({
    __esModule: true,
    isVoipIncomingAlertNativeAvailable: jest.fn(() => true),
    startNativeIncomingVoipAlert: jest.fn(),
    startNativeChatIncomingAlert: jest.fn(),
    stopNativeIncomingVoipAlert: jest.fn(async () => undefined),
}));

jest.mock('../services/voipIncomingNotifications', () => ({
    __esModule: true,
    showIncomingVoipLocalNotification: jest.fn(async () => undefined),
    dismissIncomingVoipLocalNotification: jest.fn(async () => undefined),
}));

jest.mock('../services/voipToneService', () => ({
    getVoIPToneService: jest.fn(() => ({
        stopAll: jest.fn(),
        playMessageTone: jest.fn(),
    })),
}));

jest.mock('../services/chatIncomingNotifications', () => ({
    showChatMessageLocalNotification: jest.fn(),
}));

jest.mock('../services/worldlincoPushBridge', () => ({
    parseChatMessageFcmData: jest.fn(() => null),
}));

jest.mock('../services/voipIncomingPushBridge', () => ({
    parseIncomingCallFcmData: jest.fn(() => null),
}));

jest.mock('../utils/voiceAnnounce', () => ({
    announceServerVoice: jest.fn(),
    buildAnnouncement: jest.fn(async () => '안내'),
    getStoredPreferredLanguage: jest.fn(async () => 'ko'),
    ttsLocaleForLang: jest.fn(() => 'ko-KR'),
}));

import { handleWorldlincoPushData } from '../services/worldlincoPushHandler';
import { emitVoipCallEnded, subscribeVoipCallEnded } from '../services/voipCallSignals';

describe('worldlincoPushHandler call-ended signal', () => {
    it('emits a shared call-ended signal for cancel pushes', async () => {
        const listener = jest.fn();
        const unsubscribe = subscribeVoipCallEnded(listener);

        await handleWorldlincoPushData(
            {
                type: 'voip_call_cancelled',
                call_id: 'call-123',
            },
            'background',
        );

        expect(listener).toHaveBeenCalledTimes(1);
        expect(listener).toHaveBeenCalledWith('call-123');

        unsubscribe();
        emitVoipCallEnded('call-123');
        expect(listener).toHaveBeenCalledTimes(1);
    });
});
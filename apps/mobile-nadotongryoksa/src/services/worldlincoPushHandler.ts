import { AppState, Platform, Vibration } from 'react-native';
import * as Speech from 'expo-speech';

import { showChatMessageLocalNotification } from './chatIncomingNotifications';
import {
    isVoipIncomingAlertNativeAvailable,
    startNativeChatIncomingAlert,
    startNativeIncomingVoipAlert,
} from '../native/voipIncomingAlert';
import { showIncomingVoipLocalNotification } from './voipIncomingNotifications';
import { parseChatMessageFcmData } from './worldlincoPushBridge';
import { parseIncomingCallFcmData } from './voipIncomingPushBridge';
import { getVoIPToneService } from './voipToneService';

const CHAT_ALERT_BURST_COUNT = 3;
const CHAT_ALERT_BURST_GAP_MS = 900;

function pulseVibration(times: number): void {
    if (Platform.OS === 'web') {
        return;
    }
    for (let index = 0; index < times; index += 1) {
        setTimeout(() => {
            try {
                Vibration.vibrate(500);
            } catch {
                // no-op
            }
        }, index * CHAT_ALERT_BURST_GAP_MS);
    }
}

function speakFriendHeyBurst(times: number): void {
    for (let index = 0; index < times; index += 1) {
        setTimeout(() => {
            try {
                Speech.speak('친구야', { language: 'ko-KR', rate: 1.0 });
            } catch {
                // no-op
            }
        }, index * CHAT_ALERT_BURST_GAP_MS);
    }
}

function playMessageToneBurst(times: number): void {
    for (let index = 0; index < times; index += 1) {
        setTimeout(() => {
            try {
                getVoIPToneService().playMessageTone();
            } catch {
                // no-op
            }
        }, index * CHAT_ALERT_BURST_GAP_MS);
    }
}

export async function handleWorldlincoPushData(
    data: Record<string, unknown>,
    source: 'foreground' | 'background' | 'notification_open',
): Promise<void> {
    const incomingCall = parseIncomingCallFcmData(data);
    if (incomingCall?.call_id) {
        if (isVoipIncomingAlertNativeAvailable()) {
            await startNativeIncomingVoipAlert(
                incomingCall.call_id,
                incomingCall.caller_label ?? incomingCall.caller_voice_id ?? '친구',
            );
        }
        await showIncomingVoipLocalNotification(data);
        return;
    }

    const chatMessage = parseChatMessageFcmData(data);
    if (!chatMessage) {
        return;
    }

    const senderLabel = chatMessage.sender_label ?? '친구';
    if (isVoipIncomingAlertNativeAvailable()) {
        await startNativeChatIncomingAlert(chatMessage.room_id, senderLabel);
    } else {
        playMessageToneBurst(CHAT_ALERT_BURST_COUNT);
        pulseVibration(CHAT_ALERT_BURST_COUNT);
        if (AppState.currentState === 'active') {
            speakFriendHeyBurst(CHAT_ALERT_BURST_COUNT);
        }
    }
    await showChatMessageLocalNotification({
        ...data,
        alert_phrase: chatMessage.alert_phrase ?? '친구야~',
    });
}

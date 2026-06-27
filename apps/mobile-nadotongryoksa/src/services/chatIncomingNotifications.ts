import { Platform } from 'react-native';
import * as Notifications from 'expo-notifications';

export const CHAT_MESSAGE_CHANNEL_ID = 'worldlinco_chat_message';

export async function ensureChatMessageNotificationChannel(): Promise<void> {
    if (Platform.OS !== 'android') {
        return;
    }
    await Notifications.setNotificationChannelAsync(CHAT_MESSAGE_CHANNEL_ID, {
        name: '채팅 메시지',
        importance: Notifications.AndroidImportance.MAX,
        sound: 'default',
        vibrationPattern: [0, 320, 160, 320, 160, 320],
        lockscreenVisibility: Notifications.AndroidNotificationVisibility.PUBLIC,
        bypassDnd: false,
        enableVibrate: true,
        enableLights: true,
        lightColor: '#58C9FF',
    });
}

export async function showChatMessageLocalNotification(
    data: Record<string, unknown>,
): Promise<void> {
    const sender = String(data.sender_label ?? '친구');
    const preview = String(data.body_preview ?? '').trim();
    const phrase = String(data.alert_phrase ?? '친구야~');
    await ensureChatMessageNotificationChannel();
    await Notifications.scheduleNotificationAsync({
        content: {
            title: '(월드링코) 채팅',
            body: preview ? `${sender}: ${phrase} ${preview}` : `${sender}: ${phrase}`,
            data,
            sound: true,
            priority: Notifications.AndroidNotificationPriority.MAX,
            ...(Platform.OS === 'android'
                ? { channelId: CHAT_MESSAGE_CHANNEL_ID }
                : {}),
        },
        trigger: null,
    });
}

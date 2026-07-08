import { Platform } from 'react-native';
import * as Notifications from 'expo-notifications';

export const VOIP_INCOMING_CHANNEL_ID = 'worldlinco_incoming_voip_v2';

Notifications.setNotificationHandler({
    handleNotification: async () => ({
        shouldShowAlert: true,
        shouldPlaySound: true,
        shouldSetBadge: false,
        shouldShowBanner: true,
        shouldShowList: true,
    }),
});

export async function ensureVoipIncomingNotificationChannel(): Promise<void> {
    if (Platform.OS !== 'android') {
        return;
    }
    await Notifications.setNotificationChannelAsync(VOIP_INCOMING_CHANNEL_ID, {
        name: '보이스톡 착신',
        importance: Notifications.AndroidImportance.MAX,
        sound: 'default',
        vibrationPattern: [0, 450, 180, 450],
        lockscreenVisibility: Notifications.AndroidNotificationVisibility.PUBLIC,
        bypassDnd: false,
        enableVibrate: true,
        enableLights: true,
        lightColor: '#58C9FF',
    });
}

export async function showIncomingVoipLocalNotification(
    data: Record<string, unknown>,
): Promise<void> {
    const caller = String(
        data.caller_label ?? data.display_label ?? data.caller_voice_id ?? '친구',
    );
    await ensureVoipIncomingNotificationChannel();
    await Notifications.scheduleNotificationAsync({
        content: {
            title: '(월드링코) 보이스톡',
            body: `${caller} 님이 보이스톡을 걸고 있습니다.`,
            data,
            sound: true,
            priority: Notifications.AndroidNotificationPriority.MAX,
            ...(Platform.OS === 'android'
                ? { channelId: VOIP_INCOMING_CHANNEL_ID }
                : {}),
        },
        trigger: null,
    });
}

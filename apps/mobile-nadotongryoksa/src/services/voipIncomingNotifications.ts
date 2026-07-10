import { Platform } from 'react-native';
import * as Notifications from 'expo-notifications';

export const VOIP_INCOMING_CHANNEL_ID = 'worldlinco_incoming_voip_v2';

// 착신 알림 고정 식별자: reassert(재요청) 시 새 알림을 쌓지 않고 **같은 알림을 교체**한다.
// (식별자가 없으면 expo 가 매번 새 알림을 만들어 수십 개가 누적·각자 링톤 재생 → 영구 벨)
export const VOIP_INCOMING_NOTIFICATION_REQUEST_ID = 'worldlinco-voip-incoming';

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
        identifier: VOIP_INCOMING_NOTIFICATION_REQUEST_ID,
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

// 착신 알림을 즉시 내린다(받기/거절/끊기/워치독 시 호출). 고정 식별자 알림을 dismiss 하고,
// 혹시 식별자 없이 이미 누적된 과거 착신 알림까지 같은 채널 기준으로 모두 정리한다.
// (이게 없으면 systemui 가 알림 링톤을 계속 재생 → 받고 끊어도 수신 벨이 안 멈춤)
export async function dismissIncomingVoipLocalNotification(): Promise<void> {
    try {
        await Notifications.dismissNotificationAsync(VOIP_INCOMING_NOTIFICATION_REQUEST_ID);
    } catch {
        // no-op
    }
    try {
        const presented = await Notifications.getPresentedNotificationsAsync();
        for (const item of presented) {
            const request: any = item?.request ?? {};
            const content: any = request?.content ?? {};
            const channelId =
                content?.channelId ??
                request?.trigger?.channelId ??
                null;
            const isVoipIncoming =
                request?.identifier === VOIP_INCOMING_NOTIFICATION_REQUEST_ID ||
                channelId === VOIP_INCOMING_CHANNEL_ID;
            if (isVoipIncoming && request?.identifier) {
                try {
                    await Notifications.dismissNotificationAsync(request.identifier);
                } catch {
                    // no-op
                }
            }
        }
    } catch {
        // no-op
    }
}

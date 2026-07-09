import { NativeModules, Platform } from 'react-native';

export type IncomingAlertSoundMode = 'sound' | 'vibrate' | 'silent';

type VoipIncomingAlertNativeModule = {
    startIncomingAlert: (callId: string, callerLabel: string, soundMode: string) => Promise<boolean>;
    startChatIncomingAlert: (
        roomId: string,
        senderLabel: string,
        announceText: string | null,
        localeTag: string | null,
        skipSpeak: boolean,
    ) => Promise<boolean>;
    stopIncomingAlert: () => Promise<boolean>;
    areNotificationsEnabled: () => Promise<boolean>;
    openNotificationSettings: () => Promise<boolean>;
};

export type ChatIncomingAlertVoice = {
    // 백그라운드 단말 TTS 발화용 지정언어 안내 문장 + BCP47 로케일.
    announceText?: string | null;
    localeTag?: string | null;
    // true 면 네이티브가 발화하지 않는다(포그라운드에서 JS 서버 뉴럴 TTS가 발화할 때).
    skipSpeak?: boolean;
};

const nativeModule = NativeModules.VoipIncomingAlert as VoipIncomingAlertNativeModule | undefined;

export function isVoipIncomingAlertNativeAvailable(): boolean {
    return Platform.OS === 'android' && Boolean(nativeModule?.startIncomingAlert);
}

export async function startNativeIncomingVoipAlert(
    callId: string,
    callerLabel: string,
    soundMode: IncomingAlertSoundMode = 'sound',
): Promise<boolean> {
    if (!isVoipIncomingAlertNativeAvailable()) {
        return false;
    }
    try {
        return await nativeModule!.startIncomingAlert(callId, callerLabel, soundMode);
    } catch {
        return false;
    }
}

export async function startNativeChatIncomingAlert(
    roomId: string,
    senderLabel: string,
    voice: ChatIncomingAlertVoice = {},
): Promise<boolean> {
    if (Platform.OS !== 'android' || !nativeModule?.startChatIncomingAlert) {
        return false;
    }
    try {
        return await nativeModule.startChatIncomingAlert(
            roomId,
            senderLabel,
            voice.announceText ?? null,
            voice.localeTag ?? null,
            voice.skipSpeak ?? false,
        );
    } catch {
        return false;
    }
}

export async function stopNativeIncomingVoipAlert(): Promise<void> {
    if (!isVoipIncomingAlertNativeAvailable()) {
        return;
    }
    try {
        await nativeModule!.stopIncomingAlert();
    } catch {
        // no-op
    }
}

export async function areVoipNotificationsEnabled(): Promise<boolean> {
    if (!isVoipIncomingAlertNativeAvailable()) {
        return true;
    }
    try {
        return await nativeModule!.areNotificationsEnabled();
    } catch {
        return true;
    }
}

export async function openVoipNotificationSettings(): Promise<void> {
    if (!isVoipIncomingAlertNativeAvailable()) {
        return;
    }
    try {
        await nativeModule!.openNotificationSettings();
    } catch {
        // no-op
    }
}

import { NativeModules, Platform } from 'react-native';

type VoipIncomingAlertNativeModule = {
    startIncomingAlert: (callId: string, callerLabel: string) => Promise<boolean>;
    startChatIncomingAlert: (roomId: string, senderLabel: string) => Promise<boolean>;
    stopIncomingAlert: () => Promise<boolean>;
    areNotificationsEnabled: () => Promise<boolean>;
    openNotificationSettings: () => Promise<boolean>;
};

const nativeModule = NativeModules.VoipIncomingAlert as VoipIncomingAlertNativeModule | undefined;

export function isVoipIncomingAlertNativeAvailable(): boolean {
    return Platform.OS === 'android' && Boolean(nativeModule?.startIncomingAlert);
}

export async function startNativeIncomingVoipAlert(
    callId: string,
    callerLabel: string,
): Promise<boolean> {
    if (!isVoipIncomingAlertNativeAvailable()) {
        return false;
    }
    try {
        return await nativeModule!.startIncomingAlert(callId, callerLabel);
    } catch {
        return false;
    }
}

export async function startNativeChatIncomingAlert(
    roomId: string,
    senderLabel: string,
): Promise<boolean> {
    if (Platform.OS !== 'android' || !nativeModule?.startChatIncomingAlert) {
        return false;
    }
    try {
        return await nativeModule.startChatIncomingAlert(roomId, senderLabel);
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

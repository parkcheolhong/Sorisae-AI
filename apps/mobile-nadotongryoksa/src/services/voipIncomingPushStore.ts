import AsyncStorage from '@react-native-async-storage/async-storage';

export const VOIP_FCM_PENDING_STORAGE_KEY = 'nadot_voip_pending_fcm_incoming_v1';

export type StoredVoipIncomingPush = {
    stored_at: string;
    data: Record<string, unknown>;
};

export async function storePendingIncomingPush(data: Record<string, unknown>): Promise<void> {
    const envelope: StoredVoipIncomingPush = {
        stored_at: new Date().toISOString(),
        data,
    };
    await AsyncStorage.setItem(VOIP_FCM_PENDING_STORAGE_KEY, JSON.stringify(envelope));
}

export async function peekPendingIncomingPush(): Promise<StoredVoipIncomingPush | null> {
    const raw = await AsyncStorage.getItem(VOIP_FCM_PENDING_STORAGE_KEY);
    if (!raw) {
        return null;
    }
    try {
        const parsed = JSON.parse(raw) as StoredVoipIncomingPush;
        if (!parsed?.data || typeof parsed.data !== 'object') {
            return null;
        }
        return parsed;
    } catch {
        return null;
    }
}

export async function consumePendingIncomingPush(): Promise<StoredVoipIncomingPush | null> {
    const pending = await peekPendingIncomingPush();
    if (!pending) {
        return null;
    }
    await AsyncStorage.removeItem(VOIP_FCM_PENDING_STORAGE_KEY);
    return pending;
}

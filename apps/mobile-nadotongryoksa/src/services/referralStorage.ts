import AsyncStorage from '@react-native-async-storage/async-storage';

const PENDING_REFERRAL_CODE_KEY = 'worldlinco_pending_referral_code_v1';

export async function savePendingReferralCode(code: string): Promise<void> {
    const normalized = String(code || '').trim().toUpperCase();
    if (!normalized.startsWith('WL')) {
        return;
    }
    await AsyncStorage.setItem(PENDING_REFERRAL_CODE_KEY, normalized);
}

export async function getPendingReferralCode(): Promise<string | null> {
    const raw = await AsyncStorage.getItem(PENDING_REFERRAL_CODE_KEY);
    const normalized = String(raw || '').trim().toUpperCase();
    return normalized.startsWith('WL') ? normalized : null;
}

export async function consumePendingReferralCode(): Promise<string | null> {
    const code = await getPendingReferralCode();
    if (code) {
        await AsyncStorage.removeItem(PENDING_REFERRAL_CODE_KEY);
    }
    return code;
}

export async function clearPendingReferralCode(): Promise<void> {
    await AsyncStorage.removeItem(PENDING_REFERRAL_CODE_KEY);
}

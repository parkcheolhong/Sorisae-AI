import AsyncStorage from '@react-native-async-storage/async-storage';
import * as LocalAuthentication from 'expo-local-authentication';
import * as SecureStore from 'expo-secure-store';

const BIOMETRIC_LOGIN_ENABLED_KEY = 'worldlinco_biometric_login_enabled_v1';
const BIOMETRIC_CREDENTIALS_KEY = 'worldlinco_biometric_credentials_v1';

export type StoredBiometricCredentials = {
    email: string;
    password: string;
};

export async function isBiometricAvailable(): Promise<boolean> {
    try {
        const compatible = await LocalAuthentication.hasHardwareAsync();
        if (!compatible) {
            return false;
        }
        const enrolled = await LocalAuthentication.isEnrolledAsync();
        return enrolled;
    } catch {
        return false;
    }
}

export async function authenticateWithBiometric(reason: string): Promise<boolean> {
    try {
        const available = await isBiometricAvailable();
        if (!available) {
            return true;
        }
        const result = await LocalAuthentication.authenticateAsync({
            promptMessage: reason,
            cancelLabel: '취소',
            disableDeviceFallback: false,
            fallbackLabel: '기기 비밀번호 사용',
        });
        return result.success;
    } catch {
        return false;
    }
}

export async function isBiometricLoginEnabled(): Promise<boolean> {
    const raw = await AsyncStorage.getItem(BIOMETRIC_LOGIN_ENABLED_KEY);
    return raw === '1';
}

export async function setBiometricLoginEnabled(enabled: boolean): Promise<void> {
    if (enabled) {
        await AsyncStorage.setItem(BIOMETRIC_LOGIN_ENABLED_KEY, '1');
        return;
    }
    await AsyncStorage.removeItem(BIOMETRIC_LOGIN_ENABLED_KEY);
    await SecureStore.deleteItemAsync(BIOMETRIC_CREDENTIALS_KEY).catch(() => undefined);
}

export async function saveBiometricCredentials(credentials: StoredBiometricCredentials): Promise<void> {
    const available = await isBiometricAvailable();
    if (!available) {
        throw new Error('이 기기에서는 지문/생체 인증을 사용할 수 없습니다.');
    }
    await SecureStore.setItemAsync(
        BIOMETRIC_CREDENTIALS_KEY,
        JSON.stringify({
            email: credentials.email.trim(),
            password: credentials.password,
        }),
        {
            requireAuthentication: true,
            authenticationPrompt: '지문으로 로그인 정보를 저장합니다',
        },
    );
    await setBiometricLoginEnabled(true);
}

export async function loadBiometricCredentials(): Promise<StoredBiometricCredentials | null> {
    const enabled = await isBiometricLoginEnabled();
    if (!enabled) {
        return null;
    }
    try {
        const raw = await SecureStore.getItemAsync(BIOMETRIC_CREDENTIALS_KEY, {
            requireAuthentication: true,
            authenticationPrompt: '지문으로 로그인합니다',
        });
        if (!raw) {
            return null;
        }
        const parsed = JSON.parse(raw) as StoredBiometricCredentials;
        if (!parsed.email?.trim() || !parsed.password) {
            return null;
        }
        return parsed;
    } catch {
        return null;
    }
}

export async function updateBiometricStoredPassword(newPassword: string): Promise<void> {
    const enabled = await isBiometricLoginEnabled();
    if (!enabled) {
        return;
    }
    const credentials = await loadBiometricCredentials();
    if (!credentials) {
        return;
    }
    await saveBiometricCredentials({
        email: credentials.email,
        password: newPassword,
    });
}

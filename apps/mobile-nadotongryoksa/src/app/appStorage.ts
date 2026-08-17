// App.tsx 에서 분리한 영속화(SecureStore auth + AsyncStorage VoIP) 헬퍼(순수/부수효과 함수).
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';
import { AUTH_STORAGE_KEY, ACTIVE_VOIP_CALL_STORAGE_KEY } from './appConstants';
import type { UserInfo, StoredActiveVoipSession } from './appTypes';
import type { SectionRailKey } from '../features/navigation/sectionRegistry';

async function isSecureAuthStorageAvailable(): Promise<boolean> {
    try {
        return await SecureStore.isAvailableAsync();
    } catch {
        return false;
    }
}

export async function loadStoredAuthState(): Promise<{ token: string; userInfo: UserInfo } | null> {
    const secureAvailable = await isSecureAuthStorageAvailable();
    const secureRaw = secureAvailable
        ? await SecureStore.getItemAsync(AUTH_STORAGE_KEY).catch(() => null)
        : null;
    const legacyRaw = !secureRaw ? await AsyncStorage.getItem(AUTH_STORAGE_KEY) : null;
    const raw = secureRaw || legacyRaw;
    if (!raw) {
        return null;
    }

    try {
        const parsed = JSON.parse(raw) as { token?: string; userInfo?: UserInfo };
        if (!parsed.token || !parsed.userInfo?.id || !parsed.userInfo?.email) {
            return null;
        }

        if (secureAvailable && legacyRaw) {
            await SecureStore.setItemAsync(AUTH_STORAGE_KEY, raw).catch(() => undefined);
            await AsyncStorage.removeItem(AUTH_STORAGE_KEY).catch(() => undefined);
        }

        return {
            token: parsed.token,
            userInfo: parsed.userInfo,
        };
    } catch {
        return null;
    }
}

export async function saveStoredAuthState(token: string, userInfo: UserInfo): Promise<void> {
    const payload = JSON.stringify({ token, userInfo });
    if (await isSecureAuthStorageAvailable()) {
        await SecureStore.setItemAsync(AUTH_STORAGE_KEY, payload);
        await AsyncStorage.removeItem(AUTH_STORAGE_KEY).catch(() => undefined);
        return;
    }

    await AsyncStorage.setItem(AUTH_STORAGE_KEY, payload);
}

export async function clearStoredAuthState(): Promise<void> {
    await SecureStore.deleteItemAsync(AUTH_STORAGE_KEY).catch(() => undefined);
    await AsyncStorage.removeItem(AUTH_STORAGE_KEY);
}

export async function loadStoredActiveVoipSession(): Promise<StoredActiveVoipSession | null> {
    const raw = await AsyncStorage.getItem(ACTIVE_VOIP_CALL_STORAGE_KEY);
    if (!raw) {
        return null;
    }

    try {
        const parsed = JSON.parse(raw) as StoredActiveVoipSession | string;
        if (typeof parsed === 'string') {
            const normalized = parsed.trim();
            return normalized ? { callId: normalized } : null;
        }

        const normalizedCallId = typeof parsed.callId === 'string' ? parsed.callId.trim() : '';
        if (!normalizedCallId) {
            return null;
        }

        return {
            callId: normalizedCallId,
            railSection: parsed.railSection ?? null,
            acceptedParticipantRole: parsed.acceptedParticipantRole === 'caller' || parsed.acceptedParticipantRole === 'callee'
                ? parsed.acceptedParticipantRole
                : null,
            acceptedAt: typeof parsed.acceptedAt === 'string' && parsed.acceptedAt.trim() ? parsed.acceptedAt : null,
        };
    } catch {
        const normalized = raw.trim();
        return normalized ? { callId: normalized } : null;
    }
}

export async function saveStoredActiveVoipSession(
    callId: string,
    railSection?: SectionRailKey | null,
    acceptedParticipantRole?: 'caller' | 'callee' | null,
): Promise<void> {
    await AsyncStorage.setItem(
        ACTIVE_VOIP_CALL_STORAGE_KEY,
        JSON.stringify({
            callId: callId.trim(),
            railSection: 'voip',
            acceptedParticipantRole: acceptedParticipantRole ?? null,
            acceptedAt: acceptedParticipantRole ? new Date().toISOString() : null,
        } satisfies StoredActiveVoipSession),
    );
}

export function isStoredAcceptedCalleeVoipSession(storedSession: StoredActiveVoipSession | null, callId: string): boolean {
    return storedSession?.callId === callId
        && storedSession.acceptedParticipantRole === 'callee'
        && typeof storedSession.acceptedAt === 'string'
        && storedSession.acceptedAt.length > 0;
}

export function isRuntimeAcceptedCalleeVoipSession(
    storedSession: StoredActiveVoipSession | null,
    callId: string,
    acceptedCallId: string | null,
): boolean {
    return acceptedCallId === callId || isStoredAcceptedCalleeVoipSession(storedSession, callId);
}

export async function clearStoredActiveVoipSession(): Promise<void> {
    await AsyncStorage.removeItem(ACTIVE_VOIP_CALL_STORAGE_KEY);
}

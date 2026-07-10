/** 소리새 friend-chat ↔ 서버 trip_sessions 연동 (단말 session_id SSOT). */
import AsyncStorage from '@react-native-async-storage/async-storage';

const STORAGE_PREFIX = 'nadot_companion_trip_session_v1';

function storageKey(userId: number): string {
    return `${STORAGE_PREFIX}:${userId}`;
}

export async function loadCompanionTripSessionId(userId: number): Promise<string | null> {
    try {
        const raw = await AsyncStorage.getItem(storageKey(userId));
        const trimmed = String(raw || '').trim();
        return trimmed.length > 0 ? trimmed : null;
    } catch {
        return null;
    }
}

export async function saveCompanionTripSessionId(userId: number, sessionId: string): Promise<void> {
    const trimmed = String(sessionId || '').trim();
    if (!trimmed) return;
    try {
        await AsyncStorage.setItem(storageKey(userId), trimmed);
    } catch {
        // best-effort
    }
}

export async function clearCompanionTripSessionId(userId: number): Promise<void> {
    try {
        await AsyncStorage.removeItem(storageKey(userId));
    } catch {
        // best-effort
    }
}

export type FriendChatTripContext = {
    tripSessionId: string | null;
    userId: number | null;
};

/** friend-chat POST body에 trip/user 컨텍스트를 주입한다. */
export function withFriendChatTripContext<T extends Record<string, unknown>>(
    payload: T,
    ctx: FriendChatTripContext,
): T & { trip_session_id?: string; user_id?: number } {
    const out: T & { trip_session_id?: string; user_id?: number } = { ...payload };
    if (ctx.tripSessionId) {
        out.trip_session_id = ctx.tripSessionId;
    }
    if (ctx.userId != null && ctx.userId > 0) {
        out.user_id = ctx.userId;
    }
    return out;
}

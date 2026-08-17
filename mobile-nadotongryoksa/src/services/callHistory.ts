// 앱 통화내역(최근기록) SSOT — 단말 네이티브 통화로그(READ_CALL_LOG)는 Play 정책상 기본 전화앱만
// 접근 가능하므로 사용하지 않고, 앱이 직접 처리한 통화(통역통화 VoIP·일반전화 통역 발신·부재중)를
// AsyncStorage 에 로컬 기록한다. 부재중 VoIP 는 백엔드(fetchRecentMissedCalls)와 병합해 보여준다.
import AsyncStorage from '@react-native-async-storage/async-storage';

export type CallDirection = 'out' | 'in' | 'missed';
export type CallKind = 'voip' | 'pstn';

export type CallHistoryEntry = {
    id: string;
    kind: CallKind;            // voip(통역통화) | pstn(일반전화 통역)
    direction: CallDirection;  // out(발신) | in(수신) | missed(부재중)
    label: string;             // 표시 이름(연락처/친구/번호)
    phone?: string | null;
    voiceId?: string | null;
    friendUserId?: number | null;
    at: string;                // ISO timestamp
};

const KEY = 'worldlinco_call_history_v1';
const MAX = 100;

let memory: CallHistoryEntry[] | null = null;

function sortDesc(rows: CallHistoryEntry[]): CallHistoryEntry[] {
    return [...rows].sort((a, b) => (a.at < b.at ? 1 : a.at > b.at ? -1 : 0));
}

/** 로컬 통화내역 적재(최신순). 실패 시 빈 배열. */
export async function loadCallHistory(): Promise<CallHistoryEntry[]> {
    if (memory) {
        return memory;
    }
    try {
        const raw = await AsyncStorage.getItem(KEY);
        const parsed = raw ? JSON.parse(raw) : [];
        const rows: CallHistoryEntry[] = Array.isArray(parsed)
            ? parsed.filter((r) => r && r.id && r.at)
            : [];
        memory = sortDesc(rows);
        return memory;
    } catch {
        memory = [];
        return memory;
    }
}

/** 통화 1건 기록(발신/수신/부재중). 최신순으로 누적하고 MAX 건으로 제한한다. */
export async function recordCall(
    entry: Omit<CallHistoryEntry, 'id' | 'at'> & { at?: string },
): Promise<CallHistoryEntry[]> {
    const row: CallHistoryEntry = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        at: entry.at ?? new Date().toISOString(),
        kind: entry.kind,
        direction: entry.direction,
        label: entry.label,
        phone: entry.phone ?? null,
        voiceId: entry.voiceId ?? null,
        friendUserId: entry.friendUserId ?? null,
    };
    const current = await loadCallHistory();
    const next = sortDesc([row, ...current]).slice(0, MAX);
    memory = next;
    try {
        await AsyncStorage.setItem(KEY, JSON.stringify(next));
    } catch {
        /* 저장 실패는 무시(메모리 캐시는 유지) */
    }
    return next;
}

/** 통화내역 전체 삭제. */
export async function clearCallHistory(): Promise<void> {
    memory = [];
    try {
        await AsyncStorage.removeItem(KEY);
    } catch {
        /* 무시 */
    }
}

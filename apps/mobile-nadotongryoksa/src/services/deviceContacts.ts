// 단말 전화번호부(연락처) 연동 SSOT.
// - 단말 연락처를 1회 읽어 정규화 인덱스(번호 끝자리 → 이름)를 만들고 메모리/AsyncStorage 에 캐시한다.
// - 착신/부재중/친구의 전화번호를 단말 연락처 이름으로 해석(resolveContactName)한다.
// - 연락처 디렉터리 화면(VOIP/일반전화/채팅 연동)에서 목록을 제공한다.
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { normalizePhoneKey } from './phoneKey';

export type DeviceContact = {
    id: string;
    name: string;
    // 표시용 원본 번호(첫 번째). 단말에 저장된 형식 그대로.
    phone: string;
    // 매칭용 정규화 키 목록(여러 번호 가능).
    keys: string[];
};

const CACHE_KEY = 'worldlinco_device_contacts_v1';

let memoryContacts: DeviceContact[] | null = null;
// 정규화 키(끝 9자리) → 이름. 빠른 역방향 조회용.
let nameIndex: Map<string, string> | null = null;
let lastLoadedAt = 0;

// 번호 정규화 키는 순수 모듈(phoneKey.ts)로 분리해 SSOT 로 공유한다(react-native 비의존, 테스트 가능).
export { normalizePhoneKey } from './phoneKey';

function buildIndex(contacts: DeviceContact[]): Map<string, string> {
    const index = new Map<string, string>();
    for (const c of contacts) {
        for (const key of c.keys) {
            if (key && !index.has(key)) {
                index.set(key, c.name);
            }
        }
    }
    return index;
}

// 단말 연락처 적재(권한 요청 포함). force=false 면 메모리/스토리지 캐시 우선.
export async function loadDeviceContacts(force = false): Promise<DeviceContact[]> {
    if (Platform.OS === 'web') {
        return [];
    }
    if (!force && memoryContacts) {
        return memoryContacts;
    }
    if (!force) {
        try {
            const cached = await AsyncStorage.getItem(CACHE_KEY);
            if (cached) {
                const parsed = JSON.parse(cached) as DeviceContact[];
                if (Array.isArray(parsed) && parsed.length > 0) {
                    memoryContacts = parsed;
                    nameIndex = buildIndex(parsed);
                    return parsed;
                }
            }
        } catch {
            // no-op
        }
    }

    try {
        // expo SDK 56: 메인 'expo-contacts' 의 getContactsAsync 는 deprecated 라 호출 시 throw 한다.
        // 레거시 함수형 API('expo-contacts/legacy')를 사용해 기존 동작을 유지한다(마이그레이션 가이드).
        const Contacts = await import('expo-contacts/legacy');
        let permission = await Contacts.requestPermissionsAsync();
        // 이미 OS 권한이 부여됐는데 request 가 granted 를 늦게 반영하는 케이스 폴백.
        if (permission.status !== 'granted') {
            try {
                permission = await Contacts.getPermissionsAsync();
            } catch {
                // no-op
            }
        }
        console.log('[DEVICE_CONTACTS]', JSON.stringify({ event: 'permission', status: permission.status, granted: permission.granted }));
        if (permission.status !== 'granted') {
            return memoryContacts ?? [];
        }
        const { data } = await Contacts.getContactsAsync({
            fields: [Contacts.Fields.Name, Contacts.Fields.PhoneNumbers],
        });
        console.log('[DEVICE_CONTACTS]', JSON.stringify({ event: 'fetched', raw_count: Array.isArray(data) ? data.length : -1 }));
        const contacts: DeviceContact[] = [];
        for (const entry of data) {
            const numbers = (entry.phoneNumbers ?? [])
                .map((p) => String(p.number ?? '').trim())
                .filter(Boolean);
            if (numbers.length === 0) {
                continue;
            }
            const keys = Array.from(new Set(numbers.map(normalizePhoneKey).filter(Boolean)));
            if (keys.length === 0) {
                continue;
            }
            contacts.push({
                id: String(entry.id ?? `${entry.name ?? 'contact'}-${numbers[0]}`),
                name: (entry.name ?? '').trim() || numbers[0],
                phone: numbers[0],
                keys,
            });
        }
        contacts.sort((a, b) => a.name.localeCompare(b.name));
        console.log('[DEVICE_CONTACTS]', JSON.stringify({ event: 'mapped', usable_count: contacts.length }));
        memoryContacts = contacts;
        nameIndex = buildIndex(contacts);
        lastLoadedAt = Date.now();
        AsyncStorage.setItem(CACHE_KEY, JSON.stringify(contacts)).catch(() => { /* no-op */ });
        return contacts;
    } catch (e: any) {
        console.log('[DEVICE_CONTACTS]', JSON.stringify({ event: 'error', message: String(e?.message ?? e) }));
        return memoryContacts ?? [];
    }
}

// 전화번호 → 단말 연락처 이름. 인덱스가 비어 있으면 캐시를 시도 적재한다(권한 요청 없음).
export function resolveContactNameSync(phone?: string | null): string | null {
    const key = normalizePhoneKey(phone);
    if (!key || !nameIndex) {
        return null;
    }
    return nameIndex.get(key) ?? null;
}

// 비동기 해석: 캐시/메모리를 보장 적재 후 이름을 반환(권한이 이미 허용된 경우에만 신규 적재).
export async function resolveContactName(phone?: string | null): Promise<string | null> {
    const key = normalizePhoneKey(phone);
    if (!key) {
        return null;
    }
    if (!nameIndex) {
        await loadDeviceContacts(false);
    }
    return nameIndex?.get(key) ?? null;
}

export function getCachedContacts(): DeviceContact[] {
    return memoryContacts ?? [];
}

export function getContactsLastLoadedAt(): number {
    return lastLoadedAt;
}

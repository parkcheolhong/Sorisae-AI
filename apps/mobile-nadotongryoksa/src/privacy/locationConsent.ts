// 위치·검색 데이터 이용 동의(PIPA/GDPR 데이터 최소화).
// 사용자가 명시적으로 동의하기 전에는 정밀 좌표(lat/lon)를 서버로 보내지 않는다.
// 미동의 시 관광 일정/장소 기능은 '지역명' 기반으로만 동작(좌표 미전송).
import AsyncStorage from '@react-native-async-storage/async-storage';

// 동의 문구가 실질적으로 바뀌면 버전을 올려 재동의를 유도한다.
export const LOCATION_CONSENT_VERSION = '2026-06-location-v1';
const STORAGE_KEY = 'worldlinco_location_consent_v1';

export type LocationConsentState = {
    granted: boolean;
    version: string;
    decidedAt: string | null;
};

const EMPTY: LocationConsentState = { granted: false, version: '', decidedAt: null };

export async function getLocationConsent(): Promise<LocationConsentState> {
    try {
        const raw = await AsyncStorage.getItem(STORAGE_KEY);
        if (!raw) return EMPTY;
        const parsed = JSON.parse(raw) as Partial<LocationConsentState>;
        return {
            granted: Boolean(parsed.granted),
            version: String(parsed.version || ''),
            decidedAt: parsed.decidedAt ? String(parsed.decidedAt) : null,
        };
    } catch {
        return EMPTY;
    }
}

// 현재 버전 동의가 유효한지(문구 갱신 시 false → 재동의 필요).
export async function hasValidLocationConsent(): Promise<boolean> {
    const state = await getLocationConsent();
    return state.granted && state.version === LOCATION_CONSENT_VERSION;
}

export async function setLocationConsent(granted: boolean): Promise<LocationConsentState> {
    const next: LocationConsentState = {
        granted,
        version: LOCATION_CONSENT_VERSION,
        decidedAt: new Date().toISOString(),
    };
    try {
        await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
        // 저장 실패해도 런타임 결정은 호출부에서 사용 — 조용히 무시.
    }
    return next;
}

export async function clearLocationConsent(): Promise<void> {
    try {
        await AsyncStorage.removeItem(STORAGE_KEY);
    } catch {
        // noop
    }
}

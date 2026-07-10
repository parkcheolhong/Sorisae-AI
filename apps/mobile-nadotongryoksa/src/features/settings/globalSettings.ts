/**
 * 전역 설정 SSOT(APP_DESIGN 2-6) — 사용자가 톱니(⚙️) 설정 탭에서 한 번 켜두면, 각 화면이
 * 이 값을 "기본값"으로 읽어 그때그때 수동 제스처(마이크 누르기 등) 없이 동작하도록 한다.
 *
 * 영속: AsyncStorage 단일 키(JSON). 구독(subscribe)으로 화면들이 변경을 즉시 반영한다.
 * 여기서 다루는 값은 모두 실제 배선된 토글만 둔다(미배선 더미 토글 금지).
 *  - autoListen  : 채팅방 진입 시 핸즈프리(자동 듣기) 루프 자동 시작 (useChatVoiceInput).
 *  - sorisaeFab  : 홈 화면 플로팅 소리새(🐦) 버튼 표시 여부 (App.tsx).
 * (수신 메시지 자동 읽어주기는 기존 companionChatReadAloud 저장소가 SSOT 이므로 여기서 중복 보관하지 않는다.)
 */
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useEffect, useState } from 'react';

export interface GlobalSettings {
    /** 채팅 자동 듣기(핸즈프리) 기본값 — 채팅방 진입 시 마이크 대기 시작. */
    autoListen: boolean;
    /** 홈 플로팅 소리새 버튼 표시. */
    sorisaeFab: boolean;
    /** VoIP 통화 기본 오디오 출력(true=스피커, false=이어피스/이어폰 우선). */
    voipSpeakerDefaultOn: boolean;
}

export const GLOBAL_SETTINGS_STORAGE_KEY = 'worldlinco.globalSettings.v1';

export const DEFAULT_GLOBAL_SETTINGS: GlobalSettings = {
    autoListen: false,
    sorisaeFab: true,
    voipSpeakerDefaultOn: false,
};

let cache: GlobalSettings = { ...DEFAULT_GLOBAL_SETTINGS };
let loaded = false;
const listeners = new Set<(s: GlobalSettings) => void>();

/** 앱 시작 시 1회 호출 — 저장값을 캐시에 로드한다(이후 get*은 동기 반환). */
export async function loadGlobalSettings(): Promise<GlobalSettings> {
    try {
        const raw = await AsyncStorage.getItem(GLOBAL_SETTINGS_STORAGE_KEY);
        if (raw) {
            const parsed = JSON.parse(raw) as Partial<GlobalSettings>;
            cache = { ...DEFAULT_GLOBAL_SETTINGS, ...parsed };
        }
    } catch {
        cache = { ...DEFAULT_GLOBAL_SETTINGS };
    }
    loaded = true;
    listeners.forEach((fn) => fn(cache));
    return cache;
}

export function getGlobalSettings(): GlobalSettings {
    return cache;
}

export function isGlobalSettingsLoaded(): boolean {
    return loaded;
}

export async function setGlobalSetting<K extends keyof GlobalSettings>(key: K, value: GlobalSettings[K]): Promise<void> {
    cache = { ...cache, [key]: value };
    listeners.forEach((fn) => fn(cache));
    try {
        await AsyncStorage.setItem(GLOBAL_SETTINGS_STORAGE_KEY, JSON.stringify(cache));
    } catch {
        /* 저장 실패해도 메모리 캐시는 유지(다음 시도에서 재저장). */
    }
}

export function subscribeGlobalSettings(fn: (s: GlobalSettings) => void): () => void {
    listeners.add(fn);
    return () => {
        listeners.delete(fn);
    };
}

/** 컴포넌트에서 전역 설정을 라이브로 읽는 훅(변경 시 자동 리렌더). */
export function useGlobalSettings(): GlobalSettings {
    const [state, setState] = useState<GlobalSettings>(cache);
    useEffect(() => {
        setState(cache);
        return subscribeGlobalSettings(setState);
    }, []);
    return state;
}

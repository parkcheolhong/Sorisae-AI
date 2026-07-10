/**
 * 관계자(운영·개발) 전용 표면 — 실구매 사용자 UI와 분리.
 * 언어 코드, call_id, 감사 로그 등은 여기서만 노출한다.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';

const STORAGE_KEY = 'worldlinco_operator_surface_unlocked';
const VERSION_TAP_THRESHOLD = 7;
const TAP_RESET_MS = 2500;

let unlockedMemory = false;
let versionTapCount = 0;
let versionTapTimer: ReturnType<typeof setTimeout> | null = null;

export function isOperatorSurfaceVisible(): boolean {
    return __DEV__ || unlockedMemory;
}

export async function loadOperatorSurfaceUnlock(): Promise<boolean> {
    try {
        const raw = await AsyncStorage.getItem(STORAGE_KEY);
        unlockedMemory = raw === '1';
    } catch {
        unlockedMemory = false;
    }
    return unlockedMemory;
}

export async function setOperatorSurfaceUnlock(enabled: boolean): Promise<void> {
    unlockedMemory = enabled;
    try {
        if (enabled) {
            await AsyncStorage.setItem(STORAGE_KEY, '1');
        } else {
            await AsyncStorage.removeItem(STORAGE_KEY);
        }
    } catch {
        // 저장 실패는 메모리 플래그만 유지
    }
}

/** 설정 하단 버전 영역 연속 탭 — 관계자 로그 잠금 해제. */
export async function handleOperatorUnlockTap(): Promise<boolean> {
    if (__DEV__ || unlockedMemory) {
        return true;
    }
    versionTapCount += 1;
    if (versionTapTimer) {
        clearTimeout(versionTapTimer);
    }
    versionTapTimer = setTimeout(() => {
        versionTapCount = 0;
        versionTapTimer = null;
    }, TAP_RESET_MS);
    if (versionTapCount >= VERSION_TAP_THRESHOLD) {
        versionTapCount = 0;
        if (versionTapTimer) {
            clearTimeout(versionTapTimer);
            versionTapTimer = null;
        }
        await setOperatorSurfaceUnlock(true);
        return true;
    }
    return false;
}

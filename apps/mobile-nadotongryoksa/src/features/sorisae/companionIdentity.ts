/**
 * [기능 분리 Phase6.0] 소리새 AI → 사용자 지정 AI 이름 SSOT(순수 + 온디바이스 영속).
 *
 * 회원 가입 시 "나의 AI 이름"을 필수로 등록하면, 기존 고정 명칭 "소리새 AI" 가
 * 사용자 지정 "OOOO AI" 로 자동 치환된다. 표시 명칭 해석을 한 곳에서 정의한다.
 *  - normalizeAiName: 입력 정규화(트림/공백압축/제어문자 제거/길이 상한).
 *  - isValidAiName: 가입 필수 검증(정규화 후 1..MAX 자).
 *  - resolveAiDisplayName: "OOOO AI" 표시 명칭(미설정/무효 시 기본 "소리새 AI").
 * 영속은 AsyncStorage(계정 단위 식별이라 "나를 잊어줘" 메모리 초기화로는 지워지지 않음).
 */
import AsyncStorage from '@react-native-async-storage/async-storage';

export const DEFAULT_AI_DISPLAY_NAME = '소리새 AI';
export const AI_NAME_MAX_LEN = 20;
export const COMPANION_AI_NAME_STORAGE_KEY = 'worldlinco_companion_ai_name_v1';

/** 입력 AI 이름 정규화(트림·공백압축·제어문자 제거·길이 상한). */
export function normalizeAiName(raw: string | null | undefined): string {
    return String(raw ?? '')
        .replace(/[\u0000-\u001f\u007f]/g, '')
        .replace(/\s+/g, ' ')
        .trim()
        .slice(0, AI_NAME_MAX_LEN);
}

/** 가입 필수 검증 — 정규화 후 1자 이상이면 유효. */
export function isValidAiName(raw: string | null | undefined): boolean {
    return normalizeAiName(raw).length >= 1;
}

/**
 * 표시 명칭 "OOOO AI" 해석. 무효/미설정 시 기본값("소리새 AI").
 * 사용자가 끝에 'AI'/'에이아이'를 붙여도 "OOOO AI AI" 중복을 피한다.
 */
export function resolveAiDisplayName(aiName: string | null | undefined): string {
    const normalized = normalizeAiName(aiName);
    if (!normalized) return DEFAULT_AI_DISPLAY_NAME;
    const core = normalized.replace(/\s*(ai|에이아이)\s*$/i, '').trim() || normalized;
    return `${core} AI`;
}

export async function loadAiName(): Promise<string | null> {
    try {
        const raw = await AsyncStorage.getItem(COMPANION_AI_NAME_STORAGE_KEY);
        const normalized = normalizeAiName(raw);
        return normalized || null;
    } catch {
        return null;
    }
}

/** 저장된 AI 이름 → 표시 명칭(없으면 기본 "소리새 AI"). */
export async function loadAiDisplayName(): Promise<string> {
    const name = await loadAiName();
    return resolveAiDisplayName(name);
}

export async function saveAiName(aiName: string): Promise<boolean> {
    const normalized = normalizeAiName(aiName);
    if (!normalized) return false;
    try {
        await AsyncStorage.setItem(COMPANION_AI_NAME_STORAGE_KEY, normalized);
        return true;
    } catch {
        return false;
    }
}

/**
 * [기능 분리 Phase5.8] 소리새 AI 진화형 페르소나 — 온디바이스 영속 래퍼(AsyncStorage).
 *
 * companionMemory 의 순수 모델을 단말에만 저장한다(서버 영속화 0 — 프라이버시 기본값).
 * 모든 함수는 베스트에포트: 저장/로드 실패는 조용히 무시하고 빈 페르소나로 폴백한다
 * (메모리는 부가 기능이라 실패해도 친구 대화 자체를 막지 않는다).
 */
import AsyncStorage from '@react-native-async-storage/async-storage';

import {
    COMPANION_PERSONA_VERSION,
    createEmptyPersona,
    observeTurn,
    type CompanionPersona,
    type ObserveTurnInput,
} from './companionMemory';

export const COMPANION_PERSONA_STORAGE_KEY = 'worldlinco_companion_persona_v1';

/** 저장 페이로드 검증 → 손상/구버전이면 빈 페르소나. */
export function revivePersona(raw: unknown): CompanionPersona {
    if (!raw || typeof raw !== 'object') return createEmptyPersona();
    const p = raw as Partial<CompanionPersona>;
    if (p.version !== COMPANION_PERSONA_VERSION) return createEmptyPersona();
    const empty = createEmptyPersona();
    return {
        ...empty,
        ...p,
        interests: p.interests && typeof p.interests === 'object' ? p.interests : {},
        domainCounts: p.domainCounts && typeof p.domainCounts === 'object' ? p.domainCounts : {},
        notableFacts: Array.isArray(p.notableFacts) ? p.notableFacts.filter((f) => typeof f === 'string') : [],
        version: COMPANION_PERSONA_VERSION,
    };
}

export async function loadPersona(): Promise<CompanionPersona> {
    try {
        const rawStr = await AsyncStorage.getItem(COMPANION_PERSONA_STORAGE_KEY);
        if (!rawStr) return createEmptyPersona();
        return revivePersona(JSON.parse(rawStr));
    } catch {
        return createEmptyPersona();
    }
}

export async function savePersona(persona: CompanionPersona): Promise<boolean> {
    try {
        await AsyncStorage.setItem(COMPANION_PERSONA_STORAGE_KEY, JSON.stringify(persona));
        return true;
    } catch {
        return false;
    }
}

/** 한 턴 관측 → 영속화까지 한 번에(베스트에포트). 갱신된 페르소나 반환. */
export async function recordTurn(input: ObserveTurnInput): Promise<CompanionPersona> {
    const current = await loadPersona();
    const next = observeTurn(current, input);
    await savePersona(next);
    return next;
}

/** 페르소나 초기화(사용자가 '나를 잊어줘' 요청 시). */
export async function resetPersona(): Promise<void> {
    try {
        await AsyncStorage.removeItem(COMPANION_PERSONA_STORAGE_KEY);
    } catch {
        /* noop */
    }
}

/**
 * [기능 분리 Phase6.1] 소리새 AI 음성 호출형(웨이크워드) 세션 — 순수 상태기계(SSOT, App 비의존).
 *
 * 로그인 상태에서 사용자가 AI 이름("OOOO"/"소리새")을 음성으로 부르면 깨어나 대화하고,
 * 마지막 활동(사용자 발화/AI 답변) 후 3분이 지나면 자동으로 잠든다(awake → dormant 대기 복귀).
 *
 *  - off:     음성 호출 기능 꺼짐(대기 안 함).
 *  - dormant: 무장(armed) — 마이크로 들으며 웨이크워드만 감시(대화 안 함).
 *  - awake:   깨어남 — 소리새 대화창 활성, 매 턴마다 활동시각 갱신.
 *
 * RN/타이머/오디오에 의존하지 않는 순수 함수만 노출 → 단위 테스트로 회귀를 막는다.
 * 실제 마이크 캡처·창 열기·TTS 는 App.tsx 가 이 상태기계의 판정에 따라 수행한다.
 */
import { normalizeEchoText } from './sorisaeEcho';
import { resolveAiDisplayName, DEFAULT_AI_DISPLAY_NAME } from './companionIdentity';

/** 마지막 활동 후 자동 종료까지의 무활동 허용 시간(ms). 사장님 사양: 3분. */
export const COMPANION_VOICE_CALL_IDLE_MS = 180_000;

/** 웨이크워드 후보의 최소 정규화 길이(너무 짧으면 오인식 방지). */
const MIN_WAKE_CANDIDATE_LEN = 2;

export type CompanionVoiceCallPhase = 'off' | 'dormant' | 'awake';

export interface CompanionVoiceCallState {
    phase: CompanionVoiceCallPhase;
    /** awake 진입/활동 시각(epoch ms). dormant/off 에서는 0. */
    lastActivityMs: number;
}

export type CompanionVoiceCallTranscriptEvent = 'wake' | 'activity' | 'ignored';

export function createCompanionVoiceCallState(
    phase: CompanionVoiceCallPhase = 'off',
): CompanionVoiceCallState {
    return { phase, lastActivityMs: 0 };
}

/**
 * 웨이크워드 후보 목록 — 사용자 지정 AI 이름의 코어("OOOO AI" → "OOOO") + 기본 "소리새" + 별칭.
 * 정규화(공백·구두점 제거·소문자) 후 길이 미달 후보는 버린다.
 */
export function resolveWakeCandidates(
    aiName: string | null | undefined,
    extraAliases: string[] = [],
): string[] {
    const display = resolveAiDisplayName(aiName); // "OOOO AI"
    const core = display.replace(/\s*ai\s*$/i, '').trim();
    const raw = [
        core,
        DEFAULT_AI_DISPLAY_NAME.replace(/\s*ai\s*$/i, '').trim(), // "소리새"
        '소리새',
        ...extraAliases,
    ];
    const seen = new Set<string>();
    const out: string[] = [];
    for (const candidate of raw) {
        const norm = normalizeEchoText(candidate);
        if (norm.length >= MIN_WAKE_CANDIDATE_LEN && !seen.has(norm)) {
            seen.add(norm);
            out.push(norm);
        }
    }
    return out;
}

/**
 * 전사(STT)에 웨이크워드가 포함되어 있는지 판정(언어 무관, 공백·구두점 무시).
 * "OOOO야", "헤이 OOOO", "소리새!" 등 호명형 표현을 폭넓게 수용한다.
 * 단어 내부 부분 일치(예: 루나틱→루나, alunalpha→luna)는 제외한다.
 */
const WAKE_SUFFIX_CHARS = new Set(['야', '아', '이', '씨', '님', '요', '!', '~']);

function tokenizeWakeTranscript(transcript: string): string[] {
    return String(transcript || '')
        .split(/[\s.,!?;:'"`()\[\]{}~\-·…‥。、！？；：「」『』，．（）【】〔〕《》]+/u)
        .map((part) => normalizeEchoText(part))
        .filter(Boolean);
}

function wakeTokenMatches(token: string, candidate: string): boolean {
    if (!token || !candidate) return false;
    if (token === candidate) return true;
    if (!token.startsWith(candidate)) return false;
    const rest = token.slice(candidate.length);
    if (!rest) return true;
    return [...rest].every((ch) => WAKE_SUFFIX_CHARS.has(ch));
}

function isEmbeddedWakeCandidate(normTranscript: string, candidate: string): boolean {
    const isLatin = /^[a-z0-9]+$/i.test(candidate);
    let from = 0;
    while (from <= normTranscript.length) {
        const idx = normTranscript.indexOf(candidate, from);
        if (idx < 0) return false;
        const before = idx > 0 ? normTranscript[idx - 1] : '';
        const after = normTranscript[idx + candidate.length] ?? '';
        if (isLatin) {
            const beforeOk = !before || !/[a-z0-9]/i.test(before);
            const afterOk = !after || !/[a-z0-9]/i.test(after);
            if (beforeOk && afterOk) return true;
        } else if (!after || WAKE_SUFFIX_CHARS.has(after) || !/[\uac00-\ud7a3]/.test(after)) {
            return true;
        }
        from = idx + 1;
    }
    return false;
}

export function matchCompanionWakeWord(
    transcript: string | null | undefined,
    aiName: string | null | undefined,
    extraAliases: string[] = [],
): boolean {
    const normTranscript = normalizeEchoText(String(transcript ?? ''));
    if (!normTranscript) return false;
    const candidates = resolveWakeCandidates(aiName, extraAliases);
    const tokens = tokenizeWakeTranscript(String(transcript ?? ''));
    return candidates.some((candidate) => (
        tokens.some((token) => wakeTokenMatches(token, candidate))
        || isEmbeddedWakeCandidate(normTranscript, candidate)
    ));
}

/** 무장(armed) — off/awake 와 무관하게 dormant(웨이크워드 대기)로 전환. */
export function armCompanionVoiceCall(_state: CompanionVoiceCallState): CompanionVoiceCallState {
    return { phase: 'dormant', lastActivityMs: 0 };
}

/** 기능 종료 — off 로 전환(대기/대화 모두 중단). */
export function disarmCompanionVoiceCall(_state: CompanionVoiceCallState): CompanionVoiceCallState {
    return { phase: 'off', lastActivityMs: 0 };
}

/** 깨우기 — dormant → awake, 활동시각 기록. */
export function wakeCompanionVoiceCall(
    state: CompanionVoiceCallState,
    nowMs: number,
): CompanionVoiceCallState {
    return { phase: 'awake', lastActivityMs: nowMs };
}

/** 활동 기록 — awake 인 동안에만 마지막 활동시각을 갱신(무활동 타이머 리셋). */
export function markCompanionVoiceCallActivity(
    state: CompanionVoiceCallState,
    nowMs: number,
): CompanionVoiceCallState {
    if (state.phase !== 'awake') return state;
    return { ...state, lastActivityMs: nowMs };
}

/** 잠들기 — awake → dormant(다시 부르면 깨어남). 기능 자체는 유지. */
export function sleepCompanionVoiceCall(_state: CompanionVoiceCallState): CompanionVoiceCallState {
    return { phase: 'dormant', lastActivityMs: 0 };
}

/**
 * 전사 1건 처리 — dormant 에서 웨이크워드면 'wake', awake 면 'activity', 그 외 'ignored'.
 * 호출부는 반환 event 에 따라 창 열기/활동 갱신을 수행한다.
 */
export function onCompanionVoiceCallTranscript(
    state: CompanionVoiceCallState,
    transcript: string | null | undefined,
    nowMs: number,
    aiName: string | null | undefined,
    extraAliases: string[] = [],
): { state: CompanionVoiceCallState; event: CompanionVoiceCallTranscriptEvent } {
    if (state.phase === 'dormant') {
        if (matchCompanionWakeWord(transcript, aiName, extraAliases)) {
            return { state: wakeCompanionVoiceCall(state, nowMs), event: 'wake' };
        }
        return { state, event: 'ignored' };
    }
    if (state.phase === 'awake') {
        return { state: markCompanionVoiceCallActivity(state, nowMs), event: 'activity' };
    }
    return { state, event: 'ignored' };
}

/** awake 상태에서 무활동 3분 경과 여부. */
export function shouldCompanionVoiceCallSleep(
    state: CompanionVoiceCallState,
    nowMs: number,
    idleMs: number = COMPANION_VOICE_CALL_IDLE_MS,
): boolean {
    if (state.phase !== 'awake') return false;
    return nowMs - state.lastActivityMs >= idleMs;
}

/** 자동 종료까지 남은 ms(awake 가 아니면 null). UI 카운트다운용. */
export function companionVoiceCallRemainingMs(
    state: CompanionVoiceCallState,
    nowMs: number,
    idleMs: number = COMPANION_VOICE_CALL_IDLE_MS,
): number | null {
    if (state.phase !== 'awake') return null;
    return Math.max(0, idleMs - (nowMs - state.lastActivityMs));
}

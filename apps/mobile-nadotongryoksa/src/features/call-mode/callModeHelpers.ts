/**
 * [기능 분리 Phase5.6d] 콜모드/통번역 상태 순수 헬퍼 SSOT.
 *
 * App.tsx 인라인에 있던 콜모드 정규화/판정 + 통번역 상태 텍스트 포매터를 분리한다.
 * 모두 순수(부수효과 없음)하여 단위 테스트로 회귀 가드한다.
 *  - 콜모드 후보 정규화: `normalizeCallModeCandidate`
 *  - 페이로드→콜모드 확정: `resolveCallModeFromPayload`
 *  - 콜모드/상태 표기: `formatUnifiedCallModeText` / `formatUnifiedTranslationStatus`
 *  - 종료 상태 판정: `isTerminalVoipStatus`
 */
import type { CallMode } from './types';
import type { CallInitResponse } from '../../services/voipCallClient';

export type TranslationStatusRoute = 'PSTN' | 'VOIP';
export type TranslationStatusPhase = 'READY' | 'LISTEN' | 'TRANSLATE' | 'SPEAK' | 'ERROR' | 'INFO';

/** VoIP 통화가 종료(터미널) 상태로 간주되는 status 집합. */
export const TERMINAL_VOIP_STATUSES = new Set([
    'cancelled',
    'canceled',
    'completed',
    'ended',
    'failed',
    'no_answer',
    'rejected',
    'busy',
    'callee_offline',
    'timeout',
]);

/** 콜모드 문자열을 유효한 CallMode 로 정규화(유효하지 않으면 null). */
export function normalizeCallModeCandidate(mode?: string | null): CallMode | null {
    if (mode === 'pstn_assist' || mode === 'voip_full_auto') {
        return mode;
    }
    return null;
}

/** 통화 초기화 페이로드에서 콜모드를 확정(resolved→requested→라우트 휴리스틱→pstn_assist). */
export function resolveCallModeFromPayload(payload: Partial<CallInitResponse>): CallMode {
    const resolvedMode = normalizeCallModeCandidate(payload.resolved_mode);
    if (resolvedMode) {
        return resolvedMode;
    }

    const requestedMode = normalizeCallModeCandidate(payload.requested_mode);
    if (requestedMode) {
        return requestedMode;
    }

    if (payload.call_route === 'app_webrtc' || payload.phone_dialer_required === false || payload.auto_relay_applied) {
        return 'voip_full_auto';
    }

    return 'pstn_assist';
}

/** 요청/확정 콜모드를 통번역 모드 배지 텍스트로 표기. */
export function formatUnifiedCallModeText(requestedMode?: string | null, resolvedMode?: string | null): string {
    return `[통번역 모드] ${requestedMode || 'null'} -> ${resolvedMode || 'null'}`;
}

/** 통번역 라우트/단계/상세를 단일 상태 텍스트로 표기. */
export function formatUnifiedTranslationStatus(route: TranslationStatusRoute, phase: TranslationStatusPhase, detail: string): string {
    return `[통번역 ${route}/${phase}] ${detail}`;
}

/** status 가 VoIP 종료(터미널) 상태인지 판정. */
export function isTerminalVoipStatus(status?: string | null): boolean {
    return Boolean(status && TERMINAL_VOIP_STATUSES.has(status));
}

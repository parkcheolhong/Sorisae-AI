import { describe, expect, it } from '@jest/globals';

import {
    TERMINAL_VOIP_STATUSES,
    normalizeCallModeCandidate,
    resolveCallModeFromPayload,
    formatUnifiedCallModeText,
    formatUnifiedTranslationStatus,
    isTerminalVoipStatus,
} from '../features/call-mode/callModeHelpers';

describe('normalizeCallModeCandidate — 콜모드 정규화', () => {
    it('유효한 콜모드는 그대로 반환한다', () => {
        expect(normalizeCallModeCandidate('pstn_assist')).toBe('pstn_assist');
        expect(normalizeCallModeCandidate('voip_full_auto')).toBe('voip_full_auto');
    });

    it('유효하지 않은 값/누락은 null', () => {
        expect(normalizeCallModeCandidate('unknown')).toBeNull();
        expect(normalizeCallModeCandidate('')).toBeNull();
        expect(normalizeCallModeCandidate(null)).toBeNull();
        expect(normalizeCallModeCandidate(undefined)).toBeNull();
    });
});

describe('resolveCallModeFromPayload — 페이로드→콜모드 확정', () => {
    it('resolved_mode 가 최우선이다', () => {
        expect(resolveCallModeFromPayload({ resolved_mode: 'voip_full_auto', requested_mode: 'pstn_assist' } as never)).toBe('voip_full_auto');
    });

    it('resolved 가 없으면 requested 를 사용한다', () => {
        expect(resolveCallModeFromPayload({ requested_mode: 'pstn_assist' } as never)).toBe('pstn_assist');
    });

    it('둘 다 없으면 라우트 휴리스틱으로 voip_full_auto 를 추론한다', () => {
        expect(resolveCallModeFromPayload({ call_route: 'app_webrtc' } as never)).toBe('voip_full_auto');
        expect(resolveCallModeFromPayload({ phone_dialer_required: false } as never)).toBe('voip_full_auto');
        expect(resolveCallModeFromPayload({ auto_relay_applied: true } as never)).toBe('voip_full_auto');
    });

    it('아무 단서가 없으면 pstn_assist 로 폴백한다', () => {
        expect(resolveCallModeFromPayload({} as never)).toBe('pstn_assist');
    });
});

describe('표기 포매터', () => {
    it('formatUnifiedCallModeText — null 안전 표기', () => {
        expect(formatUnifiedCallModeText('pstn_assist', 'voip_full_auto')).toBe('[통번역 모드] pstn_assist -> voip_full_auto');
        expect(formatUnifiedCallModeText(null, null)).toBe('[통번역 모드] null -> null');
    });

    it('formatUnifiedTranslationStatus — 라우트/단계/상세 결합', () => {
        expect(formatUnifiedTranslationStatus('VOIP', 'TRANSLATE', '번역 중')).toBe('[통번역 VOIP/TRANSLATE] 번역 중');
        expect(formatUnifiedTranslationStatus('PSTN', 'READY', '대기')).toBe('[통번역 PSTN/READY] 대기');
    });
});

describe('isTerminalVoipStatus — 종료 상태 판정', () => {
    it('종료 상태 집합은 모두 true', () => {
        for (const status of TERMINAL_VOIP_STATUSES) {
            expect(isTerminalVoipStatus(status)).toBe(true);
        }
    });

    it('진행/누락 상태는 false', () => {
        expect(isTerminalVoipStatus('ringing')).toBe(false);
        expect(isTerminalVoipStatus('connected')).toBe(false);
        expect(isTerminalVoipStatus('')).toBe(false);
        expect(isTerminalVoipStatus(null)).toBe(false);
        expect(isTerminalVoipStatus(undefined)).toBe(false);
    });
});

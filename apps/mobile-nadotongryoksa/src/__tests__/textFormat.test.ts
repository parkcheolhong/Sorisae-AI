import { describe, expect, it } from '@jest/globals';

import { formatStatusText, extractApiErrorMessage, summarizeAuthToken } from '../features/shared/textFormat';

describe('formatStatusText — 템플릿 치환', () => {
    it('{key} 플레이스홀더를 values 로 치환한다', () => {
        expect(formatStatusText('{a} → {b}', { a: '한', b: '일' })).toBe('한 → 일');
    });

    it('누락 키는 빈 문자열, 비매칭 텍스트는 보존', () => {
        expect(formatStatusText('hello {name}!', {})).toBe('hello !');
        expect(formatStatusText('no placeholder', { x: '1' })).toBe('no placeholder');
    });
});

describe('extractApiErrorMessage — 서버 에러 메시지 추출', () => {
    it('문자열 detail 은 트림해서 반환', () => {
        expect(extractApiErrorMessage('  잘못된 요청  ', 'fallback')).toBe('잘못된 요청');
    });

    it('배열(FastAPI 검증오류) 은 msg 들을 합친다', () => {
        expect(extractApiErrorMessage([{ msg: 'field required' }, { msg: 'too short' }], 'fb')).toBe('field required, too short');
        expect(extractApiErrorMessage(['a', 'b'], 'fb')).toBe('a, b');
    });

    it('객체는 detail/message/error/msg 순으로 후보를 찾는다', () => {
        expect(extractApiErrorMessage({ message: '서버 오류' }, 'fb')).toBe('서버 오류');
        expect(extractApiErrorMessage({ error: 'e' }, 'fb')).toBe('e');
    });

    it('추출 불가하면 fallback', () => {
        expect(extractApiErrorMessage(null, 'fb')).toBe('fb');
        expect(extractApiErrorMessage('', 'fb')).toBe('fb');
        expect(extractApiErrorMessage([{}], 'fb')).toBe('fb');
        expect(extractApiErrorMessage({ unknown: 1 }, 'fb')).toBe('fb');
    });
});

describe('summarizeAuthToken — 로그-안전 토큰 요약', () => {
    it('빈 토큰은 empty', () => {
        expect(summarizeAuthToken('')).toBe('empty');
        expect(summarizeAuthToken('   ')).toBe('empty');
    });

    it('짧은(<=12) 토큰은 전체 노출', () => {
        expect(summarizeAuthToken('abc123')).toBe('len:6:abc123');
    });

    it('긴 토큰은 앞뒤 6자만 노출', () => {
        expect(summarizeAuthToken('abcdefghijklmnop')).toBe('len:16:abcdef...klmnop');
    });
});

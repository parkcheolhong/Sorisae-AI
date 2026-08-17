import { describe, expect, it } from '@jest/globals';

import { normalizeEchoText, echoOverlapRatio } from '../features/sorisae/sorisaeEcho';

describe('normalizeEchoText — 공백/구두점 제거 + 소문자', () => {
    it('공백·구두점을 제거하고 소문자로 정규화한다', () => {
        expect(normalizeEchoText('안녕, 하세요!')).toBe('안녕하세요');
        expect(normalizeEchoText('Hello, World.')).toBe('helloworld');
        expect(normalizeEchoText('「테스트」 (메모)')).toBe('테스트메모');
    });

    it('null/undefined/빈값은 빈 문자열', () => {
        expect(normalizeEchoText('')).toBe('');
        // @ts-expect-error 런타임 방어 동작 검증
        expect(normalizeEchoText(null)).toBe('');
        // @ts-expect-error 런타임 방어 동작 검증
        expect(normalizeEchoText(undefined)).toBe('');
    });
});

describe('echoOverlapRatio — 자기에코 겹침 비율(0~1)', () => {
    it('동일 문자열은 1', () => {
        const a = normalizeEchoText('오늘 날씨가 정말 좋네요');
        expect(echoOverlapRatio(a, a)).toBe(1);
    });

    it('한쪽이 다른쪽을 포함하면 1 (부분 에코)', () => {
        const full = normalizeEchoText('오늘 날씨가 정말 좋네요 산책 가기 좋습니다');
        const partial = normalizeEchoText('오늘 날씨가 정말 좋네요');
        expect(echoOverlapRatio(full, partial)).toBe(1);
    });

    it('완전히 다른 문장은 낮은 값(겹치는 bigram 없으면 0)', () => {
        const a = normalizeEchoText('abcdef');
        const b = normalizeEchoText('uvwxyz');
        expect(echoOverlapRatio(a, b)).toBe(0);
    });

    it('빈 입력은 0', () => {
        expect(echoOverlapRatio('', 'abc')).toBe(0);
        expect(echoOverlapRatio('abc', '')).toBe(0);
    });

    it('부분 겹침은 0과 1 사이', () => {
        const ratio = echoOverlapRatio('abcde', 'abcxy');
        expect(ratio).toBeGreaterThan(0);
        expect(ratio).toBeLessThan(1);
    });
});

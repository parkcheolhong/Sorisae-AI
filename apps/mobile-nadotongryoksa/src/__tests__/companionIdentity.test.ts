import { describe, expect, it } from '@jest/globals';

import {
    DEFAULT_AI_DISPLAY_NAME,
    AI_NAME_MAX_LEN,
    isValidAiName,
    normalizeAiName,
    resolveAiDisplayName,
} from '../features/sorisae/companionIdentity';

describe('normalizeAiName', () => {
    it('트림·공백압축·길이 상한', () => {
        expect(normalizeAiName('  토토   봇  ')).toBe('토토 봇');
        expect(normalizeAiName('x'.repeat(50)).length).toBe(AI_NAME_MAX_LEN);
        expect(normalizeAiName(null)).toBe('');
    });
});

describe('isValidAiName — 가입 필수 검증', () => {
    it('비거나 공백뿐이면 무효', () => {
        expect(isValidAiName('')).toBe(false);
        expect(isValidAiName('   ')).toBe(false);
        expect(isValidAiName(null)).toBe(false);
    });
    it('한 글자 이상이면 유효', () => {
        expect(isValidAiName('토토')).toBe(true);
        expect(isValidAiName('A')).toBe(true);
    });
});

describe('resolveAiDisplayName — OOOO AI', () => {
    it('지정 이름 → "OOOO AI"', () => {
        expect(resolveAiDisplayName('토토')).toBe('토토 AI');
        expect(resolveAiDisplayName('Bori')).toBe('Bori AI');
    });
    it('미설정/무효 → 기본 "소리새 AI"', () => {
        expect(resolveAiDisplayName('')).toBe(DEFAULT_AI_DISPLAY_NAME);
        expect(resolveAiDisplayName(null)).toBe(DEFAULT_AI_DISPLAY_NAME);
    });
    it('이미 AI/에이아이 접미가 있으면 중복 방지', () => {
        expect(resolveAiDisplayName('토토AI')).toBe('토토 AI');
        expect(resolveAiDisplayName('토토 ai')).toBe('토토 AI');
        expect(resolveAiDisplayName('토토 에이아이')).toBe('토토 AI');
    });
});

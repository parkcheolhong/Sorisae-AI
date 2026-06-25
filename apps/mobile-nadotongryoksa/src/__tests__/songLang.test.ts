import { describe, expect, it } from '@jest/globals';

import { normalizeSongFileLang, resolveSongFileTargetLang } from '../features/song/songLang';

describe('normalizeSongFileLang — 감지 언어 정규화 + fallback', () => {
    it('인식되는 입력은 코드로 정규화한다', () => {
        expect(normalizeSongFileLang('Korean', 'en')).toBe('ko');
        expect(normalizeSongFileLang('japanese', 'en')).toBe('ja');
        expect(normalizeSongFileLang('en-US', 'ko')).toBe('en');
    });

    it('미인식/빈 입력은 fallback 을 유지한다', () => {
        expect(normalizeSongFileLang('', 'ja')).toBe('ja');
        expect(normalizeSongFileLang('klingon', 'de')).toBe('de');
    });
});

describe('resolveSongFileTargetLang — 한국어 우선 자막 규칙', () => {
    it('소스가 한국어면 항상 한국어 자막', () => {
        expect(resolveSongFileTargetLang('ko', 'en')).toBe('ko');
        expect(resolveSongFileTargetLang('ko', 'ko')).toBe('ko');
    });

    it('타깃이 소스와 다르면 타깃을 유지한다', () => {
        expect(resolveSongFileTargetLang('en', 'fr')).toBe('fr');
        expect(resolveSongFileTargetLang('ja', 'ko')).toBe('ko');
    });

    it('타깃이 소스와 같으면 자동 타깃 규칙(ko↔en, 그 외 ko)', () => {
        expect(resolveSongFileTargetLang('en', 'en')).toBe('ko');
        expect(resolveSongFileTargetLang('ja', 'ja')).toBe('ko');
    });
});

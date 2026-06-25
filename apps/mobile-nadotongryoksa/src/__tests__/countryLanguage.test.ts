import { describe, expect, it } from '@jest/globals';

import { resolveLangFromCountry } from '../features/country/countryLanguage';

describe('resolveLangFromCountry — 국가코드→언어코드', () => {
    it('대표 국가의 언어를 반환한다', () => {
        expect(resolveLangFromCountry('KR')).toBe('ko');
        expect(resolveLangFromCountry('JP')).toBe('ja');
        expect(resolveLangFromCountry('US')).toBe('en');
        expect(resolveLangFromCountry('CN')).toBe('zh');
        expect(resolveLangFromCountry('TW')).toBe('zh-tw');
    });

    it('대소문자를 정규화한다', () => {
        expect(resolveLangFromCountry('kr')).toBe('ko');
        expect(resolveLangFromCountry('jp')).toBe('ja');
    });

    it('같은 언어를 공유하는 다중 국가를 매핑한다', () => {
        expect(resolveLangFromCountry('GB')).toBe('en');
        expect(resolveLangFromCountry('CA')).toBe('en');
        expect(resolveLangFromCountry('MX')).toBe('es');
        expect(resolveLangFromCountry('AT')).toBe('de');
        expect(resolveLangFromCountry('HK')).toBe('zh-tw');
    });

    it('미등록 국가코드는 null', () => {
        expect(resolveLangFromCountry('ZZ')).toBeNull();
        expect(resolveLangFromCountry('')).toBeNull();
    });
});

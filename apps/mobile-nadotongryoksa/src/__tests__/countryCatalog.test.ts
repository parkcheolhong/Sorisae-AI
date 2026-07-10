import { describe, expect, it } from '@jest/globals';

import {
    SIGNUP_COUNTRY_OPTIONS,
    SIGNUP_COUNTRY_OPTION_CODES,
    COUNTRY_NAME_MAP,
    normalizeSignupCountryCode,
    resolveSignupCountryFromLang,
    resolveCountryName,
} from '../features/country/countryCatalog';

describe('가입국가 카탈로그 데이터', () => {
    it('옵션과 코드 배열 길이가 일치하고 KR 을 포함한다', () => {
        expect(SIGNUP_COUNTRY_OPTION_CODES.length).toBe(SIGNUP_COUNTRY_OPTIONS.length);
        expect(SIGNUP_COUNTRY_OPTION_CODES).toContain('KR');
        expect(SIGNUP_COUNTRY_OPTION_CODES).toContain('JP');
    });

    it('COUNTRY_NAME_MAP 은 가입목록 라벨 + 추가국가를 모두 포함한다', () => {
        expect(COUNTRY_NAME_MAP.KR).toBe('대한민국');
        expect(COUNTRY_NAME_MAP.JP).toBe('일본');
        expect(COUNTRY_NAME_MAP.BE).toBe('벨기에'); // 추가 국가(가입목록 외)
        expect(COUNTRY_NAME_MAP.RS).toBe('세르비아');
    });
});

describe('resolveCountryName — 국가명 표기', () => {
    it('등록 국가는 한글명, 미등록은 코드 대문자 폴백', () => {
        expect(resolveCountryName('kr')).toBe('대한민국');
        expect(resolveCountryName('BE')).toBe('벨기에');
        expect(resolveCountryName('zz')).toBe('ZZ');
    });
});

describe('normalizeSignupCountryCode — 가입국가 정규화', () => {
    it('지원 코드는 보존(대소문자/공백 정규화)', () => {
        expect(normalizeSignupCountryCode('kr')).toBe('KR');
        expect(normalizeSignupCountryCode('  jp ')).toBe('JP');
    });

    it('미지원/누락은 KR 폴백', () => {
        expect(normalizeSignupCountryCode('ZZ')).toBe('KR');
        expect(normalizeSignupCountryCode('')).toBe('KR');
        expect(normalizeSignupCountryCode(null)).toBe('KR');
        expect(normalizeSignupCountryCode(undefined)).toBe('KR');
    });
});

describe('resolveSignupCountryFromLang — 언어→가입국가 역매핑', () => {
    it('언어에 대응하는 첫 가입국가를 반환한다', () => {
        expect(resolveSignupCountryFromLang('ko')).toBe('KR');
        expect(resolveSignupCountryFromLang('ja')).toBe('JP');
        // en 은 목록상 US 가 먼저 등장
        expect(resolveSignupCountryFromLang('en')).toBe('US');
    });

    it('대응 국가가 없으면 KR 폴백', () => {
        expect(resolveSignupCountryFromLang('zz' as never)).toBe('KR');
    });
});

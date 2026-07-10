import { describe, expect, it } from '@jest/globals';

import {
    resolveCountryFlag,
    resolveLocaleCountryCode,
    resolveLanguageLabel,
    formatVoipGenderLabel,
    formatDiscoveryGenderLabel,
    resolveDiscoveryGenderFromProfile,
} from '../features/profile/profileFormatters';

describe('resolveCountryFlag — 국가코드→국기 이모지', () => {
    it('2자리 국가코드를 국기 이모지로 변환한다(대소문자 무관)', () => {
        expect(resolveCountryFlag('KR')).toBe('🇰🇷');
        expect(resolveCountryFlag('jp')).toBe('🇯🇵');
        expect(resolveCountryFlag('us')).toBe('🇺🇸');
    });

    it('2자리 영문이 아니면 글로벌 이모지로 폴백한다', () => {
        expect(resolveCountryFlag('KOR')).toBe('🌐');
        expect(resolveCountryFlag('1')).toBe('🌐');
        expect(resolveCountryFlag('')).toBe('🌐');
    });
});

describe('resolveLocaleCountryCode — 단말 로케일 국가코드', () => {
    it('항상 대문자 region 코드를 반환한다(미상이면 KR)', () => {
        const code = resolveLocaleCountryCode();
        expect(code).toMatch(/^[A-Z]{2,}$/);
    });
});

describe('resolveLanguageLabel — 언어 라벨 표기', () => {
    it('지원 언어는 "라벨 (CODE)" 형태로 표기한다', () => {
        expect(resolveLanguageLabel('ko')).toBe('한국어 (KO)');
        expect(resolveLanguageLabel('EN')).toBe('English (EN)');
    });

    it('미설정/미지원 입력을 안전하게 처리한다', () => {
        expect(resolveLanguageLabel('')).toBe('미설정');
        expect(resolveLanguageLabel(null)).toBe('미설정');
        expect(resolveLanguageLabel(undefined)).toBe('미설정');
        expect(resolveLanguageLabel('zz')).toBe('ZZ');
    });
});

describe('성별 라벨/매핑 헬퍼', () => {
    it('formatVoipGenderLabel 은 male/female 외는 미설정', () => {
        expect(formatVoipGenderLabel('male')).toBe('남성');
        expect(formatVoipGenderLabel('female')).toBe('여성');
        expect(formatVoipGenderLabel('unknown')).toBe('미설정');
    });

    it('formatDiscoveryGenderLabel 은 other/누락도 처리', () => {
        expect(formatDiscoveryGenderLabel('male')).toBe('남성');
        expect(formatDiscoveryGenderLabel('female')).toBe('여성');
        expect(formatDiscoveryGenderLabel('other')).toBe('기타');
        expect(formatDiscoveryGenderLabel('unknown')).toBe('미설정');
        expect(formatDiscoveryGenderLabel(undefined)).toBe('미설정');
    });

    it('resolveDiscoveryGenderFromProfile 은 male/female 보존, 그외 unknown', () => {
        expect(resolveDiscoveryGenderFromProfile('male')).toBe('male');
        expect(resolveDiscoveryGenderFromProfile('female')).toBe('female');
        expect(resolveDiscoveryGenderFromProfile('unknown')).toBe('unknown');
    });
});

import { describe, expect, it } from '@jest/globals';

import { getLanguageDisplayLabel } from '../features/i18n/languageDisplayCatalog';
import {
    isTier1DisplayLangActive,
    pairFromCountry,
    pairFromLanguage,
    resolveProfileDisplayLang,
    TIER1_COUNTRY_BY_DISPLAY_LANG,
} from '../features/i18n/profileDisplayLocale';

describe('profileDisplayLocale', () => {
    it('maps service country to UI display locale', () => {
        expect(resolveProfileDisplayLang('KR')).toBe('ko');
        expect(resolveProfileDisplayLang('US')).toBe('en');
        expect(resolveProfileDisplayLang('JP')).toBe('ja');
        expect(resolveProfileDisplayLang('CN')).toBe('zh');
        expect(resolveProfileDisplayLang('RU')).toBe('ru');
    });

    it('country and language stay paired bidirectionally', () => {
        expect(pairFromCountry('RU')).toEqual({ countryCode: 'RU', languageCode: 'ru' });
        expect(pairFromLanguage('ru')).toEqual({ countryCode: 'RU', languageCode: 'ru' });
        expect(pairFromCountry('KR')).toEqual({ countryCode: 'KR', languageCode: 'ko' });
        expect(pairFromLanguage('ko')).toEqual({ countryCode: 'KR', languageCode: 'ko' });
    });

    it('tier-1 chips map to representative countries', () => {
        expect(TIER1_COUNTRY_BY_DISPLAY_LANG.ko).toBe('KR');
        expect(TIER1_COUNTRY_BY_DISPLAY_LANG.en).toBe('US');
        expect(TIER1_COUNTRY_BY_DISPLAY_LANG.ja).toBe('JP');
        expect(TIER1_COUNTRY_BY_DISPLAY_LANG.zh).toBe('CN');
    });

    it('tier-1 chip active state follows country representative language', () => {
        expect(isTier1DisplayLangActive('RU', 'en')).toBe(true);
        expect(isTier1DisplayLangActive('KR', 'ko')).toBe(true);
        expect(isTier1DisplayLangActive('KR', 'en')).toBe(false);
    });

    it('language labels follow service country locale not preferred_language', () => {
        expect(getLanguageDisplayLabel('ja', 'ko')).toBe('일본어');
        expect(getLanguageDisplayLabel('ja', 'en')).toBe('Japanese');
        expect(getLanguageDisplayLabel('ja', 'ja')).toBe('日本語');
        expect(getLanguageDisplayLabel('ko', 'en')).toBe('Korean');
    });
});

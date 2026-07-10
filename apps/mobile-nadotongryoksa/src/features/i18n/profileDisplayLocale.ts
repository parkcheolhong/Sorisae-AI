/**
 * UI 표시 로케일 SSOT — 사용자 서비스 국가·언어는 항상 1:1 동기화.
 * KR/ko · US/en · JP/ja · RU/ru … 국가 변경 → 언어 자동 · 언어 변경 → 국가 자동.
 */
import {
    normalizeSignupCountryCode,
    resolveSignupCountryFromLang,
    type SignupCountryCode,
} from '../country/countryCatalog';
import { resolveLangFromCountryOrEnglish } from '../country/countryLanguage';
import { isSupportedLangCode, type LangCode } from '../language/languageCatalog';
import { resolveBundledCatalogLang, type BundledUiLang } from './bundledUiLangs';

export type CountryLanguagePair = {
    countryCode: SignupCountryCode;
    languageCode: LangCode;
};

/** 국가 → 대표 언어(미등록 국가 en). */
export function pairFromCountry(countryCode: string | null | undefined): CountryLanguagePair {
    const cc = normalizeSignupCountryCode(countryCode);
    return {
        countryCode: cc,
        languageCode: resolveLangFromCountryOrEnglish(cc),
    };
}

/** 언어 → 대표 가입국가(미매칭 KR). */
export function pairFromLanguage(languageCode: string | null | undefined): CountryLanguagePair {
    const norm = String(languageCode || 'ko').trim().toLowerCase();
    const lang = isSupportedLangCode(norm) ? (norm as LangCode) : 'ko';
    return {
        countryCode: resolveSignupCountryFromLang(lang),
        languageCode: lang,
    };
}

/** UI·카탈로그·전역 Text 표시 언어 — 서비스 국가의 대표 언어(51개 전체). */
export function resolveProfileDisplayLang(countryCode: string | null | undefined): LangCode {
    return pairFromCountry(countryCode).languageCode;
}

/** 오프라인 번들(ko/en/ja/zh) 조회용 — 그 외 ru/fr 등은 en 카탈로그 + 런타임 번역. */
export function resolveProfileBundledCatalogLang(countryCode: string | null | undefined): BundledUiLang {
    return resolveBundledCatalogLang(resolveProfileDisplayLang(countryCode));
}

/** tier-1 앱 표시 언어 칩 → 서비스 국가 코드. */
export const TIER1_COUNTRY_BY_DISPLAY_LANG: Record<BundledUiLang, string> = {
    ko: 'KR',
    en: 'US',
    ja: 'JP',
    zh: 'CN',
};

/** tier-1 칩 활성 여부 — 국가 대표 언어 기준. */
export function isTier1DisplayLangActive(countryCode: string | null | undefined, chip: BundledUiLang): boolean {
    return resolveProfileBundledCatalogLang(countryCode) === chip;
}

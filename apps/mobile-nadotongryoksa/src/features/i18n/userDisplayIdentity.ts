/**
 * 양방향 화면(VoIP·채팅·PSTN) — 국기+이름·언어쌍 표기 SSOT.
 */
import type { LangCode } from '../language/languageCatalog';
import { getLangLabelText } from '../language/languageCatalog';
import { resolveLangFromCountry } from '../country/countryLanguage';
import { resolveCountryFlag } from '../profile/profileFormatters';

/** 언어 → 대표 국가(국기용). country_code 없을 때 preferred_language 폴백. */
const LANG_PRIMARY_COUNTRY: Partial<Record<LangCode, string>> = {
    ko: 'KR',
    en: 'US',
    ja: 'JP',
    zh: 'CN',
    'zh-tw': 'TW',
    'zh-hk': 'HK',
    es: 'ES',
    fr: 'FR',
    de: 'DE',
    pt: 'PT',
    ru: 'RU',
    ar: 'SA',
    hi: 'IN',
    th: 'TH',
    vi: 'VN',
    id: 'ID',
    tr: 'TR',
    fil: 'PH',
    ms: 'MY',
};

export function resolveUserCountryFlag(
    countryCode?: string | null,
    preferredLanguage?: string | null,
): string {
    const cc = String(countryCode || '').trim().toUpperCase();
    if (/^[A-Z]{2}$/.test(cc)) {
        return resolveCountryFlag(cc);
    }
    const lang = String(preferredLanguage || '').trim().toLowerCase() as LangCode;
    const primary = LANG_PRIMARY_COUNTRY[lang];
    if (primary) {
        return resolveCountryFlag(primary);
    }
    const fromCountryLang = resolveLangFromCountry(cc);
    if (fromCountryLang && LANG_PRIMARY_COUNTRY[fromCountryLang]) {
        return resolveCountryFlag(LANG_PRIMARY_COUNTRY[fromCountryLang]!);
    }
    return '🌐';
}

/** 국기 + 이름/닉네임 (이미 붙어 있으면 중복 방지). */
export function formatFlagPrefixedName(flag: string, name: string): string {
    const safeFlag = String(flag || '🌐').trim() || '🌐';
    const safeName = String(name || '').trim();
    if (!safeName) {
        return safeFlag;
    }
    if (safeName.startsWith(safeFlag)) {
        return safeName;
    }
    return `${safeFlag} ${safeName}`;
}

/** 양방향 통역 언어쌍 — 프로그램 전역(모든 설치 사용자) 표기. */
export function formatBidirectionalLanguagePair(fromLang: string, toLang: string): string {
    const from = getLangLabelText(fromLang as LangCode);
    const to = getLangLabelText(toLang as LangCode);
    return `${from} ⇄ ${to}`;
}

/** @deprecated formatBidirectionalLanguagePair 사용 */
export function formatTestLanguagePair(fromLang: string, toLang: string): string {
    return formatBidirectionalLanguagePair(fromLang, toLang);
}

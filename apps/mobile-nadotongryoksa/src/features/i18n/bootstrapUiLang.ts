/**
 * 앱 최초 실행(다운로드 직후) UI 언어 — GPS/프로필 로드 전 동기 추정.
 * 단말 로케일 → 언어코드, 미지원이면 로케일 국가 → resolveLangFromCountryOrEnglish.
 */
import { resolveLangFromCountryOrEnglish } from '../country/countryLanguage';
import { isSupportedLangCode, type LangCode } from '../language/languageCatalog';
import { resolveLocaleCountryCode } from '../profile/profileFormatters';

function localeTagToLang(locale: string): LangCode | null {
    const parts = String(locale || '').trim().split(/[-_]/);
    const lang = (parts[0] || '').toLowerCase();
    const region = (parts[1] || '').toUpperCase();
    if (lang === 'zh') {
        if (region === 'TW' || region === 'HANT') return 'zh-tw';
        if (region === 'HK' || region === 'MO') return 'zh-hk';
        return 'zh';
    }
    if (isSupportedLangCode(lang)) {
        return lang;
    }
    return null;
}

/** 프로필·AsyncStorage 없이 첫 프레임에 쓸 UI 언어(한국어 기본값 회피). */
export function resolveBootstrapUiLang(): LangCode {
    try {
        const locale = Intl.DateTimeFormat().resolvedOptions().locale || '';
        const fromLocale = localeTagToLang(locale);
        if (fromLocale) {
            return fromLocale;
        }
    } catch {
        // Intl 미지원 환경
    }
    const country = resolveLocaleCountryCode();
    return resolveLangFromCountryOrEnglish(country);
}

/**
 * UI 표시 언어 SSOT — 서비스 국가(country_code)가 화면·카탈로그 표기를 결정한다.
 * preferred_language 는 fromLang(통역 파이프라인) 전용이며 UI 표시에 쓰지 않는다.
 */
import { getUiText } from '../../app/appUiText';
import { isSupportedLangCode, type LangCode } from '../language/languageCatalog';
import {
    getEffectiveUiLang,
    localizeUiString,
    prefetchUiStrings,
    setProfileCountryCode,
    setProfileUiLangOverride,
    setUiLang,
} from './uiI18n';
import { resolveProfileDisplayLang } from './profileDisplayLocale';

const HANGUL_RE = /[\uAC00-\uD7A3\u1100-\u11FF\u3130-\u318F]/;

export function setProfileDisplayLangOverride(lang: LangCode | null): void {
    setProfileUiLangOverride(lang);
}

/** 카탈로그·설정 화면이 공유하는 표시 언어 — 서비스 국가 기준. */
export function getEffectiveDisplayLang(): LangCode {
    const raw = getEffectiveUiLang();
    return normalizeDisplayLang(raw);
}

export function normalizeDisplayLang(lang: string | null | undefined): LangCode {
    const norm = String(lang || 'ko').trim().toLowerCase();
    return isSupportedLangCode(norm) ? (norm as LangCode) : 'ko';
}

/** 서비스 국가 변경 시 UI 표시 언어·전역 Text 패치 동기화. */
export async function syncUiLangFromCountry(countryCode: string | null | undefined): Promise<LangCode> {
    const cc = String(countryCode || 'KR').trim().toUpperCase();
    setProfileCountryCode(cc);
    setProfileUiLangOverride(null);
    const displayLang = resolveProfileDisplayLang(cc);
    await setUiLang(displayLang);
    void prefetchUiStrings();
    return normalizeDisplayLang(displayLang);
}

/** uiLang AsyncStorage 캐시 로드 + tick — 전역 패치가 새 언어로 치환한다. */
export async function syncUiLang(lang: string | null | undefined): Promise<LangCode> {
    const safe = normalizeDisplayLang(lang);
    await setUiLang(safe);
    void prefetchUiStrings();
    return safe;
}

/** 화면 표시용 UI 사전 — 정적 카탈로그 우선, 한글 잔여분만 런타임 번역. */
export function getDisplayUiText() {
    const lang = getEffectiveDisplayLang();
    const raw = getUiText(lang);
    if (lang === 'ko') {
        return raw;
    }
    const localized = { ...raw };
    (Object.keys(localized) as Array<keyof typeof localized>).forEach((key) => {
        const value = localized[key];
        if (typeof value === 'string' && HANGUL_RE.test(value)) {
            localized[key] = localizeUiString(value);
        }
    });
    return localized;
}

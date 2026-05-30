'use client';

/**
 * useHelpLanguage — 도움말 언어 해결 훅
 *
 * 우선순위:
 * 1. localStorage에 저장된 사용자 수동 선택 언어
 * 2. 로그인 사용자의 native_language (프로필 데이터)
 * 3. 로그인 사용자의 country → COUNTRY_LANG_MAP 매핑
 * 4. 브라우저 언어
 * 5. 기본값 'ko'
 *
 * 범위: 모바일 웹앱 시각적 사용설명 전용 (전체 UI 번역 아님)
 */

import { useCallback, useEffect, useState } from 'react';

const STORAGE_KEY = 'worldlinco_help_lang';
const DEFAULT_LANG = 'ko';

/** ISO 3166-1 alpha-2 → 도움말 기본 언어 코드 */
const COUNTRY_TO_HELP_LANG: Record<string, string> = {
    KR: 'ko',
    US: 'en', GB: 'en', AU: 'en', CA: 'en', NZ: 'en', IE: 'en', SG: 'en', IN: 'en',
    CN: 'zh',
    TW: 'zh-tw', HK: 'zh-tw', MO: 'zh-tw',
    JP: 'ja',
    ES: 'es', MX: 'es', AR: 'es', CO: 'es', CL: 'es', PE: 'es', VE: 'es', EC: 'es',
    FR: 'fr', BE: 'fr', MC: 'fr',
    DE: 'de', AT: 'de',
    BR: 'pt', PT: 'pt',
    RU: 'ru', BY: 'ru',
    SA: 'ar', AE: 'ar', EG: 'ar', IQ: 'ar', MA: 'ar', DZ: 'ar', TN: 'ar', JO: 'ar', KW: 'ar', QA: 'ar',
    NP: 'hi',
    IT: 'it',
    TR: 'tr',
    VN: 'vi',
    TH: 'th',
    ID: 'id',
    MY: 'ms',
};

function normalizeLangCode(code: string | undefined | null): string | null {
    if (!code) return null;
    const lower = code.toLowerCase().trim();
    // Normalize language codes:
    // - Simplified Chinese variants (zh-cn, zh-hans) → 'zh'
    // - Traditional Chinese variants (zh-tw, zh-hant, zh-hk) → 'zh-tw'
    // - All other regional tags are reduced to base code (e.g. 'en-US' → 'en', 'pt-BR' → 'pt')
    if (lower === 'zh-cn' || lower === 'zh-hans') return 'zh';
    if (lower === 'zh-tw' || lower === 'zh-hant' || lower === 'zh-hk') return 'zh-tw';
    // keep full code if it's a known compound (e.g. 'zh-tw' already handled above)
    const base = lower.split('-')[0];
    return base || null;
}

function getBrowserLanguage(): string {
    if (typeof window === 'undefined') return DEFAULT_LANG;
    const lang = navigator.language || (navigator as any).userLanguage || '';
    return normalizeLangCode(lang) || DEFAULT_LANG;
}

export interface HelpLanguageUserProfile {
    native_language?: string | null;
    country?: string | null;
}

export interface UseHelpLanguageResult {
    /** Currently resolved help language code */
    helpLang: string;
    /** Set help language manually (persisted to localStorage) */
    setHelpLang: (lang: string) => void;
    /** Clear manual override so auto-resolution takes effect */
    clearHelpLangOverride: () => void;
    /** Whether the current selection is a manual override */
    isManualOverride: boolean;
}

/**
 * Resolves the best help language to display for the given user profile.
 * Call inside the page component and pass the loaded userInfo.
 */
export function useHelpLanguage(
    userProfile?: HelpLanguageUserProfile | null,
): UseHelpLanguageResult {
    const [manualLang, setManualLangState] = useState<string | null>(() => {
        if (typeof window === 'undefined') return null;
        return localStorage.getItem(STORAGE_KEY) || null;
    });

    // Re-read from storage on mount (handles SSR → client hydration)
    useEffect(() => {
        const stored = localStorage.getItem(STORAGE_KEY);
        setManualLangState(stored || null);
    }, []);

    const setHelpLang = useCallback((lang: string) => {
        localStorage.setItem(STORAGE_KEY, lang);
        setManualLangState(lang);
    }, []);

    const clearHelpLangOverride = useCallback(() => {
        localStorage.removeItem(STORAGE_KEY);
        setManualLangState(null);
    }, []);

    // Derive resolved language
    let helpLang: string = DEFAULT_LANG;

    if (manualLang) {
        // 1. Manual override wins
        helpLang = manualLang;
    } else if (userProfile?.native_language) {
        // 2. User's native language from signup/profile
        helpLang = normalizeLangCode(userProfile.native_language) ?? DEFAULT_LANG;
    } else if (userProfile?.country) {
        // 3. Country → default language mapping
        const countryUpper = userProfile.country.toUpperCase();
        helpLang = COUNTRY_TO_HELP_LANG[countryUpper] ?? getBrowserLanguage();
    } else {
        // 4. Browser language fallback
        helpLang = getBrowserLanguage();
    }

    return {
        helpLang,
        setHelpLang,
        clearHelpLangOverride,
        isManualOverride: manualLang !== null,
    };
}

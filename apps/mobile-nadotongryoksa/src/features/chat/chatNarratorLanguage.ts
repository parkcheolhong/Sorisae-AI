/**
 * 채팅 서버 음성(내레이터) 언어 결정 SSOT.
 * 우선순위: 사용자 선호 언어 → 서비스 국가 대표 언어 → 뷰어 출력 언어 → 한국어.
 */
import { resolveLangFromCountryOrEnglish } from '../country/countryLanguage';
import { isSupportedLangCode, type LangCode } from '../language/languageCatalog';

export type ChatNarratorInput = {
    countryCode?: string | null;
    preferredLanguage?: string | null;
    viewerOutputLang?: string | null;
};

export function resolveChatNarratorLang(input: ChatNarratorInput): LangCode {
    const preferred = String(input.preferredLanguage ?? '').trim().toLowerCase();
    if (preferred && isSupportedLangCode(preferred)) {
        return preferred as LangCode;
    }
    const fromCountry = resolveLangFromCountryOrEnglish(String(input.countryCode ?? '').trim().toUpperCase());
    if (fromCountry && isSupportedLangCode(fromCountry)) {
        return fromCountry;
    }
    const viewerOutput = String(input.viewerOutputLang ?? '').trim().toLowerCase();
    if (viewerOutput && isSupportedLangCode(viewerOutput)) {
        return viewerOutput as LangCode;
    }
    return 'ko';
}
